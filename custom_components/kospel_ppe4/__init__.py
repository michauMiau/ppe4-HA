"""KOSPEL PPE4 water heater integration."""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
import time
from dataclasses import dataclass

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_validation as cv

from .const import DEFAULT_FLOW_INTERVAL, DEFAULT_SCAN_INTERVAL, DEFAULT_STATS_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class Ppe4RuntimeData:
    """Runtime data stored on the config entry (HA 2024+ pattern)."""

    api: "Ppe4Api"
    coordinator: "Ppe4Coordinator"


class Ppe4Api:
    """Minimal HTTP client for the KOSPEL PPE4 REST API."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host
        self._session = session
        # The heater's HTTP server drops parallel connections: one request at a time.
        self._lock = asyncio.Lock()

    async def read(self, start: int, count: int) -> dict[int, int]:
        url = f"http://{self._host}/api/{start}/{count}"
        async with self._lock, self._session.get(
            url, headers={"User-Agent": "KOSPEL RESTClient/1.0"}, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        if data.get("status") != "OK":
            raise UpdateFailed(f"PPE4 error {data.get('status_value')}: {data.get('status_msg')}")
        return {int(k): v for k, v in data["res"].items()}

    async def write(self, register: int, value: int) -> None:
        url = f"http://{self._host}/api/write"
        async with self._lock, self._session.post(
            url,
            json={str(register): value},
            headers={"User-Agent": "KOSPEL RESTClient/1.0"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        if data.get("status") != "OK":
            raise UpdateFailed(f"Write failed {data.get('status_value')}: {data.get('status_msg')}")


class Ppe4Coordinator(DataUpdateCoordinator[dict[int, int]]):
    """Poll the heater for all known registers.

    Live block (1128+, temperatures/flow/power) is refreshed at the live interval,
    faster while water is flowing; slow blocks (limits, profiles, statistics) at
    the statistics interval.
    """

    # (start, count) blocks we care about — max 48 registers per request.
    # Only ranges that exist on the device: a request touching an unmapped
    # register (e.g. 1440-1447, 1568-1570) returns broken JSON.
    LIVE_BLOCKS = ((1128, 25),)
    SLOW_BLOCKS = (
        (1000, 44),
        (1388, 8),
        (1448, 4),   # energy: today
        (1512, 32),  # energy: 7 days, year, previous year, total, months
        (1576, 4),   # water: today
        (1640, 32),  # water: 7 days, year, previous year, total, months
    )

    def __init__(
        self,
        hass: HomeAssistant,
        api: Ppe4Api,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        flow_interval: int = DEFAULT_FLOW_INTERVAL,
        stats_interval: int = DEFAULT_STATS_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_dt.timedelta(seconds=scan_interval),
        )
        self.api = api
        self._idle_interval = _dt.timedelta(seconds=scan_interval)
        # While water is flowing, poll faster so short draws show up in flow and power.
        self._flow_interval = min(_dt.timedelta(seconds=flow_interval), self._idle_interval)
        self._stats_interval = stats_interval
        self._last_slow = 0.0

    async def _async_update_data(self) -> dict[int, int]:
        now = time.monotonic()
        slow_due = now - self._last_slow > self._stats_interval - 2
        blocks = list(self.LIVE_BLOCKS)
        if slow_due:
            blocks += list(self.SLOW_BLOCKS)

        # The device's HTTP server is flaky under load: a single dropped
        # connection must never take down the whole coordinator, otherwise
        # every entity goes unavailable (and setup fails on first refresh).
        results: list[dict[int, int] | Exception] = []
        for start, count in blocks:
            try:
                results.append(await self.api.read(start, count))
            except Exception as err:  # noqa: BLE001 - one failed block must not drop the others
                results.append(err)

        # Carry over previously read registers; successful reads overwrite.
        merged: dict[int, int] = dict(self.data or {})
        ok = 0
        for res in results:
            if isinstance(res, BaseException):
                _LOGGER.warning("PPE4 read failed: %s", res)
                continue
            assert isinstance(res, dict)
            merged.update(res)
            ok += 1

        if ok == 0:
            raise UpdateFailed("all register reads failed")
        if slow_due:
            self._last_slow = now
        drawing = merged.get(1137, 0) > 0 or merged.get(1138, 0) > 0
        # pylint: disable-next=attribute-defined-outside-init  # defined by DataUpdateCoordinator
        self.update_interval = self._flow_interval if drawing else self._idle_interval
        return merged


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    session = async_get_clientsession(hass)
    api = Ppe4Api(host, session)
    coordinator = Ppe4Coordinator(
        hass,
        api,
        int(entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)),
        int(entry.options.get("flow_interval", DEFAULT_FLOW_INTERVAL)),
        int(entry.options.get("stats_interval", DEFAULT_STATS_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = Ppe4RuntimeData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


# NOTE: Auto-discovery was removed — KOSPEL PPE4 heaters don't implement mDNS/zeroconf.
# Manual IP entry via config flow is the only setup path.

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True

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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
]

SCAN_INTERVAL = 30

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

    async def read(self, start: int, count: int) -> dict[int, int]:
        url = f"http://{self._host}/api/{start}/{count}"
        async with self._session.get(
            url, headers={"User-Agent": "KOSPEL RESTClient/1.0"}, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        if data.get("status") != "OK":
            raise UpdateFailed(f"PPE4 error {data.get('status_value')}: {data.get('status_msg')}")
        return {int(k): v for k, v in data["res"].items()}

    async def write(self, register: int, value: int) -> None:
        url = f"http://{self._host}/api/write"
        async with self._session.post(
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

    Live block (1128+, temperatures/flow/power) is refreshed every 5 s to match
    the official app; slow blocks (limits, profiles, statistics) every 30 s.
    """

    # (start, count) blocks we care about — max 48 registers per request
    LIVE_BLOCKS = ((1128, 25),)
    SLOW_BLOCKS = ((1000, 44), (1388, 8), (1390, 6), (1510, 14), (1520, 48), (1576, 48))
    # Water-month counter pair 1644/1645 sits just past SLOW_BLOCKS coverage;
    # poll it explicitly so the water_month sensor is never "unavailable".
    WATER_MONTH_BLOCK = ((1640, 8),)

    def __init__(self, hass: HomeAssistant, api: Ppe4Api, scan_interval: int = 5) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_dt.timedelta(seconds=scan_interval),
        )
        self.api = api
        self._last_slow = 0.0

    async def _async_update_data(self) -> dict[int, int]:
        now = time.monotonic()
        slow_due = now - self._last_slow > SCAN_INTERVAL - 2
        blocks = list(self.LIVE_BLOCKS)
        if slow_due:
            blocks += list(self.SLOW_BLOCKS + self.WATER_MONTH_BLOCK)

        # The device's HTTP server is flaky under load: a single dropped
        # connection must never take down the whole coordinator, otherwise
        # every entity goes unavailable (and setup fails on first refresh).
        results = await asyncio.gather(
            *(self.api.read(s, c) for s, c in blocks),
            return_exceptions=True,
        )

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
        return merged


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    session = async_get_clientsession(hass)
    api = Ppe4Api(host, session)
    interval = int(entry.options.get("scan_interval", 5))
    coordinator = Ppe4Coordinator(hass, api, interval)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = Ppe4RuntimeData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


# NOTE: Auto-discovery was removed — KOSPEL PPE4 heaters don't implement mDNS/zeroconf.
# Manual IP entry via config flow is the only setup path.

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True

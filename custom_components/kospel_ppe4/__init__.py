"""KOSPEL PPE4 water heater integration."""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
import time
from dataclasses import dataclass

import aiohttp

from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.BINARY_SENSOR, Platform.CLIMATE]

SCAN_INTERVAL = 30


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
    SLOW_BLOCKS = ((1000, 44), (1390, 6), (1520, 48), (1576, 48), (1624, 26))

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
        merged: dict[int, int] = {}
        try:
            live = await asyncio.gather(*(self.api.read(s, c) for s, c in self.LIVE_BLOCKS))
            now = time.monotonic()
            if now - self._last_slow > SCAN_INTERVAL - 2:  # slow refresh due
                slow = await asyncio.gather(*(self.api.read(s, c) for s, c in self.SLOW_BLOCKS))
                self._last_slow = now
                for res in slow:
                    merged.update(res)
            else:
                # reuse previous slow values
                merged.update(self.data or {})
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        for res in live:
            merged.update(res)
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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


@callback
async def _discovery_scan(hass: HomeAssistant) -> None:
    """One background scan; starts a discovery flow for each new heater."""
    from .config_flow import async_discover_heaters

    for host in await async_discover_heaters(hass):
        # skip already-configured heaters
        if any(
            e.data.get(CONF_HOST) == host
            for e in hass.config_entries.async_entries(DOMAIN)
        ):
            continue
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_DISCOVERY},
                data={"host": host},
            )
        )


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Run a discovery scan shortly after HA start, then every 10 minutes."""
    from homeassistant.helpers.event import async_track_time_interval

    def _schedule(now=None) -> None:  # noqa: ARG001 - time callback signature
        hass.async_create_task(_discovery_scan(hass))

    hass.loop.call_soon_threadsafe(_schedule)
    async_track_time_interval(hass, _schedule, _dt.timedelta(minutes=10))
    _LOGGER.info("KOSPEL PPE4 discovery scheduled every 10 min")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

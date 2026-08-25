"""KOSPEL PPE4 water heater integration."""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

SCAN_INTERVAL = 30


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
    """Poll the heater for all known registers."""

    # (start, count) blocks we care about
    BLOCKS = ((1000, 44), (1128, 25), (1390, 6), (1520, 48), (1576, 64))

    def __init__(self, hass: HomeAssistant, api: Ppe4Api) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_dt.timedelta(seconds=SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[int, int]:
        merged: dict[int, int] = {}
        try:
            results = await asyncio.gather(*(self.api.read(s, c) for s, c in self.BLOCKS))

        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        for res in results:
            merged.update(res)
        return merged


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    session = async_get_clientsession(hass)
    api = Ppe4Api(host, session)
    coordinator = Ppe4Coordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api, "coordinator": coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


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
                context={"source": config_entries.SOURCE_DISCOVERY},
                data={"host": host},
            )
        )


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Run a discovery scan shortly after HA start, then every 10 minutes."""
    from homeassistant.helpers.event import async_track_time_interval

    def _schedule(now=None) -> None:
        hass.async_create_task(_discovery_scan(hass))

    async_track_time_interval(hass, _schedule, _dt.timedelta(minutes=10))
    _LOGGER.info("KOSPEL PPE4 discovery scheduled every 10 min")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload

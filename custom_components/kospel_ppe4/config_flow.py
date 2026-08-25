"""Config flow for KOSPEL PPE4.

Discovery runs automatically in the background and any found heater shows up
as a discovered entry ("Discovered! Click to configure") without user input.
The manual form is a plain IP field only.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class CannotConnect(Exception):
    """Heater unreachable."""


async def _check_host(session, host: str) -> bool:
    try:
        async with session.get(f"http://{host}/api/1390/1", timeout=8) as resp:
            data = await resp.json(content_type=None)
            return isinstance(data, dict) and data.get("status") == "OK"
    except Exception:  # noqa: BLE001
        return False


async def _validate_and_create(hass: HomeAssistant, flow, host: str):
    """Shared validation + entry creation for both flows."""
    session = async_get_clientsession(hass)
    if not await _check_host(session, host):
        raise CannotConnect
    await flow.async_set_unique_id(f"{DOMAIN}_{host}")
    flow._abort_if_unique_id_configured()
    return flow.async_create_entry(title=f"KOSPEL PPE4 ({host})", data={CONF_HOST: host})


async def async_discover_heaters(hass) -> list[str]:
    """Background network scan used by the discovery coordinator."""
    from .discovery import discover

    try:
        found = await discover(hass)
        return list(found)
    except Exception:  # noqa: BLE001
        return []


class KospelPpe4ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle both automatic discovery and manual IP setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KospelPpe4OptionsFlow(config_entry)

    # ---- automatic discovery -------------------------------------------------
    async def async_step_discovery(self, discovery_info) -> Any:
        """Entry point when the background scanner finds a heater."""
        host = discovery_info["host"]
        await self.async_set_unique_id(f"{DOMAIN}_{host}")
        self._abort_if_unique_id_configured()
        self._host = host
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> Any:
        if user_input is not None:
            return self.async_create_entry(
                title=f"KOSPEL PPE4 ({self._host})", data={CONF_HOST: self._host}
            )
        self._set_confirm_only()
        return self.async_show_form(step_id="confirm")

    # ---- manual setup from "Add Integration" ---------------------------------
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        host = None
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            try:
                return await _validate_and_create(self.hass, self, host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_DATA_SCHEMA,
            errors=errors,
        )


class KospelPpe4OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init")

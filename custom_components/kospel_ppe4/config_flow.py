"""Config flow for KOSPEL PPE4.

Manual IP entry only — KOSPEL PPE4 heaters don't implement mDNS/zeroconf.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
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
    except Exception:  # noqa: BLE001 - any network/parse error means unreachable
        return False


class KospelPpe4ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle manual IP setup from 'Add Integration'."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import KospelPpe4OptionsFlow  # noqa: PLC0415
        return KospelPpe4OptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        host = None
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            session = async_get_clientsession(self.hass)
            if await _check_host(session, host):
                await self.async_set_unique_id(f"{DOMAIN}_{host}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"KOSPEL PPE4 ({host})", data={CONF_HOST: host}
                )
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_DATA_SCHEMA,
            errors=errors,
        )

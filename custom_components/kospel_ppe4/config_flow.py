"""Config flow to add a KOSPEL PPE4 heater by IP, with network discovery."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .discovery import discover

STEP_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


async def _check_host(session, host: str) -> bool:
    try:
        async with session.get(f"http://{host}/api/1390/1", timeout=8) as resp:
            data = await resp.json(content_type=None)
            return isinstance(data, dict) and data.get("status") == "OK"
    except Exception:  # noqa: BLE001
        return False


class KospelPpe4ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            session = async_get_clientsession(self.hass)
            if await _check_host(session, host):
                await self.async_set_unique_id(DOMAIN + "_" + host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"KOSPEL PPE4 ({host})", data={CONF_HOST: host})
            errors["base"] = "cannot_connect"

        # show discovered devices (if any) above the manual entry form
        data_schema = STEP_DATA_SCHEMA
        description_placeholders = {"found": "—"}
        if not user_input:
            try:
                self._discovered = await discover(self.hass)
            except Exception:  # noqa: BLE001
                self._discovered = {}
            if self._discovered:
                hosts = list(self._discovered)
                data_schema = vol.Schema({vol.Required(CONF_HOST, default=hosts[0]): vol.In(hosts)})
                description_placeholders["found"] = ", ".join(
                    f"{ip} ({name})" for ip, name in self._discovered.items()
                )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KospelPpe4OptionsFlow(config_entry)


class KospelPpe4OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init")

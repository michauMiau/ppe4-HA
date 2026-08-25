"""Config flow to add a KOSPEL PPE4 heater by IP."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback

from .const import DOMAIN

STEP_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class KospelPpe4ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            ok = False
            try:
                import aiohttp

                session = aiohttp.async_get_clientsession(self.hass)
                async with session.get(
                    f"http://{host}/api/1390/1", timeout=aiohttp.ClientTimeout(total=8)
                ) as resp:
                    data = await resp.json(content_type=None)
                    ok = data.get("status") == "OK"
            except Exception:  # noqa: BLE001
                ok = False
            if ok:
                return self.async_create_entry(title=f"KOSPEL PPE4 ({host})", data={CONF_HOST: host})
            errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", data_schema=STEP_DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KospelPpe4OptionsFlow(config_entry)


class KospelPpe4OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_show_form(step_id="init")

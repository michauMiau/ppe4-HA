"""Options flow: let the user change the heater's IP and scan interval."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required("scan_interval", default=5): vol.All(vol.Coerce(int), vol.Range(min=3, max=60)),
    }
)


class KospelPpe4OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.entry.options),
        )

"""Options flow: polling intervals (IP is set once during initial setup)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import DEFAULT_FLOW_INTERVAL, DEFAULT_SCAN_INTERVAL, DEFAULT_STATS_INTERVAL

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=60)
        ),
        vol.Required("flow_interval", default=DEFAULT_FLOW_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=60)
        ),
        vol.Required("stats_interval", default=DEFAULT_STATS_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=600)
        ),
    }
)


class KospelPpe4OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            # keep the existing host; only the intervals are configurable here
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, self.entry.options),
        )

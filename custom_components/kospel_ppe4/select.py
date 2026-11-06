"""Select platform for KOSPEL PPE4."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .registers import ACTIVE_PROFILE
from .sensor import Ppe4Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    async_add_entities([Ppe4ProfileSelect(coordinator, api, entry)])


class Ppe4ProfileSelect(Ppe4Entity, SelectEntity):
    """Active profile selector — register 1390 (0 = manual, 1..3 = profiles).

    Verified live: writing 1390 switches the profile and the device updates
    register 1140 (effective setpoint) to that profile's temperature.
    """

    _attr_translation_key = "profile"
    _attr_icon = "mdi:tune-variant"
    _attr_options = ["manual", "profile_1", "profile_2", "profile_3"]

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "profile")
        self._api = api

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.data.get(ACTIVE_PROFILE)
        if raw is not None and 0 <= raw < len(self._attr_options):
            return self._attr_options[raw]
        return None

    async def async_select_option(self, option: str) -> None:
        num = self._attr_options.index(option)
        await self._api.write(ACTIVE_PROFILE, num)
        self.coordinator.data[ACTIVE_PROFILE] = num
        await self.coordinator.async_request_refresh()

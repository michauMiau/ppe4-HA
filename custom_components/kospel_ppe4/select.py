"""Select platform for KOSPEL PPE4."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .sensor import Ppe4Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    async_add_entities([Ppe4ProfileSelect(coordinator, api, entry)])


class Ppe4ProfileSelect(Ppe4Entity, SelectEntity):
    """Active comfort profile selector — register 1389 (1..3).

    Verified live: writing 1389 switches the active profile and the device
    updates register 1140 (effective setpoint) to that profile's temperature.
    """

    _attr_translation_key = "profile"
    _attr_icon = "mdi:tune-variant"
    _attr_options = ["Profil 1", "Profil 2", "Profil 3"]

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "profile")
        self._api = api

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.data.get(1389)
        if raw in (1, 2, 3):
            return f"Profil {raw}"
        return None

    async def async_select_option(self, option: str) -> None:
        num = int(option.split()[-1])
        await self._api.write(1389, num)
        await self.coordinator.async_request_refresh()

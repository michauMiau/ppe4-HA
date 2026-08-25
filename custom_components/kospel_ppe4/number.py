"""Number entity to set the target temperature of KOSPEL PPE4."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sensor import Ppe4Entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Ppe4TargetTemp(data["coordinator"], data["api"], entry)])


class Ppe4TargetTemp(Ppe4Entity, NumberEntity):
    """Target temperature (register 1391)."""

    _attr_translation_key = "target_temperature"
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 5  # raw step 5 => 0.5 °C
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._api = api
        # sensible defaults from observed limits; refined from registers 1392/1395
        self._attr_native_min_value = 30
        self._attr_native_max_value = 70

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._update_limits()

    def _update_limits(self) -> None:
        d = self.coordinator.data or {}
        if 1392 in d and 1395 in d:
            self._attr_native_min_value = d[1392] / 10
            self._attr_native_max_value = d[1395] / 10

    @property
    def native_min_value(self) -> float:
        self._update_limits()
        return self._attr_native_min_value

    @property
    def native_max_value(self) -> float:
        self._update_limits()
        return self._attr_native_max_value

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.data.get(1391)
        return None if raw is None else raw / 10

    async def async_set_native_value(self, value: float) -> None:
        await self._api.write(1391, int(round(value * 10)))
        await self.coordinator.async_request_refresh()

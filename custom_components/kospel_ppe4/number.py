"""Number entities for KOSPEL PPE4.

- Target temperature: register 1140, only writable in manual mode (1390=1).
- Profiles 1-3: registers 1391/1392/1393, writable in profile mode.
"""
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
    coordinator = data["coordinator"]
    api = data["api"]
    async_add_entities([
        Ppe4TargetTemp(coordinator, api, entry),
        Ppe4Profile(coordinator, api, entry, 1391, "profile_1"),
        Ppe4Profile(coordinator, api, entry, 1392, "profile_2"),
        Ppe4Profile(coordinator, api, entry, 1393, "profile_3"),
    ])


class _Ppe4BaseNumber(Ppe4Entity, NumberEntity):
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 0.5
    _attr_icon = "mdi:water-boiler"

    def __init__(self, coordinator, api, entry: ConfigEntry,
                 register: int, key: str) -> None:
        super().__init__(coordinator, entry)
        self._api = api
        self._register = register
        self._attr_translation_key = key

    @property
    def native_min_value(self) -> float:
        d = self.coordinator.data or {}
        return d.get(1008, 300) / 10 if d else 30.0

    @property
    def native_max_value(self) -> float:
        d = self.coordinator.data or {}
        return d.get(1009, 600) / 10 if d else 60.0

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.data.get(self._register)
        return None if raw is None else raw / 10


class Ppe4TargetTemp(_Ppe4BaseNumber):
    """Setpoint in manual mode. Switches the heater to manual automatically."""

    async def async_set_native_value(self, value: float) -> None:
        await self._api.write(1390, 1)  # manual mode
        await self._api.write(1140, int(round(value * 10)))
        await self.coordinator.async_request_refresh()


class Ppe4Profile(_Ppe4BaseNumber):
    """One of the three temperature profiles (registers 1391..1393)."""

    async def async_set_native_value(self, value: float) -> None:
        await self._api.write(self._register, int(round(value * 10)))
        await self.coordinator.async_request_refresh()

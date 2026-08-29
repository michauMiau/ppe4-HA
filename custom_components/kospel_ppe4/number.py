"""Number entities for KOSPEL PPE4 — the five temperature profiles.

Profiles: registers 1391..1395 (×0.1 °C), limits read from 1008/1009.
The setpoint itself is exposed as a climate (thermostat) entity — see climate.py.
"""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .sensor import Ppe4Entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    async_add_entities([
        Ppe4Profile(coordinator, api, entry, register, f"profile_{register - 1390}")
        for register in range(1391, 1396)
    ])


class Ppe4Profile(Ppe4Entity, NumberEntity):
    """One of the five temperature profiles (registers 1391..1395)."""

    _attr_mode = None  # auto: box
    _attr_native_step = 1.0
    _attr_icon = "mdi:bookmark"

    def __init__(self, coordinator, api, entry: ConfigEntry,
                 register: int, key: str) -> None:
        super().__init__(coordinator, entry, key)
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

    async def async_set_native_value(self, value: float) -> None:
        await self._api.write(self._register, int(round(value * 10)))
        await self.coordinator.async_request_refresh()

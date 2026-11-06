"""Number entities for KOSPEL PPE4 — the three temperature profiles.

Profiles: registers 1392/1393/1394 (×0.1 °C), limits read from 1008/1009.
The setpoint itself is exposed as a climate (thermostat) entity — see climate.py.
"""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .registers import MANUAL_SETPOINT
from .sensor import Ppe4Entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    async_add_entities([
        Ppe4Profile(coordinator, api, entry, MANUAL_SETPOINT + 1, "profile_1"),
        Ppe4Profile(coordinator, api, entry, MANUAL_SETPOINT + 2, "profile_2"),
        Ppe4Profile(coordinator, api, entry, MANUAL_SETPOINT + 3, "profile_3"),
    ])


class Ppe4Profile(Ppe4Entity, NumberEntity):
    """One of the three temperature profiles (registers 1392..1394)."""

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
        raw = int(round(value * 10))
        await self._api.write(self._register, raw)
        self.coordinator.data[self._register] = raw
        await self.coordinator.async_request_refresh()

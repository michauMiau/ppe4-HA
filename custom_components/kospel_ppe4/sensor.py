"""Sensors for KOSPEL PPE4 — readings, energy and water meters."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities([
        Ppe4Sensor(coordinator, entry, 1134, "temp_in", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1),
        Ppe4Sensor(coordinator, entry, 1135, "temp_out", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1),
        Ppe4Sensor(coordinator, entry, 1140, "setpoint", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1),
        # Energy meter for the Energy Dashboard (register 1520 = month kWh ×1000)
        Ppe4Sensor(coordinator, entry, 1520, "energy_month", UnitOfEnergy.KILO_WATT_HOUR,
                   SensorDeviceClass.ENERGY, 0.001, state_class=SensorStateClass.TOTAL_INCREASING),
        # Water: today (1578, ×0.1 l) and this month (1644/1645 pair handled in coordinator merge)
        Ppe4Sensor(coordinator, entry, 1578, "water_today", UnitOfVolume.LITERS,
                   SensorDeviceClass.WATER, 0.1, state_class=SensorStateClass.TOTAL_INCREASING),
        Ppe4WaterMonth(coordinator, entry),
        Ppe4ModeSensor(coordinator, entry),
    ])


class Ppe4Entity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "KOSPEL PPE4",
            "manufacturer": "KOSPEL",
            "model": "PPE4",
        }


class Ppe4Sensor(Ppe4Entity, SensorEntity):
    def __init__(self, coordinator, entry, register: int, key: str, unit,
                 device_class, scale: float, state_class=None) -> None:
        super().__init__(coordinator, entry)
        self._register = register
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._scale = scale
        if state_class:
            self._attr_state_class = state_class

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._register in self.coordinator.data
        )

    @property
    def native_value(self):
        raw = self.coordinator.data.get(self._register)
        return None if raw is None else round(raw * self._scale, 2)


class Ppe4WaterMonth(Ppe4Entity, SensorEntity):
    """32-bit water-month counter from register pair 1644/1645 (×0.01 l)."""

    _attr_translation_key = "water_month"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        d = self.coordinator.data or {}
        lo, hi = d.get(1644), d.get(1645)
        if lo is None:
            return None
        return round((lo + (hi or 0) * 65536) / 100, 1)


class Ppe4ModeSensor(Ppe4Entity, SensorEntity):
    """Register 1390 — 0 = profile, 1 = manual."""

    _attr_translation_key = "mode"
    _MODES = {0: "profile", 1: "manual"}

    @property
    def native_value(self) -> str | None:
        raw = self.coordinator.data.get(1390)
        return None if raw is None else self._MODES.get(raw, str(raw))

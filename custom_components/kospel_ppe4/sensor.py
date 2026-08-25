"""Sensors for KOSPEL PPE4."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfVolumeFlowRate, UnitOfPower
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
        Ppe4Sensor(coordinator, entry, 1391, "Target temperature", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, scale=0.1),
        Ppe4Sensor(coordinator, entry, 1392, "Minimum setpoint", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, scale=0.1),
        Ppe4Sensor(coordinator, entry, 1393, "Limit low", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, scale=0.1),
        Ppe4Sensor(coordinator, entry, 1394, "Limit high", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, scale=0.1),
        Ppe4Sensor(coordinator, entry, 1395, "Maximum setpoint", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, scale=0.1),
        Ppe4Sensor(coordinator, entry, 1146, "Current power", UnitOfPower.WATT,
                   SensorDeviceClass.POWER, scale=10.0),
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
    def __init__(self, coordinator, entry, register: int, name: str,
                 unit: str | None = None, device_class=None, scale: float = 1.0) -> None:
        super().__init__(coordinator, entry)
        self._register = register
        self._attr_translation_key = f"reg_{register}"
        self._attr_native_value = None
        if unit:
            self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = device_class
        self._scale = scale

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._register in self.coordinator.data
        )

    @property
    def native_value(self):
        raw = self.coordinator.data.get(self._register)
        if raw is None:
            return None
        return round(raw * self._scale, 2)


class Ppe4ModeSensor(Ppe4Entity, SensorEntity):
    """Register 1390 — operating mode / profile."""

    _attr_translation_key = "mode"

    MODES = {0: "off", 1: "manual", 2: "eco", 3: "comfort", 4: "boost"}

    @property
    def native_value(self) -> str | None:
        raw = self.coordinator.data.get(1390)
        if raw is None:
            return None
        return str(raw)

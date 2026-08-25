"""Sensors for KOSPEL PPE4."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfPower
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
        Ppe4Sensor(coordinator, entry, 1143, "power_max", UnitOfPower.KILO_WATT,
                   None, 0.001),
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
    def __init__(self, coordinator, entry, register: int, key: str,
                 unit: str | None, device_class, scale: float) -> None:
        super().__init__(coordinator, entry)
        self._register = register
        self._attr_translation_key = key
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
        return None if raw is None else round(raw * self._scale, 2)


class Ppe4ModeSensor(Ppe4Entity, SensorEntity):
    """Register 1390 — 0 = profile, 1 = manual."""

    _attr_translation_key = "mode"
    _MODES = {0: "profile", 1: "manual"}

    @property
    def native_value(self) -> str | None:
        raw = self.coordinator.data.get(1390)
        return None if raw is None else self._MODES.get(raw, str(raw))

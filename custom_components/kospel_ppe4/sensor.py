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
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([
        Ppe4Sensor(coordinator, entry, 1134, "temp_in", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1),
        Ppe4Sensor(coordinator, entry, 1135, "temp_out", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1),
        # Live flow and power (non-zero only while heating)
        Ppe4Sensor(coordinator, entry, 1137, "flow", UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
                   None, 0.1, state_class=SensorStateClass.MEASUREMENT),
        Ppe4Sensor(coordinator, entry, 1138, "power_current", UnitOfPower.KILO_WATT,
                   SensorDeviceClass.POWER, 0.001, state_class=SensorStateClass.MEASUREMENT),
        # Energy meter for the Energy Dashboard (register 1520 = month kWh ×1000)
        Ppe4Sensor(coordinator, entry, 1520, "energy_month", UnitOfEnergy.KILO_WATT_HOUR,
                   SensorDeviceClass.ENERGY, 0.001, state_class=SensorStateClass.TOTAL_INCREASING),
        # Energy today: register 1510 = today kWh ×1000
        Ppe4Sensor(coordinator, entry, 1510, "energy_today", UnitOfEnergy.KILO_WATT_HOUR,
                   SensorDeviceClass.ENERGY, 0.001, state_class=SensorStateClass.TOTAL_INCREASING),
        # Water: today (1578, ×0.1 l) and this month (1644/1645 pair handled below)
        Ppe4Sensor(coordinator, entry, 1578, "water_today", UnitOfVolume.LITERS,
                   SensorDeviceClass.WATER, 0.1, state_class=SensorStateClass.TOTAL_INCREASING),
        Ppe4WaterMonth(coordinator, entry),
        Ppe4ModeSensor(coordinator, entry),
        Ppe4StatusSensor(coordinator, entry),
    ])


class Ppe4Entity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "KOSPEL PPE4",
            "manufacturer": "KOSPEL",
            "model": "PPE4",
            "entry_type": DeviceEntryType.SERVICE,
        }


class Ppe4Sensor(Ppe4Entity, SensorEntity):
    """Generic register-backed sensor."""

    # icons per translation key
    ICONS = {
        "flow": "mdi:water-pump",
        "power_current": "mdi:lightning-bolt",
        "energy_month": "mdi:calendar-month",
        "energy_today": "mdi:counter",
        "water_today": "mdi:cup-water",
    }

    def __init__(self, coordinator, entry, register: int, key: str, unit,
                 device_class, scale: float, state_class=None) -> None:  # noqa: PLR0913 - explicit config
        super().__init__(coordinator, entry, key)
        self._register = register
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if key in self.ICONS:
            self._attr_icon = self.ICONS[key]
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
    """32-bit water-month counter from register pair 1644/1645 (÷100 l)."""

    _attr_translation_key = "water_month"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "water_month")

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
    _attr_icon = "mdi:state-machine"
    _MODES = {0: "profile", 1: "manual"}

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "mode")

    @property
    def native_value(self) -> str | None:
        raw = self.coordinator.data.get(1390)
        return None if raw is None else self._MODES.get(raw, str(raw))


class Ppe4StatusSensor(Ppe4Entity, SensorEntity):
    """Raw status word (register 1129): 0=off, 1=idle/normal, 5=heating/pairing."""

    _attr_translation_key = "status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _STATES = {0: "off", 1: "idle", 5: "heating"}

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "status")

    @property
    def native_value(self) -> str | None:
        raw = self.coordinator.data.get(1129)
        return None if raw is None else self._STATES.get(raw, str(raw))

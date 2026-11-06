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
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .registers import (
    ENERGY_MONTHS,
    ENERGY_TODAY,
    ENERGY_TOTAL,
    ENERGY_YEAR,
    WATER_MONTHS,
    WATER_TODAY,
    WATER_TOTAL,
    WATER_YEAR,
    month_register,
    pair,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([
        Ppe4Sensor(coordinator, entry, 1134, "temp_in", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1, state_class=SensorStateClass.MEASUREMENT),
        Ppe4Sensor(coordinator, entry, 1135, "temp_out", UnitOfTemperature.CELSIUS,
                   SensorDeviceClass.TEMPERATURE, 0.1, state_class=SensorStateClass.MEASUREMENT),
        # Live flow and power (non-zero only while heating)
        Ppe4Sensor(coordinator, entry, 1137, "flow", UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
                   SensorDeviceClass.VOLUME_FLOW_RATE, 0.1, state_class=SensorStateClass.MEASUREMENT),
        Ppe4Sensor(coordinator, entry, 1138, "power_current", UnitOfPower.KILO_WATT,
                   SensorDeviceClass.POWER, 0.001, state_class=SensorStateClass.MEASUREMENT),
        # Lifetime meters for the Energy Dashboard — they never reset
        Ppe4Counter(coordinator, entry, ENERGY_TOTAL, "energy_total", UnitOfEnergy.KILO_WATT_HOUR,
                    SensorDeviceClass.ENERGY, 0.001),
        Ppe4Counter(coordinator, entry, WATER_TOTAL, "water_total", UnitOfVolume.LITERS,
                    SensorDeviceClass.WATER, 0.1),
        # Period counters kept by the heater (energy in Wh, water in 0.1 l)
        Ppe4Counter(coordinator, entry, ENERGY_TODAY, "energy_today", UnitOfEnergy.KILO_WATT_HOUR,
                    SensorDeviceClass.ENERGY, 0.001),
        Ppe4Counter(coordinator, entry, ENERGY_MONTHS, "energy_month", UnitOfEnergy.KILO_WATT_HOUR,
                    SensorDeviceClass.ENERGY, 0.001, monthly=True),
        Ppe4Counter(coordinator, entry, ENERGY_YEAR, "energy_year", UnitOfEnergy.KILO_WATT_HOUR,
                    SensorDeviceClass.ENERGY, 0.001),
        Ppe4Counter(coordinator, entry, WATER_TODAY, "water_today", UnitOfVolume.LITERS,
                    SensorDeviceClass.WATER, 0.1),
        Ppe4Counter(coordinator, entry, WATER_MONTHS, "water_month", UnitOfVolume.LITERS,
                    SensorDeviceClass.WATER, 0.1, monthly=True),
        Ppe4Counter(coordinator, entry, WATER_YEAR, "water_year", UnitOfVolume.LITERS,
                    SensorDeviceClass.WATER, 0.1),
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
        "water_total": "mdi:water",
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


class Ppe4Counter(Ppe4Sensor):
    """32-bit lo/hi counter; `monthly` picks the current month from a January-first block."""

    # pylint: disable-next=too-many-arguments
    def __init__(self, coordinator, entry, register: int, key: str, unit,
                 device_class, scale: float, monthly: bool = False) -> None:  # noqa: PLR0913 - explicit config
        super().__init__(coordinator, entry, register, key, unit, device_class, scale,
                         state_class=SensorStateClass.TOTAL_INCREASING)
        self._monthly = monthly

    def _raw(self) -> int | None:
        register = self._register
        if self._monthly:
            register = month_register(register, dt_util.now().month)
        return pair(self.coordinator.data or {}, register)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._raw() is not None

    @property
    def native_value(self):
        raw = self._raw()
        return None if raw is None else round(raw * self._scale, 3)


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

"""Climate (thermostat) entity for KOSPEL PPE4.

Register 1390 selects what the heater follows: 0 = the manual setpoint
(register 1391), 1..3 = a profile with its own setpoint (1391 + profile).
Register 1140 always shows the setpoint in effect (×0.1 °C).
Setting a temperature here does what the app does: it writes the manual
setpoint and switches to manual, leaving the profiles untouched.
Verified live on a 21/24 kW unit.
Current temperature = outlet (register 1135).
"""
from __future__ import annotations

import logging

import asyncio

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .registers import ACTIVE_PROFILE, MANUAL_SETPOINT, SETPOINT
from .sensor import Ppe4Entity

_LOGGER = logging.getLogger(__name__)

MIN_TEMP = 30.0
MAX_TEMP = 60.0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    async_add_entities([Ppe4Climate(coordinator, api, entry)])


class Ppe4Climate(Ppe4Entity, ClimateEntity):
    """Thermostat for the KOSPEL PPE4 water heater."""

    _attr_translation_key = "thermostat"
    _attr_icon = "mdi:thermostat"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "thermostat")
        self._api = api

    @property
    def min_temp(self) -> float:
        return (self.coordinator.data or {}).get(1008, MIN_TEMP * 10) / 10

    @property
    def max_temp(self) -> float:
        return (self.coordinator.data or {}).get(1009, MAX_TEMP * 10) / 10

    @property
    def current_temperature(self) -> float | None:
        raw = self.coordinator.data.get(1135)  # outlet
        return None if raw is None else raw / 10

    @property
    def target_temperature(self) -> float | None:
        raw = (self.coordinator.data or {}).get(SETPOINT)
        return None if raw is None else raw / 10

    @property
    def hvac_mode(self) -> HVACMode:
        # single fixed mode: the device has no real on/off via API
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        # Heating only when water is actually flowing and power is drawn;
        # status register alone (1129=5) also shows during WiFi pairing.
        flow = self.coordinator.data.get(1137, 0)
        power = self.coordinator.data.get(1138, 0)
        if power > 0 or flow > 0:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        temp = min(max(float(temp), self.min_temp), self.max_temp)
        value = int(round(temp * 10))
        await self._api.write(MANUAL_SETPOINT, value)
        if (self.coordinator.data or {}).get(ACTIVE_PROFILE) != 0:
            await self._api.write(ACTIVE_PROFILE, 0)
        # Small delay to let the device process the write before we
        # update our local state. This prevents a race condition where
        # the coordinator refreshes before the device has updated the
        # register, causing the old value to overwrite our new one.
        await asyncio.sleep(0.5)
        if self.coordinator.data is None:
            self.coordinator.data = {}
        self.coordinator.data.update({MANUAL_SETPOINT: value, ACTIVE_PROFILE: 0, SETPOINT: value})
        self.async_write_ha_state()

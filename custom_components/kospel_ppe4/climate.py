"""Climate (thermostat) entity for KOSPEL PPE4.

Temperature follows the ACTIVE PROFILE: register 1389 holds the profile
number (1..3), and each profile has its own setpoint register 1390+profile
(×0.1 °C). Writing the master setpoint 1388 is ignored by the device in
profile mode, so the thermostat reads the active profile and writes its
register directly. Verified live: writing the active profile's register
updates the effective setpoint (register 1140) immediately.
Current temperature = outlet (register 1135).
"""
from __future__ import annotations

import logging

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
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = 1.0
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "thermostat")
        self._api = api

    @property
    def current_temperature(self) -> float | None:
        raw = self.coordinator.data.get(1135)  # outlet
        return None if raw is None else raw / 10

    @property
    def target_temperature(self) -> float | None:
        d = self.coordinator.data or {}
        profile = d.get(1389)
        if profile is not None and 1 <= profile <= 3:
            raw = d.get(1390 + profile)
        else:
            raw = None
        if raw is None:
            raw = d.get(1140)  # effective setpoint (mirrors active profile)
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
        temp = min(max(float(temp), MIN_TEMP), MAX_TEMP)
        d = self.coordinator.data or {}
        profile = d.get(1389)
        if profile is not None and 1 <= profile <= 3:
            # Write the active profile's own setpoint register (1390+profile).
            # The master setpoint 1388 is ignored by the device in profile mode.
            register = 1390 + profile
        else:
            # Fallback: no known profile — use the master setpoint.
            register = 1388
        await self._api.write(register, int(round(temp * 10)))
        # Optimistic: immediately reflect the new setpoint in HA's cache so
        # the UI doesn't lag behind the physical heater's ramp.
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

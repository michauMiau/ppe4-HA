"""Climate (thermostat) entity for KOSPEL PPE4.

Register 1388 is the master setpoint (×0.1 °C): writing it propagates to
register 1140 and the active profile. Current temperature = outlet (1135).
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
        raw = self.coordinator.data.get(1388)
        if raw is None:
            raw = self.coordinator.data.get(1140)
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
        # Register 1388 is the master setpoint — the device propagates it
        # to 1140 and the active profile automatically.
        await self._api.write(1388, int(round(temp * 10)))
        await self.coordinator.async_request_refresh()

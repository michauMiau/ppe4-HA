"""Binary sensor and diagnostic attributes for KOSPEL PPE4 faults."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .errors import ERROR_BITS, WARNING_BITS, decode
from .registers import pair
from .sensor import Ppe4Entity

FAULT_REGISTERS = (1130, 1131, 1132, 1133)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([Ppe4FaultSensor(coordinator, entry)])


class Ppe4FaultSensor(Ppe4Entity, BinarySensorEntity):
    """ON when any fault register is non-zero."""

    _attr_translation_key = "fault"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "fault")

    @property
    def is_on(self) -> bool | None:
        d = self.coordinator.data or {}
        vals = [d.get(r) for r in FAULT_REGISTERS]
        if any(v is None for v in vals):
            return None
        return any(v != 0 for v in vals)

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data or {}
        error_word = pair(d, 1130)
        warning_word = pair(d, 1132)
        return {
            **{f"flag_{r}": d.get(r) for r in FAULT_REGISTERS},
            "status": d.get(1129),
            "device_code": d.get(1136),
            "error_word": error_word,
            "warning_word": warning_word,
            "errors": [] if error_word is None else decode(error_word, ERROR_BITS),
            "warnings": [] if warning_word is None else decode(warning_word, WARNING_BITS),
        }

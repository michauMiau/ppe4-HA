"""Binary sensors and diagnostics for KOSPEL PPE4 fault flags."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .sensor import Ppe4Entity

# Fault flag registers observed at 0 during normal operation.
# Meaning per flag is not yet confirmed — see ERRORS.md in the repo.
FAULT_REGISTERS = (1130, 1131, 1132, 1133)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities([Ppe4FaultSensor(coordinator, entry)])


class Ppe4FaultSensor(Ppe4Entity, BinarySensorEntity):
    """ON when any fault flag register is non-zero."""

    _attr_translation_key = "fault"
    _attr_device_class = None  # generic problem-style sensor
    _attr_icon = "mdi:alert-circle"

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
        attrs = {f"flag_{r}": d.get(r) for r in FAULT_REGISTERS}
        # status word: 1 = idle/normal, 5 = heating/pairing (see PROTOCOL.md)
        attrs["status"] = d.get(1129)
        attrs["device_code"] = d.get(1136)
        return attrs

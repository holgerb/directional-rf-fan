"""Diagnostic sensors for Directional RF Fan."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import device_info_for_entry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Directional RF Fan diagnostic sensors from a config entry."""
    async_add_entities(
        [
            DirectionalRfFanDirectionSensor(hass, entry),
            DirectionalRfFanCurrentStepSensor(hass, entry),
        ]
    )


class DirectionalRfFanDiagnosticSensor(SensorEntity):
    """Base class for diagnostic sensors backed by the linked fan entity."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the diagnostic sensor."""
        self.hass = hass
        self._entry = entry

    @property
    def available(self) -> bool:
        """Return whether the linked fan entity is available."""
        return self._fan is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Home Assistant device for this sensor."""
        return device_info_for_entry(self._entry)

    @property
    def _fan(self):
        """Return the linked Directional RF Fan entity."""
        return self.hass.data[DOMAIN]["entries"].get(self._entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to linked fan state updates."""
        if (fan := self._fan) is not None:
            self.async_on_remove(
                fan.async_add_state_update_callback(self.async_write_ha_state)
            )


class DirectionalRfFanDirectionSensor(DirectionalRfFanDiagnosticSensor):
    """Sensor that exposes the remembered airflow direction."""

    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the direction sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{entry.data[CONF_NAME]} Direction"
        self._attr_unique_id = f"{entry.entry_id}_direction"

    @property
    def native_value(self) -> str | None:
        """Return the remembered airflow direction."""
        if (fan := self._fan) is None:
            return None
        return fan.diagnostic_direction


class DirectionalRfFanCurrentStepSensor(DirectionalRfFanDiagnosticSensor):
    """Sensor that exposes the remembered physical fan step."""

    _attr_icon = "mdi:fan"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the current step sensor."""
        super().__init__(hass, entry)
        self._attr_name = f"{entry.data[CONF_NAME]} Current step"
        self._attr_unique_id = f"{entry.entry_id}_current_step"

    @property
    def native_value(self) -> int | None:
        """Return the remembered physical fan step."""
        if (fan := self._fan) is None:
            return None
        return fan.diagnostic_step

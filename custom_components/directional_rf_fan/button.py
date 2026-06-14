"""Button platform for Directional RF Fan."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import device_info_for_entry
from .const import DOMAIN, SPEED_COUNT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Directional RF Fan button entities from a config entry."""
    async_add_entities(
        [
            DirectionalRfFanRecalibrateButton(hass, entry),
            *[
                DirectionalRfFanLevelButton(hass, entry, level)
                for level in range(1, SPEED_COUNT + 1)
            ],
        ]
    )


class DirectionalRfFanRecalibrateButton(ButtonEntity):
    """Button that recalibrates the optimistic RF fan state."""

    _attr_icon = "mdi:sync"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the recalibrate button."""
        self.hass = hass
        self._entry = entry
        self._attr_name = f"{entry.data[CONF_NAME]} Recalibrate"
        self._attr_unique_id = f"{entry.entry_id}_recalibrate"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Home Assistant device for this button."""
        return device_info_for_entry(self._entry)

    async def async_press(self) -> None:
        """Recalibrate the linked fan entity."""
        fan = self.hass.data[DOMAIN]["entries"].get(self._entry.entry_id)
        if fan is None:
            raise HomeAssistantError("Linked Directional RF Fan entity is unavailable")
        await fan.async_recalibrate()


class DirectionalRfFanLevelButton(ButtonEntity):
    """Button that sets the optimistic RF fan to a fixed level in the remembered direction."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, level: int) -> None:
        """Initialize the fixed level button."""
        self.hass = hass
        self._entry = entry
        self._level = level
        self._attr_name = f"{entry.data[CONF_NAME]} Level {level}"
        self._attr_unique_id = f"{entry.entry_id}_level_{level}"
        self._attr_icon = f"mdi:numeric-{level}-box"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Home Assistant device for this button."""
        return device_info_for_entry(self._entry)

    async def async_press(self) -> None:
        """Set the linked fan entity to this level in the remembered direction."""
        fan = self.hass.data[DOMAIN]["entries"].get(self._entry.entry_id)
        if fan is None:
            raise HomeAssistantError("Linked Directional RF Fan entity is unavailable")
        await fan.async_set_level(self._level)

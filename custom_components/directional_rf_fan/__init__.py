"""Directional RF Fan integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CODE_SET_SOURCE_SLOT,
    COMMAND_PROFILE_A,
    COMMAND_PROFILE_COMMANDS,
    COMMAND_PROFILE_FREQUENCIES,
    COMMAND_PROFILE_PROTOCOLS,
    COMMAND_IN_MINUS,
    COMMAND_IN_PLUS,
    COMMAND_OUT_MINUS,
    COMMAND_OUT_PLUS,
    COMMAND_TO_CONF,
    CONF_CODE_SET_SOURCE,
    CONF_COMMAND_PROFILE,
    CONF_FAN_SLOT,
    CONF_FREQUENCY,
    CONF_REMOTE_ADDRESS,
    CONF_RF_PROTOCOL,
    DOMAIN,
    FAN_SLOT_REMOTE_ADDRESSES,
    PLATFORMS,
    PRESET_IN,
    PRESET_MODES,
    PRESET_OUT,
    STATIC_URL_PATH,
)
from .rf import build_fan_codes


type DirectionalRfFanConfigEntry = ConfigEntry[dict[str, object]]

SERVICE_SEND_COMMAND = "send_command"
SERVICE_STEP_UP = "step_up"
SERVICE_STEP_DOWN = "step_down"
SERVICE_RECALIBRATE = "recalibrate"

ATTR_COMMAND = "command"
ATTR_PRESET_MODE = "preset_mode"

SERVICE_SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_COMMAND): vol.In(sorted(COMMAND_TO_CONF)),
    }
)

SERVICE_STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_PRESET_MODE): vol.All(
            str, lambda value: normalize_preset_mode(value)
        ),
    }
)

SERVICE_RECALIBRATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_PRESET_MODE): vol.All(
            str, lambda value: normalize_preset_mode(value)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level services."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("entities", {})
    hass.data[DOMAIN].setdefault("entries", {})
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                STATIC_URL_PATH,
                str(Path(__file__).parent / "static"),
                cache_headers=False,
            )
        ]
    )

    async def async_get_entity(call: ServiceCall):
        entity_id = call.data[CONF_ENTITY_ID]
        entity = hass.data[DOMAIN]["entities"].get(entity_id)
        if entity is None:
            raise HomeAssistantError(f"Unknown Directional RF Fan entity: {entity_id}")
        return entity

    async def async_send_command(call: ServiceCall) -> None:
        entity = await async_get_entity(call)
        await entity.async_send_command(call.data[ATTR_COMMAND])

    async def async_step_up(call: ServiceCall) -> None:
        entity = await async_get_entity(call)
        await entity.async_step(1, call.data.get(ATTR_PRESET_MODE))

    async def async_step_down(call: ServiceCall) -> None:
        entity = await async_get_entity(call)
        await entity.async_step(-1, call.data.get(ATTR_PRESET_MODE))

    async def async_recalibrate(call: ServiceCall) -> None:
        entity = await async_get_entity(call)
        await entity.async_recalibrate(call.data.get(ATTR_PRESET_MODE))

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        async_send_command,
        schema=SERVICE_SEND_COMMAND_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STEP_UP,
        async_step_up,
        schema=SERVICE_STEP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STEP_DOWN,
        async_step_down,
        schema=SERVICE_STEP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECALIBRATE,
        async_recalibrate,
        schema=SERVICE_RECALIBRATE_SCHEMA,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: DirectionalRfFanConfigEntry
) -> bool:
    """Set up a Directional RF Fan config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(
    hass: HomeAssistant, entry: DirectionalRfFanConfigEntry
) -> bool:
    """Migrate old config entries."""
    if entry.version >= 2:
        return True

    data = dict(entry.data)
    if (
        data.get(CONF_CODE_SET_SOURCE) == CODE_SET_SOURCE_SLOT
        and str(data.get(CONF_FAN_SLOT)) == "2"
    ):
        address = FAN_SLOT_REMOTE_ADDRESSES["2"]
        profile = COMMAND_PROFILE_A
        data.update(build_fan_codes(address, COMMAND_PROFILE_COMMANDS[profile]))
        data.update(
            {
                CONF_COMMAND_PROFILE: profile,
                CONF_RF_PROTOCOL: COMMAND_PROFILE_PROTOCOLS[profile],
                CONF_FREQUENCY: COMMAND_PROFILE_FREQUENCIES[profile],
                CONF_REMOTE_ADDRESS: f"{address:04X}",
            }
        )

    hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: DirectionalRfFanConfigEntry
) -> bool:
    """Unload a Directional RF Fan config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def step_command_for_preset(preset_mode: str, direction: int) -> str:
    """Return the relative RF command for a preset and step direction."""
    preset_mode = normalize_preset_mode(preset_mode)
    if preset_mode == PRESET_IN:
        return COMMAND_IN_PLUS if direction > 0 else COMMAND_IN_MINUS
    if preset_mode == PRESET_OUT:
        return COMMAND_OUT_PLUS if direction > 0 else COMMAND_OUT_MINUS
    raise HomeAssistantError(f"Unsupported preset mode: {preset_mode}")


def normalize_preset_mode(preset_mode: str) -> str:
    """Normalize preset labels while accepting earlier lowercase values."""
    normalized = str(preset_mode).strip().casefold()
    if normalized == PRESET_IN.casefold():
        return PRESET_IN
    if normalized == PRESET_OUT.casefold():
        return PRESET_OUT
    raise vol.Invalid("preset_mode")


def device_info_for_entry(entry: ConfigEntry) -> DeviceInfo:
    """Return the shared Home Assistant device for one fan config entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=str(entry.data[CONF_NAME]),
        manufacturer="Directional RF Fan",
        model="433 MHz RF Fan",
    )

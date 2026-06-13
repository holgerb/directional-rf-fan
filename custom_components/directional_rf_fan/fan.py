"""Fan platform for Directional RF Fan."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.radio_frequency import async_send_command
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import device_info_for_entry, normalize_preset_mode, step_command_for_preset
from .const import (
    COMMAND_PROFILE_A,
    COMMAND_PROFILE_B,
    COMMAND_PROFILE_FREQUENCIES,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_SETTLE_TIME,
    COMMAND_TO_CONF,
    CONF_COMMAND_PROFILE,
    CONF_FREQUENCY,
    CONF_REPEATS,
    CONF_RF_PROTOCOL,
    CONF_TRANSMITTER,
    DOMAIN,
    PRESET_IN,
    PRESET_MODES,
    RECALIBRATE_STEPS,
    RF_PROTOCOL_OOK_PWM_420_1220,
    RF_PROTOCOL_RC_SWITCH_1,
    DEFAULT_FREQUENCY,
    SPEED_COUNT,
)
from .rf import build_rf_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Directional RF Fan entities from a config entry."""
    async_add_entities([DirectionalRfFan(hass, entry)])


class DirectionalRfFan(FanEntity):
    """Optimistic RF fan controlled through a radio_frequency transmitter."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.PRESET_MODE
    )
    _attr_speed_count = SPEED_COUNT
    _attr_preset_modes = PRESET_MODES

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the fan."""
        self.hass = hass
        self._entry = entry
        self._transmitter = entry.data[CONF_TRANSMITTER]
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = entry.entry_id
        self._attr_is_on = False
        self._attr_percentage = 0
        self._attr_preset_mode = PRESET_IN
        self._speed_level = 0

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Home Assistant device for this fan."""
        return device_info_for_entry(self._entry)

    async def async_added_to_hass(self) -> None:
        """Register the entity for integration services."""
        self.hass.data[DOMAIN]["entities"][self.entity_id] = self
        self.hass.data[DOMAIN]["entries"][self._entry.entry_id] = self
        transmitter_entity_id = er.async_validate_entity_id(
            er.async_get(self.hass), self._transmitter
        )

        @callback
        def _async_transmitter_state_changed(
            event: Event[EventStateChangedData],
        ) -> None:
            new_state = event.data["new_state"]
            self._attr_available = (
                new_state is not None and new_state.state != STATE_UNAVAILABLE
            )
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [transmitter_entity_id],
                _async_transmitter_state_changed,
            )
        )

        transmitter_state = self.hass.states.get(transmitter_entity_id)
        self._attr_available = (
            transmitter_state is not None
            and transmitter_state.state != STATE_UNAVAILABLE
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the entity for integration services."""
        self.hass.data[DOMAIN]["entities"].pop(self.entity_id, None)
        self.hass.data[DOMAIN]["entries"].pop(self._entry.entry_id, None)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn the fan on."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self.async_send_command(COMMAND_ON)
            self._attr_is_on = True
            self._speed_level = max(self._speed_level, 1)
            self._attr_percentage = self._level_to_percentage(self._speed_level)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_send_command(COMMAND_OFF)
        self._attr_is_on = False
        self._attr_percentage = 0
        self._speed_level = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the optimistic fan speed percentage using relative RF steps."""
        target_level = self._percentage_to_level(percentage)
        await self.async_set_level(target_level)

    async def async_set_level(self, target_level: int) -> None:
        """Set the optimistic fan speed to one physical fan level."""
        target_level = max(0, min(SPEED_COUNT, int(target_level)))
        if target_level == 0:
            await self.async_turn_off()
            return

        if not self._attr_is_on:
            await self.async_send_command(COMMAND_ON, wait_for_transmit=True)

        current_level = max(self._speed_level, 1)
        steps = target_level - current_level
        step_direction = 1 if steps > 0 else -1
        _LOGGER.debug(
            "%s changing speed from level %s to %s using %s RF step command(s)",
            self.entity_id,
            current_level,
            target_level,
            abs(steps),
        )
        for _ in range(abs(steps)):
            await self.async_send_step_command(
                step_direction, self._attr_preset_mode, wait_for_transmit=True
            )

        self._attr_is_on = True
        self._speed_level = target_level
        self._attr_percentage = self._level_to_percentage(target_level)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the airflow preset."""
        target_preset = normalize_preset_mode(preset_mode)
        if target_preset == self._attr_preset_mode:
            return

        if not self._attr_is_on or self._speed_level <= 0:
            self._attr_preset_mode = target_preset
            self.async_write_ha_state()
            return

        if self._speed_level >= SPEED_COUNT:
            sequence = (-1, 1)
        else:
            sequence = (1, -1)

        _LOGGER.debug(
            "%s changing preset from %s to %s at level %s",
            self.entity_id,
            self._attr_preset_mode,
            target_preset,
            self._speed_level,
        )
        for direction in sequence:
            await self.async_send_step_command(
                direction, target_preset, wait_for_transmit=True
            )

        self._attr_preset_mode = target_preset
        self._attr_percentage = self._level_to_percentage(self._speed_level)
        self.async_write_ha_state()

    async def async_step(self, direction: int, preset_mode: str | None = None) -> None:
        """Send a relative up/down command for the current or requested preset."""
        target_preset = (
            normalize_preset_mode(preset_mode)
            if preset_mode is not None
            else self._attr_preset_mode
        )
        await self.async_send_step_command(direction, target_preset)
        self._attr_is_on = True
        self._attr_preset_mode = target_preset
        self._speed_level = self._step_level(self._speed_level, direction)
        self._attr_percentage = self._level_to_percentage(self._speed_level)
        self.async_write_ha_state()

    async def async_recalibrate(self, preset_mode: str | None = None) -> None:
        """Force the RF fan into a known optimistic baseline state."""
        target_preset = (
            normalize_preset_mode(preset_mode)
            if preset_mode is not None
            else self._attr_preset_mode
        )
        _LOGGER.debug(
            "%s recalibrating %s with %s minus RF step command(s)",
            self.entity_id,
            target_preset,
            RECALIBRATE_STEPS,
        )
        for _ in range(RECALIBRATE_STEPS):
            await self.async_send_step_command(
                -1, target_preset, wait_for_transmit=True
            )

        self._attr_is_on = True
        self._attr_percentage = self._level_to_percentage(1)
        self._speed_level = 1
        self._attr_preset_mode = target_preset
        self.async_write_ha_state()

    async def async_send_step_command(
        self, direction: int, preset_mode: str, *, wait_for_transmit: bool = False
    ) -> None:
        """Send a relative up/down RF command for a preset."""
        command = step_command_for_preset(preset_mode, direction)
        await self.async_send_command(command, wait_for_transmit=wait_for_transmit)

    async def async_send_command(
        self, command: str, *, wait_for_transmit: bool = False
    ) -> None:
        """Send a configured RF command through the selected transmitter."""
        if command not in COMMAND_TO_CONF:
            raise HomeAssistantError(f"Unsupported RF command: {command}")

        repeats = int(self._entry.data[CONF_REPEATS])
        rf_command = build_rf_command(
            str(self._entry.data[COMMAND_TO_CONF[command]]),
            repeats=repeats,
            protocol=self._rf_protocol,
            frequency=self._rf_frequency,
        )
        _LOGGER.debug(
            "%s sending RF command %s via %s",
            self.entity_id,
            command,
            self._transmitter,
        )
        await async_send_command(
            self.hass, str(self._transmitter), rf_command, context=self._context
        )
        if wait_for_transmit:
            delay = self._transmit_delay(rf_command.get_raw_timings(), repeats)
            _LOGGER.debug(
                "%s waiting %.3fs after RF command %s before next step",
                self.entity_id,
                delay,
                command,
            )
            await asyncio.sleep(delay)

    @staticmethod
    def _percentage_to_level(percentage: int) -> int:
        """Map a Home Assistant percentage to the fan's six physical levels."""
        percentage = max(0, min(100, percentage))
        if percentage == 0:
            return 0
        return max(1, min(SPEED_COUNT, round(percentage * SPEED_COUNT / 100)))

    @staticmethod
    def _level_to_percentage(level: int) -> int:
        """Map a physical level back to a Home Assistant percentage."""
        if level <= 0:
            return 0
        return round(max(1, min(SPEED_COUNT, level)) * 100 / SPEED_COUNT)

    @staticmethod
    def _step_level(level: int, direction: int) -> int:
        """Move the optimistic level by one remote-control step."""
        current_level = max(level, 1)
        next_level = current_level + (1 if direction > 0 else -1)
        return max(1, min(SPEED_COUNT, next_level))

    @staticmethod
    def _transmit_delay(timings: list[int], repeats: int) -> float:
        """Estimate RF airtime plus a small button-like gap."""
        frame_seconds = sum(abs(timing) for timing in timings) / 1_000_000
        return frame_seconds * (repeats + 1) + COMMAND_SETTLE_TIME

    @property
    def _rf_protocol(self) -> str:
        """Return the configured RF protocol, inferring it for older entries."""
        protocol = self._entry.data.get(CONF_RF_PROTOCOL)
        if protocol is not None:
            return str(protocol)
        if self._entry.data.get(CONF_COMMAND_PROFILE) in {
            COMMAND_PROFILE_B,
        }:
            return RF_PROTOCOL_OOK_PWM_420_1220
        return RF_PROTOCOL_RC_SWITCH_1

    @property
    def _rf_frequency(self) -> int:
        """Return the configured RF frequency, inferring it for older entries."""
        frequency = self._entry.data.get(CONF_FREQUENCY)
        if frequency is not None:
            return int(frequency)
        profile = self._entry.data.get(CONF_COMMAND_PROFILE)
        if profile in COMMAND_PROFILE_FREQUENCIES:
            return COMMAND_PROFILE_FREQUENCIES[str(profile)]
        return DEFAULT_FREQUENCY

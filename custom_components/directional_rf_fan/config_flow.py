"""Config flow for the Directional RF Fan integration."""

from __future__ import annotations

import asyncio
from typing import Any

from rf_protocols import ModulationType
import voluptuous as vol

from homeassistant.components.radio_frequency import (
    async_get_transmitters,
    async_send_command,
)
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    CODE_SET_SOURCE_MANUAL,
    CODE_SET_SOURCE_SLOT,
    COMMAND_PROFILE_A,
    COMMAND_PROFILE_COMMANDS,
    CONF_CODE_IN_MINUS,
    CONF_CODE_IN_PLUS,
    CONF_CODE_OFF,
    CONF_CODE_ON,
    CONF_CODE_OUT_MINUS,
    CONF_CODE_OUT_PLUS,
    CONF_CODE_SET_SOURCE,
    CONF_COMMAND_PROFILE,
    CONF_FAN_SLOT,
    CONF_FREQUENCY,
    CONF_REMOTE_ADDRESS,
    CONF_REPEATS,
    CONF_RF_PROTOCOL,
    CONF_TRANSMITTER,
    DEFAULT_CODES,
    DEFAULT_FREQUENCY,
    DEFAULT_REPEATS,
    DOMAIN,
    FAN_SLOT_MANUAL,
    FAN_SLOT_OPTIONS,
    FAN_SLOT_REMOTE_ADDRESSES,
    LEARN_IMAGE_URL,
    RF_PROTOCOL_RC_SWITCH_1,
)
from .rf import (
    build_fan_codes,
    build_rf_command,
    code_to_bits,
    learning_repeats_for_code,
)

MENU_LEARN_SUCCESS = "learn_success"
MENU_LEARN_FAILED = "learn_failed"

SLOT_LABELS = {
    "1": "1 - Remote 1",
    "2": "2 - Remote 2",
    FAN_SLOT_MANUAL: "Manuell",
}


def _rf_code(value: Any) -> str:
    """Validate a binary or hex RF code."""
    value = str(value).strip()
    try:
        code_to_bits(value)
    except ValueError as err:
        raise vol.Invalid("rf_code") from err
    return value


class DirectionalRfFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Directional RF Fan."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize flow state."""
        self._base_data: dict[str, Any] = {}
        self._selected_slot: str | None = None
        self._candidate_data: dict[str, Any] | None = None
        self._learn_task: asyncio.Task[None] | None = None
        self._user_errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors = self._user_errors
        self._user_errors = {}

        transmitters_result = self._compatible_transmitters()
        if isinstance(transmitters_result, dict):
            return transmitters_result
        transmitters = transmitters_result

        if user_input is not None:
            registry = er.async_get(self.hass)
            transmitter = registry.async_get(user_input[CONF_TRANSMITTER])
            assert transmitter is not None

            self._base_data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_TRANSMITTER: transmitter.id,
                CONF_REPEATS: user_input[CONF_REPEATS],
            }
            self._selected_slot = user_input[CONF_FAN_SLOT]

            if self._selected_slot == FAN_SLOT_MANUAL:
                return await self.async_step_manual()

            self._candidate_data = self._build_slot_candidate(
                self._selected_slot,
            )
            return await self.async_step_learn_prepare()

        defaults = {
            CONF_NAME: "Directional RF Fan",
            CONF_REPEATS: DEFAULT_REPEATS,
            CONF_FAN_SLOT: "1",
        }

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
                vol.Required(
                    CONF_TRANSMITTER
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(include_entities=transmitters),
                ),
                vol.Required(CONF_REPEATS, default=defaults[CONF_REPEATS]): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=100)
                ),
                vol.Required(
                    CONF_FAN_SLOT, default=defaults[CONF_FAN_SLOT]
                ): vol.In({key: SLOT_LABELS[key] for key in FAN_SLOT_OPTIONS}),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle manual RF code entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                codes = {key: _rf_code(user_input[key]) for key in DEFAULT_CODES}
            except vol.Invalid:
                errors["base"] = "invalid_rf_code"
            else:
                self._candidate_data = {
                    **self._base_data,
                    **codes,
                    CONF_CODE_SET_SOURCE: CODE_SET_SOURCE_MANUAL,
                    CONF_FAN_SLOT: FAN_SLOT_MANUAL,
                    CONF_RF_PROTOCOL: RF_PROTOCOL_RC_SWITCH_1,
                    CONF_FREQUENCY: DEFAULT_FREQUENCY,
                }
                return await self.async_step_learn_prepare()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CODE_ON, default=DEFAULT_CODES[CONF_CODE_ON]): str,
                vol.Required(CONF_CODE_OFF, default=DEFAULT_CODES[CONF_CODE_OFF]): str,
                vol.Required(
                    CONF_CODE_OUT_PLUS, default=DEFAULT_CODES[CONF_CODE_OUT_PLUS]
                ): str,
                vol.Required(
                    CONF_CODE_OUT_MINUS, default=DEFAULT_CODES[CONF_CODE_OUT_MINUS]
                ): str,
                vol.Required(
                    CONF_CODE_IN_PLUS, default=DEFAULT_CODES[CONF_CODE_IN_PLUS]
                ): str,
                vol.Required(
                    CONF_CODE_IN_MINUS, default=DEFAULT_CODES[CONF_CODE_IN_MINUS]
                ): str,
            }
        )

        return self.async_show_form(
            step_id="manual",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_learn_prepare(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show instructions before sending the learning command."""
        if user_input is not None:
            self._learn_task = self.hass.async_create_background_task(
                self._async_send_learning_on(),
                "Directional RF Fan learning signal",
            )
            return await self.async_step_learn_send()

        return self.async_show_form(
            step_id="learn_prepare",
            data_schema=vol.Schema({}),
            description_placeholders=self._learn_placeholders(),
        )

    async def async_step_learn_send(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show progress while the learning ON command is being sent."""
        if self._learn_task is None:
            return await self.async_step_learn_prepare()

        if self._learn_task.done():
            if self._learn_task.exception() is not None:
                self._learn_task = None
                return self.async_show_progress_done(next_step_id="learn_send_failed")

            self._learn_task = None
            return self.async_show_progress_done(next_step_id="learn_confirm")

        return self.async_show_progress(
            step_id="learn_send",
            progress_action="send_learning_signal",
            progress_task=self._learn_task,
            description_placeholders=self._learn_placeholders(),
        )

    async def async_step_learn_send_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a failed learning transmission."""
        if user_input is not None:
            return await self.async_step_learn_prepare()

        return self.async_show_form(
            step_id="learn_send_failed",
            data_schema=vol.Schema({}),
            errors={"base": "learning_send_failed"},
            description_placeholders=self._learn_placeholders(),
        )

    async def async_step_learn_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm whether learning worked."""
        return self.async_show_menu(
            step_id="learn_confirm",
            menu_options=[MENU_LEARN_SUCCESS, MENU_LEARN_FAILED],
            description_placeholders=self._learn_placeholders(),
        )

    async def async_step_learn_success(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the entry after successful learning."""
        return await self._async_create_confirmed_entry()

    async def async_step_learn_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Return to slot selection after failed learning."""
        self._reset_learning_state()
        self._user_errors = {"base": "learning_failed"}
        return await self.async_step_user()

    def _compatible_transmitters(
        self,
    ) -> list[str] | config_entries.ConfigFlowResult:
        """Return compatible RF transmitters or an abort result."""
        try:
            transmitters = async_get_transmitters(
                self.hass, DEFAULT_FREQUENCY, ModulationType.OOK
            )
        except HomeAssistantError:
            return self.async_abort(reason="no_transmitters")

        if not transmitters:
            return self.async_abort(
                reason="no_compatible_transmitters",
                description_placeholders={
                    "frequency": f"{DEFAULT_FREQUENCY / 1_000_000} MHz",
                    "modulation": ModulationType.OOK.name,
                },
            )
        return transmitters

    def _build_slot_candidate(self, slot: str) -> dict[str, Any]:
        """Build final entry data for a selected predefined slot."""
        address = FAN_SLOT_REMOTE_ADDRESSES[slot]
        return {
            **self._base_data,
            **build_fan_codes(address, COMMAND_PROFILE_COMMANDS[COMMAND_PROFILE_A]),
            CONF_CODE_SET_SOURCE: CODE_SET_SOURCE_SLOT,
            CONF_FAN_SLOT: slot,
            CONF_COMMAND_PROFILE: COMMAND_PROFILE_A,
            CONF_RF_PROTOCOL: RF_PROTOCOL_RC_SWITCH_1,
            CONF_FREQUENCY: DEFAULT_FREQUENCY,
            CONF_REMOTE_ADDRESS: f"{address:04X}",
        }

    async def _async_send_learning_on(self) -> None:
        """Send the candidate ON command for about six seconds."""
        assert self._candidate_data is not None
        protocol = str(self._candidate_data.get(CONF_RF_PROTOCOL, "rc_switch_1"))
        frequency = int(self._candidate_data.get(CONF_FREQUENCY, DEFAULT_FREQUENCY))
        repeats = learning_repeats_for_code(
            str(self._candidate_data[CONF_CODE_ON]),
            protocol=protocol,
            frequency=frequency,
        )
        rf_command = build_rf_command(
            str(self._candidate_data[CONF_CODE_ON]),
            repeats=repeats,
            protocol=protocol,
            frequency=frequency,
        )
        await async_send_command(
            self.hass,
            str(self._candidate_data[CONF_TRANSMITTER]),
            rf_command,
        )

    async def _async_create_confirmed_entry(
        self,
    ) -> config_entries.ConfigFlowResult:
        """Create a config entry after the user confirmed learning success."""
        assert self._candidate_data is not None
        await self.async_set_unique_id(self._unique_id_for_candidate())
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=str(self._candidate_data[CONF_NAME]),
            data=self._candidate_data,
        )

    def _unique_id_for_candidate(self) -> str:
        """Return the stable unique id for the current candidate."""
        assert self._candidate_data is not None
        transmitter = self._candidate_data[CONF_TRANSMITTER]
        source = self._candidate_data.get(CONF_CODE_SET_SOURCE)
        slot = self._candidate_data.get(CONF_FAN_SLOT)
        if source == CODE_SET_SOURCE_SLOT and slot:
            return f"{transmitter}_slot_{slot}"
        name = str(self._candidate_data[CONF_NAME]).lower().replace(" ", "_")
        return f"{transmitter}_{name}"

    def _learn_placeholders(self) -> dict[str, str]:
        """Return placeholders for learning instruction translations."""
        assert self._candidate_data is not None
        slot = str(self._candidate_data.get(CONF_FAN_SLOT, FAN_SLOT_MANUAL))
        address = str(self._candidate_data.get(CONF_REMOTE_ADDRESS, "manual"))
        return {
            "slot": SLOT_LABELS.get(slot, slot),
            "address": address,
            "code_on": str(self._candidate_data[CONF_CODE_ON]),
            "learn_image_url": LEARN_IMAGE_URL,
        }

    def _reset_learning_state(self) -> None:
        """Reset candidate state after failed learning."""
        self._selected_slot = None
        self._candidate_data = None
        self._learn_task = None

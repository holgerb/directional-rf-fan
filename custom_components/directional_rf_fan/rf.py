"""RF command helpers for Directional RF Fan."""

from __future__ import annotations

import re

from rf_protocols.commands.ook import OOKCommand

from .const import (
    COMMAND_TO_CONF,
    DEFAULT_FREQUENCY,
    DEFAULT_TIMEBASE_US,
    LEARN_DURATION_SECONDS,
    RF_PROTOCOL_RC_SWITCH_1,
)

RAW_BITS_RE = re.compile(r"^[01]+$")
HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def code_to_bits(value: object) -> str:
    """Convert a user supplied binary or hex RF code to raw bits."""
    code = str(value).strip().replace(" ", "").replace("_", "").replace("-", "")
    if code.lower().startswith("0x"):
        code = code[2:]
    if not code:
        raise ValueError("RF code is empty")
    if RAW_BITS_RE.fullmatch(code) and len(code) >= 16:
        return code
    if HEX_RE.fullmatch(code):
        return "".join(f"{int(char, 16):04b}" for char in code)
    if RAW_BITS_RE.fullmatch(code):
        return code
    raise ValueError("RF code must be binary or hexadecimal")


def build_rc_switch_protocol_1_command(
    code: str,
    *,
    repeats: int,
    frequency: int = DEFAULT_FREQUENCY,
    timebase_us: int = DEFAULT_TIMEBASE_US,
) -> OOKCommand:
    """Build an OOK command matching rc_switch protocol 1 raw bitstrings."""
    raw_bits = code_to_bits(code)
    symbols = {
        "0": [timebase_us, -3 * timebase_us],
        "1": [3 * timebase_us, -timebase_us],
    }
    timings = [timebase_us, -31 * timebase_us]
    for bit in raw_bits:
        timings.extend(symbols[bit])

    return OOKCommand(
        frequency=frequency,
        timings=timings,
        repeat_count=repeats,
    )


def build_rf_command(
    code: str,
    *,
    repeats: int,
    protocol: str = RF_PROTOCOL_RC_SWITCH_1,
    frequency: int = DEFAULT_FREQUENCY,
) -> OOKCommand:
    """Build an OOK command for the fan RF protocol."""
    return build_rc_switch_protocol_1_command(
        code, repeats=repeats, frequency=frequency
    )


def build_fan_codes(address: int, commands: dict[str, int]) -> dict[str, str]:
    """Build configured RF hex codes for one remote address and command profile."""
    codes: dict[str, str] = {}
    for command, conf_key in COMMAND_TO_CONF.items():
        command_byte = commands[command]
        checksum = command_byte ^ 0xFF
        code = (address << 16) | (command_byte << 8) | checksum
        codes[conf_key] = f"{code:08X}"
    return codes


def learning_repeats_for_code(
    code: str,
    *,
    protocol: str = RF_PROTOCOL_RC_SWITCH_1,
    frequency: int = DEFAULT_FREQUENCY,
    duration_seconds: int = LEARN_DURATION_SECONDS,
) -> int:
    """Return a repeat count that keeps one RF command active for about duration_seconds."""
    command = build_rf_command(
        code, repeats=1, protocol=protocol, frequency=frequency
    )
    frame_seconds = sum(abs(timing) for timing in command.get_raw_timings()) / 1_000_000
    if frame_seconds <= 0:
        return 1
    return max(1, round(duration_seconds / frame_seconds) - 1)

# Directional RF Fan

![Directional RF Fan](logo.svg)

Home Assistant custom integration for the tested 433 MHz directional ventilation fans.

Installable HACS repository:

- `https://github.com/holgerb/directional-rf-fan`

## Branding

Home Assistant 2026.3 and newer can load local brand images for custom integrations
from the integration's `brand/` directory. This integration ships:

- `brand/icon.png`
- `brand/logo.png`

The SVG files in this directory are the editable source assets.

The integration exposes one optimistic `fan` entity. Airflow directions are modeled as fan `preset_modes`:

- `In`
- `Out`

The integration sends commands through Home Assistant's `radio_frequency` transmitter API. During setup, select a transmitter entity that supports `433.92 MHz` and `OOK` modulation.

The currently confirmed working Slot 2 code family is `0x6234` with `rc_switch`
protocol 1. During final testing the ESP32 + CC1101 firmware was tuned to
`433.89583 MHz`; retest your final ESPHome frequency before production use.

## Setup

During setup, select one fan slot:

- `1` uses the first captured real remote.
- `2` uses the second captured real remote.
- `Manual` shows six hex code fields for custom code sets.

To learn a fan, disconnect it from power, power it on again, and immediately
continue the setup flow. The integration sends the selected `On` signal for
about six seconds. The config entry is only created after confirming that
learning worked.

The learning step uses a Markdown illustration from the integration's static
assets, a Home Assistant progress step while RF is transmitting, and a final
success/failure menu.

## Controls

- `fan.turn_on` sends the configured `on` RF command and restores the remembered level and direction in the UI.
- `fan.turn_off` sends the configured `off` RF command while keeping the remembered level and direction for the next `turn_on`.
- Setting preset `In` or `Out` while the fan is running sends an offsetting plus/minus pair in the target direction, preserving the current speed level.
- `directional_rf_fan.step_up` sends `in_plus` or `out_plus`.
- `directional_rf_fan.step_down` sends `in_minus` or `out_minus`.
- `directional_rf_fan.send_command` sends a specific configured command.
- The `Recalibrate` button and `directional_rf_fan.recalibrate` service send six minus commands for the current or selected preset and reset Home Assistant's optimistic state to level 1 in that direction.
- `Level 1` to `Level 6` buttons set the fan to fixed physical levels in the current or remembered direction.
- Diagnostic sensors expose the remembered airflow direction and current physical step.

Because RF commands are one-way, the entity is optimistic. Home Assistant tracks the last command it sent, remembers the last level and direction across off/on, and restores the previous optimistic state after restart. It cannot know whether a physical remote changed the fan state.

The configured RF codes may be hexadecimal, for example `55BE0AF5`, or legacy binary bit strings. They are converted to rc_switch protocol 1 timings and wrapped in an `rf_protocols.OOKCommand` before being sent to the selected RF transmitter.

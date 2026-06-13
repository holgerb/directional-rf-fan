# Directional RF Fan

Home Assistant custom integration for directional 433 MHz ventilation fans controlled through Home Assistant's `radio_frequency` transmitter API.

## Installation With HACS

1. In HACS, add this repository as a custom repository:
   `https://github.com/holgerb/directional-rf-fan`
2. Select category `Integration`.
3. Install `Directional RF Fan`.
4. Restart Home Assistant.
5. Add the integration from **Settings -> Devices & services -> Add integration**.

## Requirements

- Home Assistant with the `radio_frequency` integration available.
- An ESPHome RF transmitter entity exposed via `radio_frequency`, for example an ESP32 + CC1101 node using ESPHome `ir_rf_proxy`.
- The transmitter must support OOK/ASK at 433 MHz.

The currently tested ESP32 + CC1101 firmware was tuned to `433.89583 MHz` during final fan testing, while Home Assistant may still advertise the RF proxy as fixed `433.920 MHz`. Retest your final ESPHome frequency before relying on the setup in production.

## Working Fan Slot

The confirmed working slot is Slot 2:

- Protocol: `rc_switch` protocol 1
- Address/prefix: `0x6234`
- `On`: `62340AF5`
- `Off`: `62340DF2`
- `Out+`: `62340BF4`
- `Out-`: `62340CF3`
- `In+`: `62340EF1`
- `In-`: `62340FF0`

Earlier RTL-SDR PWM-looking candidates such as `BB97EA15`, `3B97EA15`, `772FD42B3B97EA15`, and `9DCBF50A8` did not replay successfully for the active setup and should be treated as decoder artifacts unless proven otherwise.

## Features

- Optimistic `fan` entity.
- Direction presets: `In` and `Out`.
- Percentage control mapped to six physical fan levels.
- Level buttons from `Level 1` to `Level 6`.
- `Recalibrate` button and service.
- Services for direct command sending and relative stepping.
- Config flow with predefined fan slots and manual code entry.

Because RF control is one-way, Home Assistant tracks the last command it sent. It cannot know whether a physical remote changed the fan state.

## Release Process

HACS versioned installs use GitHub Releases. For each release:

1. Update `custom_components/directional_rf_fan/manifest.json`.
2. Commit the change.
3. Create a matching tag, for example `v0.1.0`.
4. Create a GitHub Release from that tag.

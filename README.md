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

## Features

- Optimistic `fan` entity.
- Direction presets: `In` and `Out`.
- Percentage control mapped to six physical fan levels.
- Remembered level and direction across off/on.
- Level buttons from `Level 1` to `Level 6` that preserve the current direction.
- Diagnostic sensors for remembered direction and current step.
- `Recalibrate` button and service.
- Services for direct command sending and relative stepping.
- Config flow with captured fan slots and manual code entry.

Because RF control is one-way, Home Assistant tracks the last command it sent and restores the previous optimistic state after restart. It cannot know whether a physical remote changed the fan state.

## Development And Releases

Pull request titles follow Conventional Commits. Use `fix:` for patches,
`feat:` for features, and `!` for breaking changes. Documentation, test, and
CI-only pull requests do not create a release on their own.

Release Please collects releasable changes in a release pull request. Merging
that pull request updates `CHANGELOG.md` and the integration version, then
creates the matching `vX.Y.Z` tag and GitHub release for HACS.

# Directional RF Fan

![Directional RF Fan](custom_components/directional_rf_fan/logo.svg)

[![GitHub release](https://img.shields.io/github/v/release/holgerb/directional-rf-fan)](https://github.com/holgerb/directional-rf-fan/releases/latest)
[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=holgerb&repository=directional-rf-fan&category=integration)

Directional RF Fan is a custom integration for controlling directional 433 MHz
ventilation fans from Home Assistant. It sends commands through Home
Assistant's `radio_frequency` transmitter API and exposes the fan, fixed level
buttons, diagnostic sensors, and recalibration controls.

This is a community integration and is not part of Home Assistant Core.

## Features

- Optimistic `fan` entity with `In` and `Out` direction presets.
- Percentage control mapped to six physical fan levels.
- Remembered level and direction across off/on and Home Assistant restarts.
- Level buttons from `Level 1` to `Level 6`.
- Diagnostic sensors for remembered direction and current step.
- Recalibration button and services for direct commands and relative stepping.
- Config flow with predefined fan slots and manual RF code entry.

## Requirements

- A Home Assistant version that includes the `radio_frequency` integration.
- A `radio_frequency` transmitter entity that supports OOK/ASK at 433.92 MHz.
- For example, an ESP32 with a CC1101 exposed through ESPHome `ir_rf_proxy`.
- [HACS](https://hacs.xyz/) installed and configured when using the recommended
  installation method.

The transmitter used during final fan testing was tuned to `433.89583 MHz`,
while Home Assistant may advertise the RF proxy as fixed at `433.920 MHz`.
Verify the frequency used by your final ESPHome firmware before relying on the
setup in production.

## Installation

### Recommended: HACS

HACS installs the integration into the correct `custom_components` directory,
tracks GitHub releases, and notifies you when an update is available. If HACS
is not installed yet, follow the
[official HACS installation guide](https://hacs.xyz/docs/use/download/download/)
first.

#### 1. Add this repository to HACS

Use the button below to open this repository in HACS:

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=holgerb&repository=directional-rf-fan&category=integration)

Alternatively, add it manually:

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu in the top-right corner.
3. Select **Custom repositories**.
4. Enter `https://github.com/holgerb/directional-rf-fan` as the repository.
5. Select **Integration** as the type.
6. Select **Add**.

Adding a custom repository only makes it available in HACS. It does not install
the integration yet.

#### 2. Download the integration

1. Open **Directional RF Fan** in HACS.
2. Select **Download**.
3. Choose the latest stable version and confirm the download.
4. Restart Home Assistant after the download completes.

HACS stores the integration under
`/config/custom_components/directional_rf_fan/`.

#### 3. Add the integration to Home Assistant

After restarting, use the button below:

[![Add Directional RF Fan to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=directional_rf_fan)

Or configure it manually:

1. Go to **Settings -> Devices & services**.
2. Select **Add integration**.
3. Search for **Directional RF Fan** and select it.
4. Follow the setup flow described in [Fan setup](#fan-setup).

### Manual installation

Manual installation is useful when HACS is unavailable, but it does not provide
automatic update notifications.

1. Download the source archive from the
   [latest GitHub release](https://github.com/holgerb/directional-rf-fan/releases/latest).
2. Extract the archive.
3. Copy the extracted `custom_components/directional_rf_fan` directory into
   the `custom_components` directory in your Home Assistant configuration.
4. Verify that the resulting file exists at:
   `/config/custom_components/directional_rf_fan/manifest.json`.
5. Restart Home Assistant.
6. Add **Directional RF Fan** from **Settings -> Devices & services -> Add
   integration**.

Do not copy the entire repository into `custom_components`. The directory name
must remain exactly `directional_rf_fan`.

## Fan setup

During the config flow, select the RF transmitter, a name, the normal command
repeat count, and one fan slot:

- `1` uses the first captured remote code family.
- `2` uses the second captured remote code family.
- `Manual` lets you enter six hexadecimal or binary RF commands.

To put the fan into learning mode:

1. Disconnect the fan from power.
2. Power it on again.
3. Immediately continue the setup flow.
4. Wait while the integration transmits the selected `On` command for about
   six seconds.
5. Confirm whether the fan learned the command.

The config entry is created only after you confirm that learning succeeded.

## Controls

- `fan.turn_on` sends the configured `on` command and restores the remembered
  level and direction in Home Assistant.
- `fan.turn_off` sends `off` while preserving the remembered settings for the
  next turn-on.
- Selecting the `In` or `Out` preset changes airflow direction while preserving
  the current physical level.
- The level buttons select one of the six physical levels.
- The recalibration button sends six minus commands and resets the optimistic
  level to 1.
- `directional_rf_fan.send_command`, `directional_rf_fan.step_up`,
  `directional_rf_fan.step_down`, and `directional_rf_fan.recalibrate` provide
  the same controls for scripts and automations.

## RF state limitations

RF control is one-way. Home Assistant records the last command it sent, but it
cannot detect commands sent by a physical remote. The displayed direction,
level, and power state can therefore differ from the real fan until Home
Assistant sends another command or the integration is recalibrated.

## Updating

HACS regularly checks GitHub releases and creates an update notification when a
new version is available.

1. Create a Home Assistant backup.
2. Install the update from **Settings -> Updates**, or open the repository menu
   in HACS and select **Redownload**.
3. Restart Home Assistant after updating the integration.

To force HACS to check immediately, open the repository's three-dot menu and
select **Update information**.

For a manual installation, download the latest release, replace the existing
`directional_rf_fan` directory with the new one, and restart Home Assistant.

## Troubleshooting

### The integration does not appear

- Confirm that
  `/config/custom_components/directional_rf_fan/manifest.json` exists.
- Restart Home Assistant after downloading or copying the integration.
- Perform a hard refresh or clear the browser cache before searching again.
- Check **Settings -> System -> Logs** for errors mentioning
  `directional_rf_fan`.

### No compatible transmitter is found

- Confirm that the `radio_frequency` integration is available and loaded.
- Confirm that the transmitter entity supports OOK modulation at 433.92 MHz.
- Confirm that the ESPHome RF proxy is connected and its entity is available.

### HACS does not show a new release

- Open the repository's three-dot menu and select **Update information**.
- Confirm that the version exists under
  [GitHub Releases](https://github.com/holgerb/directional-rf-fan/releases).
- Check that the HACS update entity for this repository is enabled.

## Development and releases

Pull request titles follow Conventional Commits. Use `fix:` for patches,
`feat:` for features, and `!` for breaking changes. Documentation, test, and
CI-only pull requests do not create a release on their own.

Release Please collects releasable changes in a release pull request. Merging
that pull request updates `CHANGELOG.md` and the integration version, then
creates the matching `vX.Y.Z` tag and GitHub release used by HACS.

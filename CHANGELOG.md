# Changelog

## [0.1.2](https://github.com/holgerb/directional-rf-fan/compare/v0.1.1...v0.1.2) (2026-06-21)


### Documentation

* improve installation guide ([#3](https://github.com/holgerb/directional-rf-fan/issues/3)) ([3d31e76](https://github.com/holgerb/directional-rf-fan/commit/3d31e765c80da134651912c74ef54e270aede476))

## 0.1.1

- Declare the directly imported `rf-protocols` runtime dependency.
- Import `OOKCommand` from its actual module so Home Assistant can load the config flow.

## 0.1.0

- Initial HACS-ready release.
- Adds the Directional RF Fan custom integration.
- Supports the confirmed `0x6234` Slot 2 fan code family via `rc_switch` protocol 1.

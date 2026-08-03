# Changelog

All notable changes to FotMob Leagues are documented in this file.

## [0.2.0] - Unreleased

### Added

- Fetch league information from FotMob every 30 minutes.
- Create a `<league name> Table` sensor with the active round as its state.
- Expose `league_id` and `season` as sensor attributes.
- Update the config entry title to the league name after the first successful refresh.
- Add HACS metadata and installation documentation.
- Add HACS and hassfest validation workflows.

## [0.1.0] - 2026-08-03

### Added

- Initial Home Assistant custom integration structure.
- Configuration flow for a numeric FotMob league ID.
- Duplicate league ID prevention.
- English and Norwegian translations.

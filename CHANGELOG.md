# Changelog

All notable changes to FotMob Leagues are documented in this file.

## [0.5.0] - 2026-08-04

### Added

- Add a `<league name> Top scorer` sensor with the leading goalscorer's name as
  its state and the complete goals list in the `scorers` attribute.
- Add `totalGoals` with the sum of every player's goals in `scorers`.

## [0.4.0] - 2026-08-04

### Added

- Add a `clubLogo` URL to every object in the `stands` attribute.

## [0.3.0] - 2026-08-04

### Added

- Expose the FotMob overall table as the `stands` sensor attribute.
- Include every team table field except `id` and `pageUrl`.

## [0.2.0] - 2026-08-04

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

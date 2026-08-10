# Changelog

All notable changes to FotMob Leagues are documented in this file.

## [0.7.0] - 2026-08-10

### Removed

- Remove all player statistic sensors, leaving the `<league name> Table` sensor
  as the integration's only entity.
- Remove the additional FotMob requests and parsing used exclusively by the
  player statistic sensors.

## [0.6.0] - 2026-08-04

### Added

- Add `<league name> Assist`, `Goal points`, `Yellow cards`, `Red cards` and
  `Best rated` sensors.
- Include each complete player list with names, values, clubs, club logos and
  player pictures.
- Add total card counts to the yellow-card and red-card sensors.
- Make each player statistic sensor unavailable independently when FotMob does
  not provide a non-empty list.

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

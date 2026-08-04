# FotMob Leagues

A custom Home Assistant integration that creates league sensors from a FotMob league ID.

> [!IMPORTANT]
> This project is under development and has not been submitted for inclusion in the HACS default store. It uses an undocumented FotMob endpoint. Public distribution will not take place before its use has been clarified with FotMob.

## Features

- Configured through the Home Assistant user interface
- Supports one or more FotMob leagues
- Prevents the same league ID from being configured twice
- Creates a `<league name> Table` sensor
- Creates six player statistic sensors per league
- Uses the league's active round as the table sensor state
- Adds the FotMob league ID, selected season and overall table as attributes
- Refreshes league data every 30 minutes
- Includes English and Norwegian translations

For example, league ID `203` creates a sensor named `1. Divisjon Table`.

## Installation with HACS

The repository is not listed in the HACS default store. For private testing, it can be added as a custom repository:

1. Open HACS in Home Assistant.
2. Open the menu in the upper-right corner and select **Custom repositories**.
3. Enter `https://github.com/isimagan/fotmob-leagues`.
4. Select **Integration** as the category and add the repository.
5. Download **FotMob Leagues**.
6. Restart Home Assistant.

## Manual installation

1. Copy `custom_components/fotmob_leagues` into the `custom_components` directory in your Home Assistant configuration.
2. Restart Home Assistant.

The resulting path should be:

```text
<config>/custom_components/fotmob_leagues/
```

## Configuration

1. Go to **Settings → Devices & services** in Home Assistant.
2. Select **Add integration**.
3. Search for **FotMob Leagues**.
4. Enter the numeric FotMob league ID.

The league ID is visible in a FotMob league URL. In this example, the ID is `203`:

```text
https://www.fotmob.com/nb/leagues/203/overview/1-divisjon
```

## Sensors

The integration creates seven sensors per configured league.

### Table

| Property | Example |
| --- | --- |
| Name | `1. Divisjon Table` |
| State | `17` |
| Attribute | `league_id: 203` |
| Attribute | `season: 2026` |
| Attribute | `stands: [...]` |

The state represents the active round reported by FotMob.

`stands` is an array containing one object per team from FotMob's `all` table.
Each object includes every field returned for the team except `id` and `pageUrl`.
It also includes `clubLogo`, a direct URL to the team's FotMob logo derived from
the team ID before that ID is removed from the object.
Home, away, form and other table variants are not included.

### Top scorer

| Property | Example |
| --- | --- |
| Name | `1. Divisjon Top scorer` |
| State | `Sory Diarra` |
| Attribute | `scorers: [...]` |
| Attribute | `totalGoals: 467` |

The state is the name of the leading player in FotMob's goals statistic. The
`scorers` attribute contains the complete goals list, including the leading
player. Each object contains `name`, `stat` (goals), `club`, `club_logo` and
`player_pic`. `totalGoals` is the sum of `stat` for every player in `scorers`.
The sensor is unavailable when FotMob does not provide a non-empty goals list
for the selected season.

### Player statistics

The remaining player statistic sensors follow the same structure as Top
scorer. Their state is the name of the first player in the complete FotMob list.

| Sensor name | List attribute | Total attribute |
| --- | --- | --- |
| `<league name> Assist` | `assists` | None |
| `<league name> Goal points` | `goalPoints` | None |
| `<league name> Yellow cards` | `yellowCards` | `totalYellowCards` |
| `<league name> Red cards` | `redCards` | `totalRedCards` |
| `<league name> Best rated` | `ratings` | None |

Every object in these list attributes contains `name`, `stat`, `club`,
`club_logo` and `player_pic`. `stat` is the value of the corresponding FotMob
statistic, including a decimal rating in `ratings`. Assist and Goal points do
not expose a total. Yellow cards and Red cards expose the sum of `stat` in
their listed total attribute.

Each sensor is independently unavailable when FotMob does not provide a
non-empty list for that statistic and season. Other sensors for the same league
continue to update.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by FotMob. FotMob is a trademark of its respective owner. The integration relies on an undocumented endpoint that may change or become unavailable without notice. Users are responsible for ensuring that their use complies with FotMob's applicable terms and permissions.

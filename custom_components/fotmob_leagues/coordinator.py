"""Data coordinator for the FotMob Leagues integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import math
import re
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_URL, DEEP_STATS_API_URL, DOMAIN, UPDATE_INTERVAL_MINUTES

LOGGER = logging.getLogger(__name__)

_EXCLUDED_STAND_FIELDS = {"id", "pageUrl"}
_TEAM_LOGO_URL = (
    "https://images.fotmob.com/image_resources/logo/teamlogo/{team_id}.png"
)
_PLAYER_PICTURE_URL = (
    "https://images.fotmob.com/image_resources/playerimages/{player_id}.png"
)
_FOTMOB_API_URL_PREFIXES = (
    "https://www.fotmob.com/api/",
    "https://data.fotmob.com/",
)
_PLAYER_STAT_DATA_KEYS = {
    "goals": "scorers",
    "goal_assist": "assists",
    "_goals_and_goal_assist": "goal_points",
    "yellow_card": "yellow_cards",
    "red_card": "red_cards",
}
_RATING_LINK_PATTERN = re.compile(
    r"^/leagues/(?P<league_id>\d+)/stats/season/(?P<season_id>\d+)"
    r"/players/rating(?:/|$)"
)


class FotMobLeaguesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch league data from FotMob."""

    def __init__(self, hass: HomeAssistant, league_id: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{league_id}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
            always_update=False,
        )
        self.league_id = league_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and parse the latest league data."""
        session = async_get_clientsession(self.hass)
        headers = {"User-Agent": "Home Assistant FotMob Leagues"}

        try:
            async with asyncio.timeout(15):
                async with session.get(
                    API_URL,
                    params={"id": self.league_id},
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            raise UpdateFailed(
                f"Unable to fetch FotMob league {self.league_id}"
            ) from err

        try:
            league_data = _extract_league_data(payload)
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(
                f"Invalid data returned for FotMob league {self.league_id}"
            ) from err

        for data_key in (*_PLAYER_STAT_DATA_KEYS.values(), "ratings"):
            league_data[data_key] = []

        try:
            statistic_urls = _extract_player_stat_urls(payload.get("stats"))
        except (TypeError, ValueError) as err:
            LOGGER.warning(
                "Unable to read FotMob player statistic URLs for league %s: %s",
                self.league_id,
                err,
            )
            statistic_urls = {}

        async def async_fetch_top_list(
            statistic_name: str, data_key: str, url: str
        ) -> tuple[str, list[dict[str, Any]]]:
            """Fetch one complete FotMob player statistic list."""
            try:
                async with asyncio.timeout(15):
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        statistic_payload = await response.json(content_type=None)
                return data_key, _extract_top_list_statistics(
                    statistic_payload, statistic_name
                )
            except (TimeoutError, ClientError, KeyError, TypeError, ValueError) as err:
                LOGGER.warning(
                    "Unable to fetch FotMob %s for league %s: %s",
                    statistic_name,
                    self.league_id,
                    err,
                )
                return data_key, []

        statistic_tasks = [
            async_fetch_top_list(
                statistic_name, data_key, statistic_urls[statistic_name]
            )
            for statistic_name, data_key in _PLAYER_STAT_DATA_KEYS.items()
            if statistic_name in statistic_urls
        ]
        if statistic_tasks:
            for data_key, statistic_list in await asyncio.gather(*statistic_tasks):
                league_data[data_key] = statistic_list

        try:
            rating_params = _extract_rating_params(
                payload.get("overview"), self.league_id
            )
        except (TypeError, ValueError) as err:
            LOGGER.warning(
                "Unable to read FotMob rating URL for league %s: %s",
                self.league_id,
                err,
            )
            rating_params = None

        if rating_params is not None:
            try:
                async with asyncio.timeout(15):
                    async with session.get(
                        DEEP_STATS_API_URL,
                        params=rating_params,
                        headers=headers,
                    ) as response:
                        response.raise_for_status()
                        ratings_payload = await response.json(content_type=None)
                team_names = _extract_team_names(payload["table"])
                league_data["ratings"] = _extract_ratings(
                    ratings_payload, team_names
                )
            except (
                TimeoutError,
                ClientError,
                KeyError,
                TypeError,
                ValueError,
            ) as err:
                LOGGER.warning(
                    "Unable to fetch FotMob ratings for league %s: %s",
                    self.league_id,
                    err,
                )

        return league_data


def _extract_league_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract league metadata and standings from a response."""
    details = payload["details"]
    active_round = payload["fixtures"]["fixtureInfo"]["activeRound"]["roundId"]
    stands = _extract_stands(payload["table"])

    if not details["name"] or active_round in (None, ""):
        raise ValueError("League name or active round is missing")

    try:
        round_value: int | str = int(active_round)
    except (TypeError, ValueError):
        round_value = str(active_round)

    return {
        "league_name": str(details["name"]),
        "round": round_value,
        "season": details.get("selectedSeason"),
        "stands": stands,
    }


def _extract_stands(table_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every row from FotMob's overall tables."""
    stands: list[dict[str, Any]] = []

    for section in table_sections:
        all_table = section["data"]["table"]["all"]
        if not isinstance(all_table, list):
            raise TypeError("FotMob overall table is not a list")

        for row in all_table:
            if not isinstance(row, dict):
                raise TypeError("FotMob table row is not an object")

            team_id = row["id"]
            if team_id in (None, ""):
                raise ValueError("FotMob table row is missing a team ID")

            stand = {
                key: value
                for key, value in row.items()
                if key not in _EXCLUDED_STAND_FIELDS
            }
            stand["clubLogo"] = _TEAM_LOGO_URL.format(team_id=team_id)
            stands.append(stand)

    return stands


def _extract_player_stat_urls(stats: Any) -> dict[str, str]:
    """Return full-list URLs for the supported FotMob player statistics."""
    if stats is None:
        return {}
    if not isinstance(stats, dict):
        raise TypeError("FotMob stats is not an object")

    players = stats.get("players")
    if players is None:
        return {}
    if not isinstance(players, list):
        raise TypeError("FotMob player stats is not a list")

    statistic_urls: dict[str, str] = {}
    for statistic in players:
        if not isinstance(statistic, dict):
            continue
        statistic_name = statistic.get("name")
        if statistic_name not in _PLAYER_STAT_DATA_KEYS:
            continue

        fetch_all_url = statistic.get("fetchAllUrl")
        if fetch_all_url in (None, ""):
            continue
        if not isinstance(fetch_all_url, str):
            continue
        if not fetch_all_url.startswith(_FOTMOB_API_URL_PREFIXES):
            continue

        statistic_urls[statistic_name] = fetch_all_url

    return statistic_urls


def _extract_top_list_statistics(
    payload: dict[str, Any], statistic_name: str
) -> list[dict[str, Any]]:
    """Return a complete FotMob TopLists player statistic with image URLs."""
    if not isinstance(payload, dict):
        raise TypeError("FotMob player statistics response is not an object")

    top_lists = payload.get("TopLists")
    if top_lists is None:
        return []
    if not isinstance(top_lists, list):
        raise TypeError("FotMob TopLists is not a list")
    if not top_lists:
        return []

    first_list = top_lists[0]
    if not isinstance(first_list, dict):
        raise TypeError("FotMob player statistics list is not an object")

    returned_statistic_name = first_list.get("StatName")
    if returned_statistic_name not in (None, statistic_name):
        raise ValueError("FotMob returned an unexpected player statistic")

    stat_list = first_list.get("StatList")
    if stat_list is None:
        return []
    if not isinstance(stat_list, list):
        raise TypeError("FotMob StatList is not a list")

    statistics: list[dict[str, Any]] = []
    for row in stat_list:
        if not isinstance(row, dict):
            raise TypeError("FotMob player statistic row is not an object")

        name = row.get("ParticipantName")
        stat = row.get("StatValue")
        club = row.get("TeamName")
        team_id = row.get("TeamId")
        player_id = row.get("ParticiantId")

        if name in (None, "") or club in (None, ""):
            raise ValueError("FotMob player statistic row is missing a name or club")
        if team_id in (None, "") or player_id in (None, ""):
            raise ValueError("FotMob player statistic row is missing an ID")

        statistic_value = _parse_stat_value(stat, require_integer=True)

        statistics.append(
            {
                "name": str(name),
                "stat": statistic_value,
                "club": str(club),
                "club_logo": _TEAM_LOGO_URL.format(team_id=team_id),
                "player_pic": _PLAYER_PICTURE_URL.format(player_id=player_id),
            }
        )

    return statistics


def _extract_rating_params(
    overview: Any, league_id: int
) -> dict[str, int | str] | None:
    """Return deep-stat query parameters from FotMob's rating link."""
    if overview is None:
        return None
    if not isinstance(overview, dict):
        raise TypeError("FotMob overview is not an object")

    top_players = overview.get("topPlayers")
    if top_players is None:
        return None
    if not isinstance(top_players, dict):
        raise TypeError("FotMob top players is not an object")

    by_rating = top_players.get("byRating")
    if by_rating is None:
        return None
    if not isinstance(by_rating, dict):
        raise TypeError("FotMob rating statistic is not an object")

    see_all_link = by_rating.get("seeAllLink")
    if see_all_link in (None, ""):
        return None
    if not isinstance(see_all_link, str):
        raise TypeError("FotMob rating link is not a string")

    match = _RATING_LINK_PATTERN.match(see_all_link)
    if match is None or int(match.group("league_id")) != league_id:
        raise ValueError("FotMob rating link is not valid for this league")

    return {
        "id": league_id,
        "season": int(match.group("season_id")),
        "type": "players",
        "stat": "rating",
    }


def _extract_team_names(table_sections: list[dict[str, Any]]) -> dict[int, str]:
    """Return a team ID to name lookup from FotMob's overall tables."""
    team_names: dict[int, str] = {}

    for section in table_sections:
        all_table = section["data"]["table"]["all"]
        if not isinstance(all_table, list):
            raise TypeError("FotMob overall table is not a list")

        for row in all_table:
            if not isinstance(row, dict):
                raise TypeError("FotMob table row is not an object")
            team_id = row.get("id")
            team_name = row.get("name")
            if team_id in (None, "") or team_name in (None, ""):
                raise ValueError("FotMob table row is missing a team ID or name")
            team_names[int(team_id)] = str(team_name)

    return team_names


def _extract_ratings(
    payload: dict[str, Any], team_names: dict[int, str]
) -> list[dict[str, Any]]:
    """Return the complete FotMob player rating list with image URLs."""
    if not isinstance(payload, dict):
        raise TypeError("FotMob ratings response is not an object")

    stats_data = payload.get("statsData")
    if stats_data is None:
        return []
    if not isinstance(stats_data, list):
        raise TypeError("FotMob ratings list is not a list")

    ratings: list[dict[str, Any]] = []
    for row in stats_data:
        if not isinstance(row, dict):
            raise TypeError("FotMob rating row is not an object")

        name = row.get("name")
        team_id = row.get("teamId")
        player_id = row.get("id")
        stat_value = row.get("statValue")
        if name in (None, ""):
            raise ValueError("FotMob rating row is missing a player name")
        if team_id in (None, "") or player_id in (None, ""):
            raise ValueError("FotMob rating row is missing an ID")
        if not isinstance(stat_value, dict):
            raise TypeError("FotMob rating value is not an object")

        try:
            club = team_names[int(team_id)]
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("FotMob rating row refers to an unknown team") from err

        ratings.append(
            {
                "name": str(name),
                "stat": _parse_stat_value(
                    stat_value.get("value"), require_integer=False
                ),
                "club": club,
                "club_logo": _TEAM_LOGO_URL.format(team_id=team_id),
                "player_pic": _PLAYER_PICTURE_URL.format(player_id=player_id),
            }
        )

    return ratings


def _parse_stat_value(value: Any, *, require_integer: bool) -> int | float:
    """Return a finite, non-negative numeric FotMob statistic."""
    if value is None or isinstance(value, bool):
        raise ValueError("FotMob player statistic is missing a valid value")

    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError("FotMob player statistic is not numeric") from err
    if not math.isfinite(number) or number < 0:
        raise ValueError("FotMob player statistic must be finite and non-negative")

    if require_integer:
        if not number.is_integer():
            raise ValueError("FotMob player statistic is not an integer")
        return int(number)

    return number

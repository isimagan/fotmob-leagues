"""Data coordinator for the FotMob Leagues integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_URL, DOMAIN, UPDATE_INTERVAL_MINUTES

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
            raise UpdateFailed(f"Unable to fetch FotMob league {self.league_id}") from err

        try:
            league_data = _extract_league_data(payload)
            scorers_url = _extract_scorers_url(payload.get("stats"))
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(
                f"Invalid data returned for FotMob league {self.league_id}"
            ) from err

        scorers: list[dict[str, Any]] = []
        if scorers_url is not None:
            try:
                async with asyncio.timeout(15):
                    async with session.get(scorers_url, headers=headers) as response:
                        response.raise_for_status()
                        scorers_payload = await response.json(content_type=None)
                scorers = _extract_scorers(scorers_payload)
            except (TimeoutError, ClientError, KeyError, TypeError, ValueError) as err:
                LOGGER.warning(
                    "Unable to fetch FotMob top scorers for league %s: %s",
                    self.league_id,
                    err,
                )

        league_data["scorers"] = scorers
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


def _extract_scorers_url(stats: Any) -> str | None:
    """Return the full-list URL from FotMob's goals statistic."""
    if stats is None:
        return None
    if not isinstance(stats, dict):
        raise TypeError("FotMob stats is not an object")

    players = stats.get("players")
    if players is None:
        return None
    if not isinstance(players, list):
        raise TypeError("FotMob player stats is not a list")

    for statistic in players:
        if not isinstance(statistic, dict):
            raise TypeError("FotMob player statistic is not an object")
        if statistic.get("name") != "goals":
            continue

        fetch_all_url = statistic.get("fetchAllUrl")
        if fetch_all_url in (None, ""):
            return None
        if not isinstance(fetch_all_url, str):
            raise TypeError("FotMob top scorers URL is not a string")
        if not fetch_all_url.startswith(_FOTMOB_API_URL_PREFIXES):
            raise ValueError("FotMob top scorers URL is not a FotMob API URL")

        return fetch_all_url

    return None


def _extract_scorers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the complete goals list with image URLs."""
    if not isinstance(payload, dict):
        raise TypeError("FotMob top scorers response is not an object")

    top_lists = payload.get("TopLists")
    if top_lists is None:
        return []
    if not isinstance(top_lists, list):
        raise TypeError("FotMob TopLists is not a list")
    if not top_lists:
        return []

    first_list = top_lists[0]
    if not isinstance(first_list, dict):
        raise TypeError("FotMob top scorers list is not an object")

    stat_list = first_list.get("StatList")
    if stat_list is None:
        return []
    if not isinstance(stat_list, list):
        raise TypeError("FotMob StatList is not a list")

    scorers: list[dict[str, Any]] = []
    for row in stat_list:
        if not isinstance(row, dict):
            raise TypeError("FotMob top scorer row is not an object")

        name = row.get("ParticipantName")
        stat = row.get("StatValue")
        club = row.get("TeamName")
        team_id = row.get("TeamId")
        player_id = row.get("ParticiantId")

        if name in (None, "") or club in (None, ""):
            raise ValueError("FotMob top scorer row is missing a name or club")
        if stat is None or isinstance(stat, bool):
            raise ValueError("FotMob top scorer row is missing a valid stat")
        if team_id in (None, "") or player_id in (None, ""):
            raise ValueError("FotMob top scorer row is missing an ID")

        try:
            goals = int(stat)
        except (TypeError, ValueError) as err:
            raise ValueError("FotMob top scorer stat is not an integer") from err
        if goals < 0:
            raise ValueError("FotMob top scorer stat cannot be negative")

        scorers.append(
            {
                "name": str(name),
                "stat": goals,
                "club": str(club),
                "club_logo": _TEAM_LOGO_URL.format(team_id=team_id),
                "player_pic": _PLAYER_PICTURE_URL.format(player_id=player_id),
            }
        )

    return scorers

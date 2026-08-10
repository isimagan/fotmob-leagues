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
            return _extract_league_data(payload)
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(
                f"Invalid data returned for FotMob league {self.league_id}"
            ) from err


def _extract_league_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract league metadata and standings from a response."""
    details = payload["details"]
    active_round = payload["fixtures"]["fixtureInfo"]["activeRound"]["roundId"]
    stands = _extract_stands(payload["table"])
    leader = stands[0].get("name") if stands else None

    if (
        not details["name"]
        or active_round in (None, "")
        or leader in (None, "")
    ):
        raise ValueError("League name, active round or leader is missing")

    try:
        round_value: int | str = int(active_round)
    except (TypeError, ValueError):
        round_value = str(active_round)

    return {
        "league_name": str(details["name"]),
        "leader": str(leader),
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

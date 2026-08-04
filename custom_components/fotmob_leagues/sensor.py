"""Sensor platform for the FotMob Leagues integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FotMobLeaguesConfigEntry
from .const import DOMAIN
from .coordinator import FotMobLeaguesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FotMobLeaguesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the league sensors."""
    async_add_entities(
        [
            FotMobTableSensor(entry.runtime_data),
            FotMobTopScorerSensor(entry.runtime_data),
        ]
    )


class FotMobTableSensor(CoordinatorEntity[FotMobLeaguesCoordinator], SensorEntity):
    """Show the active round for a FotMob league."""

    _attr_icon = "mdi:table"

    def __init__(self, coordinator: FotMobLeaguesCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        league_name = coordinator.data["league_name"]
        league_id = coordinator.league_id

        self._attr_name = f"{league_name} Table"
        self._attr_unique_id = f"{league_id}_table"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(league_id))},
            name=league_name,
            manufacturer="FotMob",
            model="League",
            configuration_url=f"https://www.fotmob.com/leagues/{league_id}/overview",
        )

    @property
    def native_value(self) -> int | str:
        """Return the active league round."""
        return self.coordinator.data["round"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful league metadata."""
        league_id = self.coordinator.league_id
        return {
            "league_id": league_id,
            "season": self.coordinator.data["season"],
            "stands": self.coordinator.data["stands"],
            "logo_path": (
                "https://images.fotmob.com/image_resources/logo/"
                f"leaguelogo/{league_id}.png"
            ),
        }


class FotMobTopScorerSensor(
    CoordinatorEntity[FotMobLeaguesCoordinator], SensorEntity
):
    """Show the top scorer for a FotMob league."""

    _attr_icon = "mdi:soccer"

    def __init__(self, coordinator: FotMobLeaguesCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        league_name = coordinator.data["league_name"]
        league_id = coordinator.league_id

        self._attr_name = f"{league_name} Top scorer"
        self._attr_unique_id = f"{league_id}_top_scorer"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(league_id))},
            name=league_name,
            manufacturer="FotMob",
            model="League",
            configuration_url=f"https://www.fotmob.com/leagues/{league_id}/overview",
        )

    @property
    def native_value(self) -> str | None:
        """Return the top scorer's name."""
        scorers = self.coordinator.data["scorers"]
        return scorers[0]["name"] if scorers else None

    @property
    def available(self) -> bool:
        """Return whether FotMob has a non-empty goals list."""
        return super().available and bool(self.coordinator.data.get("scorers"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the complete FotMob goals list."""
        scorers = self.coordinator.data["scorers"]
        return {
            "scorers": scorers,
            "totalGoals": sum(scorer["stat"] for scorer in scorers),
        }

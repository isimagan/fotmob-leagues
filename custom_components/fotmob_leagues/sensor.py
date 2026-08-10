"""Sensor platform for the FotMob Leagues integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FotMobLeaguesConfigEntry
from .const import DOMAIN
from .coordinator import FotMobLeaguesCoordinator

_REMOVED_PLAYER_STATISTIC_SENSOR_KEYS = (
    "top_scorer",
    "assist",
    "goal_points",
    "yellow_cards",
    "red_cards",
    "best_rated",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FotMobLeaguesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the league sensor."""
    entity_registry = er.async_get(hass)
    league_id = entry.runtime_data.league_id

    for sensor_key in _REMOVED_PLAYER_STATISTIC_SENSOR_KEYS:
        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR,
            DOMAIN,
            f"{league_id}_{sensor_key}",
        )
        if entity_id is not None:
            entity_registry.async_remove(entity_id)

    async_add_entities([FotMobTableSensor(entry.runtime_data)])


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

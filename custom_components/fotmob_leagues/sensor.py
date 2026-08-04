"""Sensor platform for the FotMob Leagues integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FotMobLeaguesConfigEntry
from .const import DOMAIN
from .coordinator import FotMobLeaguesCoordinator


@dataclass(frozen=True, kw_only=True)
class FotMobPlayerStatisticEntityDescription(SensorEntityDescription):
    """Describe a FotMob player statistic sensor."""

    data_key: str
    attribute_key: str
    total_attribute_key: str | None = None


PLAYER_STATISTIC_SENSORS = (
    FotMobPlayerStatisticEntityDescription(
        key="top_scorer",
        name="Top scorer",
        icon="mdi:soccer",
        data_key="scorers",
        attribute_key="scorers",
        total_attribute_key="totalGoals",
    ),
    FotMobPlayerStatisticEntityDescription(
        key="assist",
        name="Assist",
        icon="mdi:soccer-field",
        data_key="assists",
        attribute_key="assists",
    ),
    FotMobPlayerStatisticEntityDescription(
        key="goal_points",
        name="Goal points",
        icon="mdi:counter",
        data_key="goal_points",
        attribute_key="goalPoints",
    ),
    FotMobPlayerStatisticEntityDescription(
        key="yellow_cards",
        name="Yellow cards",
        icon="mdi:card",
        data_key="yellow_cards",
        attribute_key="yellowCards",
        total_attribute_key="totalYellowCards",
    ),
    FotMobPlayerStatisticEntityDescription(
        key="red_cards",
        name="Red cards",
        icon="mdi:card",
        data_key="red_cards",
        attribute_key="redCards",
        total_attribute_key="totalRedCards",
    ),
    FotMobPlayerStatisticEntityDescription(
        key="best_rated",
        name="Best rated",
        icon="mdi:star",
        data_key="ratings",
        attribute_key="ratings",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FotMobLeaguesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the league sensors."""
    async_add_entities(
        [
            FotMobTableSensor(entry.runtime_data),
            *(
                FotMobPlayerStatisticSensor(entry.runtime_data, description)
                for description in PLAYER_STATISTIC_SENSORS
            ),
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


class FotMobPlayerStatisticSensor(
    CoordinatorEntity[FotMobLeaguesCoordinator], SensorEntity
):
    """Show the leading player for a FotMob league statistic."""

    entity_description: FotMobPlayerStatisticEntityDescription

    def __init__(
        self,
        coordinator: FotMobLeaguesCoordinator,
        description: FotMobPlayerStatisticEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        league_name = coordinator.data["league_name"]
        league_id = coordinator.league_id

        self.entity_description = description
        self._attr_name = f"{league_name} {description.name}"
        self._attr_unique_id = f"{league_id}_{description.key}"
        self._attr_icon = description.icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(league_id))},
            name=league_name,
            manufacturer="FotMob",
            model="League",
            configuration_url=f"https://www.fotmob.com/leagues/{league_id}/overview",
        )

    @property
    def native_value(self) -> str | None:
        """Return the leading player's name."""
        statistics = self.coordinator.data[self.entity_description.data_key]
        return statistics[0]["name"] if statistics else None

    @property
    def available(self) -> bool:
        """Return whether FotMob has a non-empty statistic list."""
        return super().available and bool(
            self.coordinator.data.get(self.entity_description.data_key)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the complete FotMob player statistic list."""
        statistics = self.coordinator.data[self.entity_description.data_key]
        attributes = {self.entity_description.attribute_key: statistics}
        if self.entity_description.total_attribute_key is not None:
            attributes[self.entity_description.total_attribute_key] = sum(
                statistic["stat"] for statistic in statistics
            )
        return attributes

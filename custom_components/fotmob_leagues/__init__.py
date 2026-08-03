"""The FotMob Leagues integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_LEAGUE_ID
from .coordinator import FotMobLeaguesCoordinator

PLATFORMS = [Platform.SENSOR]

type FotMobLeaguesConfigEntry = ConfigEntry[FotMobLeaguesCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: FotMobLeaguesConfigEntry
) -> bool:
    """Set up FotMob Leagues from a config entry."""
    coordinator = FotMobLeaguesCoordinator(hass, entry.data[CONF_LEAGUE_ID])
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.config_entries.async_update_entry(entry, title=coordinator.data["league_name"])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FotMobLeaguesConfigEntry
) -> bool:
    """Unload a FotMob Leagues config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

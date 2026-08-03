"""Config flow for the FotMob Leagues integration."""

from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_LEAGUE_ID, DOMAIN


class FotMobLeaguesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FotMob Leagues."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial configuration step."""
        if user_input is not None:
            league_id = user_input[CONF_LEAGUE_ID]

            await self.async_set_unique_id(str(league_id))
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"FotMob league {league_id}",
                data={CONF_LEAGUE_ID: league_id},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LEAGUE_ID): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    )
                }
            ),
        )

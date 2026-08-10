"""Config flow for the FotMob Leagues integration."""

from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_LEAGUE_ID, DOMAIN, LEAGUE_LOGO_URL
from .coordinator import (
    FotMobConnectionError,
    InvalidFotMobLeagueError,
    async_fetch_league_data,
)


class FotMobLeaguesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FotMob Leagues."""

    VERSION = 1

    _league_id: int
    _league_name: str

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate a league ID entered by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            league_id = user_input[CONF_LEAGUE_ID]

            try:
                league_data = await async_fetch_league_data(self.hass, league_id)
            except InvalidFotMobLeagueError:
                errors["base"] = "invalid_league"
            except FotMobConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(str(league_id))
                self._abort_if_unique_id_configured()

                self._league_id = league_id
                self._league_name = league_data["league_name"]
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LEAGUE_ID): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    )
                }
            ),
            errors=errors,
        )

    @override
    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm the validated league."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._league_name,
                data={CONF_LEAGUE_ID: self._league_id},
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "league_id": str(self._league_id),
                "league_name": self._league_name,
                "league_logo_url": LEAGUE_LOGO_URL.format(
                    league_id=self._league_id
                ),
            },
        )

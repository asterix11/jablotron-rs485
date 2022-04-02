from homeassistant import config_entries
from .const import DOMAIN
import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

class JablotronRS485ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    data = None

    async def async_step_user(self, info):
        """Config flow step user."""
        if info is not None:
            if not info.get("host") is None and not info.get("port") is None and not info.get("pin") is None and not info.get("pgcount") is None:
                self.data = info
                return await self.async_step_finish()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("port"): int,
                vol.Required("pin"): str,
                vol.Required("pgcount"): int,
            })
        )
    
    async def async_step_finish(self, user_input=None):
        return self.async_create_entry(title="Jablotron RS485", data=self.data)

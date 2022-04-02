import logging

PLATFORMS = ["switch"]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """Setup Jablotron RS485."""
    _LOGGER.info("Setting up.")
    return True

async def async_setup_entry(hass, config_entry):
    """Set up entry."""
    _LOGGER.info("Initializing config entry.")
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True
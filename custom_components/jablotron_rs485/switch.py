"""Support for lights through the Jablotron API."""
from __future__ import annotations

from collections.abc import Sequence

import logging
import colorsys
import asyncio

from homeassistant.components.switch import (
    SwitchEntity
)
import homeassistant.util.color as color_util
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.util import Throttle
from datetime import timedelta

from .api import JablotronRS485TerminalAPI
from .const import ATTR_DEVICE_TYPE_SWITCH, DOMAIN


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the WiZ Light platform from legacy config."""

    return True


async def async_setup_entry(hass, config_entry, async_add_devices):
    try:
        api = JablotronRS485TerminalAPI(hass, config_entry.data)
        device_registry = await hass.helpers.device_registry.async_get_registry()
        
        devices = await api.getDevices(ATTR_DEVICE_TYPE_SWITCH)
        for i in devices:
            try:
                async_add_devices(
                    [JablotronRS485Switch(api, i)],
                    update_before_add=True,
                )
                device_registry.async_get_or_create(
                    config_entry_id=config_entry.entry_id,
                    connections={(dr.CONNECTION_UPNP, str(i))},
                    identifiers={(DOMAIN, str(i))},
                    manufacturer="Jablotron",
                    name="PG" + str(i),
                    model="Switch V1.0",
                    sw_version=0.2,
                )
            except Exception as e:
                _LOGGER.error("Can't add Jablotron Switch with ID %s.", str(i))
                _LOGGER.error(e)
    except Exception as e:
        _LOGGER.error("Can't add Jablotron Switches:")
        _LOGGER.error(e)
        return False

    return True


def get_capabilities(capabilities: Sequence[str]) -> Sequence[str] | None:
    """Return all capabilities supported if minimum required are present."""
    supported = [
        Capability.switch,
    ]
    return supported


class JablotronRS485Switch(SwitchEntity):
    """Define a Jablotron Switch."""

    def __init__(self, api, device_id):
        """Initialize a Jablotron Switch."""
        self._lock = asyncio.Lock()
        self._api = api
        self._device_id = str(device_id)
        self._name = "PG" + str(device_id)
        self._mac = None
        self._brightness = 0
        self._hs_color = [0, 0]
        self._state = False
        self._supported_features = self._determine_features()
        self._logger = logging.getLogger(
            ("%s:%s:<%s>") % (__name__, self.__class__.__name__, self._device_id)
        )

    def _determine_features(self):
        """Get features supported by the device."""
        return None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        try:
            await self._lock.acquire()
            self._logger.info("On")
            if not self._state:
                await self._api.setPGState(self._device_id, True)
                self._state = True
            self.async_schedule_update_ha_state(True)
        finally:
            self._lock.release()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        try:
            await self._lock.acquire()
            self._logger.info("Off")
            self._state = False
            await self._api.setPGState(self._device_id, False)    
            self.async_schedule_update_ha_state(True)
        finally:
            self._lock.release()

    async def async_update(self):
        """Update entity attributes when the device status has changed."""
        self._logger.info(
            "HIER PASSIERT FIESES ZEUGS! Diesmal mit jenem Jablotron Switch: %s",
            self._device_id,
        )

        self._state = await self._api.getPGState(self._device_id)

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self.unique_id)
            },
            #"connections": {(dr.CONNECTION_NETWORK_MAC, self._mac)},
            "name": self.name,
            "manufacturer": "Jablotron",
            "model": "PG",
            "sw_version": 0.2,
        }

    @property
    def unique_id(self):
        """Return light unique_id."""
        return self._device_id

    @property
    def name(self):
        """Return the ip as name of the device if any."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

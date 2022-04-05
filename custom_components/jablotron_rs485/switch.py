"""Support for lights through the Jablotron API."""
from __future__ import annotations

from collections.abc import Sequence

import logging
import colorsys
import asyncio
import threading

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

from telnetlib import Telnet

import time

from .const import (
    ATTR_DEVICE_TYPE_SWITCH,
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_PIN,
    CONF_PGCOUNT,
    CMD_PGSTATE,
    CMD_PGON,
    CMD_PGOFF,
    OBJ_PG
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the WiZ Light platform from legacy config."""

    return True


async def async_setup_entry(hass, config_entry, async_add_devices):
    try:
        device_registry = await hass.helpers.device_registry.async_get_registry()
        
        devices = []
        for i in range(1, config_entry.data.get(CONF_PGCOUNT) + 1):
            devices.append(i)

        for i in devices:
            try:
                async_add_devices(
                    [JablotronRS485Switch(i, config_entry.data)],
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

    def __init__(self, device_id, config):
        """Initialize a Jablotron Switch."""
        self._lock = asyncio.Lock()
        self._device_id = str(device_id)
        self._name = "PG" + str(device_id)
        self._mac = None
        self._brightness = 0
        self._hs_color = [0, 0]
        self._state = False
        self._supported_features = self._determine_features()
        self._config = config
        self._telnet = Telnet(self._config.get(CONF_HOST), self._config.get(CONF_PORT))
        self._logger = logging.getLogger(
            ("%s:%s:<%s>") % (__name__, self.__class__.__name__, self._device_id)
        )
        self._thread = threading.Thread(target=self._updater, args=())
        self._thread.start()

    def _updater(self):
        while True:
            try:
                line = self._telnet.read_until(b"\n", timeout = 0.01)
                msg = line.decode("utf-8").replace("\n", "").strip()
                splitted = msg.split(" ")
                if (splitted[0] == OBJ_PG and int(splitted[1]) == int(self._device_id)):
                    if (splitted[2] == "ON" and self._state != True):
                        self._state = True
                        self.async_schedule_update_ha_state(True)
                    elif (splitted[2] == "OFF" and self._state != False):
                        self._state = False
                        self.async_schedule_update_ha_state(True)
            except EOFError as e:
                print(e)
                self._telnet = Telnet(self._config.get(CONF_HOST), self._config.get(CONF_PORT))
            except Exception as e:
                print(e)

    async def _request(self, command, _object, index):
        try:
            self._telnet.write(bytes(self._config.get(CONF_PIN)+" "+command+" "+str(index)+"\n",'UTF-8'))
        except Exception as e:
            self._logger.error("Error while executing telnet query:")
            self._logger.error(e)
            return None
    
    async def setPGState(self, index, state):
        if (state):
            return (await self._request(CMD_PGON, OBJ_PG, index))
        else:
            return (await self._request(CMD_PGOFF, OBJ_PG, index))
    
    async def getPGState(self, index):
        return (await self._request(CMD_PGSTATE, OBJ_PG, index))

    def _determine_features(self):
        """Get features supported by the device."""
        return None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        try:
            await self._lock.acquire()
            self._logger.info("On")
            if not self._state:
                await self.setPGState(self._device_id, True)
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
            await self.setPGState(self._device_id, False)    
            self.async_schedule_update_ha_state(True)
        finally:
            self._lock.release()

    async def async_update(self):
        """Update entity attributes when the device status has changed."""
        self._logger.info(
            "HIER PASSIERT FIESES ZEUGS! Diesmal mit jenem Jablotron Switch: %s",
            self._device_id,
        )

        await self.getPGState(self._device_id)

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

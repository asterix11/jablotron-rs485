import asyncio
import logging, os
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import json
import time
from telnetlib import Telnet

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PIN,
    CONF_PGCOUNT,
    CMD_PGSTATE,
    CMD_PGON,
    CMD_PGOFF,
    OBJ_PG
)

class JablotronRS485TerminalAPI:
    def __init__(self, hass, config):
        self._hass = hass
        self._config = config
        self._logger = logging.getLogger(__name__ + ":" + self.__class__.__name__)

    async def _request(self, command, _object, index, wait):
        try:
            with Telnet(self._config.get(CONF_HOST), self._config.get(CONF_PORT)) as tn:
                tn.write(bytes(self._config.get(CONF_PIN)+" "+command+" "+str(index)+"\n",'UTF-8'))
                if not wait:
                    tn.close()
                    return None
                arrived = [False, False]
                result = False
                while not arrived[0] or not arrived[1]:
                    line = tn.read_until(b"\n")
                    msg = line.decode("utf-8").replace("\n", "").strip()
                    if (msg.replace(":", "") == command):
                        arrived[0] = True
                    if (arrived[0]):
                        splitted = msg.split(" ")
                        if (splitted[0] == _object):
                            arrived[1] = True
                            if (splitted[2] == "ON"):
                                result = True
                            elif (splitted[2] == "OFF"):
                                result = False
                tn.close()
                return result
        except Exception as e:
            self._logger.error("Error while executing telnet query:")
            self._logger.error(e)
            return None

    async def sleep(self, _time):
        def _sleep():
            time.sleep(_time)
        await self._hass.async_add_executor_job(_sleep)

    async def getDevices(self, _type):
        devices = []
        for i in range(1, self._config.get(CONF_PGCOUNT) + 1):
            devices.append(i)

        return devices
    
    async def getPGState(self, index):
        return (await self._request(CMD_PGSTATE, OBJ_PG, index, True))
    
    async def setPGState(self, index, state):
        if (state):
            return (await self._request(CMD_PGON, OBJ_PG, index, False))
        else:
            return (await self._request(CMD_PGOFF, OBJ_PG, index, False))

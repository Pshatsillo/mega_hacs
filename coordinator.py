"""DataUpdateCoordinator for the Adax component."""
import json
import logging
import urllib

from typing import Any, cast

import aiohttp
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import SCAN_INTERVAL, DOMAIN, PATT_FW

_LOGGER = logging.getLogger(__name__)

type MegaConfigEntry = ConfigEntry[MegaCoordinator]


class MegaCoordinator(DataUpdateCoordinator[dict[str, Any] | None]):
    """Coordinator for updating data to and from Mega."""

    def __init__(self, hass: HomeAssistant, entry: MegaConfigEntry) -> None:
        """Initialize the Mega coordinator."""
        super().__init__(
            hass,
            config_entry=entry,
            logger=_LOGGER,
            name="AdaxLocal",
            update_interval=SCAN_INTERVAL,
        )
        self.firmware = None
        self.ports_count = None
        self.entry = entry
        self.hass = hass
        self.sensorsList = None
        self.mega = hass.data[DOMAIN][entry.entry_id]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Mega."""
        _LOGGER.warning("MegaCoordinator update")
        return cast(dict[str, Any], "result")

    async def async_config_entry_first_refresh(self) -> None:
        timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                        f"https://raw.githubusercontent.com/Pshatsillo/openhab2MegadBinding/refs/heads/V4_n/sensors.json") as resp:
                    self.sensorsList = json.loads(await resp.text())
                async with session.get(self.mega.base_url) as resp:
                    response = await resp.text()
        except Exception as msg:
            _LOGGER.warning(f"MegaCoordinator http request error {type(msg)} args {msg.args}")
        if "[45" in response:
            self.ports_count = 45
        self.firmware = PATT_FW.search(response).groups()[0]

        self.mega.ports = await get_all_ports_data(self.mega.base_url, self.ports_count)
        _LOGGER.warning(f"MegaCoordinator async_config_entry_first_refresh")
        await super().async_config_entry_first_refresh()


async def get_all_ports_data(num_ports):
    timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
    ports = {}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for port in range(num_ports):
            # Выполняем запросы строго по одному
            result = await fetch_port_data(session, port, None)
            if result is not None:
                ports[result["port"]] = result

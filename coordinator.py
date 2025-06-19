"""DataUpdateCoordinator for the Adax component."""
import json
import logging
import re
import urllib

from typing import Any, cast

import aiohttp
import requests
from bs4 import BeautifulSoup

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

#TODO need to be adopted
def parse_port_data(port, html, ext):
    try:
        soup = BeautifulSoup(html, "html.parser")
        # form = soup.find("form")
        form = soup.select("form")[-1] if soup.select("form") else None

        if ext is not None:
            ety = form.find("select", {"name": "ety"})
            ept = form.find("input", {"name": "ept"})

            ety_value = ety.find("option", selected=True)["value"] if ety else None
            ept_value = ept["value"] if ept else None

            if ety_value is not None and ety_value != "255":

                title = None
                config = None
                if ept_value and ept_value is not None:
                    title = re.sub(r'\{.*?\}', '', ept_value)
                    title = title.strip()
                    config = parse_as_json(ept_value)

                return {
                    "etype": int(ety_value),
                    "etitle": title,
                    "config": config
                }
            else:
                return None

        else:
            pty = form.find("select", {"name": "pty"})
            m = form.find("select", {"name": "m"})
            emt = form.find("input", {"name": "emt"})
            d = form.find("select", {"name": "d"})
            inta = form.find("input", {"name": "inta"})

            pty_value = pty.find("option", selected=True)["value"] if pty else None
            m_value = m.find("option", selected=True)["value"] if m else "0"
            emt_value = emt["value"] if emt else None
            d_value = d.find("option", selected=True)["value"] if d else "0"
            inta_value = inta["value"] if inta else None
            if inta_value and inta_value is not None:
                port_inta[int(inta_value)] = port

            if pty_value is not None and pty_value != "255":
                # config = parse_as_json(emt_value)
                # _LOGGER.debug(f"config: {config}")
                title = None
                config = None
                if emt_value:
                    title = re.sub(r'\{.*?\}', '', emt_value)
                    title = title.strip()
                    config = parse_as_json(emt_value)
                return {
                    "port": port,
                    "type": int(pty_value),
                    "mode": int(m_value),
                    "dev": int(d_value),
                    "bus": {},
                    "parent": 255,
                    "title": title,
                    "config": config
                }
            else:
                return None

    except Exception as e:
        _LOGGER.debug(f"Ошибка парсинга данных для порта {port}: {e}")
        return None

async def fetch_port_data(session, base_url, port, ext):
    url = f"{base_url}?pt={port}"
    if ext is not None:
        url += f"&ext={ext}"
    try:
        #if port:
        #    await asyncio.sleep(0.15)
        _LOGGER.debug(f"Fetching URL: {url}")
        async with session.get(url) as response:
            html = await response.text(encoding="windows-1251")
            return parse_port_data(port, html, ext)
    except Exception as e:
        _LOGGER.debug(f"Ошибка при запросе порта {port}: {e}")
        return None


async def get_all_ports_data(base_url, num_ports):
    timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
    ports = {}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for port in range(num_ports):
            # Выполняем запросы строго по одному
            result = await fetch_port_data(session, base_url, port, None)
            if result is not None:
                ports[result["port"]] = result

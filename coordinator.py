"""DataUpdateCoordinator for the Adax component."""
import json
import logging
import re
from typing import Any, cast

import aiohttp
import httpx
import requests
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import SCAN_INTERVAL, DOMAIN, PATT_FW
from .enums import Type, Mode, Dev, ModeI2C, DevI2C, MCP230XXType, PCA9685Type
from .model import Mega

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
            name="MegaCoordinator",
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
        for port, port_config in self.mega.ports.items():
            cmd = f"pt={port}&cmd=get"
            response = await self.send_request(cmd)
            if response:
                self.mega.ports[port].state = response
                # _LOGGER.warning(f" State of port {port} is {response}")
                if port_config.dev is DevI2C.PCA9685 or port_config.dev is DevI2C.MCP230XX:
                    response = response.split(";")
                    # _LOGGER.warning(f" State of port {port} is {response}")
                    for ext_port_number in range(16):
                        self.mega.ports[port].extender_port[ext_port_number].state = response[ext_port_number]
        return cast(dict[str, Any], "result")

    async def async_config_entry_first_refresh(self) -> None:
        timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
        response = None
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                        f"https://raw.githubusercontent.com/Pshatsillo/openhab2MegadBinding/refs/heads/V4_n/sensors.json") as resp:
                    self.sensorsList = json.loads(await resp.text())
                async with session.get(self.mega.base_url) as resp:
                    response = await resp.text()
        except Exception as msg:
            _LOGGER.warning(f"MegaCoordinator http request error {type(msg)} args {msg.args}")
        if response is not None:
            if "[45" in response:
                self.ports_count = 45
            self.firmware = PATT_FW.search(response).groups()[0]
            await self.get_all_ports_config(self.mega.base_url, self.ports_count)
        # _LOGGER.warning(f"MegaCoordinator async_config_entry_first_refresh")
        await super().async_config_entry_first_refresh()

    async def get_all_ports_config(self, base_url, num_ports):
        timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for port in range(num_ports):
                # Выполняем запросы строго по одному
                result: Mega.Port = await fetch_port_config(self.mega, session, base_url, port)
                if result is not None:
                    self.mega.ports[port] = result
                    if result.port_type is Type.I2C and result.dev is DevI2C.MCP230XX or result.dev is DevI2C.PCA9685:
                        for port_extender in range(16):
                            extender_result = await fetch_port_config(self.mega, session, base_url, port, port_extender)
                            result.extender_port[port_extender] = extender_result

    async def send_request(self, cmd):
        url = f"{self.mega.base_url}?{cmd}"
        timeout = aiohttp.ClientTimeout(total=self.mega.http_timeout, connect=1, sock_connect=1, sock_read=1)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        rsp = await response.text(encoding="windows-1251")
                        return rsp
            except aiohttp.ClientError as e:
                _LOGGER.debug(f"Ошибка отправки запроса: {e} url:{url}")
        return False


def scan_port_for_sensors(mega, port, inited_sensor_type):
    response = httpx.get(f'{mega.base_url}/?pt={port}&cmd=scan')
    sensors = {}
    sensors["Test"] = "wrr"
    sensors["Test1"] = "wrt"
    _LOGGER.warning(f"inited sensor: {inited_sensor_type} at port {port}")
    return sensors


def parse_port_config(mega, port, html, ext=None):
    try:
        soup = BeautifulSoup(html, "html.parser")
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
                external_type = None
                if mega.ports[port].dev is DevI2C.MCP230XX:
                    external_type = MCP230XXType(int(ety_value))
                else:
                    if mega.ports[port].dev is DevI2C.PCA9685:
                        external_type = PCA9685Type(int(ety_value))
                return Mega.Port.Extender(external_type, title, config)
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

            if pty_value is not None and pty_value != "255":
                title = None
                config = None
                if emt_value:
                    title = re.sub(r'\{.*?\}', '', emt_value)
                    title = title.strip()
                    config = parse_as_json(emt_value)
                if Type(int(pty_value)) is Type.I2C:
                    mode = ModeI2C(int(m_value))
                    if d_value == 20 or d_value == 21 or d_value == 0:
                        dev = DevI2C(int(d_value))
                    else:
                        #TODO сделать парсинг датчиков на порту
                        inited_sensor_type = d.find("option", selected=True).next if d else None
                        dev = scan_port_for_sensors(mega, port, inited_sensor_type)
                else:
                    mode = Mode(int(m_value))
                    dev = Dev(int(d_value))
                if mode is not ModeI2C.SCL:
                    return Mega.Port(port, Type(int(pty_value)), mode, dev, inta_value, title, config)
                return None
            else:
                return None

    except Exception as e:
        _LOGGER.error(f"Ошибка парсинга данных для порта {port}: {e.args}")
        return None


async def fetch_port_config(mega, session, base_url, port, ext=None):
    url = f"{base_url}?pt={port}"
    if ext is not None:
        url += f"&ext={ext}"
    try:
        _LOGGER.debug(f"Fetching URL: {url}")
        async with session.get(url) as response:
            html = await response.text(encoding="windows-1251")
            return parse_port_config(mega, port, html, ext)
    except Exception as e:
        _LOGGER.debug(f"Ошибка при запросе порта {port}: {e}")
        return None


def parse_as_json(data):
    # Извлекаем текст внутри первых фигурных скобок
    match = re.search(r'\{.*?\}', data)
    if not match:
        return None
        # raise ValueError("No JSON-like structure found in the input string.")

    json_part = match.group(0)  # Достаём текст, включая фигурные скобки
    # Убираем пробелы и кавычки
    json_part = re.sub(r'[\'"\s]', '', json_part).lower()
    json_like = '{' + ','.join(
        f'"{k}":"{v}"' for k, v in (pair.split(':', 1) for pair in re.split(r'[;,]', json_part.strip('{}')))) + '}'

    # _LOGGER.debug(f"json like config: {json_like}")

    return json.loads(json_like)

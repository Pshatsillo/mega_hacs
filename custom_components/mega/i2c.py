import json
import logging
import os
import typing
from dataclasses import dataclass, astuple
from urllib.parse import parse_qsl, urlparse

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from .const import DOMAIN, CONF_LOCAL_SENSORS_LIST, CONF_SENSORS_LIST, CONF_SENSORS_URL

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    LIGHT_LUX,
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfTemperature, UnitOfPressure, CONCENTRATION_PARTS_PER_CUBIC_METER,
)
from collections import namedtuple


# DeviceType = namedtuple('DeviceType', 'device_class,unit_of_measurement,suffix')
lg = logging.getLogger(__name__)
@dataclass
class DeviceType:
    device_class: typing.Optional[str] = None
    unit_of_measurement: typing.Optional[str] = None
    suffix: typing.Optional[str] = None
    delay: typing.Optional[float] = None


async def parse_scan_page(mega, page: str, inited_sensor: str = None):
    ret = []
    req = []
    sensors_list = None
    local_sensors = None
    page = BeautifulSoup(page, features="lxml")
    #reading local JSON file, with name CONF_LOCAL_SENSORS_LIST in const file
    if os.path.exists(f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_LOCAL_SENSORS_LIST}"):
        lg.debug(f"The path '{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_LOCAL_SENSORS_LIST}' exists.")
        local_sensors = await read_sensors_file(f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_LOCAL_SENSORS_LIST}")
    else:
        lg.debug(f"The path '{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_LOCAL_SENSORS_LIST}' does not exist, creating")
        await write_sensors_file(f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_LOCAL_SENSORS_LIST}")
    # downloading and reading file sensors from github
    if os.path.exists(f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_SENSORS_LIST}"):
        json_data = None
        remote_sensors_list = None
        lg.debug(f"The path '{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_SENSORS_LIST}' exists.")
        remote_sensors_file = await read_sensors_file(f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_SENSORS_LIST}")
        remote_sensors_list = await download_sensors()
        if remote_sensors_file is not None and remote_sensors_list is not None:
                if remote_sensors_file["sensors"] == remote_sensors_list:
                    lg.debug("list is identical")
                else:
                    lg.debug("not ident")
                    try:
                        async with aiofiles.open(
                                f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_SENSORS_LIST}",
                                mode='w') as f:
                            await f.write(sensors_list)
                    except Exception as e:
                        lg.debug(f"An error occurred: {e}")

    else:
        lg.debug(f"The path '{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_SENSORS_LIST}' does not exist, creating")
        try:
            timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                        CONF_SENSORS_URL) as resp:
                    response = await resp.text()
                    async with aiofiles.open(f"{mega.hass.data["integrations"][DOMAIN].file_path}/{CONF_SENSORS_LIST}",
                                             mode='w') as f:
                        await f.write(response)
                    sensors_list = json.loads(response)["sensors"]
        except Exception as msg:
            lg.debug(f"http request error {type(msg)} args {msg.args}")
    for x in page.find_all('a'):
        params = x.get('href')
        if params is None:
            continue
        params = dict(parse_qsl(urlparse(params).query))
        dev = params.get('i2c_dev')
        if dev is None:
            continue
        classes = i2c_classes.get(dev, [])
        for i, c in enumerate(classes):
            _params = params.copy()
            if c is Skip:
                continue
            elif c is Request:
                req.append(_params)
                continue
            elif isinstance(c, Request):
                if c.delay:
                    _params['delay'] = c.delay
                req.append(_params)
                continue
            elif isinstance(c, DeviceType):
                c, m, suffix, delay = astuple(c)
                if delay is not None:
                    _params['delay'] = delay
            else:
                continue
            suffix = suffix or c
            if 'addr' in _params:
                suffix += f"_{_params['addr']}" if suffix else str(_params['addr'])
            if suffix:
                _dev = f'{dev}_{suffix}'
            else:
                _dev = dev
            if i > 0:
                _params['i2c_par'] = i

            ret.append({
                'id_suffix': _dev,
                'device_class': c,
                'params': _params,
                'unit_of_measurement': m,
            })
            req.append(_params)
    return req, ret


async def download_sensors():
    try:
        timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                    CONF_SENSORS_URL) as resp:
                remote_sensors_list = json.loads(await resp.text())["sensors"]
    except Exception as msg:
        lg.debug(f"http request error {type(msg)} args {msg.args}")
    return remote_sensors_list


async def write_sensors_file(path: str):
    try:
        async with aiofiles.open(path,
                                 mode='w') as f:
            await f.write("{}")
    except Exception as e:
        lg.debug(f"An error occurred: {e}")


async def read_sensors_file(path):
    try:
        async with aiofiles.open(path,
                                 mode='r', encoding='utf-8') as f:
            contents = await f.read()
            json_data = json.loads(contents)
    except json.JSONDecodeError:
        print(
            f"Error: Invalid JSON format in '{path}'")
        return None
    return json_data


class Skip:
    pass


@dataclass
class Request:
    delay: float = None


# timeout = aiohttp.ClientTimeout(total=2, connect=1, sock_connect=1, sock_read=1)
# response = None
# try:
#     async with aiohttp.ClientSession(timeout=timeout) as session:
#         async with session.get(
#                 SENSORS_JSON) as resp:
#             self.sensorsList = json.loads(await resp.text())["sensors"]
#         async with session.get(self.mega.base_url) as resp:
#             response = await resp.text()
# except Exception as msg:
#     _LOGGER.debug(f"MegaCoordinator http request error {type(msg)} args {msg.args}")

i2c_classes = {
    'htu21d': [
        DeviceType(SensorDeviceClass.HUMIDITY, PERCENTAGE, None),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
    ],
    'sht31': [
        DeviceType(SensorDeviceClass.HUMIDITY, PERCENTAGE, None, delay=1.5),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
    ],
    'max44009': [
        DeviceType(SensorDeviceClass.ILLUMINANCE, LIGHT_LUX, None)
    ],
    'bh1750': [
        DeviceType(SensorDeviceClass.ILLUMINANCE, LIGHT_LUX, None)
    ],
    'tsl2591': [
        DeviceType(SensorDeviceClass.ILLUMINANCE, LIGHT_LUX, None)
    ],
    'bmp180': [
        DeviceType(SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, None),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
    ],
    'bmx280': [
        DeviceType(SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, None),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
        DeviceType(SensorDeviceClass.HUMIDITY, PERCENTAGE, None)
    ],
    'scd4x': [
        Skip,
        DeviceType(SensorDeviceClass.CO2, CONCENTRATION_PARTS_PER_MILLION, None),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
        DeviceType(SensorDeviceClass.HUMIDITY, PERCENTAGE, None)
    ],
    'dps368': [
        DeviceType(SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, None),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
    ],
    'mlx90614': [
        Skip,
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, 'temp'),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, 'object'),
    ],
    'ptsensor': [
        Skip,
        Request(delay=3),  # запрос на измерение
        DeviceType(SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, None),
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
    ],
    'mcp9600': [
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),  # термопара
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),  # сенсор встроенный в микросхему
    ],
    't67xx': [
        DeviceType(SensorDeviceClass.CO2, CONCENTRATION_PARTS_PER_MILLION, None)
    ],
    'tmp117': [
        DeviceType(SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, None),
    ],
    'ads1115': [
        DeviceType(None, None, 'ch0'),
        DeviceType(None, None, 'ch1'),
        DeviceType(None, None, 'ch2'),
        DeviceType(None, None, 'ch3'),
    ],
    'ads1015': [
        DeviceType(None, None, 'ch0'),
        DeviceType(None, None, 'ch1'),
        DeviceType(None, None, 'ch2'),
        DeviceType(None, None, 'ch3'),
    ],
}

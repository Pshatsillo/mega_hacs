"""Platform for light integration."""
from __future__ import annotations

import asyncio
import logging
import typing
from datetime import timedelta, datetime
from functools import partial
from typing import Any

import requests
import voluptuous as vol
import colorsys
import time

from bs4 import BeautifulSoup

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode, ATTR_TARGET_TEMP_HIGH, \
    ATTR_TARGET_TEMP_LOW, ATTR_HVAC_MODE
from homeassistant.components.light import (
    PLATFORM_SCHEMA as LIGHT_SCHEMA,
    LightEntity,
    SUPPORT_COLOR,
    ColorMode,
    LightEntityFeature,
    # SUPPORT_WHITE_VALUE
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PORT,
    CONF_UNIQUE_ID,
    CONF_ID,
    CONF_DOMAIN, UnitOfTemperature, ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant
from .entities import MegaOutPort, BaseMegaEntity, safe_int, MegaPushEntity

from .hub import MegaD
from .const import (
    CONF_DIMMER,
    CONF_SWITCH,
    DOMAIN,
    CONF_CUSTOM,
    CONF_SKIP,
    CONF_LED,
    CONF_WS28XX,
    CONF_PORTS,
    CONF_WHITE_SEP,
    CONF_SMOOTH,
    CONF_ORDER,
    CONF_CHIP,
    RGB,
)
from .tools import int_ignore, map_reorder_rgb

lg = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=5)
SUPPORT_FLAGS = ClimateEntityFeature(0)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    mid = config_entry.data[CONF_ID]
    hub: MegaD = hass.data["mega"][mid]
    devices = []
    customize = hass.data.get(DOMAIN, {}).get(CONF_CUSTOM, {}).get(mid, {})
    skip = []
    if 'climate' in customize:
        for entity_id, conf in customize['climate'].items():
            data = await hub.request(pt=conf.get('temperature'))
            page = BeautifulSoup(data, features="lxml")
            target_temperature = page.find('input', attrs={'name': 'misc'})['value']
            relay_status = await hub.request(pt=conf.get('relay'), cmd='get')
            devices.append(
                MegaClimate(
                    mega=hub,
                    port=conf.get('temperature'),
                    temperature=conf.get('temperature'), relay=conf.get('relay'), unique_id=entity_id, target_temperature=target_temperature, relay_status=relay_status)
            )
    async_add_devices(devices)


class MegaClimate(ClimateEntity, MegaOutPort):
    def __init__(self, temperature: int, relay:int, unique_id:str,target_temperature, relay_status, *args, **kwargs):
        self._target_temperature_low = None
        self._target_temperature_high = None
        self._clim_unique_id = unique_id
        self._clim_name = unique_id
        self._attr_supported_features = SUPPORT_FLAGS
        self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_supported_features |= ClimateEntityFeature.TURN_ON
        self._attr_supported_features |= ClimateEntityFeature.TURN_OFF
        self._fan_modes = ["on_low", "on_high", "auto_low", "auto_high", "off"]
        self._swing_modes = ["auto", "1", "2", "3", "off"]
        if relay_status == "OFF":
            self._hvac_mode = HVACMode.OFF
        else:
            self._hvac_mode = HVACMode.HEAT
        self._hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._unit_of_measurement = UnitOfTemperature.CELSIUS
        self._target_temperature = float(target_temperature)
        self._temperature_sensor = temperature
        self._relay = relay
        super().__init__(*args, **kwargs)


    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return self._clim_unique_id
    @property
    def target_temperature(self) -> float:
        """Return the unique id."""
        return self._target_temperature
    @property
    def name(self) -> str:
        """Return the unique id."""
        return self._clim_name
    async def async_turn_on(self):
        """Turn the entity on."""
        await self.mega.request(pt=self._relay, cmd=f"{self._relay}:1")
        self.async_write_ha_state()
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._target_temperature = kwargs.get(ATTR_TEMPERATURE)
            await self.mega.request(pt=self._temperature_sensor, misc=kwargs.get(ATTR_TEMPERATURE))
        if (
            kwargs.get(ATTR_TARGET_TEMP_HIGH) is not None
            and kwargs.get(ATTR_TARGET_TEMP_LOW) is not None
        ):
            self._target_temperature_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
            self._target_temperature_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            self._hvac_mode = hvac_mode
        self.async_write_ha_state()
    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac target hvac state."""
        return self._hvac_mode
    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available operation modes."""
        return self._hvac_modes
    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self._unit_of_measurement
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new operation mode."""
        self._hvac_mode = hvac_mode
        if hvac_mode is HVACMode.OFF:
            await self.mega.request(pt=self._relay, cmd=f"{self._relay}:0")
        else:
            await self.mega.request(pt=self._relay, cmd=f"{self._relay}:1")
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return True

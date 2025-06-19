import logging
from typing import cast

import aiohttp

from homeassistant.components.light import LightEntity, LightEntityFeature, ColorMode
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import MegaConfigEntry, MegaCoordinator
from .model import Mega

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    mega_coordinator = cast(MegaCoordinator, entry.runtime_data)
    mega = hass.data[DOMAIN][entry.entry_id]
    switches = []
    switches.append(MegaLight(hass, 11,mega_coordinator, mega))
    switches.append(MegaLight(hass, 12, mega_coordinator, mega))
    switches.append(MegaLight(hass,  13, mega_coordinator, mega))
    async_add_entities(switches)


class MegaLight(CoordinatorEntity[MegaCoordinator], SwitchEntity):
    def __init__(self, hass,  port, coordinator: MegaCoordinator, mega: Mega):
        self.hass = hass
        self._unique_id = f"P{port}"
        self._attr_name = self._unique_id
        self.eport = None
        self._is_on = False
        self._brightness = None
        self.restore_brightness = None
        self.port = port
        self.coordinator = coordinator
        self.mega = mega
        super().__init__(coordinator)

    @property
    def device_info(self)-> DeviceInfo:
        return self.mega.device_info()
    async def async_turn_on(self, **kwargs):

            self.async_write_ha_state()  # Обновление состояния в Home Assistant


    async def async_turn_off(self, **kwargs):

            self.async_write_ha_state()  # Обновление состояния в Home Assistant

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def supported_features(self):
        return LightEntityFeature.TRANSITION

    @property
    def supported_color_modes(self):

            return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self):
            return ColorMode.ONOFF

    @property
    def brightness(self):
        if self.eport is not None:
            return self._brightness / 16
            #_LOGGER.debug(f"eport {self.eport}; brightness: {self._brightness}")
            #return self._brightness
        else:
            return self._brightness

    @property
    def is_on(self):
        return self._is_on

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.warning(f"Mega switch _handle_coordinator_update port: {self.hass.data[DOMAIN][self.mega.entry_id]}")
        super()._handle_coordinator_update()
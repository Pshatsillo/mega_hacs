import logging
import math
import re
from typing import cast, Optional

from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.color import value_to_brightness
from homeassistant.util.percentage import percentage_to_ranged_value
from .const import DOMAIN
from .coordinator import MegaCoordinator
from .enums import Type, Mode, MCP230XXType, PCA9685Type
from .model import Mega

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    mega_coordinator = cast(MegaCoordinator, entry.runtime_data)
    mega = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if "ports" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["ports"] = {}

    if entry.entry_id not in hass.data[DOMAIN]["ports"]:
        hass.data[DOMAIN]["ports"][entry.entry_id] = []

    for mega_port, port_entity in mega.ports.items():
        if port_entity.port_type is Type.OUT and port_entity.mode is Mode.PWM:
            entities.append(MegaLight(hass, mega_port, mega_coordinator, mega, None))
        if port_entity.extender_port:
            for ext_port, ext_port_entity in port_entity.extender_port.items():
                if ext_port_entity.port_type is PCA9685Type.PWM:
                    entities.append(MegaLight(hass, mega_port, mega_coordinator, mega, ext_port))

    hass.data[DOMAIN]["ports"][entry.entry_id].extend(entities)
    async_add_entities(entities)


class MegaLight(CoordinatorEntity[MegaCoordinator], LightEntity):
    def __init__(self, hass, port, coordinator: MegaCoordinator, mega: Mega, extender_port):
        self.hass = hass
        if extender_port is not None:
            self._unique_id = f"{mega.mega_id}_{port:02}e{extender_port:02}"
        else:
            self._unique_id = f"{mega.mega_id}_{port:02}"
        self._attr_name = self._unique_id
        self.eport = extender_port
        self._is_on = False
        self.port = port
        self.coordinator = coordinator
        self.mega = mega
        self._brightness = 0
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        return self.mega.device_info(self.coordinator.firmware)

    async def async_turn_on(self, **kwargs):
        cmd = ""
        if ATTR_BRIGHTNESS in kwargs:
            if self.eport is not None:
                    cmd = f"cmd={self.port}e{self.eport}:{kwargs[ATTR_BRIGHTNESS] * 16}"
                    self._brightness = kwargs[ATTR_BRIGHTNESS]
            else:
                cmd = f"cmd={self.port}:{kwargs[ATTR_BRIGHTNESS] }"
                self._brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            if self._brightness != 0 and self._brightness != 255:
                if self.eport is not None:
                    cmd = f"cmd={self.port}e{self.eport}:{self._brightness * 16}"
                else:
                    cmd = f"cmd={self.port}e{self.eport}:{self._brightness}"
            else:
                if self.eport is not None:
                        cmd = f"cmd={self.port}e{self.eport}:4095"
                        self._brightness = 255
                else:
                    cmd = f"cmd={self.port}:255"
                    self._brightness = 255
        response = await self.coordinator.send_request(cmd)
        if response:
            self._is_on = True
            self.async_write_ha_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        cmd = ""
        if self.eport is not None:
            if isinstance(self.eport, int):
                cmd = f"cmd={self.port}e{self.eport}:0"
        else:
            cmd = f"cmd={self.port}:0"
        response = await self.coordinator.send_request(cmd)
        if response:
            self._is_on = False
            self.async_write_ha_state()

    @property
    def brightness(self) -> Optional[int]:
        """Return the current brightness."""
        return self._brightness

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        return self._is_on

    @property
    def supported_color_modes(self):
            return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        state = ""
        if self.eport is not None:
            if isinstance(self.eport, int):
                if self.mega.ports[self.port].extender_port[self.eport].state:
                    state = self.mega.ports[self.port].extender_port[self.eport].state
                    state = int(state) / 16
        else:
            if self.mega.ports[self.port].state:
                state = self.mega.ports[self.port].state
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        if int(state) != 0:
            self._is_on = True
            self._brightness = int(state)
        else:
            self._is_on = False
        self.async_write_ha_state()
        super()._handle_coordinator_update()

    def incoming_update(self):
        state: str = ""
        if self.eport is not None:
            if isinstance(self.eport, int):
                if self.mega.ports[self.port].extender_port[self.eport].state:
                    state = self.mega.ports[self.port].extender_port[self.eport].state
        else:
            if self.mega.ports[self.port].state is not None:
                state = self.mega.ports[self.port].state
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        if state != 0:
            self._is_on = True
            self._brightness = state
        else:
            self._is_on = False
        self.async_write_ha_state()

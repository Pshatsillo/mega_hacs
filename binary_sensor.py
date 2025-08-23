import asyncio
import logging
import re
from time import sleep
from typing import cast

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
        port_extender_int = next(
            (
                port
                for port, port_entity in mega.ports.items()
                if port_entity.port_int == mega_port
            ), None
        )
        if port_extender_int is None:
            if port_entity.port_type is Type.IN:
                entities.append(MegaBinarySensor(hass, mega_port, mega_coordinator, mega, None))
                entities.append(MegaBinarySensor(hass, mega_port, mega_coordinator, mega, None, sp=True))
                entities.append(MegaBinarySensor(hass, mega_port, mega_coordinator, mega, None, lp=True))
            if port_entity.extender_port:
                for ext_port, ext_port_entity in port_entity.extender_port.items():
                    if ext_port_entity.port_type is MCP230XXType.IN:
                        entities.append(MegaBinarySensor(hass, mega_port, mega_coordinator, mega, ext_port))

    hass.data[DOMAIN]["ports"][entry.entry_id].extend(entities)
    async_add_entities(entities)


class MegaBinarySensor(CoordinatorEntity[MegaCoordinator], BinarySensorEntity):
    def __init__(self, hass, port, coordinator: MegaCoordinator, mega: Mega, extender_port, sp=None, lp=None):
        self.hass = hass
        if extender_port is not None:
            self._unique_id = f"{mega.mega_id}_{port:02}e{extender_port:02}"
        else:
            self._unique_id = f"{mega.mega_id}_{port:02}"
        if sp is not None:
            self._unique_id += f"_SP"
        if lp is not None:
            self._unique_id += f"_LP"
        self._attr_name = self._unique_id
        self.eport = extender_port
        self._is_on = False
        self.port = port
        self.coordinator = coordinator
        self.mega = mega
        self.sp = sp
        self.lp = lp
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        return self.mega.device_info(self.coordinator.firmware)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        return self._is_on

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.sp is None:
            state: str = ""
            if self.eport is not None:
                if isinstance(self.eport, int):
                    if self.mega.ports[self.port].extender_port[self.eport].state:
                        state = self.mega.ports[self.port].extender_port[self.eport].state
            else:
                if self.mega.ports[self.port].state:
                    state = self.mega.ports[self.port].state
            state = state.split("/")[0]
            # _LOGGER.warning(f"Mega port {self.port} state: {state}")
            if state == 'ON':
                self._is_on = True
            else:
                self._is_on = False
            self.async_write_ha_state()
            super()._handle_coordinator_update()

    def incoming_update(self, sp =None, lp=None, status=None):
        state: str = ""
        if self.eport is not None:
            if isinstance(self.eport, int):
                if self.mega.ports[self.port].extender_port[self.eport].state:
                    state = self.mega.ports[self.port].extender_port[self.eport].state
        else:
            if self.mega.ports[self.port].state:
                state = self.mega.ports[self.port].state
        state = state.split("/")[0]
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        if sp is None and self.sp is None and lp is None and self.lp is None:
            if state == 'ON':
                self._is_on = True
            else:
                self._is_on = False
            self.async_write_ha_state()
        elif self.sp is not None and lp is True:
            self.lp = True
        else:
            if self.sp is True and self.lp is True:
                self.lp = None
            elif status is not None:
                self._is_on = status
                self.async_write_ha_state()
        _LOGGER.warning(f"sensor: {self._unique_id}: sp = {self.sp}, lp = {self.lp}, status = {status}, http lp = {lp}, http sp = {sp}")

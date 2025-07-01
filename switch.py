import logging
from typing import cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import MegaCoordinator
from .enums import Type, Mode
from .model import Mega

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    mega_coordinator = cast(MegaCoordinator, entry.runtime_data)
    mega = hass.data[DOMAIN][entry.entry_id]
    switches = []
    for mega_port, port_entity in mega.ports.items():
        _LOGGER.warning(f"port {mega.ports[mega_port].port_type}")
        if port_entity.port_type is Type.OUT and port_entity.mode is Mode.SW:
            switches.append(MegaSwitch(hass, mega_port, mega_coordinator, mega, None))
    async_add_entities(switches)


class MegaSwitch(CoordinatorEntity[MegaCoordinator], SwitchEntity):
    def __init__(self, hass, port, coordinator: MegaCoordinator, mega: Mega, extender_port):
        self.hass = hass
        if extender_port:
            self._unique_id = f"P{port}e{extender_port}"
        else:
            self._unique_id = f"P{port}"
        self._attr_name = self._unique_id
        self.eport = extender_port
        self._is_on = False
        self.port = port
        self.coordinator = coordinator
        self.mega = mega
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        return self.mega.device_info()

    async def async_turn_on(self, **kwargs):
        cmd = f"cmd={self.port}:1"
        response = await self.coordinator.send_request(cmd)
        if response:
            self._is_on = True
            self.async_write_ha_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        cmd = f"cmd={self.port}:0"
        response = await self.coordinator.send_request(cmd)
        if response:
            self._is_on = False
            self.async_write_ha_state()

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        return self._is_on

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.warning(f"Mega switch _handle_coordinator_update port: {self.port}")
        state: str = ""
        if self.eport:
            if self.mega.ports[self.port].extender_port[self.eport].state:
                state = self.mega.ports[self.port].extender_port[self.eport].state
        else:
            if self.mega.ports[self.port].state:
                state = self.mega.ports[self.port].state
        # state = state.split("/")[0]
        _LOGGER.warning(f"Mega port {self.port} state: {state}")
        if state == 'ON':
            self._is_on = True
        else:
            self._is_on = False
        self.async_write_ha_state()
        super()._handle_coordinator_update()

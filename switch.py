import logging
from typing import cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CUSTOM_CONFIG
from .coordinator import MegaCoordinator
from .enums import Type, Mode, MCP230XXType, PCA9685Type
from .model import Mega

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    mega_coordinator = cast(MegaCoordinator, entry.runtime_data)
    mega = hass.data[DOMAIN][entry.entry_id]
    custom_config = None
    if mega.mega_id in hass.data[DOMAIN][CUSTOM_CONFIG]:
        custom_config = hass.data[DOMAIN][CUSTOM_CONFIG][mega.mega_id]
    entities = []

    if "ports" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["ports"] = {}

    if entry.entry_id not in hass.data[DOMAIN]["ports"]:
        hass.data[DOMAIN]["ports"][entry.entry_id] = []

    for mega_port, port_entity in mega.ports.items():
        if port_entity.port_type is Type.OUT and port_entity.mode is Mode.SW:
            entities.append(MegaSwitch(hass, mega_port, mega_coordinator, mega, None, custom_config=custom_config))
        if port_entity.port_type is Type.OUT and port_entity.mode is Mode.DS2413:
            entities.append(MegaSwitch(hass, mega_port, mega_coordinator, mega, "A", custom_config=custom_config))
            entities.append(MegaSwitch(hass, mega_port, mega_coordinator, mega, "B", custom_config=custom_config))
        if port_entity.extender_port:
            for ext_port, ext_port_entity in port_entity.extender_port.items():
                if ext_port_entity.port_type is MCP230XXType.OUT or ext_port_entity.port_type is PCA9685Type.SW:
                    entities.append(MegaSwitch(hass, mega_port, mega_coordinator, mega, ext_port, custom_config=custom_config))

    hass.data[DOMAIN]["ports"][entry.entry_id].extend(entities)
    async_add_entities(entities)


class MegaSwitch(CoordinatorEntity[MegaCoordinator], SwitchEntity):
    def __init__(self, hass, port, coordinator: MegaCoordinator, mega: Mega, extender_port,
                 custom_config=None):
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
        self.custom_config=custom_config
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        return self.mega.device_info(self.coordinator.firmware)

    async def async_turn_on(self, **kwargs):
        is_on = None
        if self.eport is not None:
            if isinstance(self.eport, int):
                cmd = f"cmd={self.port}e{self.eport}:1"
            else:
                cmd = f"cmd={self.port}{self.eport}:1"
        else:
            cmd = f"cmd={self.port}:1"
        response = await self.coordinator.send_request(cmd)
        if response:
            if self.invert:
                is_on = False
            else:
                is_on = True
        self._is_on = is_on
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        is_on = None
        if self.eport is not None:
            if isinstance(self.eport, int):
                cmd = f"cmd={self.port}e{self.eport}:0"
            else:
                cmd = f"cmd={self.port}{self.eport}:0"
        else:
            cmd = f"cmd={self.port}:0"
        response = await self.coordinator.send_request(cmd)
        if response:
            if self.invert:
                is_on = True
            else:
                is_on = False
            self._is_on = is_on
            self.async_write_ha_state()

    @property
    def invert(self):
        if self.custom_config is not None:
            return self.custom_config.get(self.port, {}).get("invert")
        return False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        return self._is_on

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        state: str = ""
        if self.eport is not None:
            if isinstance(self.eport, int):
                if self.mega.ports[self.port].extender_port[self.eport].state:
                    state = self.mega.ports[self.port].extender_port[self.eport].state
        else:
            if self.mega.ports[self.port].state:
                state = self.mega.ports[self.port].state
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        if state == 'ON':
            self._is_on = True
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
            if self.mega.ports[self.port].state:
                state = self.mega.ports[self.port].state
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        if state == 'ON':
            self._is_on = True
        else:
            self._is_on = False
        self.async_write_ha_state()

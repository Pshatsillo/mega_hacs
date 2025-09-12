from enum import StrEnum
from importlib import import_module
from typing import cast
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .enums import Type, Dev
from .model import Mega
from .coordinator import MegaConfigEntry, MegaCoordinator
from .const import DOMAIN
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: MegaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Mega sensors with config flow."""
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
                entities.append(MegaSensor(hass, mega_port, mega_coordinator, mega, None, counter=True))
            if port_entity.port_type is Type.I2C:
                if isinstance(port_entity.dev, dict):
                    for name, sensor in port_entity.dev.items():
                        for parameter, value in sensor["Parameters"].items():
                            entities.append(MegaSensor(hass, mega_port, mega_coordinator, mega, None, sensor=sensor, parameter={parameter:value}, sensor_name=name))
            if port_entity.port_type is Type.DSEN:
                if port_entity.dev is Dev.ONEWIREBUS:
                    for sensor_id in port_entity.misc:
                        entities.append(MegaSensor(hass, mega_port, mega_coordinator, mega, None, sensor_name=sensor_id))
                if port_entity.dev is Dev.ONEWIRE:
                    entities.append(MegaSensor(hass, mega_port, mega_coordinator, mega, None))
    hass.data[DOMAIN]["ports"][entry.entry_id].extend(entities)
    async_add_entities(entities)


class MegaSensor(CoordinatorEntity[MegaCoordinator], SensorEntity):
    """Representation of Mega sensor."""

    def __init__(self, hass, port, coordinator: MegaCoordinator, mega: Mega, extender_port, counter=None, sensor=None,
                 parameter:dict =None, sensor_name=None):
        self.hass = hass
        if extender_port is not None:
            self._unique_id = f"{mega.mega_id}_{port:02}e{extender_port:02}"
        elif sensor_name is not None and sensor is not None:
            self._unique_id = f"{mega.mega_id}_{port:02}_{sensor_name}_{ list(parameter.keys())[0]}"
        elif sensor_name is not None:
            self._unique_id = f"{mega.mega_id}_{port:02}_{sensor_name}"
        else:
            self._unique_id = f"{mega.mega_id}_{port:02}"
        if counter is not None:
            self._unique_id += f"_Counter"
            self._attr_entity_registry_enabled_default = False
        self._attr_name = self._unique_id
        self.eport = extender_port
        self._is_on = False
        self.port = port
        self.coordinator = coordinator
        self.mega = mega
        self.counter = counter
        self.sensor = sensor
        self.parameter = parameter
        self.sensor_name = sensor_name
        super().__init__(coordinator)

    @property
    def device_info(self)-> DeviceInfo:
        return self.mega.device_info(self.coordinator.firmware)

    @property
    def unique_id(self):
        return self._unique_id
    @property
    def device_class(self) -> SensorDeviceClass:
        if self.mega.ports[self.port].dev is Dev.ONEWIREBUS or self.mega.ports[self.port].dev is Dev.ONEWIRE:
            return SensorDeviceClass.TEMPERATURE
        elif self.sensor is None:
            return SensorDeviceClass.ENUM
        else:
            var = getattr(SensorDeviceClass, list(self.parameter.values())[0]["HASS"].upper())
            pass
            return var

    @property
    def native_unit_of_measurement(self):
        if self.mega.ports[self.port].dev is Dev.ONEWIREBUS or self.mega.ports[self.port].dev is Dev.ONEWIRE:
            return UnitOfTemperature.CELSIUS
        elif self.sensor is None:
            return None
        else:
            par = list(self.parameter.values())[0]["measurement"].split(".")
            if len(par) == 2:
                var = getattr(getattr(__import__('homeassistant.const', fromlist=[None]), f"{par[0]}"), par[1])
                return var
            else:
                var = getattr(__import__('homeassistant.const', fromlist=[None]), par[0])
                return var

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        state: str = ""
        if self.eport is not None:
            if isinstance(self.eport, int):
                if self.mega.ports[self.port].extender_port[self.eport].state:
                    state = self.mega.ports[self.port].extender_port[self.eport].state
        else:
            if self.mega.ports[self.port].dev is Dev.ONEWIREBUS:
                if self.sensor_name in self.mega.ports[self.port].state:
                    state = self.mega.ports[self.port].state[self.sensor_name]
                else:
                    _LOGGER.debug(f"sensor {self.sensor_name} not found in: {self.mega.ports[self.port].state}")
            elif self.sensor is None:
                    if self.mega.ports[self.port].state:
                        state = self.mega.ports[self.port].state
            else:
                state = self.mega.ports[self.port].state[self.sensor_name][list(self.parameter.keys())[0]]
        if self.counter:
            state = state.split("/")[1]
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        try:
            self.native_value = int(state)
        except:
            try:
                self.native_value = float(state)
            except:
             _LOGGER.debug(f"Cannot update sensor {self.name}")
        self.async_write_ha_state()
        super()._handle_coordinator_update()

    def incoming_update(self):
        state: str = ""
        if self.mega.ports[self.port].state:
            state = self.mega.ports[self.port].state
        if self.counter:
            state = state.split("/")[1]
        try:
            self.native_value = int(state)
        except:
            try:
                self.native_value = float(state)
            except:
                _LOGGER.debug(f"Cannot update sensor {self.name}")
        self.async_write_ha_state()

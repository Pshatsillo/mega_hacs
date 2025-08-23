from typing import cast
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .enums import Type
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
    hass.data[DOMAIN]["ports"][entry.entry_id].extend(entities)
    async_add_entities(entities)


class MegaSensor(CoordinatorEntity[MegaCoordinator], SensorEntity):
    """Representation of Mega sensor."""
    def __init__(self, hass, port, coordinator: MegaCoordinator, mega: Mega, extender_port, counter=None):
        self.hass = hass
        if extender_port is not None:
            self._unique_id = f"{mega.mega_id}_{port:02}e{extender_port:02}"
        else:
            self._unique_id = f"{mega.mega_id}_{port:02}"
        if counter is not None:
            self._unique_id += f"_Counter"
        self._attr_name = self._unique_id
        self.eport = extender_port
        self._is_on = False
        self.port = port
        self.coordinator = coordinator
        self.mega = mega
        self.counter = counter
        super().__init__(coordinator)

    @property
    def device_info(self)-> DeviceInfo:
        return self.mega.device_info(self.coordinator.firmware)

    @property
    def unique_id(self):
        return self._unique_id

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
        if self.counter:
            state = state.split("/")[1]
        # _LOGGER.warning(f"Mega port {self.port} state: {state}")
        self.native_value = int(state)
        self.async_write_ha_state()
        super()._handle_coordinator_update()

    def incoming_update(self):
        state: str = ""
        if self.mega.ports[self.port].state:
            state = self.mega.ports[self.port].state
        if self.counter:
            state = state.split("/")[1]
        self.native_value = int(state)
        self.async_write_ha_state()

from typing import cast
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
    switches = []
    switches.append(MegaSensor(hass, 11, mega_coordinator, mega))
    switches.append(MegaSensor(hass, 12, mega_coordinator, mega))
    switches.append(MegaSensor(hass, 13, mega_coordinator, mega))
    async_add_entities(switches)


class MegaSensor(CoordinatorEntity[MegaCoordinator], SensorEntity):
    """Representation of an Mega sensor."""
    def __init__(self, hass,  port, coordinator: MegaCoordinator, mega: Mega):
        self.hass = hass
        self._unique_id = f"S{port}"
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

    @property
    def unique_id(self):
        return self._unique_id

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.warning("Mega sensor _handle_coordinator_update")
        super()._handle_coordinator_update()
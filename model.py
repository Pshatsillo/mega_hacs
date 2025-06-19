from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import MegaCoordinator
from .const import DOMAIN


class Mega():
    def __init__(self, hass: HomeAssistant, entry_id, host: str, mega_id: str, password: str):
        self.hass = hass
        self.entry_id = entry_id
        self.host = host
        self.mega_id = mega_id
        self.password = password
        self.base_url = f"http://{host}/{password}/"
        self.ports = {}
        self.http_timeout = 2

    def device_info(self)-> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"mega{self.mega_id}")},
            name=f"Mega device ID: {self.mega_id}",
            manufacturer= "AB-LOG.RU",
            model_id=f"Mega-2561",
            configuration_url=f"http://{self.host}/{self.password}",
        )
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class Mega:
    def __init__(self, hass: HomeAssistant, entry_id, host: str, mega_id: str, password: str):
        self.hass = hass
        self.entry_id = entry_id
        self.host = host
        self.mega_id = mega_id
        self.password = password
        self.base_url = f"http://{host}/{password}/"
        self.ports = {}
        self.http_timeout = 2

    def device_info(self, firmware)-> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"mega{self.mega_id}")},
            name=f"Mega device ID: {self.mega_id}",
            manufacturer= "AB-LOG.RU",
            model_id=f"Mega-2561",
            sw_version=f"{firmware}",
            configuration_url=f"http://{self.host}/{self.password}",
        )
    class Port:
        def __init__(self, port, port_type, mode, dev, port_int, title, config):
            self.port_type = port_type
            self.mode = mode
            self.dev = dev
            self.title = title
            self.config = config
            self.port_int = None
            self.extender_port = {}
            if port_int is not None:
               self.port_int =int(port_int)
            self.state = None

        class Extender:
            def __init__(self, port_type, title, config):
                self.port_type = port_type
                self.title = title
                self.config = config
                self.state = None
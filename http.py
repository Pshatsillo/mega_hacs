import aiohttp

from homeassistant.helpers.http import HomeAssistantView
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class MegaDView(HomeAssistantView):
    url = f"/{DOMAIN}"  # URL, на который будет отправлять запросы контроллер
    name = f"{DOMAIN}"
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        _LOGGER.warning(f" get: {request.remote} {request.query}")

        host = request.remote
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            host = real_ip.strip()
        _LOGGER.warning(f"host={host}")
        st = request.query.get("st")
        pt = request.query.get("pt")
        cnt = request.query.get("cnt")
        v = request.query.get("v")

        mega_entity = self.hass.data[DOMAIN][self.hass.data[DOMAIN]['ip_for_entity'][host]]
        if pt is not None:
            entity = next(
                (
                    port_entity
                    for port_entity in self.hass.data[DOMAIN]["ports"][mega_entity.entry_id]
                    if port_entity.port == int(pt)
                ), None
            )
            if v is not None:
                if int(v) == 1:
                    mega_entity.ports[int(pt)].state = "ON"
                else:
                    mega_entity.ports[int(pt)].state = "OFF"
            if entity is not None:
                entity.incoming_update()
        return aiohttp.web.Response(status=200)

    async def update_entity(hass, mega_id, port_entity):
        _LOGGER.warning(f" update_entity URL: {mega_id}")
import aiohttp

from homeassistant.helpers.http import HomeAssistantView
import logging

from .const import DOMAIN
from .light import MegaLight

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
        m = request.query.get("m")
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
            if entity is not None:
                if v is not None:
                    if int(v) == 1 and not isinstance(entity, MegaLight):
                        mega_entity.ports[int(pt)].state = "ON"
                    else:
                        if isinstance(entity, MegaLight):
                            mega_entity.ports[int(pt)].state = int(v)
                        else:
                            mega_entity.ports[int(pt)].state = "OFF"
                else:
                    if m is None:
                        mega_entity.ports[int(pt)].state = "ON"
                    else:
                        if m is not None:
                            mega_entity.ports[int(pt)].state = "OFF"
                    entity.incoming_update()
            else:
                port_extender_int = next(
                    (
                        port
                        for port, port_entity in self.hass.data[DOMAIN][mega_entity.entry_id].ports.items()
                        if port_entity.port_int == int(pt)
                    ), None
                )
                query = dict(request.query)
                ext_list = dict()
                for ext in query:
                    if ext.startswith("ext"):
                        ext_list[ext] = query[ext]
                for port_entity in self.hass.data[DOMAIN]["ports"][mega_entity.entry_id]:
                    if port_entity.port == port_extender_int:
                        extport = int(port_entity.unique_id.split("_")[1].split("e")[1])
                        for ext_in, val in ext_list.items():
                            if int(ext_in[3]) == extport:
                                if int(val) == 0:
                                    mega_entity.ports[int(port_extender_int)].extender_port[int(ext_in[3])].state = "OFF"
                                else:
                                    mega_entity.ports[int(port_extender_int)].extender_port[int(ext_in[3])].state = "ON"
                                port_entity.incoming_update()
        return aiohttp.web.Response(status=200)
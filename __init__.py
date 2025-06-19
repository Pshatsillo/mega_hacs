"""The Mega integration by Petros integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform, CONF_HOST, CONF_ID, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from .coordinator import MegaCoordinator, MegaConfigEntry
from .const import DOMAIN, IP_FOR_ENTITY
from .model import Mega

_PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # hass.http.register_view(MegaDView(hass))
    return True

# TODO Update entry annotation
async def async_setup_entry(hass: HomeAssistant, entry: MegaConfigEntry) -> bool:
    """Set up Mega integration by Petros from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = Mega(hass,entry.entry_id,entry.data[CONF_HOST],entry.title,entry.data[CONF_PASSWORD])
    hass.data[DOMAIN].setdefault(IP_FOR_ENTITY, {})[entry.data[CONF_HOST]] = entry.entry_id
    entry.runtime_data = MegaCoordinator(hass, entry)

    await entry.runtime_data.async_config_entry_first_refresh()
    _LOGGER.warning("Before sensors init actions")
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: MegaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

"""The Mega integration by Petros integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform, CONF_HOST, CONF_ID, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from .coordinator import MegaCoordinator, MegaConfigEntry
from .const import DOMAIN, IP_FOR_ENTITY
from .http import MegaDView
from .model import Mega

_PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.http.register_view(MegaDView(hass))
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
    entity_registry = async_get(hass)
    # device_registry = async_get_device_registry(hass)


    current_entities = set()
    for port, port_model in hass.data[DOMAIN][entry.entry_id].ports.items():
        if hass.data[DOMAIN][entry.entry_id].ports[port].extender_port:
            for port_extender in range(16):
                current_entities.add(entry.title + f"_{port:02}"+ 'e' + f"{port_extender:02}")
        else: current_entities.add(entry.title + f"_{port:02}")


    all_entities = {
        entity_id: entity
        for entity_id, entity in entity_registry.entities.items()
        if entity.config_entry_id == entry.entry_id
    }

    entities_to_remove = [
        entity_id
        for entity_id, entity in all_entities.items()
        if entity.unique_id not in current_entities
    ]

    for entity_id in entities_to_remove:
        entity_registry.async_remove(entity_id)

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: MegaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

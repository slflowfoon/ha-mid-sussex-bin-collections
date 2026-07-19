"""Mid Sussex Bin Collections integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MidSussexBinsClient
from .const import CONF_POSTCODE, CONF_PROPERTY_NUMBER, CONF_STREET_NAME
from .coordinator import MidSussexBinsCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mid Sussex Bin Collections from a config entry."""
    client = MidSussexBinsClient(
        async_get_clientsession(hass),
        entry.data[CONF_PROPERTY_NUMBER],
        entry.data[CONF_STREET_NAME],
        entry.data[CONF_POSTCODE],
    )
    coordinator = MidSussexBinsCoordinator(hass, entry.entry_id, client)
    await coordinator.async_load_cached_data()

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        if coordinator.data is None:
            raise
        _LOGGER.warning(
            "Using cached bin collection data because the initial refresh failed"
        )

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

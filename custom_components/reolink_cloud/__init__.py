"""Reolink Cloud Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN
from .coordinator import ReolinkCloudCoordinator
from .api import ReolinkCloudAPI
from .services import async_setup_services, async_unload_services
from .views import async_setup_views
from .panel import async_setup_panel

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.SENSOR, Platform.BUTTON]
STORAGE_VERSION = 1


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Reolink Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Setup token storage for persistence across restarts
    store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.tokens")
    
    async def save_token(token_data: dict[str, Any]) -> None:
        """Save token to persistent storage."""
        await store.async_save(token_data)
        _LOGGER.debug("Token saved to persistent storage")
    
    session = async_get_clientsession(hass)
    api = ReolinkCloudAPI(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        token_callback=save_token,
    )
    
    # Try to restore token from storage first
    stored_token = await store.async_load()
    token_restored = api.restore_token(stored_token) if stored_token else False
    
    # Only login if token wasn't restored or is invalid
    if not token_restored:
        _LOGGER.debug("No valid stored token, performing fresh login")
        if not await api.async_login():
            raise ConfigEntryAuthFailed("Login failed. Please check your credentials.")
    else:
        _LOGGER.info("Session restored from storage - no fresh login needed")
    
    coordinator = ReolinkCloudCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "store": store,
    }
    
    # Setup services, views and panel (only once)
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)
        await async_setup_views(hass)
        await async_setup_panel(hass)
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Unload services if no more entries
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            
    return unload_ok

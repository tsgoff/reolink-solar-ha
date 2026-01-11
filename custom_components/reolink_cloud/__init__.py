"""Reolink Cloud Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, CONF_MFA_TRUST_TOKEN
from .coordinator import ReolinkCloudCoordinator
from .api import ReolinkCloudAPI
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Reolink Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    session = async_get_clientsession(hass)
    api = ReolinkCloudAPI(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        mfa_trust_token=entry.data.get(CONF_MFA_TRUST_TOKEN),
    )
    
    # Initial login
    if not await api.async_login():
        # MFA trust token might be expired, trigger reauth
        raise ConfigEntryAuthFailed("MFA trust token expired. Please re-authenticate.")
    
    coordinator = ReolinkCloudCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }
    
    # Setup services (only once)
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)
    
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

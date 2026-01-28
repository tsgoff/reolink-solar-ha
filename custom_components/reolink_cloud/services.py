"""Services for Reolink Cloud integration."""
from __future__ import annotations

import logging
from datetime import datetime
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_DOWNLOAD_VIDEOS = "download_videos"
SERVICE_SET_DATE = "set_date"

SERVICE_DOWNLOAD_VIDEOS_SCHEMA = vol.Schema({
    vol.Required("date"): cv.date,
    vol.Optional("save_permanently", default=True): cv.boolean,
})

SERVICE_SET_DATE_SCHEMA = vol.Schema({
    vol.Required("date"): cv.date,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Reolink Cloud."""

    async def handle_download_videos(call: ServiceCall) -> None:
        """Handle download videos service call."""
        date = call.data["date"]
        save_permanently = call.data.get("save_permanently", True)
        
        for entry_id, data in hass.data[DOMAIN].items():
            coordinator = data["coordinator"]
            
            # Convert date to datetime
            dt = datetime.combine(date, datetime.min.time())
            
            _LOGGER.info("Downloading videos for date: %s", dt)
            paths = await coordinator.async_download_all_videos_for_date(dt)
            _LOGGER.info("Downloaded %d videos", len(paths))

    async def handle_set_date(call: ServiceCall) -> None:
        """Handle set date service call."""
        date = call.data["date"]
        
        for entry_id, data in hass.data[DOMAIN].items():
            coordinator = data["coordinator"]
            
            # Convert date to datetime
            dt = datetime.combine(date, datetime.min.time())
            
            coordinator.set_selected_date(dt)
            await coordinator.async_request_refresh()
            _LOGGER.info("Set date filter to: %s", dt)

    hass.services.async_register(
        DOMAIN,
        SERVICE_DOWNLOAD_VIDEOS,
        handle_download_videos,
        schema=SERVICE_DOWNLOAD_VIDEOS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DATE,
        handle_set_date,
        schema=SERVICE_SET_DATE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_DOWNLOAD_VIDEOS)
    hass.services.async_remove(DOMAIN, SERVICE_SET_DATE)

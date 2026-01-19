"""Panel for Reolink Cloud video gallery."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Set up the Reolink Cloud panel."""
    # Check if panel is already registered
    if "reolink-cloud" in hass.data.get("frontend_panels", {}):
        _LOGGER.debug("Panel already registered, skipping")
        return
    
    # Register the panel
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            "/reolink_cloud/gallery",
            hass.config.path("custom_components/reolink_cloud/www"),
            cache_headers=False,
        )
    ])
    
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="reolink-cloud-panel",
        frontend_url_path="reolink-cloud",
        sidebar_title="Reolink Cloud",
        sidebar_icon="mdi:cctv",
        module_url="/reolink_cloud/gallery/panel.js",
        embed_iframe=False,
        require_admin=False,
    )

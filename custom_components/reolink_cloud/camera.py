"""Camera platform for Reolink Cloud."""
from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ReolinkCloudCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink Cloud camera."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        ReolinkCloudLatestThumbnail(coordinator, entry),
    ])


class ReolinkCloudLatestThumbnail(CoordinatorEntity[ReolinkCloudCoordinator], Camera):
    """Camera entity showing the latest thumbnail from Reolink Cloud."""

    _attr_has_entity_name = True
    _attr_name = "Latest Thumbnail"

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        
        self._attr_unique_id = f"{entry.entry_id}_latest_thumbnail"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }
        self._cached_image: bytes | None = None
        self._last_video_id: str | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest thumbnail."""
        thumbnail_path = self.coordinator.last_thumbnail_path
        current_video_id = self.coordinator.last_video.get("id") if self.coordinator.last_video else None
        
        # Clear cache if video ID changed
        if current_video_id != self._last_video_id:
            self._cached_image = None
            self._last_video_id = current_video_id
            _LOGGER.debug("Video ID changed to %s, clearing cache", current_video_id)
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            def read_image():
                with open(thumbnail_path, "rb") as f:
                    return f.read()
            
            image_data = await self.hass.async_add_executor_job(read_image)
            self._cached_image = image_data
            return image_data
        
        # If no local file, try to download from URL
        if self.coordinator.last_video:
            cover_url = self.coordinator.last_video.get("coverUrl")
            if cover_url:
                data = await self.coordinator.api.async_download_file(cover_url)
                if data:
                    self._cached_image = data
                    return data
        
        return self._cached_image

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "video_count_today": self.coordinator.video_count_today,
        }
        
        if self.coordinator.last_video:
            video = self.coordinator.last_video
            attrs.update({
                "last_video_id": video.get("id"),
                "last_video_created_at": video.get("createdAt"),
                "last_video_duration": video.get("duration"),
                "last_video_device": video.get("deviceName"),
            })
        
        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

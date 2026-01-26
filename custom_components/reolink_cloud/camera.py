"""Camera platform for Reolink Cloud."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ReolinkCloudCoordinator

_LOGGER = logging.getLogger(__name__)

# Stream timeout in seconds (auto-stop after 5 minutes of inactivity)
STREAM_TIMEOUT = 300


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink Cloud camera."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Add both thumbnail and live camera entities
    async_add_entities([
        ReolinkCloudLiveCamera(coordinator, entry),
        ReolinkCloudLatestThumbnail(coordinator, entry),
    ])


class ReolinkCloudLatestThumbnail(CoordinatorEntity[ReolinkCloudCoordinator], Camera):
    """Camera entity showing the latest thumbnail from Reolink Cloud."""

    _attr_has_entity_name = True
    _attr_name = "Latest Thumbnail"
    _attr_supported_features = CameraEntityFeature(0)

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


class ReolinkCloudLiveCamera(CoordinatorEntity[ReolinkCloudCoordinator], Camera):
    """Camera entity with livestream support."""

    _attr_has_entity_name = True
    _attr_name = "Camera"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        
        self._attr_unique_id = f"{entry.entry_id}_live_camera"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }
        self._cached_image: bytes | None = None
        self._last_video_id: str | None = None
        self._stream_stop_task: asyncio.Task | None = None

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

    async def stream_source(self) -> str | None:
        """Return the stream source URL."""
        _LOGGER.info("Stream source requested")
        
        # Cancel any pending auto-stop task
        if self._stream_stop_task and not self._stream_stop_task.done():
            self._stream_stop_task.cancel()
        
        # If stream is already active, return it
        if self.coordinator.active_stream:
            _LOGGER.info("Reusing existing stream")
            # Schedule auto-stop
            self._schedule_stream_stop()
            return self.coordinator.active_stream.get("url")
        
        # Start new stream
        _LOGGER.info("Starting new livestream")
        stream_url = await self.coordinator.async_start_stream()
        
        if stream_url:
            _LOGGER.info("Stream started successfully: %s", stream_url)
            # Schedule auto-stop after timeout
            self._schedule_stream_stop()
            return stream_url
        
        _LOGGER.error("Failed to start livestream")
        return None

    def _schedule_stream_stop(self) -> None:
        """Schedule automatic stream stop after timeout."""
        async def _auto_stop():
            try:
                await asyncio.sleep(STREAM_TIMEOUT)
                _LOGGER.info("Auto-stopping stream after %d seconds of inactivity", STREAM_TIMEOUT)
                await self.coordinator.async_stop_stream()
            except asyncio.CancelledError:
                pass
        
        self._stream_stop_task = self.hass.async_create_task(_auto_stop())

    async def async_will_remove_from_hass(self) -> None:
        """Stop stream when entity is removed."""
        if self._stream_stop_task and not self._stream_stop_task.done():
            self._stream_stop_task.cancel()
        await self.coordinator.async_stop_stream()

    @property
    def is_streaming(self) -> bool:
        """Return true if currently streaming."""
        return self.coordinator.active_stream is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            "video_count_today": self.coordinator.video_count_today,
            "is_streaming": self.is_streaming,
        }
        
        if self.coordinator.last_video:
            video = self.coordinator.last_video
            attrs.update({
                "last_video_id": video.get("id"),
                "last_video_created_at": video.get("createdAt"),
                "last_video_duration": video.get("duration"),
                "last_video_device": video.get("deviceName"),
            })
        
        if self.coordinator.active_stream:
            attrs["stream_started_at"] = self.coordinator.active_stream.get("started_at").isoformat()
        
        if self.coordinator.primary_device_id:
            attrs["device_id"] = self.coordinator.primary_device_id
        
        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

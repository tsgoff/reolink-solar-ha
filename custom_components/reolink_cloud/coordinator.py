"""Data update coordinator for Reolink Cloud."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ReolinkCloudAPI
from .const import DOMAIN, SCAN_INTERVAL_MINUTES, DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)


class ReolinkCloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage Reolink Cloud data."""

    def __init__(self, hass: HomeAssistant, api: ReolinkCloudAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.api = api
        self._storage_path = DEFAULT_STORAGE_PATH
        self._last_video: dict[str, Any] | None = None
        self._last_thumbnail_path: str | None = None
        self._last_video_path: str | None = None
        self._videos_today: list[dict[str, Any]] = []
        self._selected_date: datetime = datetime.now()
        self._devices: list[dict[str, Any]] = []
        self._active_stream: dict[str, Any] | None = None

    @property
    def last_video(self) -> dict[str, Any] | None:
        """Return the last video."""
        return self._last_video

    @property
    def last_thumbnail_path(self) -> str | None:
        """Return path to the last thumbnail."""
        return self._last_thumbnail_path

    @property
    def last_video_path(self) -> str | None:
        """Return path to the last video."""
        return self._last_video_path

    @property
    def videos_today(self) -> list[dict[str, Any]]:
        """Return videos from today."""
        return self._videos_today

    @property
    def video_count_today(self) -> int:
        """Return count of videos today."""
        return len(self._videos_today)

    def set_selected_date(self, date: datetime) -> None:
        """Set the selected date for filtering."""
        self._selected_date = date

    @property
    def devices(self) -> list[dict[str, Any]]:
        """Return available devices."""
        return self._devices

    @property
    def active_stream(self) -> dict[str, Any] | None:
        """Return active stream info."""
        return self._active_stream

    @property
    def primary_device_id(self) -> str | None:
        """Get the first device ID (for single-device setups)."""
        if self._devices:
            return self._devices[0].get("deviceId")
        # Fallback: try to get from last video
        if self._last_video:
            return self._last_video.get("deviceId")
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Reolink Cloud."""
        try:
            # Load devices if not yet loaded
            if not self._devices:
                self._devices = await self.api.async_get_devices()
                _LOGGER.info("Loaded %d devices", len(self._devices))
            
            # Always use today's date unless explicitly changed
            today = datetime.now()
            if self._selected_date.date() != today.date():
                _LOGGER.debug("Selected date (%s) differs from today (%s), updating to today", 
                            self._selected_date.date(), today.date())
                self._selected_date = today
            
            # Get videos for selected date
            start_of_day = self._selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = self._selected_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # API returns list of items directly
            videos = await self.api.async_get_videos(
                start_date=start_of_day,
                end_date=end_of_day,
                count=1000,
            )
            
            self._videos_today = videos
            
            _LOGGER.info("Found %d videos for %s", len(videos), self._selected_date.date())
            
            if videos:
                # Get the most recent video (first item, sorted by createdAt desc)
                latest_video = videos[0]
                latest_video_id = latest_video.get("id")
                current_video_id = self._last_video.get("id") if self._last_video else None
                
                _LOGGER.info("Latest video ID: %s, Current video ID: %s", latest_video_id, current_video_id)
                
                # Check if this is a different video than before
                video_changed = (
                    not self._last_video or 
                    current_video_id != latest_video_id
                )
                
                self._last_video = latest_video
                
                # Always download latest thumbnail when video changes or on first run
                if video_changed and self._last_video.get("coverUrl"):
                    _LOGGER.info("New video detected (changed: %s), downloading thumbnail for video ID: %s", 
                               video_changed, latest_video_id)
                    await self._download_latest_thumbnail()
                else:
                    _LOGGER.debug("Video unchanged, skipping thumbnail download")
            
            return {
                "videos": videos,
                "video_count": len(videos),
                "last_video": self._last_video,
                "last_thumbnail_path": self._last_thumbnail_path,
                "selected_date": self._selected_date.isoformat(),
            }
            
        except Exception as err:
            raise UpdateFailed(f"Error fetching Reolink Cloud data: {err}") from err

    async def _download_latest_thumbnail(self) -> None:
        """Download the latest thumbnail."""
        if not self._last_video:
            _LOGGER.warning("No last video to download thumbnail for")
            return
            
        cover_url = self._last_video.get("coverUrl")
        if not cover_url:
            _LOGGER.warning("No cover URL for video %s", self._last_video.get("id"))
            return
        
        _LOGGER.info("Downloading thumbnail from: %s", cover_url)
        
        # Create storage directory
        os.makedirs(self._storage_path, exist_ok=True)
        
        # Download thumbnail
        data = await self.api.async_download_file(cover_url)
        if data:
            self._last_thumbnail_path = os.path.join(self._storage_path, "latest_thumbnail.jpg")
            
            _LOGGER.info("Saving thumbnail to: %s (size: %d bytes)", self._last_thumbnail_path, len(data))
            
            def write_file():
                with open(self._last_thumbnail_path, "wb") as f:
                    f.write(data)
            
            await self.hass.async_add_executor_job(write_file)
            _LOGGER.info("Thumbnail saved successfully")
        else:
            _LOGGER.error("Failed to download thumbnail data")

    async def async_download_video(self, video_id: str, save_permanently: bool = False) -> str | None:
        """Download a specific video."""
        video_url = await self.api.async_get_video_url(video_id)
        if not video_url:
            return None
            
        data = await self.api.async_download_file(video_url)
        if not data:
            return None
            
        # Create storage directory
        if save_permanently:
            date_str = self._selected_date.strftime("%Y-%m-%d")
            save_path = os.path.join(self._storage_path, date_str)
        else:
            save_path = self._storage_path
            
        os.makedirs(save_path, exist_ok=True)
        
        filename = f"{video_id}.mp4"
        filepath = os.path.join(save_path, filename)
        
        def write_file():
            with open(filepath, "wb") as f:
                f.write(data)
        
        await self.hass.async_add_executor_job(write_file)
        
        if not save_permanently:
            self._last_video_path = filepath
            
        return filepath

    async def async_download_all_videos_for_date(self, date: datetime) -> list[str]:
        """Download all videos for a specific date."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        videos = await self.api.async_get_videos(
            start_date=start_of_day,
            end_date=end_of_day,
            count=1000,
        )
        
        downloaded = []
        for video in videos:
            video_id = video.get("id")
            if video_id:
                path = await self.async_download_video(video_id, save_permanently=True)
                if path:
                    downloaded.append(path)
                    
                # Also download thumbnail
                cover_url = video.get("coverUrl")
                if cover_url:
                    thumb_data = await self.api.async_download_file(cover_url)
                    if thumb_data:
                        date_str = date.strftime("%Y-%m-%d")
                        thumb_dir = os.path.join(self._storage_path, date_str)
                        os.makedirs(thumb_dir, exist_ok=True)  # Ensure directory exists
                        thumb_path = os.path.join(thumb_dir, f"{video_id}.jpg")
                        
                        def write_thumb():
                            with open(thumb_path, "wb") as f:
                                f.write(thumb_data)
                        
                        await self.hass.async_add_executor_job(write_thumb)
        
        return downloaded

    async def async_start_stream(self, device_id: str | None = None) -> str | None:
        """Start a livestream and return the stream URL."""
        if device_id is None:
            device_id = self.primary_device_id
            _LOGGER.info("Using primary device ID: %s", device_id)
        
        if not device_id:
            _LOGGER.error("No device ID available for livestream")
            _LOGGER.error("Devices loaded: %s", len(self._devices))
            _LOGGER.error("Last video: %s", self._last_video.get("deviceId") if self._last_video else "None")
            return None
        
        # Stop any existing stream first
        if self._active_stream:
            _LOGGER.info("Stopping existing stream before starting new one")
            await self.async_stop_stream()
        
        _LOGGER.info("Starting livestream for device %s", device_id)
        stream_info = await self.api.async_start_livestream(device_id)
        
        if stream_info:
            self._active_stream = {
                "device_id": device_id,
                "stream_id": stream_info.get("id"),
                "url": stream_info.get("url"),
                "started_at": datetime.now(),
            }
            _LOGGER.info("Livestream started successfully!")
            _LOGGER.info("Stream URL: %s", self._active_stream.get("url"))
            _LOGGER.info("Stream ID: %s", self._active_stream.get("stream_id"))
            return self._active_stream.get("url")
        
        _LOGGER.error("stream_info was None, livestream failed to start")
        return None

    async def async_stop_stream(self) -> bool:
        """Stop the active livestream."""
        if not self._active_stream:
            return True
        
        device_id = self._active_stream.get("device_id")
        stream_id = self._active_stream.get("stream_id")
        
        if device_id and stream_id:
            _LOGGER.info("Stopping livestream for device %s", device_id)
            success = await self.api.async_stop_livestream(device_id, stream_id)
            if success:
                self._active_stream = None
                return True
        
        return False

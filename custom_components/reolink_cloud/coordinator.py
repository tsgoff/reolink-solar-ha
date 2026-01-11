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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Reolink Cloud."""
        try:
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
            
            if videos:
                # Get the most recent video (first item, sorted by createdAt desc)
                self._last_video = videos[0]
                
                # Download latest thumbnail
                if self._last_video.get("coverUrl"):
                    await self._download_latest_thumbnail()
            
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
            return
            
        cover_url = self._last_video.get("coverUrl")
        if not cover_url:
            return
            
        # Create storage directory
        os.makedirs(self._storage_path, exist_ok=True)
        
        # Download thumbnail
        data = await self.api.async_download_file(cover_url)
        if data:
            self._last_thumbnail_path = os.path.join(self._storage_path, "latest_thumbnail.jpg")
            
            def write_file():
                with open(self._last_thumbnail_path, "wb") as f:
                    f.write(data)
            
            await self.hass.async_add_executor_job(write_file)

    async def async_download_video(self, video_id: str, save_permanently: bool = False) -> str | None:
        """Download a specific video."""
        video_url = await self.api.async_get_video_download_url(video_id)
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
                        thumb_path = os.path.join(self._storage_path, date_str, f"{video_id}.jpg")
                        
                        def write_thumb():
                            with open(thumb_path, "wb") as f:
                                f.write(thumb_data)
                        
                        await self.hass.async_add_executor_job(write_thumb)
        
        return downloaded

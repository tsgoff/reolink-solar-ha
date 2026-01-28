"""Button platform for Reolink Cloud."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    """Set up Reolink Cloud buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        ReolinkCloudDownloadLatestButton(coordinator, entry),
        ReolinkCloudDownloadAllTodayButton(coordinator, entry),
        ReolinkCloudRefreshButton(coordinator, entry),
    ])


class ReolinkCloudDownloadLatestButton(CoordinatorEntity[ReolinkCloudCoordinator], ButtonEntity):
    """Button to download the latest video."""

    _attr_has_entity_name = True
    _attr_name = "Download Latest Video"
    _attr_icon = "mdi:download"

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_download_latest"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }

    async def async_press(self) -> None:
        """Handle button press."""
        if self.coordinator.last_video:
            video_id = self.coordinator.last_video.get("id")
            if video_id:
                _LOGGER.info("Downloading latest video: %s", video_id)
                path = await self.coordinator.async_download_video(video_id, save_permanently=True)
                if path:
                    _LOGGER.info("Video downloaded to: %s", path)


class ReolinkCloudDownloadAllTodayButton(CoordinatorEntity[ReolinkCloudCoordinator], ButtonEntity):
    """Button to download all videos from today."""

    _attr_has_entity_name = True
    _attr_name = "Download All Today"
    _attr_icon = "mdi:download-multiple"

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_download_all_today"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }

    async def async_press(self) -> None:
        """Handle button press."""
        _LOGGER.info("Downloading all videos for today")
        today = datetime.now()
        paths = await self.coordinator.async_download_all_videos_for_date(today)
        _LOGGER.info("Downloaded %d videos", len(paths))


class ReolinkCloudRefreshButton(CoordinatorEntity[ReolinkCloudCoordinator], ButtonEntity):
    """Button to refresh data."""

    _attr_has_entity_name = True
    _attr_name = "Refresh"
    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_request_refresh()

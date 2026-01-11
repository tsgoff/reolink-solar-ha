"""Sensor platform for Reolink Cloud."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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
    """Set up Reolink Cloud sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([
        ReolinkCloudVideoCountSensor(coordinator, entry),
        ReolinkCloudLastVideoSensor(coordinator, entry),
    ])


class ReolinkCloudVideoCountSensor(CoordinatorEntity[ReolinkCloudCoordinator], SensorEntity):
    """Sensor showing video count for the selected date."""

    _attr_has_entity_name = True
    _attr_name = "Video Count"
    _attr_icon = "mdi:video-box"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "videos"

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_video_count"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }

    @property
    def native_value(self) -> int:
        """Return the video count."""
        return self.coordinator.video_count_today

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "selected_date": self.coordinator._selected_date.isoformat(),
        }


class ReolinkCloudLastVideoSensor(CoordinatorEntity[ReolinkCloudCoordinator], SensorEntity):
    """Sensor showing last video timestamp."""

    _attr_has_entity_name = True
    _attr_name = "Last Video"
    _attr_icon = "mdi:video"
    _attr_device_class = "timestamp"

    def __init__(
        self,
        coordinator: ReolinkCloudCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._attr_unique_id = f"{entry.entry_id}_last_video"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Reolink Cloud",
            "manufacturer": "Reolink",
            "model": "Cloud",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the last video timestamp."""
        if self.coordinator.last_video:
            created_at = self.coordinator.last_video.get("createdAt")
            if created_at:
                # createdAt is in milliseconds
                return datetime.fromtimestamp(created_at / 1000)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        if self.coordinator.last_video:
            video = self.coordinator.last_video
            attrs.update({
                "video_id": video.get("id"),
                "duration": video.get("duration"),
                "device_name": video.get("deviceName"),
                "cover_url": video.get("coverUrl"),
                "channel_name": video.get("channelName"),
            })
        return attrs

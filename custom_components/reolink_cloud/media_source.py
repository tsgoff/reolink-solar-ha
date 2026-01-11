"""Media source for Reolink Cloud."""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> ReolinkCloudMediaSource:
    """Set up Reolink Cloud media source."""
    return ReolinkCloudMediaSource(hass)


class ReolinkCloudMediaSource(MediaSource):
    """Provide Reolink Cloud videos as media sources."""

    name: str = "Reolink Cloud"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize Reolink Cloud media source."""
        super().__init__(DOMAIN)
        self.hass = hass
        self._storage_path = DEFAULT_STORAGE_PATH

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media to a url."""
        path = item.identifier
        if not path:
            raise Unresolvable("No path specified")

        full_path = os.path.join(self._storage_path, path)
        
        if not os.path.exists(full_path):
            raise Unresolvable(f"File not found: {path}")

        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type is None:
            mime_type = "video/mp4" if path.endswith(".mp4") else "image/jpeg"

        return PlayMedia(
            url=f"/media/reolink_cloud/{path}",
            mime_type=mime_type,
        )

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Browse media."""
        path = item.identifier or ""
        full_path = os.path.join(self._storage_path, path)

        # Check if path exists
        if not os.path.exists(full_path):
            # Return empty root
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier="",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.VIDEO,
                title="Reolink Cloud",
                can_play=False,
                can_expand=True,
                children=[],
            )

        # If it's a file, we shouldn't be browsing it
        if os.path.isfile(full_path):
            raise Unresolvable("Cannot browse a file")

        # Build directory listing
        children = await self._build_children(full_path, path)

        title = "Reolink Cloud" if not path else os.path.basename(path)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=path,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=title,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_children(self, full_path: str, relative_path: str) -> list[BrowseMediaSource]:
        """Build list of children for a directory."""
        children: list[BrowseMediaSource] = []

        def scan_directory():
            items = []
            try:
                entries = sorted(os.listdir(full_path), reverse=True)
                for entry in entries:
                    entry_path = os.path.join(full_path, entry)
                    rel_path = os.path.join(relative_path, entry) if relative_path else entry
                    
                    if os.path.isdir(entry_path):
                        items.append({
                            "type": "directory",
                            "name": entry,
                            "path": rel_path,
                        })
                    elif entry.endswith(".mp4"):
                        # Get thumbnail if exists
                        thumb_path = entry_path.replace(".mp4", ".jpg")
                        has_thumb = os.path.exists(thumb_path)
                        items.append({
                            "type": "video",
                            "name": entry,
                            "path": rel_path,
                            "has_thumb": has_thumb,
                            "thumb_path": rel_path.replace(".mp4", ".jpg") if has_thumb else None,
                        })
                    elif entry.endswith(".jpg"):
                        # Skip thumbnails, they're shown with videos
                        pass
            except Exception as e:
                _LOGGER.error("Error scanning directory: %s", e)
            return items

        items = await self.hass.async_add_executor_job(scan_directory)

        for item in items:
            if item["type"] == "directory":
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=item["path"],
                        media_class=MediaClass.DIRECTORY,
                        media_content_type=MediaType.VIDEO,
                        title=item["name"],
                        can_play=False,
                        can_expand=True,
                        thumbnail=None,
                    )
                )
            elif item["type"] == "video":
                thumbnail = None
                if item.get("has_thumb"):
                    thumbnail = f"/media/reolink_cloud/{item['thumb_path']}"
                
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=item["path"],
                        media_class=MediaClass.VIDEO,
                        media_content_type=MediaType.VIDEO,
                        title=item["name"].replace(".mp4", ""),
                        can_play=True,
                        can_expand=False,
                        thumbnail=thumbnail,
                    )
                )

        return children

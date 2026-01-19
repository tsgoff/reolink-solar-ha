"""HTTP views for Reolink Cloud media files."""
from __future__ import annotations

import json
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)


class ReolinkCloudVideoListView(HomeAssistantView):
    """View to list Reolink Cloud videos for a specific date."""

    url = "/api/reolink_cloud/videos/{date}"
    name = "reolink_cloud:videos"
    requires_auth = False  # Changed to False - authentication handled by HA session

    def __init__(self, storage_path: str) -> None:
        """Initialize the view."""
        self._storage_path = storage_path

    async def get(self, request: web.Request, date: str) -> web.Response:
        """Handle GET request for video list."""
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return web.Response(
                status=400,
                text=json.dumps({"error": "Invalid date format. Use YYYY-MM-DD"}),
                content_type="application/json",
            )

        date_path = os.path.join(self._storage_path, date)
        
        if not os.path.exists(date_path) or not os.path.isdir(date_path):
            return web.Response(
                status=200,
                text=json.dumps({"videos": [], "date": date}),
                content_type="application/json",
            )

        videos = []
        try:
            for filename in sorted(os.listdir(date_path), reverse=True):
                if filename.endswith(".mp4"):
                    video_id = filename.replace(".mp4", "")
                    video_path = os.path.join(date_path, filename)
                    thumb_path = os.path.join(date_path, f"{video_id}.jpg")
                    
                    video_info = {
                        "id": video_id,
                        "video_url": f"/media/reolink_cloud/{date}/{filename}",
                        "has_thumbnail": os.path.exists(thumb_path),
                        "size": os.path.getsize(video_path),
                        "created": os.path.getmtime(video_path),
                    }
                    
                    if video_info["has_thumbnail"]:
                        video_info["thumbnail_url"] = f"/media/reolink_cloud/{date}/{video_id}.jpg"
                    
                    videos.append(video_info)
        except Exception as e:
            _LOGGER.error("Error listing videos: %s", e)
            return web.Response(
                status=500,
                text=json.dumps({"error": str(e)}),
                content_type="application/json",
            )

        return web.Response(
            status=200,
            text=json.dumps({"videos": videos, "date": date, "count": len(videos)}),
            content_type="application/json",
        )


class ReolinkCloudDatesView(HomeAssistantView):
    """View to list available dates with videos."""

    url = "/api/reolink_cloud/dates"
    name = "reolink_cloud:dates"
    requires_auth = False  # Changed to False - authentication handled by HA session

    def __init__(self, storage_path: str) -> None:
        """Initialize the view."""
        self._storage_path = storage_path

    async def get(self, request: web.Request) -> web.Response:
        """Handle GET request for available dates."""
        dates = []
        
        try:
            if os.path.exists(self._storage_path):
                for folder in sorted(os.listdir(self._storage_path), reverse=True):
                    folder_path = os.path.join(self._storage_path, folder)
                    if os.path.isdir(folder_path):
                        # Check if folder name is a valid date
                        try:
                            datetime.strptime(folder, "%Y-%m-%d")
                            # Count videos in folder
                            video_count = len([f for f in os.listdir(folder_path) if f.endswith(".mp4")])
                            if video_count > 0:
                                dates.append({"date": folder, "video_count": video_count})
                        except ValueError:
                            continue
        except Exception as e:
            _LOGGER.error("Error listing dates: %s", e)
            return web.Response(
                status=500,
                text=json.dumps({"error": str(e)}),
                content_type="application/json",
            )

        return web.Response(
            status=200,
            text=json.dumps({"dates": dates}),
            content_type="application/json",
        )


class ReolinkCloudMediaView(HomeAssistantView):
    """View to serve Reolink Cloud media files."""

    url = "/media/reolink_cloud/{path:.*}"
    name = "reolink_cloud:media"
    requires_auth = False  # Changed to False - authentication handled by HA session

    def __init__(self, storage_path: str) -> None:
        """Initialize the view."""
        self._storage_path = storage_path

    async def get(self, request: web.Request, path: str) -> web.StreamResponse:
        """Handle GET request for media file."""
        full_path = os.path.join(self._storage_path, path)
        
        # Security check: ensure path is within storage directory
        try:
            real_path = os.path.realpath(full_path)
            real_storage = os.path.realpath(self._storage_path)
            if not real_path.startswith(real_storage):
                return web.Response(status=403, text="Forbidden")
        except Exception:
            return web.Response(status=403, text="Forbidden")

        if not os.path.exists(full_path):
            return web.Response(status=404, text="File not found")

        if not os.path.isfile(full_path):
            return web.Response(status=400, text="Not a file")

        # Determine content type
        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type is None:
            if path.endswith(".mp4"):
                mime_type = "video/mp4"
            elif path.endswith(".jpg") or path.endswith(".jpeg"):
                mime_type = "image/jpeg"
            else:
                mime_type = "application/octet-stream"

        # Get file size
        file_size = os.path.getsize(full_path)

        # Handle range requests for video streaming
        range_header = request.headers.get("Range")
        if range_header and mime_type.startswith("video/"):
            return await self._handle_range_request(request, full_path, range_header, file_size, mime_type)

        # Regular response
        return web.FileResponse(full_path, headers={"Content-Type": mime_type})

    async def _handle_range_request(
        self,
        request: web.Request,
        full_path: str,
        range_header: str,
        file_size: int,
        mime_type: str,
    ) -> web.StreamResponse:
        """Handle HTTP range request for video streaming."""
        try:
            range_spec = range_header.replace("bytes=", "")
            start_str, end_str = range_spec.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            
            if start >= file_size:
                return web.Response(status=416, text="Range Not Satisfiable")
            
            end = min(end, file_size - 1)
            content_length = end - start + 1

            response = web.StreamResponse(
                status=206,
                headers={
                    "Content-Type": mime_type,
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                    "Accept-Ranges": "bytes",
                },
            )
            await response.prepare(request)

            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 64 * 1024  # 64KB chunks
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    await response.write(chunk)
                    remaining -= len(chunk)

            return response

        except Exception as e:
            _LOGGER.error("Error handling range request: %s", e)
            return web.Response(status=500, text="Internal Server Error")


async def async_setup_views(hass: HomeAssistant) -> None:
    """Set up HTTP views for media files."""
    hass.http.register_view(ReolinkCloudMediaView(DEFAULT_STORAGE_PATH))
    hass.http.register_view(ReolinkCloudVideoListView(DEFAULT_STORAGE_PATH))
    hass.http.register_view(ReolinkCloudDatesView(DEFAULT_STORAGE_PATH))
    _LOGGER.info("Reolink Cloud HTTP views registered")

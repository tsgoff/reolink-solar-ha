"""HTTP views for Reolink Cloud media files."""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)


class ReolinkCloudMediaView(HomeAssistantView):
    """View to serve Reolink Cloud media files."""

    url = "/media/reolink_cloud/{path:.*}"
    name = "reolink_cloud:media"
    requires_auth = True

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
            return await self._handle_range_request(full_path, range_header, file_size, mime_type)

        # Regular response
        return web.FileResponse(full_path, headers={"Content-Type": mime_type})

    async def _handle_range_request(
        self,
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

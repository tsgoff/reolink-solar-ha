"""Reolink Cloud API client."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from aiohttp import ClientSession

from .const import API_TOKEN_URL, API_VIDEOS_URL, CLIENT_ID

_LOGGER = logging.getLogger(__name__)


class ReolinkCloudAPI:
    """Reolink Cloud API client."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid token."""
        return self._access_token is not None and time.time() < self._token_expires_at - 60

    async def async_login(self) -> bool:
        """Login to Reolink Cloud."""
        try:
            data = {
                "username": self._username,
                "password": self._password,
                "grant_type": "password",
                "session_mode": "true",
                "client_id": CLIENT_ID,
            }

            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://my.reolink.com",
                "referer": "https://my.reolink.com/",
                "x-verify-scenario": "users.login_with_password",
            }

            async with self._session.post(API_TOKEN_URL, data=data, headers=headers) as resp:
                result = await resp.json()

            if "access_token" in result:
                self._access_token = result["access_token"]
                self._token_expires_at = time.time() + result.get("expires_in", 1800)
                _LOGGER.debug("Login successful")
                return True

            _LOGGER.error("Login failed: %s", result.get("error", result))
            return False

        except Exception as err:
            _LOGGER.error("Login failed: %s", err)
            return False

    async def async_get_videos(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get videos from Reolink Cloud."""
        if not self.is_authenticated:
            if not await self.async_login():
                return {"videos": [], "total": 0}

        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = datetime.now()

        params = {
            "startTime": int(start_date.timestamp() * 1000),
            "endTime": int(end_date.timestamp() * 1000),
            "page": page,
            "pageSize": page_size,
        }

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
        }

        try:
            async with self._session.get(API_VIDEOS_URL, params=params, headers=headers) as resp:
                if resp.status == 401:
                    # Token expired, try to re-login
                    self._access_token = None
                    if await self.async_login():
                        return await self.async_get_videos(start_date, end_date, page, page_size)
                    return {"videos": [], "total": 0}

                result = await resp.json()
                return result.get("data", {"videos": [], "total": 0})

        except Exception as err:
            _LOGGER.error("Failed to get videos: %s", err)
            return {"videos": [], "total": 0}

    async def async_get_video_url(self, video_id: str) -> str | None:
        """Get download URL for a video."""
        if not self.is_authenticated:
            if not await self.async_login():
                return None

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
        }

        try:
            url = f"{API_VIDEOS_URL}{video_id}/url"
            async with self._session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("data", {}).get("url")
                return None

        except Exception as err:
            _LOGGER.error("Failed to get video URL: %s", err)
            return None

    async def async_download_video(self, video_url: str) -> bytes | None:
        """Download video content."""
        try:
            async with self._session.get(video_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None

        except Exception as err:
            _LOGGER.error("Failed to download video: %s", err)
            return None

    async def async_get_thumbnail(self, thumbnail_url: str) -> bytes | None:
        """Download thumbnail image."""
        try:
            async with self._session.get(thumbnail_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None

        except Exception as err:
            _LOGGER.error("Failed to get thumbnail: %s", err)
            return None

"""API client for Reolink Cloud."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Callable, Awaitable

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
        token_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._token_callback = token_callback

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid token."""
        return self._access_token is not None and time.time() < self._token_expires_at - 60

    def restore_token(self, token_data: dict[str, Any]) -> bool:
        """Restore token from stored data."""
        if not token_data:
            return False
        
        access_token = token_data.get("access_token")
        expires_at = token_data.get("expires_at", 0)
        
        if access_token and time.time() < expires_at - 60:
            self._access_token = access_token
            self._token_expires_at = expires_at
            _LOGGER.debug("Token restored from storage, valid until %s", 
                         datetime.fromtimestamp(expires_at).isoformat())
            return True
        
        _LOGGER.debug("Stored token is expired or invalid")
        return False

    async def async_login(self) -> bool:
        """Login to Reolink Cloud."""
        try:
            data = {
                "username": self._username,
                "password": self._password,
                "grant_type": "password",
                "session_mode": "true",
                "client_id": CLIENT_ID,
                "mfa_trusted": "false",
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
                _LOGGER.debug("Login successful, token valid until %s",
                             datetime.fromtimestamp(self._token_expires_at).isoformat())
                
                # Save token for persistence
                if self._token_callback:
                    await self._token_callback({
                        "access_token": self._access_token,
                        "expires_at": self._token_expires_at,
                    })
                
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
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """Get videos from Reolink Cloud."""
        if not self.is_authenticated:
            if not await self.async_login():
                return []

        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = datetime.now()

        # API expects timestamps in milliseconds
        start_at = int(start_date.timestamp() * 1000)
        end_at = int(end_date.timestamp() * 1000)

        params = {
            "start_at": start_at,
            "end_at": end_at,
            "data_type": "create_at",
            "page": page,
            "count": count,
        }

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
            "origin": "https://cloud.reolink.com",
            "referer": "https://cloud.reolink.com/",
        }

        try:
            async with self._session.get(API_VIDEOS_URL, params=params, headers=headers) as resp:
                if resp.status == 401:
                    # Token expired, try to re-login
                    self._access_token = None
                    if await self.async_login():
                        return await self.async_get_videos(start_date, end_date, page, count)
                    return []

                result = await resp.json()
                # Response format: { items: [...] }
                return result.get("items", [])

        except Exception as err:
            _LOGGER.error("Failed to get videos: %s", err)
            return []

    async def async_get_video_url(self, video_id: str) -> str | None:
        """Get download URL for a video."""
        if not self.is_authenticated:
            if not await self.async_login():
                return None

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
            "origin": "https://cloud.reolink.com",
            "referer": "https://cloud.reolink.com/",
        }

        try:
            url = f"{API_VIDEOS_URL}{video_id}/url?type=download"
            async with self._session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("url")
                return None

        except Exception as err:
            _LOGGER.error("Failed to get video URL: %s", err)
            return None

    async def async_download_file(self, url: str) -> bytes | None:
        """Download any file (thumbnail, video, etc.)."""
        try:
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None

        except Exception as err:
            _LOGGER.error("Failed to download file: %s", err)
            return None

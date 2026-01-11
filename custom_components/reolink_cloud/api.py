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
        mfa_trust_token: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._mfa_trust_token = mfa_trust_token

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid token."""
        return self._access_token is not None and time.time() < self._token_expires_at - 60

    @property
    def mfa_trust_token(self) -> str | None:
        """Return the current MFA trust token."""
        return self._mfa_trust_token

    def set_mfa_trust_token(self, token: str) -> None:
        """Set the MFA trust token."""
        self._mfa_trust_token = token

    async def async_login(self) -> bool:
        """Login to Reolink Cloud using stored MFA trust token."""
        if not self._mfa_trust_token:
            _LOGGER.error("No MFA trust token available")
            return False

        try:
            return await self._login_with_mfa_trust()
        except Exception as err:
            _LOGGER.error("Login failed: %s", err)
            return False

    async def _login_with_mfa_trust(self) -> bool:
        """Login using stored MFA trust token."""
        data = {
            "username": self._username,
            "password": self._password,
            "grant_type": "password",
            "session_mode": "true",
            "client_id": CLIENT_ID,
            "mfa_trusted": "true",
            "mfa_trust_token": self._mfa_trust_token,
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
            _LOGGER.debug("Login successful with MFA trust token")
            return True

        _LOGGER.error("Login failed: %s", result.get("error", result))
        return False

    async def async_login_with_mfa_code(self, mfa_code: str) -> tuple[bool, str | None]:
        """Login with 6-digit MFA code. Returns (success, mfa_trust_token)."""
        try:
            # Step 1: Initial login to get MFA token
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

            # Check if MFA is required (expected)
            if "error" not in result:
                # No MFA required? Unexpected but let's handle it
                if "access_token" in result:
                    self._access_token = result["access_token"]
                    self._token_expires_at = time.time() + result.get("expires_in", 1800)
                    return True, None
                return False, None

            error_code = result["error"].get("code")
            if error_code != 20482:  # Not MFA required error
                _LOGGER.error("Unexpected error: %s", result["error"])
                return False, None

            mfa_token = result["error"].get("metadata", {}).get("mfa_token")
            if not mfa_token:
                _LOGGER.error("No MFA token in response")
                return False, None

            # Step 2: Complete login with MFA code
            return await self._complete_login_with_mfa_code(mfa_token, mfa_code)

        except Exception as err:
            _LOGGER.error("Login with MFA code failed: %s", err)
            return False, None

    async def _complete_login_with_mfa_code(self, mfa_token: str, mfa_code: str) -> tuple[bool, str | None]:
        """Complete login with MFA code."""
        data = {
            "username": self._username,
            "password": self._password,
            "grant_type": "password",
            "session_mode": "true",
            "client_id": CLIENT_ID,
            "mfa_token": mfa_token,
            "mfa_code": mfa_code,
            "mfa_type": "totp",
            "mfa_trusted": "true",
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
            
            # Extract and store MFA trust token for future logins
            mfa_trust_token = result.get("mfa_trust_token")
            if mfa_trust_token:
                self._mfa_trust_token = mfa_trust_token
                _LOGGER.info("Login successful, MFA trust token obtained")
                return True, mfa_trust_token
            
            _LOGGER.warning("Login successful but no MFA trust token received")
            return True, None

        _LOGGER.error("Login with MFA code failed: %s", result.get("error", result))
        return False, None

    async def async_ensure_token(self) -> bool:
        """Ensure we have a valid token, refresh if needed."""
        if not self.is_authenticated:
            return await self.async_login()
        return True

    async def async_get_videos(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """Get videos from Reolink Cloud."""
        if not await self.async_ensure_token():
            return []

        if start_date is None:
            start_date = datetime.now() - timedelta(days=1)
        if end_date is None:
            end_date = datetime.now()

        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        url = f"{API_VIDEOS_URL}?start_at={start_ts}&end_at={end_ts}&data_type=create_at&page=1&count={count}"

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
            "origin": "https://cloud.reolink.com",
        }

        try:
            async with self._session.get(url, headers=headers) as resp:
                result = await resp.json()
                return result.get("items", [])
        except Exception as err:
            _LOGGER.error("Failed to get videos: %s", err)
            return []

    async def async_get_video_download_url(self, video_id: str) -> str | None:
        """Get download URL for a video."""
        if not await self.async_ensure_token():
            return None

        url = f"{API_VIDEOS_URL}{video_id}/url?type=download"

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
            "origin": "https://cloud.reolink.com",
        }

        try:
            async with self._session.get(url, headers=headers) as resp:
                result = await resp.json()
                return result.get("url")
        except Exception as err:
            _LOGGER.error("Failed to get video URL: %s", err)
            return None

    async def async_download_file(self, url: str) -> bytes | None:
        """Download a file from URL."""
        try:
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as err:
            _LOGGER.error("Failed to download file: %s", err)
        return None

"""Reolink Cloud API client."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

import pyotp
from aiohttp import ClientSession

from .const import API_TOKEN_URL, API_VIDEOS_URL, API_MFA_VERIFY_URL, CLIENT_ID

_LOGGER = logging.getLogger(__name__)


class ReolinkCloudAPI:
    """Reolink Cloud API client."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
        totp_secret: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._totp_secret = totp_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._mfa_trust_token: str | None = None

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid token."""
        return self._access_token is not None and time.time() < self._token_expires_at - 60

    def _generate_totp(self) -> str | None:
        """Generate TOTP code from secret."""
        if not self._totp_secret:
            return None
        totp = pyotp.TOTP(self._totp_secret)
        return totp.now()

    async def async_login(self) -> bool:
        """Login to Reolink Cloud."""
        try:
            # First attempt: try with MFA trust token if we have one
            if self._mfa_trust_token:
                if await self._try_login_with_mfa_trust():
                    return True

            # Second attempt: login and handle MFA
            return await self._login_with_mfa()

        except Exception as err:
            _LOGGER.error("Login failed: %s", err)
            return False

    async def _try_login_with_mfa_trust(self) -> bool:
        """Try to login using stored MFA trust token."""
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

        return False

    async def _login_with_mfa(self) -> bool:
        """Login with MFA verification."""
        # Step 1: Initial login (will fail with MFA required)
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

        # Check if MFA is required
        if "error" in result:
            error_code = result["error"].get("code")
            if error_code == 20482:  # MFA required
                mfa_token = result["error"].get("metadata", {}).get("mfa_token")
                if mfa_token and self._totp_secret:
                    return await self._verify_mfa(mfa_token)
                else:
                    _LOGGER.error("MFA required but no TOTP secret configured")
                    return False
            else:
                _LOGGER.error("Login error: %s", result["error"])
                return False

        if "access_token" in result:
            self._access_token = result["access_token"]
            self._token_expires_at = time.time() + result.get("expires_in", 1800)
            return True

        return False

    async def _verify_mfa(self, mfa_token: str) -> bool:
        """Verify MFA code and complete login."""
        totp_code = self._generate_totp()
        if not totp_code:
            _LOGGER.error("Could not generate TOTP code")
            return False

        _LOGGER.debug("Verifying MFA with code: %s", totp_code)

        # Verify MFA
        verify_data = {
            "mfa_token": mfa_token,
            "mfa_code": totp_code,
            "mfa_type": "totp",
            "trust_device": "true",
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://my.reolink.com",
            "referer": "https://my.reolink.com/",
        }

        async with self._session.post(API_MFA_VERIFY_URL, data=verify_data, headers=headers) as resp:
            result = await resp.json()

        if "error" in result:
            _LOGGER.error("MFA verification failed: %s", result["error"])
            return False

        # Get the MFA trust token for future logins
        mfa_trust_token = result.get("data", {}).get("mfa_trust_token")
        if mfa_trust_token:
            self._mfa_trust_token = mfa_trust_token

        # Now complete login with MFA trust token
        return await self._complete_login_after_mfa(mfa_token, totp_code)

    async def _complete_login_after_mfa(self, mfa_token: str, totp_code: str) -> bool:
        """Complete login after MFA verification."""
        data = {
            "username": self._username,
            "password": self._password,
            "grant_type": "password",
            "session_mode": "true",
            "client_id": CLIENT_ID,
            "mfa_token": mfa_token,
            "mfa_code": totp_code,
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
            
            # Store MFA trust token for next login
            if "mfa_trust_token" in result:
                self._mfa_trust_token = result["mfa_trust_token"]
            
            _LOGGER.info("Login successful with MFA")
            return True

        _LOGGER.error("Login failed after MFA: %s", result)
        return False

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

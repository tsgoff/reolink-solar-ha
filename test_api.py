#!/usr/bin/env python3
"""Simple test script for Reolink Cloud API."""
import asyncio
import aiohttp
import sys
from datetime import datetime

# API endpoints
API_TOKEN_URL = "https://apis.reolink.com/v1.0/oauth2/token/"
API_VIDEOS_URL = "https://apis.reolink.com/v2/videos/"
CLIENT_ID = "REO-.AJ,HO/L6_TG44T78KB7"


async def test_login(username: str, password: str) -> str | None:
    """Test login and return access token."""
    async with aiohttp.ClientSession() as session:
        data = {
            "username": username,
            "password": password,
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

        print("Attempting login...")
        async with session.post(API_TOKEN_URL, data=data, headers=headers) as resp:
            result = await resp.json()

        if "access_token" in result:
            print("✅ Login successful!")
            return result["access_token"]
        else:
            print(f"❌ Login failed: {result.get('error', result)}")
            return None


async def test_get_videos(access_token: str) -> None:
    """Test getting videos."""
    async with aiohttp.ClientSession() as session:
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Correct API format: start_at/end_at in milliseconds
        params = {
            "start_at": int(start_of_day.timestamp() * 1000),
            "end_at": int(now.timestamp() * 1000),
            "data_type": "create_at",
            "page": 1,
            "count": 100,
        }

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {access_token}",
            "origin": "https://cloud.reolink.com",
            "referer": "https://cloud.reolink.com/",
        }

        print("\nFetching videos...")
        async with session.get(API_VIDEOS_URL, params=params, headers=headers) as resp:
            result = await resp.json()
            print(f"Status: {resp.status}")

        # Response format: { items: [...] }
        if "items" in result:
            videos = result["items"]
            print(f"✅ Found {len(videos)} videos today")
            if videos:
                video = videos[0]
                print(f"   Latest video ID: {video.get('id')}")
                print(f"   Created at: {video.get('createdAt')}")
                print(f"   Cover URL: {video.get('coverUrl', 'N/A')[:80]}...")
        else:
            print(f"❌ Failed to get videos: {result}")


async def main():
    if len(sys.argv) < 3:
        print("Usage: python test_api.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    token = await test_login(username, password)
    if token:
        await test_get_videos(token)


if __name__ == "__main__":
    asyncio.run(main())

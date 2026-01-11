"""Constants for the Reolink Cloud integration."""

DOMAIN = "reolink_cloud"

CONF_STORAGE_PATH = "storage_path"
CONF_DOWNLOAD_VIDEOS = "download_videos"
CONF_DOWNLOAD_THUMBNAILS = "download_thumbnails"

DEFAULT_STORAGE_PATH = "/config/reolink_cloud"

# API endpoints
API_BASE_URL = "https://apis.reolink.com"
API_TOKEN_URL = f"{API_BASE_URL}/v1.0/oauth2/token/"
API_VIDEOS_URL = f"{API_BASE_URL}/v2/videos/"

CLIENT_ID = "REO-.AJ,HO/L6_TG44T78KB7"

# Update interval
SCAN_INTERVAL_MINUTES = 5

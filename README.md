# Reolink Solar Cloud Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/tsgoff/reolink-solar-ha)](https://github.com/tsgoff/reolink-solar-ha/releases)

A custom integration to access Reolink Cloud videos and thumbnails in Home Assistant. Especially suited for Reolink Solar cameras with cloud storage.

## Features

- ✅ Login with Username, Password and **TOTP** (2FA) - fully automatic!
- ✅ Displays the latest thumbnail as a camera entity
- ✅ Video count per day as sensor
- ✅ Last video timestamp as sensor
- ✅ Download buttons for videos
- ✅ Services for downloading by date
- ✅ Local storage of videos

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/tsgoff/reolink-solar-ha`
3. Category: Integration
4. Install

### Manual

1. Copy the `custom_components/reolink_cloud` folder to `/config/custom_components/`
2. Restart Home Assistant

## Configuration

1. Settings → Devices & Services → Add Integration
2. Search for "Reolink Cloud"
3. Enter:
   - **Email**: Your Reolink account email
   - **Password**: Your Reolink password
   - **TOTP Secret**: The secret from your authenticator app (see below)

### Getting the TOTP Secret from 1Password

1. Open 1Password → Reolink entry
2. Click edit on the "One-Time Password" field
3. You'll see a URL like: `otpauth://totp/Reolink:email@example.com?secret=ABCDEFGH123456&issuer=Reolink`
4. Copy the part after `secret=` (in this example: `ABCDEFGH123456`)

### Getting the TOTP Secret from other authenticator apps

Most authenticator apps allow you to export or view the secret key. Look for options like "Export", "Show secret key", or "Manual entry" in your app's settings.

## Entities

After setup, you'll get the following entities:

| Entity | Type | Description |
|--------|------|-------------|
| `camera.reolink_cloud_latest_thumbnail` | Camera | Shows the latest thumbnail |
| `sensor.reolink_cloud_video_count` | Sensor | Number of videos today |
| `sensor.reolink_cloud_last_video` | Sensor | Timestamp of the last video |
| `button.reolink_cloud_download_latest` | Button | Downloads the latest video |
| `button.reolink_cloud_download_all_today` | Button | Downloads all videos from today |
| `button.reolink_cloud_refresh` | Button | Refreshes the data |

## Services

### `reolink_cloud.download_videos`

Downloads all videos for a specific date.

```yaml
service: reolink_cloud.download_videos
data:
  date: "2026-01-11"
  save_permanently: true
```

### `reolink_cloud.set_date`

Sets the date filter for display.

```yaml
service: reolink_cloud.set_date
data:
  date: "2026-01-10"
```

## Lovelace Card Example

```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: camera.reolink_cloud_latest_thumbnail
    name: Latest Recording
    show_state: false
    
  - type: entities
    entities:
      - sensor.reolink_cloud_video_count
      - sensor.reolink_cloud_last_video
      
  - type: horizontal-stack
    cards:
      - type: button
        entity: button.reolink_cloud_download_latest
        name: Download
        icon: mdi:download
        
      - type: button
        entity: button.reolink_cloud_refresh
        name: Refresh
        icon: mdi:refresh
```

## Automation Example

Download all videos daily at 2:00 AM:

```yaml
automation:
  - alias: "Reolink Videos Daily Backup"
    trigger:
      - platform: time
        at: "02:00:00"
    action:
      - service: reolink_cloud.download_videos
        data:
          date: "{{ (now() - timedelta(days=1)).strftime('%Y-%m-%d') }}"
          save_permanently: true
```

## Storage Location

Videos are saved by default to:

```
/config/reolink_cloud/YYYY-MM-DD/
├── video_id_1.mp4
├── video_id_1.jpg
├── video_id_2.mp4
├── video_id_2.jpg
└── ...
```

## Troubleshooting

### Login fails

1. Check if the TOTP secret is correct (the long string, not the 6-digit code)
2. Make sure the time on your HA server is correct (important for TOTP)
3. Check the logs: Settings → System → Logs

### Videos not loading

- Check if you have cloud storage enabled in Reolink
- Verify that videos are visible in the Reolink app

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

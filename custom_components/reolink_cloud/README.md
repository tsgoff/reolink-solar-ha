# Reolink Solar Cloud Integration für Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/sgofferj/reolink-solar-ha)](https://github.com/sgofferj/reolink-solar-ha/releases)

Eine Custom Integration um Reolink Cloud Videos und Thumbnails in Home Assistant zu integrieren. Besonders geeignet für Reolink Solar-Kameras mit Cloud-Speicher.

## Features

- ✅ Login mit Username, Password und **TOTP** (2FA) - vollautomatisch!
- ✅ Zeigt das neueste Thumbnail als Kamera-Entity
- ✅ Video-Anzahl pro Tag als Sensor
- ✅ Letztes Video Timestamp als Sensor  
- ✅ Download-Buttons für Videos
- ✅ Services zum Herunterladen nach Datum
- ✅ Lokale Speicherung der Videos

## Installation

### HACS (empfohlen)

1. HACS öffnen → Integrationen → ⋮ → Custom repositories
2. URL: `https://github.com/sgofferj/reolink-solar-ha`
3. Kategorie: Integration
4. Installieren

### Manuell

1. Kopiere den Ordner `custom_components/reolink_cloud` nach `/config/custom_components/`
2. Home Assistant neustarten

## Konfiguration

1. Einstellungen → Geräte & Dienste → Integration hinzufügen
2. Nach "Reolink Cloud" suchen
3. Eingeben:
   - **E-Mail**: Deine Reolink Account E-Mail
   - **Passwort**: Dein Reolink Passwort
   - **TOTP Secret**: Das Secret aus deiner Authenticator App (siehe unten)

### TOTP Secret aus 1Password holen

1. 1Password öffnen → Reolink Eintrag
2. "Einmalpasswort" Feld → Bearbeiten klicken
3. Du siehst eine URL wie: `otpauth://totp/Reolink:email@example.com?secret=ABCDEFGH123456&issuer=Reolink`
4. Kopiere den Teil nach `secret=` (hier: `ABCDEFGH123456`)

## Entities

Nach der Einrichtung erhältst du:

| Entity | Typ | Beschreibung |
|--------|-----|--------------|
| `camera.reolink_cloud_latest_thumbnail` | Camera | Zeigt das neueste Thumbnail |
| `sensor.reolink_cloud_video_count` | Sensor | Anzahl Videos heute |
| `sensor.reolink_cloud_last_video` | Sensor | Zeitstempel des letzten Videos |
| `button.reolink_cloud_download_latest` | Button | Lädt das neueste Video herunter |
| `button.reolink_cloud_download_all_today` | Button | Lädt alle Videos von heute |
| `button.reolink_cloud_refresh` | Button | Aktualisiert die Daten |

## Services

### `reolink_cloud.download_videos`

Lädt alle Videos für ein bestimmtes Datum herunter.

```yaml
service: reolink_cloud.download_videos
data:
  date: "2026-01-11"
  save_permanently: true
```

### `reolink_cloud.set_date`

Setzt den Datumsfilter für die Anzeige.

```yaml
service: reolink_cloud.set_date
data:
  date: "2026-01-10"
```

## Lovelace Card Beispiel

```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: camera.reolink_cloud_latest_thumbnail
    name: Letzte Aufnahme
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

## Automatisierung Beispiel

Täglich alle Videos um 2:00 Uhr herunterladen:

```yaml
automation:
  - alias: "Reolink Videos täglich sichern"
    trigger:
      - platform: time
        at: "02:00:00"
    action:
      - service: reolink_cloud.download_videos
        data:
          date: "{{ (now() - timedelta(days=1)).strftime('%Y-%m-%d') }}"
          save_permanently: true
```

## Speicherort

Videos werden standardmäßig gespeichert unter:
```
/config/reolink_cloud/YYYY-MM-DD/
├── video_id_1.mp4
├── video_id_1.jpg
├── video_id_2.mp4
├── video_id_2.jpg
└── ...
```

## Troubleshooting

### Login schlägt fehl

1. Überprüfe ob das TOTP Secret korrekt ist (der lange String, nicht der 6-stellige Code)
2. Stelle sicher dass die Uhrzeit auf deinem HA-Server korrekt ist (wichtig für TOTP)
3. Schaue in die Logs: Einstellungen → System → Logs

### Videos werden nicht geladen

- Überprüfe ob du Cloud-Speicher bei Reolink aktiviert hast
- Prüfe ob Videos in der Reolink App sichtbar sind

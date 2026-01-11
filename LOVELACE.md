# Reolink Cloud Lovelace Dashboard

Füge folgendes zu deinem Lovelace Dashboard hinzu:

## Komplettes Dashboard

```yaml
title: Reolink Cloud
views:
  - title: Übersicht
    path: reolink
    icon: mdi:cctv
    cards:
      # Aktuelle Aufnahme
      - type: vertical-stack
        cards:
          - type: markdown
            content: "## 📹 Aktuelle Aufnahme"
          
          - type: picture-entity
            entity: image.reolink_cloud_latest_thumbnail
            name: Letztes Thumbnail
            show_state: false
            show_name: true
            
          - type: entities
            entities:
              - entity: sensor.reolink_cloud_video_count
                name: Videos heute
              - entity: sensor.reolink_cloud_last_video
                name: Letzte Aufnahme
                format: relative
      
      # Steuerung
      - type: vertical-stack
        cards:
          - type: markdown
            content: "## ⬇️ Download"
          
          - type: horizontal-stack
            cards:
              - type: button
                entity: button.reolink_cloud_download_latest
                name: Letztes Video
                icon: mdi:download
                tap_action:
                  action: call-service
                  service: button.press
                  target:
                    entity_id: button.reolink_cloud_download_latest
                    
              - type: button
                entity: button.reolink_cloud_download_all_today
                name: Alle heute
                icon: mdi:download-multiple
                tap_action:
                  action: call-service
                  service: button.press
                  target:
                    entity_id: button.reolink_cloud_download_all_today
                    
              - type: button
                entity: button.reolink_cloud_refresh
                name: Aktualisieren
                icon: mdi:refresh
                tap_action:
                  action: call-service
                  service: button.press
                  target:
                    entity_id: button.reolink_cloud_refresh

      # Media Browser
      - type: vertical-stack
        cards:
          - type: markdown
            content: "## 🎬 Videos ansehen"
          
          - type: media-control
            entity: media_player.browser_mod  # Optional: wenn du browser_mod nutzt
            
          - type: markdown
            content: |
              **Videos durchsuchen:**
              
              Gehe zu **Media** → **Reolink Cloud** um alle gespeicherten Videos anzusehen.
              
              Oder nutze diesen Button:
              
          - type: button
            name: Video-Galerie öffnen
            icon: mdi:folder-play
            tap_action:
              action: navigate
              navigation_path: /media-browser/browser/media-source%3A%2F%2Freolink_cloud
```

## Einfache Karte

```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: image.reolink_cloud_latest_thumbnail
    name: Reolink Baustelle
    
  - type: glance
    entities:
      - entity: sensor.reolink_cloud_video_count
        name: Videos
      - entity: sensor.reolink_cloud_last_video
        name: Letzte
        
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

## Videos abspielen

Die Videos können im **Media Browser** angesehen werden:

1. **Seitenleiste** → **Media**
2. Wähle **Reolink Cloud**
3. Navigiere durch die Datumsordner
4. Klicke auf ein Video zum Abspielen

Alternativ direkter Link:
```
/media-browser/browser/media-source://reolink_cloud
```

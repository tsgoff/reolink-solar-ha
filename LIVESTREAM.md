# Reolink Cloud Livestream Feature

## Übersicht

Die Reolink Cloud Integration unterstützt jetzt **Livestreaming** für Solar-Kameras direkt in Home Assistant!

## Features

✅ **On-Demand Streaming**: Stream startet automatisch beim Öffnen der Camera-Entity  
✅ **Auto-Stop**: Stream stoppt automatisch nach 5 Minuten Inaktivität (spart Batterie)  
✅ **Thumbnail-Vorschau**: Zeigt das letzte Video-Thumbnail, wenn kein Stream aktiv ist  
✅ **Manuelles Stoppen**: Service zum sofortigen Stoppen des Streams  
✅ **Single-Stream**: Nur ein Stream gleichzeitig (optimal für Solar-Kameras)  

## Verwendung

### 1. Camera-Entity hinzufügen

Nach der Installation erscheint eine neue Entity:
- **Reolink Cloud Camera** - Camera mit Livestream-Support

### 2. Livestream starten

**In der Home Assistant UI:**
1. Öffne die Camera-Entity "Reolink Cloud Camera"
2. Klicke auf das Thumbnail
3. Der Livestream startet automatisch (dauert 5-10 Sekunden)

**In Lovelace:**
```yaml
type: picture-entity
entity: camera.reolink_cloud_camera
camera_view: live
```

### 3. Stream stoppen

**Automatisch:**
- Stream stoppt nach 5 Minuten Inaktivität
- Stream stoppt beim Schließen der Camera-Ansicht

**Manuell:**
```yaml
service: reolink_cloud.stop_stream
```

## Konfiguration

### Stream-Qualität

Die Standard-Qualität ist `fluent` (niedrig) für bessere Batterie-Laufzeit.

Für höhere Qualität, ändere in `api.py`:
```python
data = {
    "type": "flv",
    "quality": "clear",  # Statt "fluent"
}
```

### Auto-Stop-Zeit anpassen

Standard: 300 Sekunden (5 Minuten)

In `camera.py` ändern:
```python
STREAM_TIMEOUT = 600  # 10 Minuten
```

## Wichtige Hinweise für Solar-Kameras

⚠️ **Batterieverbrauch**: Livestreaming verbraucht deutlich mehr Energie als normale Aufnahmen

📱 **Wake-up Zeit**: Solar-Kameras brauchen 5-10 Sekunden zum Aufwachen

🔋 **Best Practices**:
- Verwende niedrige Qualität (`fluent`) für längere Batterie-Laufzeit
- Stoppe Stream manuell, wenn nicht mehr benötigt
- Vermeide dauerhafte Livestreams

## Automatisierungen

### Stream bei Bewegungserkennung starten

```yaml
automation:
  - alias: "Start Stream bei Bewegung"
    trigger:
      - platform: state
        entity_id: binary_sensor.reolink_motion
        to: "on"
    action:
      - service: camera.play_stream
        target:
          entity_id: camera.reolink_cloud_camera
        data:
          media_player: media_player.living_room_tv
```

### Stream nachts automatisch stoppen

```yaml
automation:
  - alias: "Stream nachts stoppen"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: reolink_cloud.stop_stream
```

## Troubleshooting

### Stream startet nicht

1. Prüfe Logs: `Settings -> System -> Logs` → Filter: `reolink_cloud`
2. Stelle sicher, dass die Kamera online ist
3. Prüfe die Signalstärke der Kamera
4. Versuche einen Neustart der Integration

### Stream friert ein

- Normal bei schwacher Internetverbindung
- Reduziere Qualität auf `fluent`
- Stoppe und starte Stream neu

### "No device ID available"

- Die Integration konnte keine Geräte laden
- Drücke "Refresh" Button
- Prüfe Reolink Cloud Login

## Technische Details

**API-Endpunkte:**
- `POST /v2/devices/{deviceId}/liveStreaming/start`
- `POST /v2/devices/{deviceId}/liveStreaming/stop`

**Stream-Format:**
- Type: FLV (Flash Video)
- Quality: fluent (low) oder clear (high)
- Protokoll: HTTP/FLV

**Attribute:**
- `is_streaming`: True wenn Stream aktiv
- `stream_started_at`: Zeitstempel des Stream-Starts
- `last_video_id`: ID des letzten aufgenommenen Videos

## Support

Bei Problemen oder Fragen, bitte ein Issue auf GitHub erstellen mit:
- Home Assistant Version
- Kamera-Modell
- Relevante Logs
- Fehlerbeschreibung

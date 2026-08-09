# Klimmzug-Tracker

Ein schlankes, immer-im-Vordergrund-Popup, um Klimmzüge in Spielpausen zu
zählen – im dunklen, sportlichen Design mit eigener (rahmenloser)
Titelleiste, angelehnt an Overlay-Programme wie Overwolf.

Es gibt die App als Windows-Desktop-Programm (Python/tkinter) und als
reine Browser-Version (HTML/CSS/JS, z.B. über GitHub Pages) – beide mit
identischem Funktionsumfang.

## Funktionen

- Buttons **+1 / +3 / +5** zum schnellen Hochzählen des aktuellen Satzes
- **✓ Satz beenden**: schließt den aktuellen Arbeitssatz ab, der Zähler
  springt zurück auf 0, die Wiederholungszahl erscheint in der
  **Sätze heute**-Liste (z.B. `8 · 6 · 5`)
- **↺ Rückgängig**: macht den letzten Klick im laufenden Satz rückgängig.
  Ist der Satz gerade leer, öffnet der Button stattdessen den zuletzt
  abgeschlossenen Satz von heute wieder (Beschriftung wechselt dann zu
  "Satz öffnen") – die Gesamtsumme bleibt dabei unverändert
- **📅 Verlauf**: Kalender im Strava-Heatmap-Stil – Tage als
  unterschiedlich große/farbige Kreise je nach Anzahl. Hovern zeigt pro
  Tag die einzelnen Sätze auf (z.B. `3 Sätze: 8 · 3 · 8 = 19 Klimmzüge`)
- Alle Daten (Gesamtzähler, Klick-Verlauf, abgeschlossene Sätze) werden
  dauerhaft gespeichert und überstehen einen Neustart

## Desktop-Version (Windows)

### Voraussetzungen

- Windows mit installiertem [Python 3](https://www.python.org/downloads/)
  (bei der Installation den Haken bei "Add python.exe to PATH" setzen)
- Die Bildbibliothek [Pillow](https://pypi.org/project/Pillow/) für
  kantengeglättete (Anti-Aliasing) Rundungen:
  ```bash
  pip install pillow
  ```

### Starten

```bash
python pullup_tracker.py
```

Ein Doppelklick auf die Datei funktioniert ebenfalls, falls `.py`-Dateien
mit Python verknüpft sind.

### Daten

Der Gesamtzähler, der Klick-Verlauf und die abgeschlossenen Arbeitssätze
werden gespeichert unter:

```
%USERPROFILE%\.pullup_tracker\data.json
```

Die Datei kann bei Bedarf gelöscht werden, um komplett von vorne zu
beginnen.

### Als eigenständige .exe bauen

```bash
pip install pyinstaller
pyinstaller --onedir --noconsole --name "Klimmzug-Tracker" pullup_tracker.py
```

Das Ergebnis liegt danach in `dist/Klimmzug-Tracker/` – die `.exe` und der
`_internal/`-Ordner gehören zusammen und müssen beim Verschieben/Kopieren
immer zusammenbleiben.

> **Hinweis zu `--onefile`:** Eine einzelne, selbst-entpackende `.exe`
> (`--onefile`) ist bequemer zu verteilen, wird von Windows' **Smart App
> Control** aber deutlich häufiger fälschlich blockiert, weil das
> Selbst-Entpack-Verhalten typisch für Malware-Dropper ist. `--onedir`
> (Ordner statt Einzeldatei) vermeidet dieses Muster und startet
> außerdem etwas schneller.

Falls Windows beim ersten Start trotzdem warnt: Über "Weitere
Informationen" → "Trotzdem ausführen" bestätigen (SmartScreen-Warnung bei
unsignierten Programmen ist normal).

## Browser-Version (GitHub Pages)

Im Ordner [`docs/`](docs/) liegt eine reine HTML/CSS/JS-Version des
Trackers – funktioniert in jedem modernen Browser, ganz ohne Python,
mit identischem Design und Funktionsumfang wie die Desktop-Version
(Sätze, Rückgängig-Verhalten, Kalender mit Satz-Aufschlüsselung).

**Datenspeicherung:** Die Werte werden per `localStorage` direkt im
Browser gespeichert – keine Anmeldung, kein Server. Die Daten bleiben
nach Schließen des Browsers und nach einem PC-Neustart erhalten,
solange niemand die Browserdaten löscht. Sie sind allerdings an genau
diesen Browser auf genau diesem Gerät gebunden (kein Abgleich zwischen
Geräten/Browsern, im Inkognito-Modus gehen die Daten beim Schließen
verloren).

### Auf GitHub Pages veröffentlichen

1. Diesen Branch nach `main` mergen (per Pull Request)
2. Im Repository zu **Settings → Pages** gehen
3. Bei **Source** "Deploy from a branch" wählen
4. Branch **`main`**, Ordner **`/docs`** auswählen und speichern
5. Nach kurzer Zeit ist die Seite erreichbar unter:
   `https://justinpriem.github.io/tracker/`

### Lokal testen

```bash
cd docs
python -m http.server 8000
```

und dann `http://localhost:8000` aufrufen. (Direktes Öffnen der
`index.html` per Doppelklick funktioniert ebenfalls, ein lokaler Server
vermeidet aber gelegentliche Browser-Caching-Eigenheiten bei
`file://`-URLs.)

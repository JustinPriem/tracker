# Klimmzug-Tracker

Ein einfaches Popup-Programm, um Klimmzüge in Spielpausen zu zählen.
Das Fenster bleibt immer im Vordergrund und kann frei auf dem Desktop
verschoben werden.

## Funktionen

- Buttons **+1 / +3 / +5** zum schnellen Hochzählen
- **Rückgängig**-Button, falls man sich vertan hat
- **Verlauf**-Fenster mit allen Einträgen (Datum, Uhrzeit, Anzahl) sowie
  Tages- und Gesamtsumme
- Zähler wird dauerhaft gespeichert und übersteht einen Neustart

## Voraussetzungen

- Windows mit installiertem [Python 3](https://www.python.org/downloads/)
  (bei der Installation den Haken bei "Add python.exe to PATH" setzen)
- Keine zusätzlichen Pakete nötig – es wird nur die in Python enthaltene
  Bibliothek `tkinter` verwendet

## Starten

```bash
python pullup_tracker.py
```

Ein Doppelklick auf die Datei funktioniert ebenfalls, falls `.py`-Dateien
mit Python verknüpft sind.

## Daten

Der Gesamtzähler und der Verlauf werden gespeichert unter:

```
%USERPROFILE%\.pullup_tracker\data.json
```

Die Datei kann bei Bedarf gelöscht werden, um komplett von vorne zu
beginnen.

## Optional: als eigenständige .exe ohne Konsole starten

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole pullup_tracker.py
```

Die fertige `.exe` liegt danach im Ordner `dist/`.

## Browser-Version (GitHub Pages)

Im Ordner [`docs/`](docs/) liegt eine reine HTML/CSS/JS-Version des
Trackers – funktioniert in jedem modernen Browser, ganz ohne Python.

**Funktionsumfang:** identisch zur Desktop-Version (+1/+3/+5, Rückgängig,
Verlauf mit Tages- und Gesamtsumme).

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

Einfach `docs/index.html` im Browser öffnen, oder z.B. mit:

```bash
cd docs
python -m http.server 8000
```

und dann `http://localhost:8000` aufrufen.

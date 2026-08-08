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

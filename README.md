# Repxo

Ein schlankes, immer-im-Vordergrund-Popup, um Klimmzüge in Spielpausen zu
zählen – im dunklen, sportlichen Design mit eigener (rahmenloser)
Titelleiste, angelehnt an Overlay-Programme wie Overwolf.

> **Der Name:** REP für Wiederholungen (Repetitions), XO als Verweis auf
> den Computer/das System.

Es gibt die App als Windows-Desktop-Programm (Python/tkinter), als
Android-App und als reine Browser-Version (HTML/CSS/JS, z.B. über
GitHub Pages) – alle mit identischem Funktionsumfang und Design.

**📥 Downloads** (auf der Website links in der Sidebar, am Handy im
Seitenmenü – oder direkt hier):
[Windows-Installer](https://github.com/JustinPriem/tracker/releases/latest/download/Repxo-Setup.exe) ·
[Windows portable ZIP](https://github.com/JustinPriem/tracker/releases/latest/download/Repxo-Windows.zip) ·
[Android APK](https://github.com/JustinPriem/tracker/releases/latest/download/Repxo.apk)

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
- **☁ Optionaler Cloud-Sync:** Anmeldung mit Google synchronisiert die
  Stats geräteübergreifend (Desktop-App + Browser). Ohne Login läuft alles
  wie gehabt rein lokal/offline weiter.

## Desktop-Version (Windows)

### Voraussetzungen

- Windows mit installiertem [Python 3](https://www.python.org/downloads/)
  (bei der Installation den Haken bei "Add python.exe to PATH" setzen)
- Die Bildbibliothek [Pillow](https://pypi.org/project/Pillow/) für
  kantengeglättete (Anti-Aliasing) Rundungen, und der
  [Supabase](https://pypi.org/project/supabase/)-Client für den optionalen
  Cloud-Sync:
  ```bash
  pip install pillow supabase
  ```

### Starten

```bash
python repxo.py
```

Ein Doppelklick auf die Datei funktioniert ebenfalls, falls `.py`-Dateien
mit Python verknüpft sind.

### Daten

Der Gesamtzähler, der Klick-Verlauf und die abgeschlossenen Arbeitssätze
werden gespeichert unter:

```
%USERPROFILE%\.repxo\data.json
```

Die Datei kann bei Bedarf gelöscht werden, um komplett von vorne zu
beginnen. Daten aus der Zeit vor dem Rebranding (`%USERPROFILE%\.pullup_tracker`)
werden beim ersten Start automatisch übernommen.

Bei aktivem Cloud-Login liegt zusätzlich `%USERPROFILE%\.repxo\session.json`
(nur der Refresh-Token, keine Passwörter) – diese Datei löschen entspricht
einem lokalen Abmelden.

### Cloud-Sync (optional)

Über **☁ Mit Google anmelden** werden die Stats zusätzlich in einer
[Supabase](https://supabase.com)-Datenbank gespeichert und geräteübergreifend
synchronisiert (Desktop + Browser, gleiches Konto). Technisch:

- Login via Google-OAuth (PKCE-Flow); die Desktop-App öffnet dafür kurz den
  System-Browser und fängt den Redirect über einen lokalen HTTP-Server auf
  `localhost:8765` ab (ähnliches Prinzip wie `gh auth login --web`)
- Lokale Datei bleibt immer die schnelle, offline-fähige Quelle – jede
  Änderung wird zuerst lokal gespeichert und danach im Hintergrund
  hochgeladen (Netzwerkfehler blockieren die App nie)
- Ohne Login: keine Netzwerk-Calls, alles wie zuvor rein lokal

### Automatische Update-Prüfung

Beim Start prüft die App im Hintergrund den neuesten
[GitHub-Release](https://github.com/JustinPriem/tracker/releases/latest)
gegen die eigene Version. Gibt es eine neuere, erscheint unten ein kleiner
Hinweis "🔄 Update x.y.z verfügbar" – ein Klick öffnet die Release-Seite
im Browser, von wo aus sich der neue Installer/ZIP herunterladen lässt.
Die Android-App macht dasselbe (nur dort, nicht auf der Website – die ist
über GitHub Pages ohnehin immer aktuell) und öffnet den APK-Download.

Kein Internet oder GitHub nicht erreichbar? Wird stillschweigend
ignoriert, die App startet ganz normal ohne Verzögerung.

### Als eigenständige .exe bauen

```bash
pip install pyinstaller
pyinstaller --onedir --noconsole --name "Repxo" --icon assets\icon.ico --add-data "assets;assets" repxo.py
```

Das Ergebnis liegt danach in `dist/Repxo/` – die `.exe` und der
`_internal/`-Ordner gehören zusammen und müssen beim Verschieben/Kopieren
immer zusammenbleiben.

> **Hinweis zu `--onefile`:** Eine einzelne, selbst-entpackende `.exe`
> (`--onefile`) ist bequemer zu verteilen, wird von Windows' **Smart App
> Control** aber deutlich häufiger fälschlich blockiert, weil das
> Selbst-Entpack-Verhalten typisch für Malware-Dropper ist. `--onedir`
> (Ordner statt Einzeldatei) vermeidet dieses Muster und startet
> außerdem etwas schneller.

### Installer bauen (empfohlen für die Weitergabe)

Damit Nutzer nur eine einzige Datei herunterladen müssen (statt Ordner +
`_internal`), gibt es ein [Inno Setup](https://jrsoftware.org/isinfo.php)-
Skript unter [`installer/repxo.iss`](installer/repxo.iss). Es installiert
Repxo nach `%LOCALAPPDATA%\Programs\Repxo` (kein Admin/UAC nötig, wie bei
VS Code/Discord), legt Startmenü- und optional Desktop-Verknüpfung an und
registriert einen sauberen Eintrag unter "Apps & Features".

```bash
# Voraussetzung: dist\Repxo\ muss existieren (siehe oben)
"C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\repxo.iss
```

Ergebnis: `dist_installer\Repxo-Setup.exe`. Auch hier gilt: unsigniert,
daher einmalige SmartScreen-Warnung beim ersten Start – siehe oben.

Falls Windows beim ersten Start trotzdem warnt: Über "Weitere
Informationen" → "Trotzdem ausführen" bestätigen (SmartScreen-Warnung bei
unsignierten Programmen ist normal).

## Neue Version veröffentlichen (automatisch per GitHub Actions)

[`.github/workflows/release.yml`](.github/workflows/release.yml) baut bei
jedem Versions-Tag automatisch Windows-Installer, portables ZIP **und**
Android-APK und veröffentlicht sie als GitHub-Release-Assets – manuelles
Bauen/Hochladen (wie oben beschrieben) ist damit nur noch zum lokalen
Testen nötig.

1. Version an vier Stellen passend hochzählen:
   - `APP_VERSION` in [`repxo.py`](repxo.py)
   - `APP_VERSION` in [`docs/app.js`](docs/app.js)
   - `MyAppVersion` in [`installer/repxo.iss`](installer/repxo.iss)
   - `versionCode` (immer nur hochzählen, nie runter) und `versionName` in
     [`android-app/android/app/build.gradle`](android-app/android/app/build.gradle)
2. Tag pushen:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```
3. Der Workflow baut alles und legt ein neues Release
   `https://github.com/JustinPriem/tracker/releases/tag/v1.2.0` mit allen
   drei Dateien an. Die Auto-Update-Prüfung (siehe oben) findet es dann
   automatisch.

## Android-Version

Statt die App nochmal nativ zu bauen, wird die Browser-Version (`docs/`)
per [Capacitor](https://capacitorjs.com) in eine native Android-Huelle
gepackt (`android-app/`) – gleiches Design, gleicher Code, keine doppelte
Pflege der UI. Die Web-Inhalte werden dabei **fest in die APK eingepackt**
(offline nutzbar, wie die Windows-Version) statt live von der Website
geladen zu werden.

### Voraussetzungen

- [Node.js](https://nodejs.org) (LTS)
- [JDK 21](https://adoptium.net) (neuere Capacitor-Versionen brauchen
  explizit 21, nicht 17)
- [Android SDK Command-line Tools](https://developer.android.com/studio#command-line-tools-only)
  mit installiertem `platform-tools`, `platforms;android-34` und
  `build-tools;34.0.0` (kein volles Android Studio nötig)

### Bauen

```bash
# Website-Inhalte in den Capacitor-Ordner kopieren (Quelle: docs/)
cp -r docs/* android-app/www/

cd android-app
npm install
npx cap sync android
cd android
./gradlew.bat assembleDebug
```

Ergebnis: `android-app/android/app/build/outputs/apk/debug/app-debug.apk`
(Debug-signiert, für Sideload/Weitergabe außerhalb des Play Store völlig
ausreichend – vergleichbar mit der unsignierten Windows-.exe).

Icon/Splash-Screen liegen als Quellbilder in `android-app/resources/` und
werden bei Bedarf über `npx @capacitor/assets generate --android` neu für
alle Auflösungen generiert.

### Installieren

APK herunterladen, auf dem Handy öffnen, bei der Sicherheitsabfrage
"Unbekannte Quellen zulassen" bestätigen (kein Play-Store-Release, daher
wie bei der Windows-.exe eine einmalige Warnung normal).

## Browser-Version (GitHub Pages)

Im Ordner [`docs/`](docs/) liegt eine reine HTML/CSS/JS-Version von
Repxo – funktioniert in jedem modernen Browser, ganz ohne Python,
mit identischem Design und Funktionsumfang wie die Desktop-Version
(Sätze, Rückgängig-Verhalten, Kalender mit Satz-Aufschlüsselung).

**Datenspeicherung:** Standardmäßig werden die Werte per `localStorage`
direkt im Browser gespeichert – keine Anmeldung, kein Server. Die Daten
bleiben nach Schließen des Browsers und nach einem PC-Neustart erhalten,
solange niemand die Browserdaten löscht. Sie sind allerdings an genau
diesen Browser auf genau diesem Gerät gebunden (kein Abgleich zwischen
Geräten/Browsern, im Inkognito-Modus gehen die Daten beim Schließen
verloren) – **außer** man meldet sich oben mit **☁ Google** an, dann
werden die Stats zusätzlich in der Cloud gespeichert und sind auf jedem
Gerät verfügbar (siehe "Cloud-Sync" oben bei der Desktop-Version).

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

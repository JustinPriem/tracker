# Kalender-Historie: Hover-Tooltip + absolute Kreisgröße

## Kontext

Der Verlaufs-Kalender (Desktop: `HistoryPage` in `repxo.py`; Web/Android:
`renderCalendar()` in `docs/app.js`) zeigt pro Tag einen Kreis, dessen Größe
und Farbe die Anzahl der Klimmzüge an diesem Tag andeuten sollen. Beide
Plattformen haben das schon, aber:

- Die Kreisgröße (und Farbe) skaliert **relativ zum höchsten Tageswert im
  aktuell angezeigten Monat** — ein Tag mit 10 Klimmzügen sieht in einem
  ruhigen Monat riesig aus, in einem starken Monat winzig.
- Desktop hat schon einen eigenen gestylten Hover-Tooltip. Web nutzt nur das
  native `title`-Attribut des Browsers (unstyled graue Standard-Box) und hat
  auf Touch-Geräten (Android) gar keine Möglichkeit, die genaue Zahl zu
  sehen.
- Beide Kreis-Maximalgrößen sind vergleichsweise klein (Desktop 30px, Web
  40px Durchmesser).

## Ziel

1. Kreisgröße wird **absolut** skaliert: 50 Klimmzüge an einem Tag = 100%
   Durchmesser, 25 = 50%, linear, gedeckelt bei 50 (alles ≥50 zeigt den
   vollen Kreis).
2. Web bekommt einen eigenen gestylten Tooltip (statt nativer Browser-Box),
   nutzbar per Hover **und** per Tap (Android/Touch).
3. Kreise werden insgesamt größer, das Desktop-Fenster wird dafür breiter.

## Skalierungs-Formel (Desktop + Web identisch)

```
REPS_FOR_FULL_SIZE = 50

ratio = min(value, REPS_FOR_FULL_SIZE) / REPS_FOR_FULL_SIZE
durchmesser = round(ratio * MAX_DURCHMESSER)
```

- Kein visueller Mindest-Floor — rein linear, wie vom Nutzer gewünscht.
  Einzige Ausnahme: ein rein technischer Mini-Floor (2–3px), damit bei sehr
  kleinen Werten kein 0px-Kreis gerendert wird (das würde bei PIL/Canvas zu
  einem Fehler bzw. unsichtbaren Tag führen).
- Werte über 50 werden auf 50 gedeckelt (kein Überragen der Zelle).
- Die Heatmap-**Farbe** (`value_to_color` / `valueToColor`) wird aus
  Konsistenzgründen auf dieselbe absolute 50er-Skala umgestellt (aktuell
  ebenfalls relativ zum Monats-Max) — Größe und Farbe eines Tages sollen
  immer zusammenpassen.
- `value == 0` bleibt wie bisher: nur ein dünner Umriss-Kreis (kein Fill),
  keine Größenberechnung nötig.

## Tooltip

**Desktop** (`repxo.py`): bleibt technisch unverändert — die eigene
Tooltip-Box (`_show_tooltip`/`_hide_tooltip`, `<Enter>`/`<Leave>`-Bindings)
existiert schon und zeigt Datum, Sätze und Gesamtzahl. Nur der zugrunde
liegende Wert (Kreisgröße/Farbe) ändert sich durch die neue Formel.

**Web** (`docs/app.js` + `docs/style.css`): neue Tooltip-Implementierung.

- Ein wiederverwendbares `<div class="day-tooltip">`-Element (per JS
  erzeugt, im DOM versteckt/`hidden` bis gebraucht), gestylt im Repxo-Look
  (`--card-bg`-Hintergrund, `--border`-Rahmen, `--text`-Textfarbe, leichter
  Schatten, abgerundete Ecken — analog zu bestehenden `.day-circle`/`dialog`
  Styles).
- Zeigt denselben Text wie bisher im `title`-Attribut (`{datum}\n{n} Sätze:
  {liste}\n= {value} Klimmzüge` bzw. `{datum}: keine Einträge`).
- Erscheint bei `mouseenter` auf einem `.day-circle`, positioniert relativ
  zum Kreis (z.B. oberhalb, mit Bildschirmrand-Kollisionsvermeidung nicht
  nötig, da der Kalender-Dialog selbst schon begrenzt ist). Verschwindet bei
  `mouseleave`.
- Zusätzlich: `click`/`touchstart` auf einem `.day-circle` zeigt denselben
  Tooltip (für Touch-Geräte ohne Hover) und blendet ihn nach ~2,5s automatisch
  wieder aus, oder sofort beim nächsten Tap auf einen anderen Tag/außerhalb.
- Das `title`-Attribut auf `.day-circle` wird entfernt (sonst doppelte
  Tooltips im Desktop-Browser).

## Desktop-Layout (repxo.py)

| Konstante | Alt | Neu |
|---|---|---|
| `WINDOW_WIDTH` | 270 | 340 |
| `CELL_SIZE` | 34 | 44 |
| `MAX_CIRCLE_RADIUS` (→ Durchmesser) | 15 (30px) | 20 (40px) |
| `MIN_CIRCLE_RADIUS` | 10 | entfällt (nur noch technischer Mini-Floor in `value_to_radius`) |

`WINDOW_HEIGHT` (552) bleibt unverändert — genug Platz vorhanden auf Haupt-
und Verlaufsseite, keine Notwendigkeit zur Vergrößerung.

Da Haupt-Zähler-Seite und Verlaufs-Seite durch die Flip-Animation gleich
breit sein müssen, wachsen die Haupt-Buttons proportional mit (Faktor
340/270 ≈ 1,26×, auf sinnvolle Pixelwerte gerundet):

| Element | Alt (B×H) | Neu (B×H) |
|---|---|---|
| „Mit Google anmelden" | 214×32 | 270×32 |
| „Satz beenden" | 214×42 | 270×42 |
| +1/+3/+5-Buttons | 66×48 | 84×60 |
| „Rückgängig" | 126×38 | 159×38 |
| „Verlauf" | 100×38 | 126×38 |

Textgrößen (Fonts) bleiben unverändert — nur die Button-Flächen wachsen.
`wraplength`-Werte für Hinweistexte (`login_error_label`, Sätze-Anzeige)
werden proportional angepasst (230→290, 220→280).

## Web-Layout (docs/app.js + docs/style.css)

| Konstante/Regel | Alt | Neu |
|---|---|---|
| `MAX_CIRCLE_SIZE` | 40 | 48 |
| `MIN_CIRCLE_SIZE` | 26 | entfällt (nur techn. Mini-Floor) |
| `.calendar-grid` `grid-auto-rows` | 48px | 58px |

Kein Fenster-Resize nötig — der Verlaufs-Dialog ist bereits responsiv
(prozentuale Breite, 7-Spalten-Grid).

## Betroffene Dateien

- `repxo.py` — Konstanten, `value_to_radius`, `value_to_color`,
  `HistoryPage`, Haupt-Button-Größen in `_build_counter_page`
- `docs/app.js` — `valueToRadius`, `valueToColor`, `renderCalendar`, neue
  Tooltip-Funktionen
- `docs/style.css` — `.calendar-grid`, neue `.day-tooltip`-Klasse

## Out of Scope

- Kein echtes Auto-Update (nur der bestehende Hinweis-Link bleibt wie er
  ist — separates Thema, hier nicht angefasst).
- Keine Änderung an der Android-App selbst (nutzt dieselbe `docs/`-Quelle,
  profitiert automatisch beim nächsten APK-Build).

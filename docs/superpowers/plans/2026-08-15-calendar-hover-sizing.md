# Kalender Hover-Tooltip + absolute Kreisgröße Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verlaufs-Kalender (Desktop + Web/Android) auf eine absolute 50-Klimmzüge-Skala für Kreisgröße/-farbe umstellen, dem Web-Tooltip einen eigenen Look inkl. Tap-Support geben, und das Desktop-Fenster dafür sichtbar verbreitern.

**Architecture:** Zwei parallele, unabhängige Codepfade für dasselbe visuelle Konzept — `repxo.py` (tkinter, Python) für Desktop und `docs/app.js`/`docs/style.css` (Vanilla JS/CSS) für Web/Android (Capacitor lädt dieselbe `docs/`-Quelle offline). Beide bekommen dieselbe lineare 0–50-Skalenformel, aber jeweils in ihrer eigenen Sprache/ihrem eigenen Rendering-Stil implementiert.

**Tech Stack:** Python 3.12 + tkinter + Pillow (Desktop), Vanilla JS + CSS Custom Properties (Web/Android via Capacitor)

## Global Constraints

- Absolute Skala: `REPS_FOR_FULL_SIZE = 50` — 50 (oder mehr) Klimmzüge an einem Tag = 100% Kreisdurchmesser, linear darunter, gedeckelt bei 50.
- Kein sichtbarer Mindest-Floor für Werte >0 — nur ein rein technischer Mini-Floor (Desktop: `MIN_RENDER_RADIUS = 2`, Web: `MIN_RENDER_SIZE = 4`), der ausschließlich ein 0px-Rendering verhindert.
- Tage ohne Einträge (`value == 0`) behalten ihre bisherige, feste Umriss-Kreisgröße (Desktop: `EMPTY_DAY_RADIUS = 10`, Web: `EMPTY_DAY_SIZE = 26`) — unverändert gegenüber vorher, keine Berechnung nötig.
- Die Heatmap-Farbe nutzt dieselbe absolute 50er-Skala wie die Größe (Konsistenz).
- Desktop-Fensterbreite: `WINDOW_WIDTH` 270 → 340px, Fensterhöhe bleibt 552px.
- Spec-Dokument: `docs/superpowers/specs/2026-08-15-calendar-hover-sizing-design.md` — bei Unklarheiten dort nachschlagen.

---

## Task 1: Desktop — absolute Skalen-Formel (`repxo.py`)

**Files:**
- Modify: `repxo.py:116-121` (Konstanten), `repxo.py:224-238` (`value_to_radius`, `value_to_color`), `repxo.py:685-745` (`HistoryPage.refresh`, Aufrufstellen)
- Test: `tests/test_calendar_scaling.py` (neu)

**Interfaces:**
- Produces: `value_to_radius(value: int) -> int`, `value_to_color(value: int) -> str`, Konstanten `REPS_FOR_FULL_SIZE = 50`, `MAX_CIRCLE_RADIUS = 20`, `MIN_RENDER_RADIUS = 2`, `EMPTY_DAY_RADIUS = 10` — werden von Task 2 (Layout, `MAX_CIRCLE_RADIUS`-Wert für `CELL_SIZE`-Berechnung) konsumiert.

- [ ] **Step 1: Schreibe den fehlschlagenden Test**

Erstelle `tests/test_calendar_scaling.py` (neues Verzeichnis `tests/`, kein pytest nötig — reines `assert`-Skript, direkt mit `python` ausführbar):

```python
"""Reine Funktions-Tests fuer die absolute Kalender-Skalierung (Desktop).
Kein pytest-Framework noetig - direkt ausfuehren mit:
    python tests/test_calendar_scaling.py
Importiert repxo.py direkt; das ist side-effect-frei dank des
`if __name__ == "__main__":`-Guards am Dateiende.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import repxo


def test_value_to_radius_zero_reps_for_full_size():
    assert repxo.value_to_radius(repxo.REPS_FOR_FULL_SIZE) == repxo.MAX_CIRCLE_RADIUS


def test_value_to_radius_half_reps_is_half_radius():
    half = repxo.REPS_FOR_FULL_SIZE // 2
    assert repxo.value_to_radius(half) == round(repxo.MAX_CIRCLE_RADIUS * 0.5)


def test_value_to_radius_caps_above_full_size():
    assert repxo.value_to_radius(repxo.REPS_FOR_FULL_SIZE * 3) == repxo.MAX_CIRCLE_RADIUS


def test_value_to_radius_small_value_has_technical_floor_not_zero():
    assert repxo.value_to_radius(1) >= repxo.MIN_RENDER_RADIUS
    assert repxo.value_to_radius(1) > 0


def test_value_to_color_zero_reps_for_full_size_is_low_color():
    assert repxo.value_to_color(0) == "#3a1f14"


def test_value_to_color_full_size_is_high_color():
    assert repxo.value_to_color(repxo.REPS_FOR_FULL_SIZE) == "#ff5722"


def test_value_to_color_caps_above_full_size():
    assert repxo.value_to_color(repxo.REPS_FOR_FULL_SIZE * 3) == "#ff5722"


TESTS = [
    test_value_to_radius_zero_reps_for_full_size,
    test_value_to_radius_half_reps_is_half_radius,
    test_value_to_radius_caps_above_full_size,
    test_value_to_radius_small_value_has_technical_floor_not_zero,
    test_value_to_color_zero_reps_for_full_size_is_low_color,
    test_value_to_color_full_size_is_high_color,
    test_value_to_color_caps_above_full_size,
]

if __name__ == "__main__":
    failures = 0
    for test in TESTS:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        except AttributeError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    if failures:
        print(f"\n{failures} Test(s) fehlgeschlagen")
        sys.exit(1)
    print(f"\nAlle {len(TESTS)} Tests bestanden")
```

- [ ] **Step 2: Test ausführen und Fehlschlag bestätigen**

Run: `python tests/test_calendar_scaling.py`
Expected: `AttributeError`-Fehlschläge, weil `repxo.REPS_FOR_FULL_SIZE`, `repxo.MIN_RENDER_RADIUS` und `repxo.EMPTY_DAY_RADIUS` noch nicht existieren und `value_to_radius`/`value_to_color` noch die alte Zwei-Parameter-Signatur haben (`TypeError: value_to_radius() missing 1 required positional argument`).

- [ ] **Step 3: Konstanten ersetzen**

In `repxo.py`, ersetze (Zeilen 116-117):

```python
MIN_CIRCLE_RADIUS = 10
MAX_CIRCLE_RADIUS = 15
```

durch:

```python
EMPTY_DAY_RADIUS = 10  # fester Radius fuer den duennen Umriss-Kreis an Tagen ohne Eintraege (unveraendert ggue. vorher)
MAX_CIRCLE_RADIUS = 20  # Radius bei REPS_FOR_FULL_SIZE (oder mehr) Klimmzuegen - volle Groesse (Durchmesser 40px)
REPS_FOR_FULL_SIZE = 50  # Ab dieser Tages-Anzahl ist der Kreis auf 100% (volle Groesse)
MIN_RENDER_RADIUS = 2  # rein technischer Mindestwert (kein visueller Floor), verhindert ein 0px-Bild bei sehr kleinen aber >0 Werten
```

- [ ] **Step 4: `value_to_radius` und `value_to_color` auf die absolute Skala umstellen**

Ersetze (Zeilen 224-238):

```python
def value_to_radius(value: int, max_value: int) -> int:
    """Bestimmt den Kreisradius abhaengig von der Tages-Anzahl."""
    if not value or max_value <= 0:
        return MIN_CIRCLE_RADIUS
    ratio = min(value / max_value, 1)
    return round(MIN_CIRCLE_RADIUS + ratio * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS))


def value_to_color(value: int, max_value: int) -> str:
    """Interpoliert zwischen gedaempftem und leuchtendem Orange (Heatmap-Look)."""
    low = (58, 31, 20)      # dunkles Glut-Orange
    high = (255, 87, 34)    # helles Flammen-Orange (ACCENT)
    ratio = min(value / max_value, 1) if max_value > 0 else 1
    rgb = tuple(round(lo + (hi - lo) * ratio) for lo, hi in zip(low, high))
    return "#%02x%02x%02x" % rgb
```

durch:

```python
def value_to_radius(value: int) -> int:
    """Bestimmt den Kreisradius anhand einer absoluten Skala: bei
    REPS_FOR_FULL_SIZE (oder mehr) Klimmzuegen an einem Tag ist der Kreis
    auf 100% (MAX_CIRCLE_RADIUS), linear interpoliert darunter - bewusst
    OHNE sichtbaren Mindestwert (nur MIN_RENDER_RADIUS als rein technische
    Untergrenze gegen ein 0px-Bild). Nur fuer value > 0 aufrufen - Tage
    ohne Eintraege nutzen stattdessen direkt EMPTY_DAY_RADIUS."""
    ratio = min(value, REPS_FOR_FULL_SIZE) / REPS_FOR_FULL_SIZE
    return max(MIN_RENDER_RADIUS, round(ratio * MAX_CIRCLE_RADIUS))


def value_to_color(value: int) -> str:
    """Interpoliert zwischen gedaempftem und leuchtendem Orange (Heatmap-Look),
    auf derselben absoluten REPS_FOR_FULL_SIZE-Skala wie value_to_radius."""
    low = (58, 31, 20)      # dunkles Glut-Orange
    high = (255, 87, 34)    # helles Flammen-Orange (ACCENT)
    ratio = min(value, REPS_FOR_FULL_SIZE) / REPS_FOR_FULL_SIZE
    rgb = tuple(round(lo + (hi - lo) * ratio) for lo, hi in zip(low, high))
    return "#%02x%02x%02x" % rgb
```

- [ ] **Step 5: Test ausführen und Erfolg bestätigen**

Run: `python tests/test_calendar_scaling.py`
Expected: `Alle 7 Tests bestanden`

- [ ] **Step 6: Aufrufstellen in `HistoryPage.refresh` anpassen**

In `repxo.py`, entferne innerhalb von `refresh()` die Zeile (aktuell um Zeile 687):

```python
        max_value = max(daily_totals.values(), default=0)
```

Ersetze anschließend (aktuell um Zeile 719 und 733-740):

```python
                radius = value_to_radius(value, max_value)
                tag = f"day{key.replace('-', '')}"
                day_sets = daily_sets.get(key, [])
                if day_sets:
                    sets_str = " · ".join(str(r) for r in day_sets)
                    satz_wort = "Satz" if len(day_sets) == 1 else "Sätze"
                    tooltip_text = (
                        f"{key}\n{len(day_sets)} {satz_wort}: {sets_str}\n= {value} Klimmzüge"
                    )
                elif value:
                    tooltip_text = f"{key}: {value} Klimmzüge"
                else:
                    tooltip_text = f"{key}: keine Einträge"

                diameter = radius * 2
                if value > 0:
                    color = value_to_color(value, max_value)
                    day_img = render_circle(diameter, fill=color)
                    text_color = "#ffffff"
                else:
                    day_img = render_circle(diameter, outline=BORDER, outline_width=1)
                    text_color = TEXT_SECONDARY
```

durch:

```python
                tag = f"day{key.replace('-', '')}"
                day_sets = daily_sets.get(key, [])
                if day_sets:
                    sets_str = " · ".join(str(r) for r in day_sets)
                    satz_wort = "Satz" if len(day_sets) == 1 else "Sätze"
                    tooltip_text = (
                        f"{key}\n{len(day_sets)} {satz_wort}: {sets_str}\n= {value} Klimmzüge"
                    )
                elif value:
                    tooltip_text = f"{key}: {value} Klimmzüge"
                else:
                    tooltip_text = f"{key}: keine Einträge"

                if value > 0:
                    radius = value_to_radius(value)
                    color = value_to_color(value)
                    diameter = radius * 2
                    day_img = render_circle(diameter, fill=color)
                    text_color = "#ffffff"
                else:
                    radius = EMPTY_DAY_RADIUS
                    diameter = radius * 2
                    day_img = render_circle(diameter, outline=BORDER, outline_width=1)
                    text_color = TEXT_SECONDARY
```

(Die restlichen Zeilen des Loop-Bodies — `self._circle_images.append(day_img)`, `self.canvas.create_image(...)`, `self.canvas.create_text(...)`, die Tooltip-Bindings — bleiben unverändert, sie referenzieren nur `radius`/`diameter`/`day_img`/`text_color`, die weiterhin existieren.)

- [ ] **Step 7: App startet weiterhin fehlerfrei — Smoke-Test**

Run: `python -c "import repxo; print('import ok')"`
Expected: `import ok` ohne Traceback (bestätigt, dass keine Syntaxfehler oder fehlenden Referenzen wie noch benutztes `MIN_CIRCLE_RADIUS` übrig geblieben sind).

Run: `grep -n "MIN_CIRCLE_RADIUS" repxo.py`
Expected: keine Treffer mehr (Konstante wurde vollständig durch `EMPTY_DAY_RADIUS`/`MAX_CIRCLE_RADIUS`/`MIN_RENDER_RADIUS` ersetzt).

- [ ] **Step 8: Commit**

```bash
git add repxo.py tests/test_calendar_scaling.py
git commit -m "Desktop-Kalender: absolute 50er-Skala fuer Kreisgroesse und -farbe

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Desktop — Fenster verbreitern + Buttons proportional mitwachsen (`repxo.py`)

**Files:**
- Modify: `repxo.py:119` (`CELL_SIZE`), `repxo.py:763` (`WINDOW_WIDTH`), `repxo.py:878-960` (Button-Größen, `wraplength`)

**Interfaces:**
- Consumes: `MAX_CIRCLE_RADIUS = 20` aus Task 1 (Kreis-Durchmesser 40px muss in `CELL_SIZE` passen).
- Produces: `WINDOW_WIDTH = 340`, `CELL_SIZE = 44` — keine weiteren Tasks konsumieren das direkt, aber die App muss danach visuell konsistent bleiben.

- [ ] **Step 1: `CELL_SIZE` und `WINDOW_WIDTH` erhöhen**

In `repxo.py:119`, ersetze:

```python
CELL_SIZE = 34  # muss inkl. Padding in die 270px breite Buehne passen (7 Spalten)
```

durch:

```python
CELL_SIZE = 44  # muss inkl. Padding in die 340px breite Buehne passen (7 Spalten), Kreis-Durchmesser max. 40px (MAX_CIRCLE_RADIUS)
```

In `repxo.py:763`, ersetze:

```python
WINDOW_WIDTH = 270
```

durch:

```python
WINDOW_WIDTH = 340
```

- [ ] **Step 2: Haupt-Buttons proportional vergrößern**

In `repxo.py`, in `_build_counter_page`, folgende Größenänderungen (Breite/Höhe, Faktor ≈340/270):

„Mit Google anmelden" (aktuell um Zeile 880):
```python
            width=214, height=32, radius=12, font=FONT_BUTTON_SMALL,
```
→
```python
            width=270, height=32, radius=12, font=FONT_BUTTON_SMALL,
```

`login_error_label` `wraplength` (aktuell um Zeile 906):
```python
            wraplength=230, justify="center",
```
→
```python
            wraplength=290, justify="center",
```

+1/+3/+5-Buttons (aktuell um Zeile 936):
```python
                width=66, height=48, radius=16, font=FONT_BUTTON,
```
→
```python
                width=84, height=60, radius=16, font=FONT_BUTTON,
```

„Satz beenden" (aktuell um Zeile 943):
```python
            width=214, height=42, radius=16, font=FONT_BUTTON_SMALL,
```
→
```python
            width=270, height=42, radius=16, font=FONT_BUTTON_SMALL,
```

Sätze-Anzeige `wraplength` (aktuell um Zeile 960):
```python
            bg=BG_DARK, fg=TEXT_PRIMARY, wraplength=220, justify="center",
```
→
```python
            bg=BG_DARK, fg=TEXT_PRIMARY, wraplength=280, justify="center",
```

„Rückgängig" (aktuell um Zeile 974):
```python
            width=126, height=38, radius=14, font=FONT_BUTTON_SMALL,
```
→
```python
            width=159, height=38, radius=14, font=FONT_BUTTON_SMALL,
```

„Verlauf" (aktuell um Zeile 982):
```python
                width=100, height=38, radius=14, font=FONT_BUTTON_SMALL,
```
→
```python
                width=126, height=38, radius=14, font=FONT_BUTTON_SMALL,
```

- [ ] **Step 3: App starten und visuell prüfen**

Run: `python repxo.py`

Erwartet: App startet ohne Traceback, Fenster ist sichtbar breiter (340px statt 270px), alle Buttons füllen die Breite proportional aus (kein übermäßiger Leerraum an den Seiten, keine abgeschnittenen Texte). Auf „Verlauf" klicken → Kalender-Seite zeigt größere Kreise (bis zu 40px Durchmesser bei ≥50 Klimmzügen an einem Tag), „Zurück" führt zur Haupt-Seite zurück, die weiterhin gleich breit ist wie die Kalender-Seite (keine Sprünge bei der Flip-Animation). App danach schließen.

- [ ] **Step 4: Commit**

```bash
git add repxo.py
git commit -m "Desktop-Fenster verbreitern (270->340px) fuer groessere Kalender-Kreise

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Web — absolute Skalen-Formel (`docs/app.js`)

**Files:**
- Modify: `docs/app.js:134-135` (Konstanten), `docs/app.js:232-251` (`valueToSize`, `valueToColor`), `docs/app.js:290-292` (Aufrufstelle in `renderCalendar`)

**Interfaces:**
- Produces: `valueToSize(value: number) -> number`, `valueToColor(value: number) -> string`, Konstanten `MAX_CIRCLE_SIZE = 48`, `REPS_FOR_FULL_SIZE = 50`, `MIN_RENDER_SIZE = 4`, `EMPTY_DAY_SIZE = 26` — werden von Task 5 (Layout) und indirekt von Task 4 (Tooltip nutzt `renderCalendar`-Output) konsumiert.

- [ ] **Step 1: Manuell verifizieren, dass die alte Formel relativ zum Monats-Max skaliert (Baseline)**

Starte den lokalen Server und öffne die Seite:

Preview: `preview_start` mit `{"name": "tracker-docs"}` (Config existiert bereits in `.claude/launch.json`, dient Port 8123).

Öffne im Browser-Tool die Konsole (via `javascript_tool`) und führe aus:

```js
valueToSize(25, 25)
```

Erwartet (alter Code): `40` (100%, weil 25 der Monats-Max ist) — bestätigt das aktuelle relative Verhalten, das wir jetzt ändern.

- [ ] **Step 2: Konstanten ersetzen**

In `docs/app.js:134-135`, ersetze:

```js
const MIN_CIRCLE_SIZE = 26;
const MAX_CIRCLE_SIZE = 40;
```

durch:

```js
const MAX_CIRCLE_SIZE = 48; // Durchmesser in px bei REPS_FOR_FULL_SIZE (oder mehr) Klimmzuegen
const REPS_FOR_FULL_SIZE = 50; // Ab dieser Tages-Anzahl ist der Kreis auf 100% (volle Groesse)
const MIN_RENDER_SIZE = 4; // rein technischer Mindestwert (kein visueller Floor), verhindert eine 0px-Flaeche bei sehr kleinen aber >0 Werten
const EMPTY_DAY_SIZE = 26; // fester Durchmesser fuer den duennen Umriss-Kreis an Tagen ohne Eintraege (unveraendert ggue. vorher)
```

- [ ] **Step 3: `valueToSize` und `valueToColor` auf die absolute Skala umstellen**

Ersetze (Zeilen 232-251):

```js
function valueToSize(value, maxValue) {
  if (!value || maxValue <= 0) return MIN_CIRCLE_SIZE;
  const ratio = Math.min(value / maxValue, 1);
  return Math.round(MIN_CIRCLE_SIZE + ratio * (MAX_CIRCLE_SIZE - MIN_CIRCLE_SIZE));
}

function hexToRgb(hex) {
  const clean = hex.trim().replace("#", "");
  const bigint = parseInt(clean, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

function valueToColor(value, maxValue) {
  const styles = getComputedStyle(document.documentElement);
  const low = hexToRgb(styles.getPropertyValue("--heat-low") || "#3a1f14");
  const high = hexToRgb(styles.getPropertyValue("--heat-high") || "#ff5722");
  const ratio = maxValue > 0 ? Math.min(value / maxValue, 1) : 1;
  const rgb = low.map((start, i) => Math.round(start + (high[i] - start) * ratio));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}
```

durch:

```js
function valueToSize(value) {
  const ratio = Math.min(value, REPS_FOR_FULL_SIZE) / REPS_FOR_FULL_SIZE;
  return Math.max(MIN_RENDER_SIZE, Math.round(ratio * MAX_CIRCLE_SIZE));
}

function hexToRgb(hex) {
  const clean = hex.trim().replace("#", "");
  const bigint = parseInt(clean, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

function valueToColor(value) {
  const styles = getComputedStyle(document.documentElement);
  const low = hexToRgb(styles.getPropertyValue("--heat-low") || "#3a1f14");
  const high = hexToRgb(styles.getPropertyValue("--heat-high") || "#ff5722");
  const ratio = Math.min(value, REPS_FOR_FULL_SIZE) / REPS_FOR_FULL_SIZE;
  const rgb = low.map((start, i) => Math.round(start + (high[i] - start) * ratio));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}
```

- [ ] **Step 4: Aufrufstelle in `renderCalendar` anpassen**

In `docs/app.js`, entferne innerhalb von `renderCalendar()` die Zeile (aktuell um Zeile 258):

```js
  const maxValue = Object.values(totals).length ? Math.max(...Object.values(totals)) : 0;
```

Ersetze (aktuell um Zeile 290-309):

```js
    const circle = document.createElement("div");
    const size = valueToSize(value, maxValue);
    circle.style.width = `${size}px`;
    circle.style.height = `${size}px`;

    const daySets = dailySets[key] || [];
    let tooltipText;
    if (daySets.length) {
      const setsStr = daySets.join(" · ");
      const satzWort = daySets.length === 1 ? "Satz" : "Sätze";
      tooltipText = `${key}\n${daySets.length} ${satzWort}: ${setsStr}\n= ${value} Klimmzüge`;
    } else if (value) {
      tooltipText = `${key}: ${value} Klimmzüge`;
    } else {
      tooltipText = `${key}: keine Einträge`;
    }

    if (value > 0) {
      circle.className = "day-circle";
      circle.style.background = valueToColor(value, maxValue);
    } else {
      circle.className = "day-circle no-data";
    }
```

durch:

```js
    const circle = document.createElement("div");
    const size = value > 0 ? valueToSize(value) : EMPTY_DAY_SIZE;
    circle.style.width = `${size}px`;
    circle.style.height = `${size}px`;

    const daySets = dailySets[key] || [];
    let tooltipText;
    if (daySets.length) {
      const setsStr = daySets.join(" · ");
      const satzWort = daySets.length === 1 ? "Satz" : "Sätze";
      tooltipText = `${key}\n${daySets.length} ${satzWort}: ${setsStr}\n= ${value} Klimmzüge`;
    } else if (value) {
      tooltipText = `${key}: ${value} Klimmzüge`;
    } else {
      tooltipText = `${key}: keine Einträge`;
    }

    if (value > 0) {
      circle.className = "day-circle";
      circle.style.background = valueToColor(value);
    } else {
      circle.className = "day-circle no-data";
    }
```

(Die Zeile `circle.title = tooltipText;` bleibt für diesen Task unverändert — Task 4 ersetzt sie durch die neue Tooltip-Implementierung.)

- [ ] **Step 5: Verifizieren, dass die Formel jetzt absolut skaliert**

Preview neu laden (Seite refreshen). In der Konsole (`javascript_tool`):

```js
JSON.stringify([valueToSize(50), valueToSize(25), valueToSize(0), valueToSize(1), valueToSize(200)])
```

Expected: `[48,24,4,4,48]` — 50 Klimmzüge = volle 48px, 25 = die Hälfte (24px), 0 wird hier technisch als `MIN_RENDER_SIZE` behandelt (aber in der App nie über `valueToSize` für leere Tage aufgerufen, siehe Step 4), 1 landet am technischen Floor (4px statt fast unsichtbarer <1px), 200 wird bei 48px gedeckelt.

Run:
```js
valueToColor(50) === "rgb(255, 87, 34)"
```
Expected: `true`

- [ ] **Step 6: Commit**

```bash
git add docs/app.js
git commit -m "Web-Kalender: absolute 50er-Skala fuer Kreisgroesse und -farbe

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Web — eigener gestylter Tooltip mit Tap-Support (`docs/app.js` + `docs/style.css`)

**Files:**
- Modify: `docs/app.js:290-322` (Tooltip-Text-Zuweisung + neue Event-Delegation), `docs/style.css` (neue `.day-tooltip`-Klasse)

**Interfaces:**
- Consumes: `renderCalendar()` aus Task 3 (unverändertes Verhalten, nur `circle.title` → `circle.dataset.tooltip`), `calendarGrid` (existierendes DOM-Element aus `docs/index.html`, bereits als Konstante vorhanden).
- Produces: `showDayTooltip(circleEl: HTMLElement) -> void`, `hideDayTooltip() -> void` — keine weiteren Tasks konsumieren diese direkt.

- [ ] **Step 1: `title`-Attribut durch `data-tooltip` ersetzen**

In `docs/app.js`, in `renderCalendar()`, ersetze (aktuell um Zeile 313):

```js
    circle.title = tooltipText;
```

durch:

```js
    circle.dataset.tooltip = tooltipText;
```

- [ ] **Step 2: CSS für die neue Tooltip-Box ergänzen**

In `docs/style.css`, füge nach dem Block `.day-circle.no-data { ... }` folgenden neuen Block ein:

```css
.day-tooltip {
  position: fixed;
  left: 0;
  top: 0;
  z-index: 50;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text);
  white-space: pre-line;
  text-align: center;
  line-height: 1.4;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.45);
  pointer-events: none;
  opacity: 0;
  transform: translate(-50%, -100%);
  transition: opacity 0.12s ease;
}

.day-tooltip.visible {
  opacity: 1;
}
```

- [ ] **Step 3: Tooltip-Element + Event-Delegation in `docs/app.js` ergänzen**

Füge direkt nach der `renderCalendar()`-Funktion (vor der Zeile `document.querySelectorAll(".btn-add").forEach(...)`) folgenden Block ein:

```js
const dayTooltip = document.createElement("div");
dayTooltip.className = "day-tooltip";
document.body.appendChild(dayTooltip);
let tooltipHideTimer = null;

function showDayTooltip(circleEl) {
  const text = circleEl.dataset.tooltip;
  if (!text) return;
  clearTimeout(tooltipHideTimer);
  dayTooltip.textContent = text;
  const rect = circleEl.getBoundingClientRect();
  dayTooltip.style.left = `${rect.left + rect.width / 2}px`;
  dayTooltip.style.top = `${rect.top - 8}px`;
  dayTooltip.classList.add("visible");
}

function hideDayTooltip() {
  dayTooltip.classList.remove("visible");
}

// mouseover/mouseout statt mouseenter/mouseleave, damit ein einziger
// Listener auf calendarGrid reicht (Delegation) - calendarGrid.innerHTML
// wird bei jedem renderCalendar() neu aufgebaut, pro-Kreis-Listener
// muessten sonst bei jedem Rendern neu gebunden werden.
calendarGrid.addEventListener("mouseover", (event) => {
  const circle = event.target.closest(".day-circle");
  if (circle) showDayTooltip(circle);
});

calendarGrid.addEventListener("mouseout", (event) => {
  const circle = event.target.closest(".day-circle");
  if (circle) hideDayTooltip();
});

// Tap-Support (Android/Touch): ein Klick auf einen Tag zeigt den Tooltip
// kurz an. Browser synthetisieren bei einem Tap automatisch ein "click"-
// Event, ein separater "touchstart"-Handler ist daher nicht noetig.
calendarGrid.addEventListener("click", (event) => {
  const circle = event.target.closest(".day-circle");
  if (!circle) return;
  showDayTooltip(circle);
  tooltipHideTimer = setTimeout(hideDayTooltip, 2500);
});

// Tap ausserhalb eines Tages schliesst den Tooltip sofort.
document.addEventListener("click", (event) => {
  if (!event.target.closest(".day-circle")) hideDayTooltip();
});
```

- [ ] **Step 4: Verifizieren im Browser**

Preview: `preview_start` mit `{"name": "tracker-docs"}` (falls nicht mehr offen), Seite laden/neu laden.

Testdaten erzeugen (Konsole via `javascript_tool`, damit der heutige Tag einen Kreis mit Tooltip-Text hat):

```js
addDelta(20); finishSet(); render();
```

Verlaufs-Kalender öffnen: Klick auf den „📅 Verlauf"-Button (per `computer` Tool oder `document.getElementById("historyBtn").click()` via `javascript_tool`).

Hover-Test: Maus über den heutigen Tages-Kreis bewegen (`computer` Tool, `hover`-Action, Koordinaten aus `read_page` oder `getBoundingClientRect()`).

Prüfen (via `javascript_tool`):
```js
document.querySelector(".day-tooltip").classList.contains("visible")
```
Expected: `true`, und `document.querySelector(".day-tooltip").textContent` enthält `20 Klimmzüge`.

Maus wegbewegen (hover auf ein neutrales Element) und erneut prüfen:
```js
document.querySelector(".day-tooltip").classList.contains("visible")
```
Expected: `false`.

Tap-Test: Klick auf denselben Kreis (`computer` Tool, `left_click`), dann sofort prüfen:
```js
document.querySelector(".day-tooltip").classList.contains("visible")
```
Expected: `true`. Danach auf eine neutrale Stelle im Dialog klicken (nicht auf einen Tages-Kreis) und erneut prüfen → Expected: `false`.

Zusätzlich sicherstellen, dass kein natives Browser-Tooltip mehr existiert:
```js
document.querySelector(".day-circle:not(.no-data)").title
```
Expected: `""` (leer, da wir `title` nie mehr setzen).

- [ ] **Step 5: Commit**

```bash
git add docs/app.js docs/style.css
git commit -m "Web-Kalender: eigener gestylter Tooltip statt nativer Browser-Box, Tap-Support

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Web — Kalender-Zeilenhöhe an größere Kreise anpassen (`docs/style.css`)

**Files:**
- Modify: `docs/style.css` (`.calendar-grid`)

**Interfaces:**
- Consumes: `MAX_CIRCLE_SIZE = 48` aus Task 3 (Kreis-Durchmesser muss in die Zeilenhöhe passen).

- [ ] **Step 1: `grid-auto-rows` erhöhen**

In `docs/style.css`, im Block `.calendar-grid { ... }`, ersetze:

```css
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: 48px;
  gap: 2px;
  margin-bottom: 12px;
}
```

durch:

```css
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: 58px;
  gap: 2px;
  margin-bottom: 12px;
}
```

- [ ] **Step 2: Verifizieren, dass 48px-Kreise nicht mehr an den Zeilenrand stoßen**

Preview neu laden, Verlaufs-Kalender öffnen (falls nicht schon offen), Testdaten mit hohem Wert erzeugen, damit ein Tag den vollen 48px-Kreis zeigt:

```js
addDelta(60); finishSet(); render(); renderCalendar();
```

Prüfen (via `javascript_tool`):
```js
const circle = [...document.querySelectorAll(".day-circle")].find(c => c.style.width === "48px");
const cell = circle.closest(".day-cell");
circle.getBoundingClientRect().height <= cell.getBoundingClientRect().height
```
Expected: `true` (Kreis passt vollständig in die Zelle, kein Überlappen mit der nächsten Zeile).

Screenshot zur visuellen Kontrolle: `computer` Tool, `screenshot`-Action.

- [ ] **Step 3: Commit**

```bash
git add docs/style.css
git commit -m "Web-Kalender: Zeilenhoehe an groessere Kreise (48px) anpassen

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Nach Abschluss aller Tasks

- Lokale Test-Daten (aus den `addDelta`/`finishSet`-Aufrufen in Task 4/5) sind nur `localStorage`-Zustand im Browser-Preview-Tab und beeinflussen keine echten Nutzerdaten — kein Cleanup im Repo nötig.
- Der bereits gebaute Windows-Installer/ZIP im GitHub-Release `v1.0.0` spiegelt diese Änderungen noch nicht wider — nach Merge auf `main` ggf. neu bauen und hochladen (nicht Teil dieses Plans, siehe README für den Build-Befehl).
- GitHub-Pages-Deployment nach dem finalen Push auf `main` verifizieren (siehe bisheriges Vorgehen in diesem Projekt: `gh run list`, ggf. `gh run rerun`).

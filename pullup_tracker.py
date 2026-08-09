"""
Klimmzug-Tracker
================

Ein einfaches Popup-Programm zum Zaehlen von Klimmzuegen (z.B. in
Zockpausen). Das Fenster bleibt immer im Vordergrund und kann frei auf
dem Desktop verschoben werden (normales Fensterverhalten von Windows).

Start:
    python pullup_tracker.py

Die Daten (Gesamtzaehler + Verlauf) werden dauerhaft gespeichert unter:
    ~/.pullup_tracker/data.json
"""

from __future__ import annotations

import calendar
import ctypes
import json
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageTk

DATA_DIR = Path.home() / ".pullup_tracker"
DATA_FILE = DATA_DIR / "data.json"

WEEKDAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTH_NAMES = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

MIN_CIRCLE_RADIUS = 13
MAX_CIRCLE_RADIUS = 20

CELL_SIZE = 46
HEADER_HEIGHT = 24
CANVAS_WIDTH = CELL_SIZE * 7

TITLE_BAR_HEIGHT = 34

# ---------------------------------------------------------------------------
# Sportliches Dark-Theme
# ---------------------------------------------------------------------------
BG_DARK = "#0d1117"        # Fensterhintergrund
BG_CARD = "#161b22"        # etwas hellere Flaeche (Hover/Cards)
BORDER = "#2a2f3a"         # dezente Trennlinien/Rahmen

ACCENT = "#ff5722"         # kraeftiges Sport-Orange
ACCENT_HOVER = "#ff7a45"
ACCENT_DIM = "#3a1f14"     # gedaempftes Orange fuer Verlauf/leere Tage

SUCCESS = "#22c55e"        # Gruen fuer "Satz beenden" (Abschluss-Aktion)
SUCCESS_HOVER = "#3ddc73"

TEXT_PRIMARY = "#f5f6f7"
TEXT_SECONDARY = "#8b949e"
TEXT_DISABLED = "#4b5563"

DISABLED_BG = "#1c2128"

FONT_FAMILY = "Segoe UI"
FONT_EYEBROW = (FONT_FAMILY, 9, "bold")
FONT_COUNT = (FONT_FAMILY, 52, "bold")
FONT_SUB = (FONT_FAMILY, 9)
FONT_BUTTON = (FONT_FAMILY, 13, "bold")
FONT_BUTTON_SMALL = (FONT_FAMILY, 10, "bold")
FONT_SETS_VALUE = (FONT_FAMILY, 13, "bold")
FONT_TOTAL = (FONT_FAMILY, 9, "bold")


def spaced(text: str, gap: str = " ") -> str:
    """Fuegt Buchstabenabstand ein, fuer sportliche Eyebrow-Texte in KAPITAELCHEN."""
    return gap.join(text)


SUPERSAMPLE = 4  # Faktor, in dem Formen ueberaufgeloest gezeichnet und dann
                  # sauber herunterskaliert werden (Anti-Aliasing statt Pixeltreppen).


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def render_pill(
    width: int,
    height: int,
    radius: int,
    fill: Optional[str] = None,
    outline: Optional[str] = None,
    outline_width: int = 0,
) -> ImageTk.PhotoImage:
    """Rendert ein abgerundetes Rechteck kantengeglaettet als PhotoImage.

    Wird in SUPERSAMPLE-facher Aufloesung gezeichnet und dann mit
    hochwertigem Resampling verkleinert - dadurch wirken die Ecken rund
    statt treppenstufig (was tkinters native create_polygon/create_oval
    ohne Anti-Aliasing sonst produzieren).
    """
    s = SUPERSAMPLE
    img = Image.new("RGBA", (width * s, height * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    ow = outline_width * s
    inset = ow / 2
    draw.rounded_rectangle(
        [inset, inset, width * s - 1 - inset, height * s - 1 - inset],
        radius=max(radius * s - inset, 0),
        fill=_hex_to_rgba(fill) if fill else None,
        outline=_hex_to_rgba(outline) if outline else None,
        width=ow if outline else 0,
    )
    img = img.resize((width, height), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def render_circle(
    diameter: int,
    fill: Optional[str] = None,
    outline: Optional[str] = None,
    outline_width: int = 0,
) -> ImageTk.PhotoImage:
    """Rendert einen Kreis kantengeglaettet als PhotoImage (siehe render_pill)."""
    s = SUPERSAMPLE
    d = diameter * s
    img = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    ow = outline_width * s
    inset = ow / 2
    draw.ellipse(
        [inset, inset, d - 1 - inset, d - 1 - inset],
        fill=_hex_to_rgba(fill) if fill else None,
        outline=_hex_to_rgba(outline) if outline else None,
        width=ow if outline else 0,
    )
    img = img.resize((diameter, diameter), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


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


def load_data() -> dict:
    """Laedt die gespeicherten Daten oder liefert einen leeren Startzustand.

    - total: Gesamtanzahl Klimmzuege aller Zeiten
    - log: jeder einzelne +1/+3/+5 Klick (fuer Kalender-Heatmap & Undo)
    - current_set: laufender, noch nicht abgeschlossener Arbeitssatz
    - sets: alle abgeschlossenen Arbeitssaetze (Datum, Uhrzeit, Wiederholungen)
    """
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("total", 0)
            data.setdefault("log", [])
            data.setdefault("current_set", 0)
            data.setdefault("sets", [])
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"total": 0, "log": [], "current_set": 0, "sets": []}


def save_data(data: dict) -> None:
    """Speichert die Daten sofort persistent auf die Festplatte."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_taskbar_icon(window: tk.Misc) -> None:
    """Rahmenlose Fenster (overrideredirect) verschwinden unter Windows sonst
    aus der Taskleiste - das hier holt sie per WinAPI zurueck."""
    try:
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        window.withdraw()
        window.after(10, window.deiconify)
    except Exception:
        pass


class TitleBar(tk.Frame):
    """Eigene, flache Titelleiste (statt der Standard-Windows-Leiste) mit
    Schließen-Button - Overwolf-artiger Look. Der ganze Balken (bis auf den
    Button) ist per Drag verschiebbar."""

    def __init__(
        self,
        master: tk.Widget,
        target: tk.Misc,
        title: str,
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=BG_CARD, height=TITLE_BAR_HEIGHT)
        self.target = target
        self.pack_propagate(False)

        icon_label = tk.Label(
            self, text="●", font=(FONT_FAMILY, 8), bg=BG_CARD, fg=ACCENT,
        )
        icon_label.pack(side="left", padx=(12, 4))

        title_label = tk.Label(
            self, text=spaced(title.upper(), " "), font=(FONT_FAMILY, 8, "bold"),
            bg=BG_CARD, fg=TEXT_SECONDARY,
        )
        title_label.pack(side="left")

        close_btn = tk.Label(
            self, text="✕", font=(FONT_FAMILY, 10), bg=BG_CARD, fg=TEXT_SECONDARY,
            width=4, cursor="hand2",
        )
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#e81123", fg="#ffffff"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=BG_CARD, fg=TEXT_SECONDARY))
        close_btn.bind("<Button-1>", lambda e: on_close())

        for widget in (self, icon_label, title_label):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._do_move)

    def _start_move(self, event: tk.Event) -> None:
        self._start_x = event.x_root
        self._start_y = event.y_root
        self._win_x = self.target.winfo_x()
        self._win_y = self.target.winfo_y()

    def _do_move(self, event: tk.Event) -> None:
        dx = event.x_root - self._start_x
        dy = event.y_root - self._start_y
        self.target.geometry(f"+{self._win_x + dx}+{self._win_y + dy}")


class RoundedButton(tk.Canvas):
    """Abgerundeter Button mit Hover-/Disabled-Zustand.

    tkinter kennt keine nativen abgerundeten Buttons und zeichnet Formen
    ohne Kantenglaettung - deshalb werden die Hintergruende hier einmalig
    per PIL kantengeglaettet vorgerendert (siehe render_pill) und als
    PhotoImage auf einem Canvas angezeigt; der Text bleibt natives,
    scharfes tkinter-Text-Rendering.
    """

    def __init__(
        self,
        master: tk.Widget,
        text: str,
        command: Optional[Callable[[], None]] = None,
        *,
        width: int = 68,
        height: int = 46,
        radius: int = 14,
        font=FONT_BUTTON,
        fill: str = ACCENT,
        hover: str = ACCENT_HOVER,
        text_color: str = "#ffffff",
        outline: str = "",
        outline_width: int = 0,
        bg_parent: Optional[str] = None,
    ) -> None:
        bg_parent = bg_parent or master.cget("bg")
        super().__init__(
            master, width=width, height=height, bg=bg_parent,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.text_color = text_color
        self.enabled = True

        self._img_normal = render_pill(width, height, radius, fill=fill, outline=outline, outline_width=outline_width)
        self._img_hover = render_pill(width, height, radius, fill=hover, outline=outline, outline_width=outline_width)
        self._img_disabled = render_pill(width, height, radius, fill=DISABLED_BG)
        self.font = font

        self._draw("normal")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, state: str) -> None:
        self.delete("all")
        if state == "disabled":
            img, txt_fill = self._img_disabled, TEXT_DISABLED
        elif state == "hover":
            img, txt_fill = self._img_hover, self.text_color
        else:
            img, txt_fill = self._img_normal, self.text_color
        self._current_img = img  # Referenz halten, sonst Garbage Collection
        self.create_image(0, 0, anchor="nw", image=img)
        self.create_text(
            self.width / 2, self.height / 2, text=self.text,
            fill=txt_fill, font=self.font,
        )

    def _on_enter(self, _event: tk.Event) -> None:
        if self.enabled:
            self._draw("hover")
            self.config(cursor="hand2")

    def _on_leave(self, _event: tk.Event) -> None:
        if self.enabled:
            self._draw("normal")

    def _on_click(self, _event: tk.Event) -> None:
        if self.enabled and self.command is not None:
            self.command()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self._draw("normal" if enabled else "disabled")

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw("disabled" if not self.enabled else "normal")


class HistoryWindow(tk.Toplevel):
    """Overlay-Fenster mit Kalenderansicht: Tage als unterschiedlich
    grosse/farbige Kreise, je nachdem wie viele Klimmzuege an dem Tag
    gemacht wurden (angelehnt an den Strava-Trainingskalender)."""

    def __init__(self, master: "PullupTracker") -> None:
        super().__init__(master)
        self.master_app = master
        self.title("Verlauf")
        self.configure(bg=BG_DARK, highlightthickness=1, highlightbackground=BORDER)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        TitleBar(self, self, "Verlauf", self.destroy).pack(fill="x")

        today = date.today()
        self.displayed_year = today.year
        self.displayed_month = today.month

        nav_frame = tk.Frame(self, bg=BG_DARK)
        nav_frame.pack(pady=(14, 4), fill="x", padx=14)

        tk.Button(
            nav_frame, text="◀", width=3, command=self._prev_month,
            font=(FONT_FAMILY, 10, "bold"), bg=BG_DARK, fg=ACCENT,
            activebackground=BG_CARD, activeforeground=ACCENT_HOVER,
            bd=0, highlightthickness=0, relief="flat", cursor="hand2",
        ).pack(side="left")
        self.month_label = tk.Label(
            nav_frame, text="", font=(FONT_FAMILY, 12, "bold"),
            bg=BG_DARK, fg=TEXT_PRIMARY,
        )
        self.month_label.pack(side="left", expand=True)
        tk.Button(
            nav_frame, text="▶", width=3, command=self._next_month,
            font=(FONT_FAMILY, 10, "bold"), bg=BG_DARK, fg=ACCENT,
            activebackground=BG_CARD, activeforeground=ACCENT_HOVER,
            bd=0, highlightthickness=0, relief="flat", cursor="hand2",
        ).pack(side="right")

        self.canvas = tk.Canvas(
            self,
            width=CANVAS_WIDTH,
            height=HEADER_HEIGHT + CELL_SIZE * 6,
            bg=BG_DARK,
            highlightthickness=0,
        )
        self.canvas.pack(padx=14, pady=(6, 4))

        self.summary_label = tk.Label(
            self, text="", font=(FONT_FAMILY, 10, "bold"),
            bg=BG_DARK, fg=TEXT_SECONDARY,
        )
        self.summary_label.pack(pady=(0, 14))

        self._tooltip: Optional[tk.Toplevel] = None
        self.bind("<Destroy>", lambda e: self._hide_tooltip())

        self.refresh()

    def _show_tooltip(self, event: tk.Event, text: str) -> None:
        self._hide_tooltip()
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 10}")
        tk.Label(
            self._tooltip,
            text=text,
            background=BG_CARD,
            foreground=TEXT_PRIMARY,
            font=(FONT_FAMILY, 8, "bold"),
            justify="left",
            padx=8,
            pady=4,
            highlightbackground=BORDER,
            highlightthickness=1,
        ).pack()

    def _hide_tooltip(self, _event: Optional[tk.Event] = None) -> None:
        if self._tooltip is not None:
            self._tooltip.destroy()
            self._tooltip = None

    def _prev_month(self) -> None:
        self.displayed_month -= 1
        if self.displayed_month < 1:
            self.displayed_month = 12
            self.displayed_year -= 1
        self.refresh()

    def _next_month(self) -> None:
        self.displayed_month += 1
        if self.displayed_month > 12:
            self.displayed_month = 1
            self.displayed_year += 1
        self.refresh()

    def _daily_totals(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for entry in self.master_app.data["log"]:
            ts = datetime.fromisoformat(entry["timestamp"])
            key = ts.date().isoformat()
            totals[key] = totals.get(key, 0) + entry["delta"]
        return totals

    def _daily_sets(self) -> dict[str, list[int]]:
        """Gruppiert die abgeschlossenen Arbeitssaetze nach Datum."""
        sets_by_day: dict[str, list[int]] = {}
        for s in self.master_app.data["sets"]:
            sets_by_day.setdefault(s["date"], []).append(s["reps"])
        return sets_by_day

    def refresh(self) -> None:
        """Zeichnet den Kalender fuer den aktuell angezeigten Monat neu."""
        self._hide_tooltip()
        self.canvas.delete("all")
        self._circle_images: list[ImageTk.PhotoImage] = []  # Referenzen halten (sonst GC)

        year, month = self.displayed_year, self.displayed_month
        self.month_label.config(text=f"{MONTH_NAMES[month - 1]} {year}")

        daily_totals = self._daily_totals()
        daily_sets = self._daily_sets()
        max_value = max(daily_totals.values(), default=0)

        for col, label in enumerate(WEEKDAY_LABELS):
            x = col * CELL_SIZE + CELL_SIZE / 2
            self.canvas.create_text(
                x, HEADER_HEIGHT / 2, text=label,
                font=(FONT_FAMILY, 8, "bold"), fill=TEXT_SECONDARY,
            )

        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
        today_iso = date.today().isoformat()
        month_total = 0

        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                if day == 0:
                    continue

                key = date(year, month, day).isoformat()
                value = daily_totals.get(key, 0)
                month_total += value

                cx = col * CELL_SIZE + CELL_SIZE / 2
                top = HEADER_HEIGHT + row * CELL_SIZE
                cy = top + CELL_SIZE / 2

                if key == today_iso:
                    ring_d = (MAX_CIRCLE_RADIUS + 3) * 2
                    ring_img = render_circle(ring_d, outline="#f5f6f7", outline_width=2)
                    self._circle_images.append(ring_img)
                    self.canvas.create_image(cx - ring_d / 2, cy - ring_d / 2, anchor="nw", image=ring_img)

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
                self._circle_images.append(day_img)
                self.canvas.create_image(
                    cx - radius, cy - radius, anchor="nw", image=day_img, tags=(tag,),
                )

                self.canvas.create_text(
                    cx, cy, text=str(day), font=(FONT_FAMILY, 8, "bold"),
                    fill=text_color, tags=(tag,),
                )

                self.canvas.tag_bind(
                    tag, "<Enter>",
                    lambda e, t=tooltip_text: self._show_tooltip(e, t),
                )
                self.canvas.tag_bind(tag, "<Leave>", self._hide_tooltip)

        total = self.master_app.data["total"]
        self.summary_label.config(
            text=f"DIESEN MONAT  {month_total}      GESAMT  {total}"
        )


class PullupTracker(tk.Tk):
    """Hauptfenster: kompaktes, verschiebbares Popup mit den Zaehl-Buttons."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Klimmzug-Tracker")
        self.geometry("270x520")
        self.configure(bg=BG_DARK, highlightthickness=1, highlightbackground=BORDER)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.data = load_data()
        self.history_window: Optional[HistoryWindow] = None

        self._build_ui()
        self.after(10, lambda: ensure_taskbar_icon(self))

    def _build_ui(self) -> None:
        TitleBar(self, self, "Klimmzug-Tracker", self.destroy).pack(fill="x")

        content = tk.Frame(self, bg=BG_DARK)
        content.pack(fill="both", expand=True)

        tk.Label(
            content, text=spaced("KLIMMZÜGE"), font=FONT_EYEBROW,
            bg=BG_DARK, fg=ACCENT,
        ).pack(pady=(16, 0))

        self.set_var = tk.StringVar(value=str(self.data["current_set"]))
        tk.Label(
            content, textvariable=self.set_var, font=FONT_COUNT,
            bg=BG_DARK, fg=TEXT_PRIMARY,
        ).pack()

        tk.Label(
            content, text=spaced("AKTUELLER SATZ", " "), font=FONT_SUB,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).pack(pady=(0, 12))

        divider = tk.Frame(content, bg=BORDER, height=1)
        divider.pack(fill="x", padx=28, pady=(0, 14))

        btn_frame = tk.Frame(content, bg=BG_DARK)
        btn_frame.pack()

        for delta in (1, 3, 5):
            RoundedButton(
                btn_frame, text=f"+{delta}", command=lambda d=delta: self.add(d),
                width=66, height=48, radius=16, font=FONT_BUTTON,
                fill=ACCENT, hover=ACCENT_HOVER, text_color="#ffffff",
                bg_parent=BG_DARK,
            ).pack(side="left", padx=5)

        self.finish_btn = RoundedButton(
            content, text="✓  Satz beenden", command=self.finish_set,
            width=214, height=42, radius=16, font=FONT_BUTTON_SMALL,
            fill=SUCCESS, hover=SUCCESS_HOVER, text_color="#ffffff",
            bg_parent=BG_DARK,
        )
        self.finish_btn.pack(pady=(12, 14))

        sets_divider = tk.Frame(content, bg=BORDER, height=1)
        sets_divider.pack(fill="x", padx=28, pady=(0, 12))

        tk.Label(
            content, text=spaced("SÄTZE HEUTE", " "), font=FONT_EYEBROW,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).pack()

        self.sets_today_var = tk.StringVar(value="–")
        tk.Label(
            content, textvariable=self.sets_today_var, font=FONT_SETS_VALUE,
            bg=BG_DARK, fg=TEXT_PRIMARY, wraplength=220, justify="center",
        ).pack(pady=(2, 6))

        self.total_var = tk.StringVar(value=f"GESAMT  {self.data['total']}")
        tk.Label(
            content, textvariable=self.total_var, font=FONT_TOTAL,
            bg=BG_DARK, fg=TEXT_SECONDARY,
        ).pack(pady=(0, 12))

        action_frame = tk.Frame(content, bg=BG_DARK)
        action_frame.pack(pady=(0, 18))

        self.undo_btn = RoundedButton(
            action_frame, text="↺  Rückgängig", command=self.undo,
            width=126, height=38, radius=14, font=FONT_BUTTON_SMALL,
            fill=BG_DARK, hover=BG_CARD, text_color=TEXT_SECONDARY,
            outline=BORDER, outline_width=1, bg_parent=BG_DARK,
        )
        self.undo_btn.pack(side="left", padx=(0, 6))

        RoundedButton(
            action_frame, text="📅  Verlauf", command=self.show_history,
            width=100, height=38, radius=14, font=FONT_BUTTON_SMALL,
            fill=ACCENT_DIM, hover=BORDER, text_color=ACCENT_HOVER,
            bg_parent=BG_DARK,
        ).pack(side="left")

        self._refresh_display()

    def add(self, delta: int) -> None:
        self.data["total"] += delta
        self.data["current_set"] += delta
        self.data["log"].append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "delta": delta,
            }
        )
        save_data(self.data)
        self._refresh_display()

    def finish_set(self) -> None:
        if self.data["current_set"] <= 0:
            return
        self.data["sets"].append(
            {
                "date": date.today().isoformat(),
                "time": datetime.now().strftime("%H:%M"),
                "reps": self.data["current_set"],
            }
        )
        self.data["current_set"] = 0
        save_data(self.data)
        self._refresh_display()

    def undo(self) -> None:
        if self.data["current_set"] > 0:
            if self.data["log"]:
                last = self.data["log"].pop()
                self.data["total"] -= last["delta"]
                self.data["current_set"] = max(0, self.data["current_set"] - last["delta"])
            else:
                self.data["current_set"] = 0
        elif self._last_set_is_today():
            last_set = self.data["sets"].pop()
            self.data["current_set"] = last_set["reps"]
        else:
            return
        save_data(self.data)
        self._refresh_display()

    def _last_set_is_today(self) -> bool:
        sets = self.data["sets"]
        return bool(sets) and sets[-1]["date"] == date.today().isoformat()

    def _todays_set_reps(self) -> list[int]:
        today_iso = date.today().isoformat()
        return [s["reps"] for s in self.data["sets"] if s["date"] == today_iso]

    def _refresh_display(self) -> None:
        self.set_var.set(str(self.data["current_set"]))
        self.total_var.set(f"GESAMT  {self.data['total']}")

        today_reps = self._todays_set_reps()
        self.sets_today_var.set(" · ".join(str(r) for r in today_reps) if today_reps else "–")

        self.finish_btn.set_enabled(self.data["current_set"] > 0)

        can_undo = self.data["current_set"] > 0 or self._last_set_is_today()
        self.undo_btn.set_enabled(can_undo)
        if self.data["current_set"] == 0 and self._last_set_is_today():
            self.undo_btn.set_text("↺  Satz öffnen")
        else:
            self.undo_btn.set_text("↺  Rückgängig")

        self._refresh_history()

    def show_history(self) -> None:
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.lift()
            self.history_window.focus_force()
            return
        self.history_window = HistoryWindow(self)

    def _refresh_history(self) -> None:
        if self.history_window is not None and self.history_window.winfo_exists():
            self.history_window.refresh()


if __name__ == "__main__":
    app = PullupTracker()
    app.mainloop()

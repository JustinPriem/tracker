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
import json
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import ttk
from typing import Optional

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
HEADER_HEIGHT = 22
CANVAS_WIDTH = CELL_SIZE * 7


def value_to_radius(value: int, max_value: int) -> int:
    """Bestimmt den Kreisradius abhaengig von der Tages-Anzahl."""
    if not value or max_value <= 0:
        return MIN_CIRCLE_RADIUS
    ratio = min(value / max_value, 1)
    return round(MIN_CIRCLE_RADIUS + ratio * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS))


def value_to_color(value: int, max_value: int) -> str:
    """Interpoliert zwischen hellem und kraeftigem Orange je nach Anzahl."""
    low = (255, 224, 189)
    high = (234, 88, 12)
    ratio = min(value / max_value, 1) if max_value > 0 else 1
    rgb = tuple(round(lo + (hi - lo) * ratio) for lo, hi in zip(low, high))
    return "#%02x%02x%02x" % rgb


def load_data() -> dict:
    """Laedt die gespeicherten Daten oder liefert einen leeren Startzustand."""
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("total", 0)
            data.setdefault("log", [])
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"total": 0, "log": []}


def save_data(data: dict) -> None:
    """Speichert die Daten sofort persistent auf die Festplatte."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class HistoryWindow(tk.Toplevel):
    """Overlay-Fenster mit Kalenderansicht: Tage als unterschiedlich
    grosse/farbige Kreise, je nachdem wie viele Klimmzuege an dem Tag
    gemacht wurden (angelehnt an den Strava-Trainingskalender)."""

    def __init__(self, master: "PullupTracker") -> None:
        super().__init__(master)
        self.master_app = master
        self.title("Verlauf")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        today = date.today()
        self.displayed_year = today.year
        self.displayed_month = today.month

        nav_frame = tk.Frame(self)
        nav_frame.pack(pady=(10, 2), fill="x", padx=10)

        tk.Button(nav_frame, text="◀", width=3, command=self._prev_month).pack(
            side="left"
        )
        self.month_label = tk.Label(
            nav_frame, text="", font=("Segoe UI", 11, "bold")
        )
        self.month_label.pack(side="left", expand=True)
        tk.Button(nav_frame, text="▶", width=3, command=self._next_month).pack(
            side="right"
        )

        self.canvas = tk.Canvas(
            self,
            width=CANVAS_WIDTH,
            height=HEADER_HEIGHT + CELL_SIZE * 6,
            highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=(4, 4))

        self.summary_label = ttk.Label(self, text="", font=("Segoe UI", 10))
        self.summary_label.pack(pady=(0, 10))

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
            background="#333333",
            foreground="white",
            font=("Segoe UI", 8),
            padx=6,
            pady=3,
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

    def refresh(self) -> None:
        """Zeichnet den Kalender fuer den aktuell angezeigten Monat neu."""
        self._hide_tooltip()
        self.canvas.delete("all")

        year, month = self.displayed_year, self.displayed_month
        self.month_label.config(text=f"{MONTH_NAMES[month - 1]} {year}")

        daily_totals = self._daily_totals()
        max_value = max(daily_totals.values(), default=0)

        for col, label in enumerate(WEEKDAY_LABELS):
            x = col * CELL_SIZE + CELL_SIZE / 2
            self.canvas.create_text(
                x, HEADER_HEIGHT / 2, text=label, font=("Segoe UI", 8), fill="#6b7280"
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
                    self.canvas.create_oval(
                        cx - MAX_CIRCLE_RADIUS - 3, cy - MAX_CIRCLE_RADIUS - 3,
                        cx + MAX_CIRCLE_RADIUS + 3, cy + MAX_CIRCLE_RADIUS + 3,
                        outline="#2563eb", width=1.5,
                    )

                radius = value_to_radius(value, max_value)
                tag = f"day{key.replace('-', '')}"
                tooltip_text = (
                    f"{key}: {value} Klimmzüge" if value else f"{key}: keine Einträge"
                )

                if value > 0:
                    color = value_to_color(value, max_value)
                    self.canvas.create_oval(
                        cx - radius, cy - radius, cx + radius, cy + radius,
                        fill=color, outline="", tags=(tag,),
                    )
                    text_color = "white"
                else:
                    self.canvas.create_oval(
                        cx - radius, cy - radius, cx + radius, cy + radius,
                        outline="#c3c8d1", tags=(tag,),
                    )
                    text_color = "#6b7280"

                self.canvas.create_text(
                    cx, cy, text=str(day), font=("Segoe UI", 8, "bold"),
                    fill=text_color, tags=(tag,),
                )

                self.canvas.tag_bind(
                    tag, "<Enter>",
                    lambda e, t=tooltip_text: self._show_tooltip(e, t),
                )
                self.canvas.tag_bind(tag, "<Leave>", self._hide_tooltip)

        total = self.master_app.data["total"]
        self.summary_label.config(
            text=f"Diesen Monat: {month_total}   |   Gesamt: {total}"
        )


class PullupTracker(tk.Tk):
    """Hauptfenster: kompaktes, verschiebbares Popup mit den Zaehl-Buttons."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Klimmzug-Tracker")
        self.geometry("240x220")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.data = load_data()
        self.history_window: Optional[HistoryWindow] = None

        self._build_ui()

    def _build_ui(self) -> None:
        self.count_var = tk.StringVar(value=str(self.data["total"]))

        count_label = tk.Label(
            self, textvariable=self.count_var, font=("Segoe UI", 36, "bold")
        )
        count_label.pack(pady=(15, 5))

        tk.Label(self, text="Klimmzuege gesamt", font=("Segoe UI", 9)).pack()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        for delta in (1, 3, 5):
            tk.Button(
                btn_frame,
                text=f"+{delta}",
                width=5,
                font=("Segoe UI", 11, "bold"),
                command=lambda d=delta: self.add(d),
            ).pack(side="left", padx=4)

        action_frame = tk.Frame(self)
        action_frame.pack(pady=(5, 10))

        self.undo_btn = tk.Button(
            action_frame, text="Rueckgaengig", command=self.undo, state="disabled"
        )
        self.undo_btn.pack(side="left", padx=4)

        tk.Button(action_frame, text="Verlauf", command=self.show_history).pack(
            side="left", padx=4
        )

        self._update_undo_state()

    def add(self, delta: int) -> None:
        self.data["total"] += delta
        self.data["log"].append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "delta": delta,
            }
        )
        save_data(self.data)
        self.count_var.set(str(self.data["total"]))
        self._update_undo_state()
        self._refresh_history()

    def undo(self) -> None:
        if not self.data["log"]:
            return
        last = self.data["log"].pop()
        self.data["total"] -= last["delta"]
        save_data(self.data)
        self.count_var.set(str(self.data["total"]))
        self._update_undo_state()
        self._refresh_history()

    def _update_undo_state(self) -> None:
        self.undo_btn.config(state="normal" if self.data["log"] else "disabled")

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

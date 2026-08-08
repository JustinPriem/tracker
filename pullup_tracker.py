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

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Optional

DATA_DIR = Path.home() / ".pullup_tracker"
DATA_FILE = DATA_DIR / "data.json"


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
    """Overlay-Fenster mit dem kompletten Verlauf aller Eintraege."""

    def __init__(self, master: "PullupTracker") -> None:
        super().__init__(master)
        self.master_app = master
        self.title("Verlauf")
        self.geometry("340x420")
        self.attributes("-topmost", True)

        ttk.Label(self, text="Verlauf", font=("Segoe UI", 12, "bold")).pack(
            pady=(10, 4)
        )

        columns = ("datum", "uhrzeit", "anzahl")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        self.tree.heading("datum", text="Datum")
        self.tree.heading("uhrzeit", text="Uhrzeit")
        self.tree.heading("anzahl", text="Anzahl")
        self.tree.column("datum", width=100, anchor="center")
        self.tree.column("uhrzeit", width=90, anchor="center")
        self.tree.column("anzahl", width=70, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.summary_label = ttk.Label(self, text="", font=("Segoe UI", 10))
        self.summary_label.pack(pady=(0, 10))

        self.refresh()

    def refresh(self) -> None:
        """Baut die Tabelle neu auf Basis der aktuellen Daten."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        log = self.master_app.data["log"]
        daily_totals: dict[str, int] = {}
        for entry in reversed(log):
            ts = datetime.fromisoformat(entry["timestamp"])
            date_str = ts.strftime("%d.%m.%Y")
            time_str = ts.strftime("%H:%M:%S")
            self.tree.insert("", "end", values=(date_str, time_str, f"+{entry['delta']}"))
            daily_totals[date_str] = daily_totals.get(date_str, 0) + entry["delta"]

        total = self.master_app.data["total"]
        today_str = datetime.now().strftime("%d.%m.%Y")
        today_total = daily_totals.get(today_str, 0)
        self.summary_label.config(text=f"Heute: {today_total}   |   Gesamt: {total}")


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

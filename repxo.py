"""
Repxo
=====

Klimmzug-Tracker: ein schlankes Popup-Programm zum Zaehlen von
Klimmzuegen (z.B. in Zockpausen). Das Fenster bleibt immer im
Vordergrund und kann frei auf dem Desktop verschoben werden.

Name: REP fuer Wiederholungen (Repetitions), XO als Verweis auf den
Computer/das System.

Start:
    python repxo.py

Die Daten (Gesamtzaehler + Verlauf) werden dauerhaft gespeichert unter:
    ~/.repxo/data.json
"""

from __future__ import annotations

import calendar
import ctypes
import http.server
import json
import shutil
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageTk
from supabase import Client, create_client

APP_NAME = "Repxo"
APP_VERSION = "1.1.0"

# --- Auto-Update-Check (gegen GitHub Releases) --------------------------
LATEST_RELEASE_API_URL = "https://api.github.com/repos/JustinPriem/tracker/releases/latest"
UPDATE_CHECK_TIMEOUT = 4  # Sekunden

DATA_DIR = Path.home() / ".repxo"
DATA_FILE = DATA_DIR / "data.json"
SESSION_FILE = DATA_DIR / "session.json"

# Alter Datenordner aus der Zeit vor dem Rebranding zu "Repxo" - wird beim
# ersten Start automatisch nach DATA_DIR migriert, damit niemand seine
# bisherigen Klimmzuege verliert.
LEGACY_DATA_FILE = Path.home() / ".pullup_tracker" / "data.json"

# --- Cloud-Sync (optional) ---------------------------------------------
# Anmeldung mit Google ueber Supabase synchronisiert die Stats zusaetzlich
# in die Cloud, damit sie geraeteuebergreifend verfuegbar sind. Ohne Login
# funktioniert die App unveraendert komplett lokal/offline.
SUPABASE_URL = "https://yfqatrurllwgegoytgbn.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_6ebvJQzvg2_Tf-COMSAPXw_feGjsNE0"
OAUTH_REDIRECT_PORT = 8765
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_REDIRECT_PORT}/callback"


def resource_path(*parts: str) -> Path:
    """Findet Dateien wie das Icon sowohl im Skript- als auch im
    PyInstaller-gebuendelten Modus (dort liegen Extra-Dateien unter
    sys._MEIPASS statt neben dem Skript)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def _parse_version(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.strip().lstrip("v").split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def fetch_latest_release() -> Optional[dict]:
    """Fragt den neuesten GitHub-Release ab (Tag-Name + Release-Seite).

    Laeuft blockierend - MUSS ueber _run_async in einem Hintergrund-Thread
    aufgerufen werden. Netzwerkfehler werden bewusst nach oben durchgereicht
    (der Aufrufer/_run_async faengt Exceptions ab und ignoriert sie dann).
    """
    request = urllib.request.Request(
        LATEST_RELEASE_API_URL,
        headers={"Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=UPDATE_CHECK_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {"version": payload.get("tag_name", ""), "url": payload.get("html_url", "")}


def _migrate_legacy_data() -> None:
    """Einmalige Migration alter Daten aus ~/.pullup_tracker nach ~/.repxo."""
    if DATA_FILE.exists() or not LEGACY_DATA_FILE.exists():
        return
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_DATA_FILE, DATA_FILE)
    except OSError:
        pass

WEEKDAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTH_NAMES = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

EMPTY_DAY_RADIUS = 10  # fester Radius fuer den duennen Umriss-Kreis an Tagen ohne Eintraege (unveraendert ggue. vorher)
MAX_CIRCLE_RADIUS = 20  # Radius bei REPS_FOR_FULL_SIZE (oder mehr) Klimmzuegen - volle Groesse (Durchmesser 40px)
REPS_FOR_FULL_SIZE = 50  # Ab dieser Tages-Anzahl ist der Kreis auf 100% (volle Groesse)
MIN_RENDER_RADIUS = 2  # rein technischer Mindestwert (kein visueller Floor), verhindert ein 0px-Bild bei sehr kleinen aber >0 Werten

CELL_SIZE = 34  # muss inkl. Padding in die 270px breite Buehne passen (7 Spalten)
HEADER_HEIGHT = 22
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


def load_data() -> dict:
    """Laedt die gespeicherten Daten oder liefert einen leeren Startzustand.

    - total: Gesamtanzahl Klimmzuege aller Zeiten
    - log: jeder einzelne +1/+3/+5 Klick (fuer Kalender-Heatmap & Undo)
    - current_set: laufender, noch nicht abgeschlossener Arbeitssatz
    - sets: alle abgeschlossenen Arbeitssaetze (Datum, Uhrzeit, Wiederholungen)
    - window: zuletzt gespeicherte Fensterposition {"x": int, "y": int}
      oder None, wenn die App noch nie manuell verschoben wurde
    """
    _migrate_legacy_data()
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)
            data.setdefault("total", 0)
            data.setdefault("log", [])
            data.setdefault("current_set", 0)
            data.setdefault("sets", [])
            data.setdefault("window", None)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"total": 0, "log": [], "current_set": 0, "sets": [], "window": None}


def save_data(data: dict) -> None:
    """Speichert die Daten sofort persistent auf die Festplatte."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_session(refresh_token: str, email: str) -> None:
    """Speichert den Refresh-Token, damit der Login einen Neustart uebersteht
    (separate Datei, damit ein simples Loeschen von session.json zum
    Abmelden reicht, ohne die eigentlichen Stats anzufassen)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SESSION_FILE.open("w", encoding="utf-8") as f:
        json.dump({"refresh_token": refresh_token, "email": email}, f)


def load_session() -> Optional[dict]:
    if not SESSION_FILE.exists():
        return None
    try:
        with SESSION_FILE.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def clear_session() -> None:
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def create_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Faengt den OAuth-Redirect von Supabase/Google lokal ab (siehe
    login_with_google). Der PKCE-Flow liefert den Code als Query-Parameter
    (anders als beim klassischen Implicit-Flow mit URL-Fragment), der
    Query-Teil kommt tatsaechlich beim lokalen Server an."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        self.server.auth_code = params.get("code", [None])[0]
        self.server.auth_error = params.get("error_description", [None])[0]

        ok = bool(self.server.auth_code)
        title = "Anmeldung erfolgreich ✓" if ok else "Anmeldung fehlgeschlagen"
        detail = (
            "Du kannst dieses Fenster jetzt schließen."
            if ok
            else "Bitte dieses Fenster schließen und in Repxo erneut versuchen."
        )
        html = (
            "<html><body style=\"font-family:'Segoe UI',sans-serif;"
            "text-align:center;padding-top:80px;background:#0d1117;color:#f5f6f7;\">"
            f"<h2 style=\"color:#ff5722;\">{title}</h2><p>{detail}</p></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # Konsolen-Spam unterdruecken
        pass


def login_with_google(client: Client):
    """Oeffnet den System-Browser zum Google-Login (via Supabase) und wartet
    ueber einen kurzlebigen lokalen HTTP-Server auf den Callback.

    Blockiert bis zu 2 Minuten - MUSS in einem Hintergrund-Thread laufen,
    sonst friert das tkinter-Fenster fuer die Dauer des Logins ein.
    """
    server = http.server.HTTPServer(("localhost", OAUTH_REDIRECT_PORT), _OAuthCallbackHandler)
    server.auth_code = None
    server.auth_error = None

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    res = client.auth.sign_in_with_oauth(
        {"provider": "google", "options": {"redirect_to": OAUTH_REDIRECT_URI}}
    )
    webbrowser.open(res.url)

    thread.join(timeout=120)
    server.server_close()

    if not server.auth_code:
        raise RuntimeError(server.auth_error or "Zeitüberschreitung beim Login.")

    auth_response = client.auth.exchange_code_for_session({"auth_code": server.auth_code})
    return auth_response.session


def _virtual_screen_bounds() -> tuple[int, int, int, int]:
    """Liefert (left, top, right, bottom) der gesamten virtuellen Anzeigeflaeche
    ueber alle angeschlossenen Monitore hinweg (nicht nur den primaeren) -
    fuer die Pruefung, ob eine gespeicherte Fensterposition noch erreichbar
    ist. Bei einem Fehler (0,0,0,0), was als "nicht ermittelbar" behandelt wird."""
    try:
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79
        user32 = ctypes.windll.user32
        left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return left, top, left + width, top + height
    except Exception:
        return 0, 0, 0, 0


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
        on_move_end: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, bg=BG_CARD, height=TITLE_BAR_HEIGHT)
        self.target = target
        self.on_move_end = on_move_end
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
            widget.bind("<ButtonRelease-1>", self._end_move)

    def _start_move(self, event: tk.Event) -> None:
        self._start_x = event.x_root
        self._start_y = event.y_root
        self._win_x = self.target.winfo_x()
        self._win_y = self.target.winfo_y()
        self._moved = False

    def _do_move(self, event: tk.Event) -> None:
        dx = event.x_root - self._start_x
        dy = event.y_root - self._start_y
        self.target.geometry(f"+{self._win_x + dx}+{self._win_y + dy}")
        self._moved = True

    def _end_move(self, _event: tk.Event) -> None:
        if self._moved and self.on_move_end is not None:
            self.on_move_end()


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


class HistoryPage(tk.Frame):
    """Kalenderansicht als eingebettete Seite (kein eigenes Fenster mehr):
    Tage als unterschiedlich grosse/farbige Kreise, je nachdem wie viele
    Klimmzuege an dem Tag gemacht wurden (angelehnt an den
    Strava-Trainingskalender). Wird per Karten-Flip-Animation im
    Hauptfenster ein- und ausgeblendet, siehe RepxoApp._flip_to_page."""

    def __init__(self, master: tk.Widget, app: "RepxoApp") -> None:
        super().__init__(master, bg=BG_DARK)
        self.master_app = app

        today = date.today()
        self.displayed_year = today.year
        self.displayed_month = today.month

        header_frame = tk.Frame(self, bg=BG_DARK)
        header_frame.pack(fill="x", padx=14, pady=(14, 2))

        RoundedButton(
            header_frame, text="←  Zurück", command=app.show_counter,
            width=92, height=30, radius=12, font=FONT_BUTTON_SMALL,
            fill=BG_DARK, hover=BG_CARD, text_color=TEXT_SECONDARY,
            outline=BORDER, outline_width=1, bg_parent=BG_DARK,
        ).pack(side="left")

        tk.Label(
            header_frame, text=spaced("VERLAUF"), font=FONT_EYEBROW,
            bg=BG_DARK, fg=ACCENT,
        ).pack(side="right")

        nav_frame = tk.Frame(self, bg=BG_DARK)
        nav_frame.pack(pady=(10, 4), fill="x", padx=14)

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


WINDOW_WIDTH = 270
WINDOW_HEIGHT = 552  # +32 gegenueber vorher, Platz fuer die Account-Zeile
STAGE_HEIGHT = WINDOW_HEIGHT - TITLE_BAR_HEIGHT

FLIP_STEPS = 10
FLIP_INTERVAL_MS = 16


def _ease_in_out(t: float) -> float:
    """Smoothstep-Easing fuer eine natuerlich wirkende Flip-Bewegung."""
    return t * t * (3 - 2 * t)


class RepxoApp(tk.Tk):
    """Hauptfenster: kompaktes, verschiebbares Popup mit den Zaehl-Buttons.

    Zaehler- und Verlaufsansicht leben als zwei Seiten im selben Fenster
    und werden per Karten-Flip-Animation gewechselt (siehe _flip_to_page) -
    kein separates Popup-Fenster mehr fuer den Kalender.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=BG_DARK, highlightthickness=1, highlightbackground=BORDER)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        try:
            self.iconbitmap(default=str(resource_path("assets", "icon.ico")))
        except Exception:
            pass

        self.data = load_data()
        self._animating = False

        self.supabase = create_supabase_client()
        self.cloud_user = None

        start_x, start_y = self._resolve_startup_position()
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{start_x}+{start_y}")

        self._build_ui()
        self.after(10, lambda: ensure_taskbar_icon(self))
        self._try_restore_session()
        self._run_async(fetch_latest_release, self._on_update_check_done)

    def _resolve_startup_position(self) -> tuple[int, int]:
        """Gespeicherte Fensterposition wiederherstellen - aber nur, wenn
        davon noch genug auf einem tatsaechlich angeschlossenen Monitor
        sichtbar waere. Sonst (z.B. Monitor seitdem abgesteckt) faellt die
        Position sonst dauerhaft ausserhalb des Bildschirms und die App
        waere unerreichbar - dann stattdessen auf dem Hauptbildschirm
        zentrieren, wie beim allerersten Start."""
        center_x = max(0, (self.winfo_screenwidth() - WINDOW_WIDTH) // 2)
        center_y = max(0, (self.winfo_screenheight() - WINDOW_HEIGHT) // 2)

        saved = self.data.get("window")
        if not saved or "x" not in saved or "y" not in saved:
            return center_x, center_y

        x, y = saved["x"], saved["y"]
        left, top, right, bottom = _virtual_screen_bounds()
        if right <= left or bottom <= top:
            return x, y  # virtuelle Anzeigeflaeche nicht ermittelbar - ungeprueft uebernehmen

        margin = 40  # mindestens so viel Titelleiste muss erreichbar sein
        off_screen = (
            x + WINDOW_WIDTH < left + margin
            or x > right - margin
            or y + TITLE_BAR_HEIGHT < top
            or y > bottom - margin
        )
        return (center_x, center_y) if off_screen else (x, y)

    def _save_window_position(self) -> None:
        self.data["window"] = {"x": self.winfo_x(), "y": self.winfo_y()}
        save_data(self.data)

    def _close(self) -> None:
        self._save_window_position()
        self.destroy()

    def _build_ui(self) -> None:
        TitleBar(
            self, self, APP_NAME, self._close,
            on_move_end=self._save_window_position,
        ).pack(fill="x")

        # "Buehne": haelt beide Seiten (Zaehler/Verlauf) uebereinander in
        # einem Canvas, damit die Flip-Animation die sichtbare Seite per
        # Breiten-Animation zusammenschrumpfen/aufwachsen lassen kann.
        self.stage = tk.Canvas(
            self, width=WINDOW_WIDTH, height=STAGE_HEIGHT,
            bg=BG_DARK, highlightthickness=0,
        )
        self.stage.pack(fill="both", expand=True)

        self.counter_page = tk.Frame(self.stage, bg=BG_DARK)
        self._build_counter_page(self.counter_page)

        self.history_page = HistoryPage(self.stage, self)

        self._stage_item = self.stage.create_window(
            WINDOW_WIDTH // 2, 0, anchor="n", window=self.counter_page,
            width=WINDOW_WIDTH, height=STAGE_HEIGHT,
        )

        self._refresh_display()

    def _build_counter_page(self, content: tk.Frame) -> None:
        self.account_frame = tk.Frame(content, bg=BG_DARK)
        self.account_frame.pack(pady=(14, 0))

        self.login_btn = RoundedButton(
            self.account_frame, text="☁  Mit Google anmelden", command=self.start_login,
            width=214, height=32, radius=12, font=FONT_BUTTON_SMALL,
            fill=BG_DARK, hover=BG_CARD, text_color=TEXT_SECONDARY,
            outline=BORDER, outline_width=1, bg_parent=BG_DARK,
        )

        self.account_info_frame = tk.Frame(self.account_frame, bg=BG_DARK)
        self.account_email_var = tk.StringVar(value="")
        tk.Label(
            self.account_info_frame, textvariable=self.account_email_var,
            font=FONT_TOTAL, bg=BG_DARK, fg=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 8))
        RoundedButton(
            self.account_info_frame, text="Abmelden", command=self.logout,
            width=76, height=26, radius=10, font=(FONT_FAMILY, 8, "bold"),
            fill=BG_DARK, hover=BG_CARD, text_color=ACCENT_HOVER,
            bg_parent=BG_DARK,
        ).pack(side="left")

        # Fehlermeldung bei fehlgeschlagenem Login - standardmaessig nicht
        # gepackt (nimmt keinen Platz weg), erscheint nur bei Bedarf. Ohne
        # das war ein Login-Fehler bisher komplett unsichtbar (nur ein
        # print(), das es in der gebauten .exe ohne Konsole nie zu sehen gibt).
        self.login_error_var = tk.StringVar(value="")
        self.login_error_label = tk.Label(
            self.account_frame, textvariable=self.login_error_var,
            font=(FONT_FAMILY, 8, "bold"), bg=BG_DARK, fg="#f87171",
            wraplength=230, justify="center",
        )

        self._update_account_ui()

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

        self.update_label = tk.Label(
            content, text="", font=(FONT_FAMILY, 8, "bold", "underline"),
            bg=BG_DARK, fg=ACCENT_HOVER, cursor="hand2",
        )
        self.update_label.bind("<Button-1>", self._open_update_page)

    # --- Auto-Update-Check (gegen GitHub Releases) --------------------------

    def _on_update_check_done(self, result: object) -> None:
        if isinstance(result, Exception) or not result:
            return  # kein Internet / GitHub nicht erreichbar -> einfach ignorieren
        latest_version = result["version"]
        if _parse_version(latest_version) > _parse_version(APP_VERSION):
            self._show_update_banner(latest_version, result["url"])

    def _show_update_banner(self, latest_version: str, url: str) -> None:
        self._update_url = url
        self.update_label.config(text=f"🔄 Update {latest_version} verfügbar")
        self.update_label.pack(pady=(10, 0))

    def _open_update_page(self, _event: Optional[tk.Event] = None) -> None:
        webbrowser.open(self._update_url)

    # --- Cloud-Login (Google via Supabase) ---------------------------------

    def _run_async(self, fn: Callable[[], object], on_done: Optional[Callable[[object], None]] = None) -> None:
        """Fuehrt fn() in einem Hintergrund-Thread aus (Netzwerk-Calls duerfen
        die tkinter-UI nicht blockieren) und ruft on_done(result) danach im
        Tk-Hauptthread auf (ueber self.after) - Tk-Widgets duerfen nur vom
        Hauptthread aus angefasst werden."""
        def worker() -> None:
            try:
                result: object = fn()
            except Exception as exc:  # best effort: Fehler nur melden, nie crashen
                result = exc
            if on_done:
                self.after(0, lambda: on_done(result))
        threading.Thread(target=worker, daemon=True).start()

    def _fetch_cloud_row(self, user_id: str) -> Optional[dict]:
        res = (
            self.supabase.table("repxo_stats")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return res.data if res else None

    def _try_restore_session(self) -> None:
        """Beim Start pruefen, ob ein gespeicherter Login vom letzten Mal
        existiert, und ihn im Hintergrund stillschweigend erneuern (kein
        Browser-Popup noetig, nur ein Netzwerk-Call)."""
        saved = load_session()
        if not saved:
            return

        def restore():
            auth_response = self.supabase.auth.refresh_session(saved["refresh_token"])
            session = auth_response.session
            cloud_row = self._fetch_cloud_row(session.user.id)
            return session, cloud_row

        # silent=True: ein abgelaufener/ungueltiger gespeicherter Login beim
        # stillen Hintergrund-Refresh ist normal (Token laeuft irgendwann
        # ab) - dafuer keine Fehlermeldung zeigen, nur bei einem aktiven,
        # vom Nutzer angestossenen Login-Versuch.
        self._run_async(restore, lambda result: self._on_login_done(result, silent=True))

    def start_login(self) -> None:
        self._hide_login_error()
        self.login_btn.set_enabled(False)
        self.login_btn.set_text("Öffne Browser…")

        def do_login():
            session = login_with_google(self.supabase)
            cloud_row = self._fetch_cloud_row(session.user.id)
            return session, cloud_row

        self._run_async(do_login, self._on_login_done)

    def _show_login_error(self, message: str) -> None:
        self.login_error_var.set(f"⚠ Login fehlgeschlagen: {message}")
        self.login_error_label.pack(pady=(6, 0))

    def _hide_login_error(self) -> None:
        self.login_error_label.pack_forget()

    def _on_login_done(self, result: object, silent: bool = False) -> None:
        self.login_btn.set_enabled(True)
        self.login_btn.set_text("☁  Mit Google anmelden")

        if isinstance(result, Exception):
            print(f"Login fehlgeschlagen: {result}", flush=True)
            if not silent:
                self._show_login_error(str(result))
            return

        self._hide_login_error()
        session, cloud_row = result
        self.cloud_user = session.user
        save_session(session.refresh_token, session.user.email or "")

        if cloud_row:
            self.data["total"] = cloud_row.get("total", self.data["total"])
            self.data["current_set"] = cloud_row.get("current_set", self.data["current_set"])
            self.data["log"] = cloud_row.get("log") or []
            self.data["sets"] = cloud_row.get("sets") or []
            save_data(self.data)
        else:
            self._sync_to_cloud()

        self._update_account_ui()
        self._refresh_display()

    def logout(self) -> None:
        client = self.supabase
        self._run_async(lambda: client.auth.sign_out())
        clear_session()
        self.cloud_user = None
        self._update_account_ui()

    def _update_account_ui(self) -> None:
        if self.cloud_user:
            self.login_btn.pack_forget()
            self.account_email_var.set(self.cloud_user.email or "Angemeldet")
            self.account_info_frame.pack()
        else:
            self.account_info_frame.pack_forget()
            self.login_btn.pack()

    def _sync_to_cloud(self) -> None:
        """Schreibt den aktuellen Stand im Hintergrund nach Supabase (best
        effort - Netzwerkfehler duerfen die App nie blockieren/crashen)."""
        if not self.cloud_user:
            return
        snapshot = dict(self.data)
        user_id = self.cloud_user.id
        client = self.supabase

        def push():
            client.table("repxo_stats").upsert({
                "user_id": user_id,
                "total": snapshot["total"],
                "current_set": snapshot["current_set"],
                "log": snapshot["log"],
                "sets": snapshot["sets"],
                "updated_at": datetime.now().isoformat(),
            }).execute()

        self._run_async(push)

    def _flip_to_page(self, target_widget: tk.Widget, on_swap: Optional[Callable[[], None]] = None) -> None:
        """Karten-Flip: aktuelle Seite schrumpft horizontal zur Mitte zusammen,
        Inhalt wird im schmalsten Moment ausgetauscht, dann waechst die neue
        Seite wieder auf volle Breite - simuliert eine Karte, die sich dreht."""
        if self._animating:
            return
        self._animating = True

        def shrink(i: int = 0) -> None:
            t = i / FLIP_STEPS
            w = max(2, round(WINDOW_WIDTH * (1 - _ease_in_out(t))))
            self.stage.itemconfig(self._stage_item, width=w)
            if i < FLIP_STEPS:
                self.after(FLIP_INTERVAL_MS, lambda: shrink(i + 1))
            else:
                self.stage.itemconfig(self._stage_item, window=target_widget, width=2)
                if on_swap:
                    on_swap()
                grow()

        def grow(i: int = 0) -> None:
            t = i / FLIP_STEPS
            w = max(2, round(WINDOW_WIDTH * _ease_in_out(t)))
            self.stage.itemconfig(self._stage_item, width=w)
            if i < FLIP_STEPS:
                self.after(FLIP_INTERVAL_MS, lambda: grow(i + 1))
            else:
                self.stage.itemconfig(self._stage_item, width=WINDOW_WIDTH)
                self._animating = False

        shrink()

    def show_history(self) -> None:
        self._flip_to_page(self.history_page, on_swap=self.history_page.refresh)

    def show_counter(self) -> None:
        self._flip_to_page(self.counter_page)

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
        self._sync_to_cloud()
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
        self._sync_to_cloud()
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
        self._sync_to_cloud()
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

        self.history_page.refresh()


if __name__ == "__main__":
    app = RepxoApp()
    app.mainloop()

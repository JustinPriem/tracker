// Repxo (Browser-Version) – Klimmzug-Tracker
// Speichert Daten lokal im Browser (localStorage) - funktioniert komplett
// ohne Login. Optional: Anmeldung mit Google (via Supabase) synchronisiert
// die Stats zusätzlich in die Cloud, damit sie geräteübergreifend
// verfügbar sind. Lokal bleibt dabei immer die schnelle, offline-fähige
// Quelle; die Cloud wird nur im Hintergrund nachgezogen.
//
// Datenmodell (analog zur Desktop-Version):
// - total: Gesamtanzahl Klimmzüge aller Zeiten
// - log: jeder einzelne +1/+3/+5 Klick (für Kalender-Heatmap & Undo)
// - currentSet: laufender, noch nicht abgeschlossener Arbeitssatz
// - sets: alle abgeschlossenen Arbeitssätze (Datum, Uhrzeit, Wiederholungen)

const STORAGE_KEY = "repxoData";
const LEGACY_STORAGE_KEY = "pullupTrackerData"; // vor dem Rebranding zu Repxo

// Muss zu jedem Release passend mit hochgezaehlt werden (siehe
// android-app/android/app/build.gradle versionName und
// installer/repxo.iss MyAppVersion) - wird nur fuer den Auto-Update-Check
// der nativen Android-App verwendet (siehe checkForUpdate unten), die
// Website selbst ist ueber GitHub Pages ohnehin immer aktuell.
const APP_VERSION = "1.1.0";
const LATEST_RELEASE_API_URL = "https://api.github.com/repos/JustinPriem/repxo/releases/latest";

const SUPABASE_URL = "https://yfqatrurllwgegoytgbn.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_6ebvJQzvg2_Tf-COMSAPXw_feGjsNE0";
// Defensiv: falls supabase.min.js aus irgendeinem Grund nicht laedt (z.B.
// kein Internet beim ersten Start der Android-App), soll wenigstens das
// lokale Tracking weiterhin funktionieren statt die ganze Seite zu crashen.
const sb = typeof supabase !== "undefined"
  ? supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
  : null;

let currentUser = null;

function loadData() {
  try {
    let raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      // Einmalige Migration alter Daten aus der Zeit vor "Repxo".
      const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (legacy) {
        raw = legacy;
        localStorage.setItem(STORAGE_KEY, legacy);
      }
    }
    if (raw) {
      const parsed = JSON.parse(raw);
      if (typeof parsed.total !== "number") parsed.total = 0;
      if (!Array.isArray(parsed.log)) parsed.log = [];
      if (typeof parsed.currentSet !== "number") parsed.currentSet = 0;
      if (!Array.isArray(parsed.sets)) parsed.sets = [];
      return parsed;
    }
  } catch (err) {
    console.warn("Gespeicherte Daten konnten nicht gelesen werden, starte neu.", err);
  }
  return { total: 0, log: [], currentSet: 0, sets: [] };
}

function saveData(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  pushToCloud();
}

async function pushToCloud() {
  if (!currentUser) return;
  try {
    const { error } = await sb.from("repxo_stats").upsert({
      user_id: currentUser.id,
      total: data.total,
      current_set: data.currentSet,
      log: data.log,
      sets: data.sets,
      updated_at: new Date().toISOString(),
    });
    if (error) console.warn("Cloud-Sync fehlgeschlagen:", error.message);
  } catch (err) {
    console.warn("Cloud-Sync fehlgeschlagen:", err);
  }
}

async function pullFromCloud(user) {
  try {
    const { data: row, error } = await sb
      .from("repxo_stats")
      .select("*")
      .eq("user_id", user.id)
      .maybeSingle();
    if (error) {
      console.warn("Cloud-Daten konnten nicht geladen werden:", error.message);
      return;
    }
    if (row) {
      data = {
        total: row.total,
        currentSet: row.current_set,
        log: row.log || [],
        sets: row.sets || [],
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } else {
      // Erster Login, noch keine Cloud-Zeile - lokale (Gast-)Daten hochladen.
      await pushToCloud();
    }
    render();
  } catch (err) {
    console.warn("Cloud-Daten konnten nicht geladen werden:", err);
  }
}

let data = loadData();

const counterEl = document.getElementById("counter");
const finishBtn = document.getElementById("finishBtn");
const setsTodayEl = document.getElementById("setsToday");
const totalLineEl = document.getElementById("totalLine");
const undoBtn = document.getElementById("undoBtn");
const historyBtn = document.getElementById("historyBtn");
const historyDialog = document.getElementById("historyDialog");
const closeHistoryBtn = document.getElementById("closeHistory");
const historySummary = document.getElementById("historySummary");
const calendarTitle = document.getElementById("calendarTitle");
const weekdayRow = document.getElementById("weekdayRow");
const calendarGrid = document.getElementById("calendarGrid");
const prevMonthBtn = document.getElementById("prevMonth");
const nextMonthBtn = document.getElementById("nextMonth");
const loginBtn = document.getElementById("loginBtn");
const accountInfo = document.getElementById("accountInfo");
const accountEmail = document.getElementById("accountEmail");
const logoutBtn = document.getElementById("logoutBtn");

const WEEKDAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const MAX_CIRCLE_SIZE = 48; // Durchmesser in px bei REPS_FOR_FULL_SIZE (oder mehr) Klimmzuegen
const REPS_FOR_FULL_SIZE = 50; // Ab dieser Tages-Anzahl ist der Kreis auf 100% (volle Groesse)
const MIN_RENDER_SIZE = 4; // rein technischer Mindestwert (kein visueller Floor), verhindert eine 0px-Flaeche bei sehr kleinen aber >0 Werten
const EMPTY_DAY_SIZE = MIN_RENDER_SIZE; // Tage ohne Eintraege sind exakt so klein wie der kleinstmoegliche reale Wert - nie kleiner UND nie groesser als ein trainierter Tag

let calendarDate = new Date();

function dateKey(year, monthIndex, day) {
  return `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function todayKey() {
  const now = new Date();
  return dateKey(now.getFullYear(), now.getMonth(), now.getDate());
}

function todaysSetReps() {
  return data.sets.filter((s) => s.date === todayKey()).map((s) => s.reps);
}

function lastSetIsToday() {
  return data.sets.length > 0 && data.sets[data.sets.length - 1].date === todayKey();
}

function render() {
  counterEl.textContent = data.currentSet;

  const todayReps = todaysSetReps();
  setsTodayEl.textContent = todayReps.length ? todayReps.join(" · ") : "–";
  totalLineEl.textContent = `GESAMT ${data.total}`;

  finishBtn.disabled = data.currentSet <= 0;

  const canUndo = data.currentSet > 0 || lastSetIsToday();
  undoBtn.disabled = !canUndo;
  undoBtn.textContent =
    data.currentSet === 0 && lastSetIsToday() ? "↺ Satz öffnen" : "↺ Rückgängig";

  if (historyDialog.open) renderCalendar();
}

function addDelta(delta) {
  data.total += delta;
  data.currentSet += delta;
  data.log.push({ timestamp: new Date().toISOString(), delta });
  saveData(data);
  render();
}

function finishSet() {
  if (data.currentSet <= 0) return;
  const now = new Date();
  data.sets.push({
    date: todayKey(),
    time: now.toTimeString().slice(0, 5),
    reps: data.currentSet,
  });
  data.currentSet = 0;
  saveData(data);
  render();
}

function undo() {
  if (data.currentSet > 0) {
    if (data.log.length > 0) {
      const last = data.log.pop();
      data.total -= last.delta;
      data.currentSet = Math.max(0, data.currentSet - last.delta);
    } else {
      data.currentSet = 0;
    }
  } else if (lastSetIsToday()) {
    const lastSet = data.sets.pop();
    data.currentSet = lastSet.reps;
  } else {
    return;
  }
  saveData(data);
  render();
}

function getDailyTotals() {
  const totals = {};
  for (const entry of data.log) {
    const d = new Date(entry.timestamp);
    const key = dateKey(d.getFullYear(), d.getMonth(), d.getDate());
    totals[key] = (totals[key] || 0) + entry.delta;
  }
  return totals;
}

function getDailySets() {
  const byDay = {};
  for (const s of data.sets) {
    if (!byDay[s.date]) byDay[s.date] = [];
    byDay[s.date].push(s.reps);
  }
  return byDay;
}

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

function renderCalendar() {
  const year = calendarDate.getFullYear();
  const monthIndex = calendarDate.getMonth();
  const totals = getDailyTotals();
  const dailySets = getDailySets();

  calendarTitle.textContent = calendarDate.toLocaleDateString("de-DE", {
    month: "long",
    year: "numeric",
  });

  weekdayRow.innerHTML = WEEKDAY_LABELS.map((label) => `<div>${label}</div>`).join("");
  calendarGrid.innerHTML = "";

  const firstOfMonth = new Date(year, monthIndex, 1);
  const firstWeekday = (firstOfMonth.getDay() + 6) % 7; // Montag = 0
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

  const todayK = todayKey();

  for (let i = 0; i < firstWeekday; i++) {
    const filler = document.createElement("div");
    filler.className = "day-cell empty-cell";
    calendarGrid.appendChild(filler);
  }

  let monthTotal = 0;

  for (let day = 1; day <= daysInMonth; day++) {
    const key = dateKey(year, monthIndex, day);
    const value = totals[key] || 0;
    monthTotal += value;

    const cell = document.createElement("div");
    cell.className = "day-cell" + (key === todayK ? " today" : "");

    const circle = document.createElement("div");
    const size = value > 0 ? valueToSize(value) : EMPTY_DAY_SIZE;
    // Als Prozent der Zelle statt fixer px setzen, damit der Kreis auf
    // schmalen Handy-Breiten automatisch mitschrumpft (sonst ueberragt ein
    // 48px-Kreis die Spaltenbreite bei allem < ca. 440px Viewport-Breite).
    // .day-circle begrenzt per aspect-ratio/max-width in CSS die absolute
    // Obergrenze auf MAX_CIRCLE_SIZE, damit "100%" auf breiten Screens
    // nicht groesser als der eigentlich beabsichtigte Maximalwert wird.
    circle.style.width = `${(size / MAX_CIRCLE_SIZE) * 100}%`;

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
    circle.dataset.tooltip = tooltipText;
    circle.setAttribute("aria-label", tooltipText);
    circle.textContent = String(day);
    cell.appendChild(circle);

    calendarGrid.appendChild(cell);
  }

  historySummary.textContent = `DIESEN MONAT ${monthTotal}      GESAMT ${data.total}`;
}

const dayTooltip = document.createElement("div");
dayTooltip.className = "day-tooltip";
historyDialog.appendChild(dayTooltip);
let tooltipHideTimer = null;

function showDayTooltip(circleEl) {
  const text = circleEl.dataset.tooltip;
  if (!text) return;
  clearTimeout(tooltipHideTimer);
  dayTooltip.textContent = text;
  const rect = circleEl.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  dayTooltip.style.left = `${centerX}px`;
  dayTooltip.style.top = `${rect.top - 8}px`;
  dayTooltip.classList.add("visible");
  // Erst nach dem Sichtbarmachen messen (Breite haengt vom gerade erst
  // gesetzten Textinhalt ab) und horizontal an den Viewport-Rand klemmen -
  // auf schmalen Handy-Breiten wuerde die Box sonst links/rechts
  // abgeschnitten aus dem Bildschirm ragen.
  const half = dayTooltip.offsetWidth / 2;
  const clampedX = Math.min(Math.max(centerX, half + 4), window.innerWidth - half - 4);
  dayTooltip.style.left = `${clampedX}px`;
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

// Beim Schliessen des Dialogs (Escape, Klick auf "Schliessen", ...) auch
// einen gerade sichtbaren Tooltip zuruecksetzen, sonst blitzt er beim
// naechsten Oeffnen kurz an der alten Stelle auf.
historyDialog.addEventListener("close", hideDayTooltip);

document.querySelectorAll(".btn-add").forEach((btn) => {
  btn.addEventListener("click", () => addDelta(Number(btn.dataset.delta)));
});

finishBtn.addEventListener("click", finishSet);
undoBtn.addEventListener("click", undo);

historyBtn.addEventListener("click", () => {
  calendarDate = new Date();
  renderCalendar();
  historyDialog.showModal();
});

closeHistoryBtn.addEventListener("click", () => historyDialog.close());

prevMonthBtn.addEventListener("click", () => {
  calendarDate = new Date(calendarDate.getFullYear(), calendarDate.getMonth() - 1, 1);
  renderCalendar();
});

nextMonthBtn.addEventListener("click", () => {
  calendarDate = new Date(calendarDate.getFullYear(), calendarDate.getMonth() + 1, 1);
  renderCalendar();
});

// --- Cloud-Login (Google via Supabase) ---

async function updateAccountUI(session) {
  if (session && session.user) {
    currentUser = session.user;
    loginBtn.hidden = true;
    accountInfo.hidden = false;
    accountEmail.textContent = session.user.email || "Angemeldet";
    await pullFromCloud(session.user);
  } else {
    currentUser = null;
    loginBtn.hidden = false;
    accountInfo.hidden = true;
  }
}

function currentPageUrl() {
  // Normalisiert auf einen abschliessenden "/", damit die Redirect-URL
  // immer exakt mit dem in Supabase hinterlegten Eintrag matcht, egal ob
  // die Seite mit oder ohne trailing slash aufgerufen wurde.
  let url = window.location.origin + window.location.pathname;
  if (!url.endsWith("/")) url += "/";
  return url;
}

// In der nativen Android-App (Capacitor) laeuft die Seite unter einer
// lokalen capacitor://-URL, nicht unter der echten Website-Adresse - ein
// normaler Redirect wuerde daher ins Leere laufen (siehe Bugreport: "komme
// nicht zurueck in die App"). Ausserdem verweigert Google Sign-in generell
// in eingebetteten WebViews. Deshalb: Login-Seite explizit im System-
// Browser (Custom Tab) oeffnen und ueber einen eigenen Deep-Link
// (repxo://callback) wieder zurueck in die App leiten.
const NATIVE_OAUTH_REDIRECT = "repxo://callback";
const isNativeApp = !!(
  window.Capacitor &&
  window.Capacitor.isNativePlatform &&
  window.Capacitor.isNativePlatform()
);

// --- Download-Versionen anzeigen + Auto-Update-Check (gegen GitHub Releases) ---

const updateBanner = document.getElementById("updateBanner");
let updateUrl = null;

function parseVersion(version) {
  return version
    .trim()
    .replace(/^v/, "")
    .split(".")
    .map((piece) => parseInt(piece, 10) || 0);
}

function isNewerVersion(remote, local) {
  const a = parseVersion(remote);
  const b = parseVersion(local);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const diff = (a[i] || 0) - (b[i] || 0);
    if (diff !== 0) return diff > 0;
  }
  return false;
}

function showDownloadVersions(version) {
  // Haengt die aktuelle Release-Version an jeden Download-Untertitel in der
  // Sidebar an (z.B. "Installer (.exe) · v1.1.0"), damit auf der Website
  // immer sichtbar ist, welche Version gerade zum Download bereitsteht.
  document.querySelectorAll(".download-sub").forEach((el) => {
    el.textContent = `${el.textContent} · ${version}`;
  });
}

async function checkForUpdate() {
  try {
    const res = await fetch(LATEST_RELEASE_API_URL, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!res.ok) return;
    const release = await res.json();
    const latest = release.tag_name || "";
    if (latest) showDownloadVersions(latest);
    // Der Update-Hinweis-Banner ist nur fuer die native App relevant, deren
    // Inhalte fest in der APK stecken - die Website selbst ist ueber
    // GitHub Pages ohnehin immer aktuell.
    if (isNativeApp && latest && isNewerVersion(latest, APP_VERSION)) {
      updateUrl = release.html_url;
      updateBanner.textContent = `🔄 Update ${latest} verfügbar`;
      updateBanner.hidden = false;
    }
  } catch (err) {
    console.warn("Update-Check fehlgeschlagen:", err); // z.B. kein Internet
  }
}

updateBanner.addEventListener("click", () => {
  if (!updateUrl) return;
  if (isNativeApp && window.Capacitor.Plugins.Browser) {
    window.Capacitor.Plugins.Browser.open({ url: updateUrl });
  } else {
    window.open(updateUrl, "_blank");
  }
});

async function handleOAuthCallbackUrl(urlString) {
  try {
    const url = new URL(urlString);
    if (url.hash && url.hash.includes("access_token")) {
      // Implicit-Flow: Tokens stehen im Fragment.
      const params = new URLSearchParams(url.hash.substring(1));
      const access_token = params.get("access_token");
      const refresh_token = params.get("refresh_token");
      if (access_token && refresh_token) {
        await sb.auth.setSession({ access_token, refresh_token });
      }
    } else if (url.searchParams.get("code")) {
      // PKCE-Flow: Code als Query-Parameter, wird gegen die Session getauscht.
      await sb.auth.exchangeCodeForSession(url.searchParams.get("code"));
    }
  } catch (err) {
    console.warn("OAuth-Callback konnte nicht verarbeitet werden:", err);
  }
  if (window.Capacitor.Plugins.Browser) {
    window.Capacitor.Plugins.Browser.close().catch(() => {});
  }
}

if (sb) {
  loginBtn.addEventListener("click", async () => {
    if (isNativeApp) {
      const { data, error } = await sb.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: NATIVE_OAUTH_REDIRECT, skipBrowserRedirect: true },
      });
      if (!error && data && data.url) {
        await window.Capacitor.Plugins.Browser.open({ url: data.url });
      } else if (error) {
        console.warn("Login fehlgeschlagen:", error.message);
      }
    } else {
      await sb.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: currentPageUrl() },
      });
    }
  });

  logoutBtn.addEventListener("click", async () => {
    await sb.auth.signOut();
  });

  sb.auth.onAuthStateChange((_event, session) => {
    updateAccountUI(session);
  });

  if (isNativeApp) {
    window.Capacitor.Plugins.App.addListener("appUrlOpen", (event) => {
      if (event.url && event.url.startsWith(NATIVE_OAUTH_REDIRECT)) {
        handleOAuthCallbackUrl(event.url);
      }
    });
  } else if (window.location.hash.includes("access_token")) {
    // Nach dem OAuth-Redirect haengt ein #access_token=... in der URL - aus
    // der Adressleiste entfernen, sobald Supabase die Session daraus gelesen hat.
    sb.auth.getSession().then(() => {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    });
  }
} else {
  // Cloud-Bibliothek konnte nicht geladen werden (z.B. offline) - Button
  // ausblenden, App funktioniert ansonsten unveraendert rein lokal weiter.
  console.warn("Supabase konnte nicht geladen werden - Cloud-Sync deaktiviert.");
  loginBtn.hidden = true;
}

// --- Downloads-Seitenmenü (nur auf schmalen Bildschirmen sichtbar/nutzbar) ---

const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const sidebarClose = document.getElementById("sidebarClose");
const sidebarBackdrop = document.getElementById("sidebarBackdrop");

function openSidebar() {
  sidebar.classList.add("open");
  sidebarBackdrop.classList.add("visible");
  menuToggle.classList.add("is-hidden");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  sidebarBackdrop.classList.remove("visible");
  menuToggle.classList.remove("is-hidden");
}

menuToggle.addEventListener("click", openSidebar);
sidebarClose.addEventListener("click", closeSidebar);
sidebarBackdrop.addEventListener("click", closeSidebar);

render();
checkForUpdate();

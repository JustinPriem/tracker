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

const SUPABASE_URL = "https://yfqatrurllwgegoytgbn.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_6ebvJQzvg2_Tf-COMSAPXw_feGjsNE0";
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);

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
const MIN_CIRCLE_SIZE = 26;
const MAX_CIRCLE_SIZE = 40;

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

function renderCalendar() {
  const year = calendarDate.getFullYear();
  const monthIndex = calendarDate.getMonth();
  const totals = getDailyTotals();
  const dailySets = getDailySets();
  const maxValue = Object.values(totals).length ? Math.max(...Object.values(totals)) : 0;

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
    circle.title = tooltipText;
    circle.textContent = String(day);
    cell.appendChild(circle);

    calendarGrid.appendChild(cell);
  }

  historySummary.textContent = `DIESEN MONAT ${monthTotal}      GESAMT ${data.total}`;
}

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

loginBtn.addEventListener("click", async () => {
  await sb.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin + window.location.pathname },
  });
});

logoutBtn.addEventListener("click", async () => {
  await sb.auth.signOut();
});

sb.auth.onAuthStateChange((_event, session) => {
  updateAccountUI(session);
});

// Nach dem OAuth-Redirect haengt ein #access_token=... in der URL - aus der
// Adressleiste entfernen, sobald Supabase die Session daraus gelesen hat.
if (window.location.hash.includes("access_token")) {
  sb.auth.getSession().then(() => {
    history.replaceState(null, "", window.location.pathname + window.location.search);
  });
}

render();

// Klimmzug-Tracker (Browser-Version)
// Speichert Gesamtzähler + Verlauf lokal im Browser (localStorage).
// Keine Anmeldung, kein Server nötig; Daten bleiben nach Neustart erhalten,
// sind aber an diesen einen Browser auf diesem einen Gerät gebunden.

const STORAGE_KEY = "pullupTrackerData";

function loadData() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (typeof parsed.total !== "number") parsed.total = 0;
      if (!Array.isArray(parsed.log)) parsed.log = [];
      return parsed;
    }
  } catch (err) {
    console.warn("Gespeicherte Daten konnten nicht gelesen werden, starte neu.", err);
  }
  return { total: 0, log: [] };
}

function saveData(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

let data = loadData();

const counterEl = document.getElementById("counter");
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

const WEEKDAY_LABELS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const MIN_CIRCLE_SIZE = 26;
const MAX_CIRCLE_SIZE = 40;

let calendarDate = new Date();

function render() {
  counterEl.textContent = data.total;
  undoBtn.disabled = data.log.length === 0;
}

function addDelta(delta) {
  data.total += delta;
  data.log.push({ timestamp: new Date().toISOString(), delta });
  saveData(data);
  render();
  if (historyDialog.open) renderCalendar();
}

function undo() {
  if (data.log.length === 0) return;
  const last = data.log.pop();
  data.total -= last.delta;
  saveData(data);
  render();
  if (historyDialog.open) renderCalendar();
}

function dateKey(year, monthIndex, day) {
  return `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
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
  const low = hexToRgb(styles.getPropertyValue("--heat-low") || "#ffe0bd");
  const high = hexToRgb(styles.getPropertyValue("--heat-high") || "#ea580c");
  const ratio = maxValue > 0 ? Math.min(value / maxValue, 1) : 1;
  const rgb = low.map((start, i) => Math.round(start + (high[i] - start) * ratio));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function renderCalendar() {
  const year = calendarDate.getFullYear();
  const monthIndex = calendarDate.getMonth();
  const totals = getDailyTotals();
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

  const today = new Date();
  const todayKey = dateKey(today.getFullYear(), today.getMonth(), today.getDate());

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
    cell.className = "day-cell" + (key === todayKey ? " today" : "");

    const circle = document.createElement("div");
    const size = valueToSize(value, maxValue);
    circle.style.width = `${size}px`;
    circle.style.height = `${size}px`;
    if (value > 0) {
      circle.className = "day-circle";
      circle.style.background = valueToColor(value, maxValue);
      circle.title = `${key}: ${value} Klimmzüge`;
    } else {
      circle.className = "day-circle no-data";
      circle.title = `${key}: keine Einträge`;
    }
    circle.textContent = String(day);
    cell.appendChild(circle);

    calendarGrid.appendChild(cell);
  }

  historySummary.textContent = `Diesen Monat: ${monthTotal}  |  Gesamt: ${data.total}`;
}

document.querySelectorAll(".btn-add").forEach((btn) => {
  btn.addEventListener("click", () => addDelta(Number(btn.dataset.delta)));
});

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

render();

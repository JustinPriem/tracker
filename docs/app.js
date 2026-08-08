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
const historyBody = document.getElementById("historyBody");
const historySummary = document.getElementById("historySummary");

function render() {
  counterEl.textContent = data.total;
  undoBtn.disabled = data.log.length === 0;
}

function addDelta(delta) {
  data.total += delta;
  data.log.push({ timestamp: new Date().toISOString(), delta });
  saveData(data);
  render();
  if (historyDialog.open) renderHistory();
}

function undo() {
  if (data.log.length === 0) return;
  const last = data.log.pop();
  data.total -= last.delta;
  saveData(data);
  render();
  if (historyDialog.open) renderHistory();
}

function formatTimestamp(iso) {
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString("de-DE"),
    time: d.toLocaleTimeString("de-DE"),
  };
}

function renderHistory() {
  historyBody.innerHTML = "";
  const dailyTotals = {};
  const todayStr = new Date().toLocaleDateString("de-DE");

  for (let i = data.log.length - 1; i >= 0; i--) {
    const entry = data.log[i];
    const { date, time } = formatTimestamp(entry.timestamp);
    const row = document.createElement("tr");
    row.innerHTML = `<td>${date}</td><td>${time}</td><td>+${entry.delta}</td>`;
    historyBody.appendChild(row);
    dailyTotals[date] = (dailyTotals[date] || 0) + entry.delta;
  }

  const todayTotal = dailyTotals[todayStr] || 0;
  historySummary.textContent = `Heute: ${todayTotal}  |  Gesamt: ${data.total}`;
}

document.querySelectorAll(".btn-add").forEach((btn) => {
  btn.addEventListener("click", () => addDelta(Number(btn.dataset.delta)));
});

undoBtn.addEventListener("click", undo);

historyBtn.addEventListener("click", () => {
  renderHistory();
  historyDialog.showModal();
});

closeHistoryBtn.addEventListener("click", () => historyDialog.close());

render();

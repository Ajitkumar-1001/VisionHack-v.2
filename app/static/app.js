// Polls /api/status and repaints. No framework, no build step — the UI ships
// inside the same Cloud Run container as the engine (PRD §19).
//
// Scaffold state: the endpoints return honest placeholders until the engine
// lands, so every field degrades to a dash rather than throwing.

const POLL_MS = 1000;

const $ = (id) => document.getElementById(id);

// AC-15: whatever variant we land on, the UI states the measured frame rate and
// the temporal mode. A system that says "Δ 1 frame at 0.5 fps" is more credible
// than one that says "ΔT 0.72s" with nothing behind it.
function renderFps(s) {
  const fps = s.measured_fps == null ? "—" : `${s.measured_fps} fps`;
  const mode = { seconds: "second-delta mode", frames: "frame-delta mode", cooccupancy: "co-occupancy mode" }[s.temporal_mode] || "mode pending probe";
  $("fps-line").textContent = `${fps} · ${mode}`;
}

// AC-13: never present prerecorded footage as live.
function renderMode(s) {
  const live = s.mode === "live";
  const badge = $("mode-badge");
  badge.textContent = live ? "● LIVE" : "● DEMO REPLAY";
  badge.className = `badge ${live ? "badge-live" : "badge-replay"}`;
}

function renderState(s) {
  const sev = $("severity");
  sev.textContent = s.agent_state || "NORMAL";
  sev.className = `severity ${(s.severity || "").toLowerCase()}`;
  $("delta").textContent = s.delta_display || "—";
  $("event-flag").textContent = s.agent_state === "ALERT_CREATED" ? "SAFETY EVENT CREATED" : "";
}

// AC-11 + §17: the Open Data layer renders in its own region and never touches
// severity. Unavailable is a legitimate state (scenario 6), not an error.
function renderContext(c) {
  if (!c || c.status !== "available") {
    $("context-line").textContent = "Historical context unavailable";
    return;
  }
  const parts = [];
  if (c.historical_cyclist_collisions != null) {
    parts.push(`${c.historical_cyclist_collisions} cyclist-injury collisions within 250m (2021–2026)`);
  }
  if (c.facility_type) parts.push(c.facility_type);
  if (c.on_truck_route) {
    const n = (c.truck_route_streets || []).length;
    parts.push(n ? `on ${n} designated truck routes` : "on a designated truck route");
  }
  if (c.source) parts.push(`source: ${c.source}`);
  $("context-line").textContent = parts.join(" · ");
}

function renderEvents(events) {
  const ul = $("events");
  if (!events || !events.length) {
    ul.innerHTML = '<li class="muted">No events yet</li>';
    return;
  }
  ul.innerHTML = events
    .map((e) => `<li>${e.timestamp || "--:--"}  ${(e.decision?.severity || "").toUpperCase()}  ${e.summary || ""}</li>`)
    .join("");
}

async function tick() {
  try {
    const s = await (await fetch("/api/status")).json();
    renderMode(s);
    renderFps(s);
    renderState(s);
    $("sys-cloudrun").textContent = "Cloud Run ✓";

    const { events } = await (await fetch("/api/events")).json();
    renderEvents(events);

    renderContext(await (await fetch("/api/context")).json());
  } catch {
    // §21 failure philosophy: a dead enrichment call must never blank the screen.
    $("sys-cloudrun").textContent = "Cloud Run ⚠";
  }
}

tick();
setInterval(tick, POLL_MS);

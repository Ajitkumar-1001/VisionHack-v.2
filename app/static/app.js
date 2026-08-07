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
  } catch {
    // §21 failure philosophy: a dead enrichment call must never blank the screen.
    $("sys-cloudrun").textContent = "Cloud Run ⚠";
  }
}

tick();
setInterval(tick, POLL_MS);

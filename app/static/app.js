// One screen, no framework, no build step. Ships inside the same Cloud Run
// container as the engine (PRD §19).
//
// Two loops: a status poll that keeps the panels honest, and a replay driver
// that steps the §18 sequence through the real pipeline on demand.

const POLL_MS = 2000;
const REPLAY_STEP_MS = 1400;
const $ = (id) => document.getElementById(id);

let replayTimer = null;

// Built in JS rather than in markup: two HTML entry points are served (the
// Astro build at /static/next/ and the original index.html), and this keeps
// the fallback working in both without editing generated output.
function noFeed() {
  let el = $("no-feed");
  if (!el) {
    el = document.createElement("div");
    el.id = "no-feed";
    el.hidden = true;
    el.textContent = "● DEMO REPLAY — no live feed on this rung";
    el.style.cssText =
      "position:absolute;inset:0;display:flex;align-items:center;" +
      "justify-content:center;font-size:12px;letter-spacing:.08em;" +
      "color:#f5a623;background:#000;text-align:center;padding:16px;";
    document.querySelector(".stage")?.appendChild(el);
  }
  return el;
}

// AC-15 / §7 rule 7. Every number on screen carries its measurement basis.
function renderFps(s) {
  const fps = s.measured_fps == null ? "—" : `${s.measured_fps} fps`;
  const mode = {
    seconds: "second-delta mode",
    frames: "frame-delta mode",
    cooccupancy: "co-occupancy mode",
  }[s.temporal_mode] || "mode pending probe";
  $("fps-line").textContent = `${fps} · ${mode}`;
}

// AC-13. Never present prerecorded footage as live.
function renderMode(s) {
  // Three independent conditions, all must hold. run_mode catches the case
  // that matters most: a replay driven from another tab or by curl leaving
  // replay events on screen under a LIVE badge.
  const live = s.mode === "live" && s.run_mode === "live" && !replayTimer;
  const badge = $("mode-badge");
  badge.textContent = live ? "● LIVE" : "● DEMO REPLAY";
  badge.className = `badge ${live ? "badge-live" : "badge-replay"}`;
}

function renderState(s) {
  const sev = $("severity");
  const label = s.severity ? s.severity.toUpperCase() : s.agent_state || "NORMAL";
  sev.textContent = label;
  sev.className = `severity ${(s.severity || "").toLowerCase()}`;
  $("agent-state").textContent = `agent state: ${s.agent_state || "NORMAL"}`;
  $("delta").textContent = s.delta_display || "—";
  $("event-flag").textContent =
    s.agent_state === "ALERT_CREATED" ? "SAFETY EVENT CREATED" : "";
}

// AC-11 + §17: the Open Data layer renders in its own region and never touches
// severity. "unavailable" is a legitimate state (scenario 6), not an error.
function renderContext(c) {
  if (!c || c.status !== "available") {
    $("context-line").textContent = "Historical context unavailable";
    return;
  }
  const parts = [];
  if (c.historical_cyclist_collisions != null) {
    parts.push(`${c.historical_cyclist_collisions} cyclist-injury collisions within 250 m (2021–2026)`);
  }
  if (c.facility_type) parts.push(c.facility_type);
  if (c.on_truck_route) {
    const n = (c.truck_route_streets || []).length;
    parts.push(n ? `on ${n} designated truck routes` : "on a designated truck route");
  }
  $("context-line").textContent = parts.join(" · ");
  $("context-source").textContent = c.source || "";
}

function renderEvents(events) {
  const ul = $("events");
  if (!events || !events.length) {
    ul.innerHTML = '<li class="muted">No events yet</li>';
    return;
  }
  ul.innerHTML = events
    .map((e) => {
      const p = e.participants;
      const o = e.observation;
      const d = o.temporal_gap_frames != null
        ? `Δ ${o.temporal_gap_frames} frame${o.temporal_gap_frames === 1 ? "" : "s"}`
        : o.same_frame_cooccupancy ? "same frame"
        : `ΔT ${o.temporal_gap_seconds}s`;
      const sev = e.decision.severity.toUpperCase();
      const t = (e.timestamp || "").slice(11, 19);
      return `<li><span class="sev-${e.decision.severity}">${sev}</span> ${t}  ${p.vehicle.class} #${p.vehicle.track_id} × ${p.vru.class} #${p.vru.track_id}  ${d}</li>`;
    })
    .join("");
}

// Zones and boxes are drawn in the camera's native pixel space and scaled by
// the SVG viewBox, so the overlay stays aligned at any panel width.
function renderOverlay(d) {
  const [w, h] = d.frame_size || [352, 240];
  const svg = $("overlay");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);

  const poly = (pts, cls) =>
    pts && pts.length >= 3
      ? `<polygon class="${cls}" points="${pts.map((p) => p.join(",")).join(" ")}"/>`
      : "";

  const zones = d.zones || {};
  let out =
    poly(zones.vru_approach, "z-vru") +
    poly(zones.vehicle_turn_approach, "z-veh") +
    poly(zones.conflict_zone, "z-conflict");

  for (const det of d.detections || []) {
    const [x1, y1, x2, y2] = det.bbox;
    const vru = det.class === "bicycle" || det.class === "person";
    const cls = det.zone === "conflict_zone" ? "b-conflict" : vru ? "b-vru" : "b-veh";
    out += `<rect class="${cls}" x="${x1}" y="${y1}" width="${x2 - x1}" height="${y2 - y1}"/>`;
    out += `<text class="b-label" x="${x1}" y="${y1 - 2}">${det.class.toUpperCase()} #${det.track_id}</text>`;
  }
  svg.innerHTML = out;
}

async function tick() {
  try {
    const s = await (await fetch("/api/status")).json();
    renderMode(s);
    renderFps(s);
    renderState(s);
    $("sys-cloudrun").textContent = "Cloud Run ✓";
    $("camera-name").textContent = s.camera?.name || "replay clip — no live feed";

    // The replay rung has no image_url (§18). Leaving the <img> pointed at
    // nothing renders a broken-image glyph and alt text, which reads as a
    // crash rather than as the labelled fallback it actually is.
    const img = $("camera-img");
    if (s.camera?.image_url) {
      // Cache-bust: the feed serves a new still roughly every 2 s.
      if (!replayTimer) img.src = `${s.camera.image_url}?t=${Date.now()}`;
      img.hidden = false;
      noFeed().hidden = true;
    } else {
      img.removeAttribute("src");
      img.hidden = true;
      noFeed().hidden = false;
    }

    renderEvents((await (await fetch("/api/events")).json()).events);
    renderContext(await (await fetch("/api/context")).json());
    renderOverlay(await (await fetch("/api/detections")).json());
  } catch {
    // §21 failure philosophy: a dead enrichment call must never blank the screen.
    $("sys-cloudrun").textContent = "Cloud Run ⚠";
  }
}

async function runReplay() {
  if (replayTimer) return;
  await fetch("/api/run/reset", { method: "POST" });
  const info = await (await fetch("/api/replay/info")).json();
  $("replay-note").textContent = `Replay: ${info.frames} frames of ${info.source} through the live pipeline`;

  let i = 0;
  replayTimer = setInterval(async () => {
    const r = await (
      await fetch(`/api/replay/step?frame_index=${i}`, { method: "POST" })
    ).json();
    if (r.note) $("replay-note").textContent = `f${r.frame_index}: ${r.note}`;
    renderOverlay(await (await fetch("/api/detections")).json());
    await tick();
    if (r.done || i >= (r.total || 8) - 1) {
      clearInterval(replayTimer);
      replayTimer = null;
      $("replay-btn").textContent = "▶ Run demo replay";
    }
    i += 1;
  }, REPLAY_STEP_MS);
  $("replay-btn").textContent = "● replaying…";
}

$("replay-btn").addEventListener("click", runReplay);
$("failover-btn").addEventListener("click", async () => {
  await fetch("/api/camera/failover", { method: "POST" });
  tick();
});
// Reset must climb the camera ladder back too, not just clear the engine.
// Failover is one-way (§18), so without this a single "Force camera failure"
// strands the UI on the replay rung — image_url goes null, the camera panel
// shows a broken image and the context block empties — with no way back from
// the UI. AC-14 requires the demo to repeat without manual intervention.
$("reset-btn").addEventListener("click", async () => {
  await Promise.all([
    fetch("/api/run/reset", { method: "POST" }),
    fetch("/api/camera/reset", { method: "POST" }),
  ]);
  $("replay-note").textContent = "";
  tick();
});

tick();
setInterval(tick, POLL_MS);

# RightHook NYC

## Ultimate Product Requirements Document — Single Source of Truth

| | |
|---|---|
| **Version** | 4.0 |
| **Status** | BUILD THIS — supersedes v1.0 and v3.0 |
| **Event** | NYC Vision Hack v.2 · Friday, August 7, 2026 · 4:00–10:00 PM |
| **Submission lock** | **8:30 PM sharp** |
| **Stack** | Roboflow · Python/FastAPI · Google Cloud Run · NYC Open Data · Veris AI |
| **Philosophy** | One problem. One agent. One screen. One excellent demo. |

### How to use this document

This is the only spec. If any decision during the build conflicts with **§4 (Judging Rubric)** or **§6 (Frame-Rate Gate)**, those two sections win. Everything else is negotiable under time pressure via the degradation ladder in **§25**.

**What changed from v3.0 — read this first:**

1. **§4 replaces the invented compliance table with the actual published rubric.** v3.0 optimized against requirements that don't appear in the handbook and *omitted Open Source, which is a scored criterion.* That was a sixth of the score going unclaimed.
2. **§6 is new and is the highest-risk unknown in the build.** The sanctioned NYC DOT feed serves *stills refreshing every couple of seconds*. A 1.0-second ΔT threshold cannot be measured at a 2-second sampling period. The build forks on a 15-minute probe.
3. **Pedestrians are promoted from optional to P0 co-primary** (§9). Right-hooks are rare; turning-vehicle-vs-pedestrian conflicts are constant. The cyclist story stays; pedestrians carry the live firing rate.
4. **NYC Open Data is precomputed to config, not queried live** (§16). Saves ~75 minutes, still satisfies the criterion.
5. **Verification is pytest-first, Veris-second** (§20). The test artifact then exists regardless of whether the Veris integration lands, and it feeds both Technical Execution and Open Source.
6. **§23 (Privacy) and §22 (README) are new** — both are explicitly called out as scoring in the handbook and both were absent from v1.0 and v3.0.

---

# 1. Product in one sentence

> **RightHook NYC turns live NYC traffic cameras into proactive road-safety sensors by detecting dangerous turning-vehicle conflicts with cyclists and pedestrians, and automatically emitting structured safety events.**

Do not pitch it as "AI traffic monitoring." Do not pitch it as "a traffic dashboard."

Pitch it as:

> **"An agent that watches an NYC intersection and takes an action when it observes a potential vehicle–cyclist conflict."**

---

# 2. Problem

NYC crash datasets are lagging indicators. They record where somebody already got hurt.

They do not capture the far larger population of interactions where:

- a cyclist nearly gets cut off by a turning vehicle;
- a turning vehicle crosses an occupied bike lane;
- two road users occupy the same conflict area seconds apart;
- dangerous geometry repeatedly produces near-conflicts.

An intersection can exhibit unsafe behavior for years before enough severe crashes accumulate to form a statistically meaningful signal. **RightHook exposes that missing layer.**

### Core thesis

```text
TODAY                          RIGHTHOOK

Crash happens                  Traffic interaction
     ↓                                ↓
Police report                  Live camera
     ↓                                ↓
Dataset                        Computer vision
     ↓                                ↓
Safety analysis                Conflict detection
                                      ↓
                               Structured safety event
                                      ↓
                               Proactive analysis
```

---

# 3. Scope

## In scope — exactly one interaction class

**A turning vehicle entering the movement corridor of a vulnerable road user (VRU) at a single intersection.**

- **Primary narrative subject:** cyclist (the right hook)
- **Primary demo-frequency subject:** pedestrian in the crosswalk

Both are handled by the same engine with the same zones and the same rule. Class asymmetry is preserved in the event schema — vehicle is always the *subject*, VRU is always the *object*.

## Out of scope

Every traffic violation · every near miss · illegal parking · speeding · jaywalking · congestion · citywide conditions · crash prediction · intersection ranking · multi-camera tracking.

## Deliberate constraint

The goal is **not** "we built a traffic platform." The goal is:

> *"Watch this intersection. That car and that cyclist are converging. Our system detected it, changed state, and created an event — automatically."*

---

# 4. Judging rubric — the real one

*Eligibility gate: agent deployed on Cloud Run. Binary. Nothing else matters if this fails.*

| Criterion | What's scored | RightHook's claim | Owning section |
|---|---|---|---|
| **Working Demo** | Running on real feeds | Live feed primary, labeled replay fallback through the identical pipeline | §17, §27 |
| **NYC Relevance** | Clear tie-in to the city | NYC DOT cameras + NYC Open Data + a Vision Zero problem | §2, §16 |
| **Usefulness / Insight** | Makes something clearer, faster, safer, or more legible | Converts a lagging indicator into a leading one | §2, §11 |
| **Technical Execution** | Thoughtful approach, clean system, good tradeoffs | Deterministic interpretable rule, honest units, tested failure paths | §11, §20, §25 |
| **Cloud Run** | Must use it to submit | Entire agent is one Cloud Run service | §18 |
| **Open Source** | Repo + README tell the story, public GitHub | Public repo, honest README, tests, ADR trail | §22 |

**Open Source is a full scored criterion and both prior PRD versions ignored it.** Budget 20 minutes for it and treat it as P0, not cleanup.

## Event-day operational facts

- Build window is **5:15 PM → 8:30 PM ≈ 3h15m**. Demos 8:45. Awards 9:45.
- Deploy early — the gate is binary and 8:30 arrives fast.
- Judges want it live and warn that a camera may go dark at 8:45. The replay fallback is not optional.
- Clear sourcing, privacy-aware handling, and reproducible pipelines are explicitly noted as scoring. Faces and plates in public feeds deserve care. → §23.
- **The temp `@gcplab.me` environment and its project are decommissioned at the end of the event.** The Cloud Run URL dies with it. Therefore: repo lives on a **personal GitHub account**, README carries a `docker run` path, and the demo is **screen-recorded before 8:30**.

---

# 5. Data sources

## Primary: NYC DOT traffic cameras

```text
All cameras   GET https://webcams.nyctmc.org/api/cameras
Single still  GET https://webcams.nyctmc.org/api/cameras/{id}/image
```

The camera list returns hundreds of objects with `id`, `name`, `latitude`, `longitude`, `area` (borough), `isOnline`, and `imageUrl`. Frames refresh every couple of seconds.

**Gotcha:** `isOnline` is a *string*, not a boolean. Filter with `c["isOnline"] == "true"`.

```python
import requests, time

cams = requests.get("https://webcams.nyctmc.org/api/cameras").json()
online = [c for c in cams if c["isOnline"] == "true"]

cam = online[0]  # or filter by name / borough / lat-lng
while True:
    frame = requests.get(cam["imageUrl"]).content  # JPEG bytes
    # hand off to Roboflow inference here
    time.sleep(2)
```

Be polite: one poll every 2s per camera, no parallel hammering.

## Secondary (probe in §6): any public video-rate NYC intersection stream

The handbook permits any public feed responsibly integrated during the evening. A video-rate stream, if one is ingestible, unlocks Variant A below and is worth 15 minutes of investigation — **but no more than 15**.

## Tertiary: NYC Open Data (context only, §16)

Motor Vehicle Collisions · NYC Bicycle Routes.

---

# 6. The frame-rate gate — RUN THIS FIRST

**This is the highest-risk unknown in the entire build and it must be resolved before any conflict-engine code is written.**

## Why it matters

ΔT thresholds of 1.0s and 2.0s require a sampling period well under 1 second. At a 2-second still refresh:

- Your temporal quantum is 2000 ms. Every severity bin is narrower than one frame interval.
- A vehicle at 15 mph moves ~13 m between frames; at 30 mph, ~27 m — wider than the conflict zone itself.
- ByteTrack associates by IoU. When displacement exceeds object size, IDs thrash and `track_id` continuity — AC-04 — fails.

Reporting "ΔT = 0.72 sec" from a 0.5 fps source is not a tuning error. It is a false precision claim, and it is exactly the kind of thing a judge asks about.

## The probe (15 minutes, hard timebox)

```text
1. Pull the camera list. Count online cameras.
2. Pull 10 consecutive stills from 3–4 candidate cameras.
   Measure actual wall-clock interval between distinct frames.
3. Measure pedestrian and cyclist pixel height in those stills.
4. Attempt ingest of one public video-rate NYC intersection stream.
5. STOP AT 15 MINUTES AND COMMIT.
```

## The fork

| | **Variant A** | **Variant B** | **Variant C** |
|---|---|---|---|
| **Condition** | Video-rate source ingestible (≥10 fps) | Stills only, ~0.5 fps | Tracking unstable by 7:00 PM |
| **Tracking** | ByteTrack, stable IDs | ByteTrack, best-effort, short TTL | None |
| **Measurement** | ΔT in **seconds** | ΔT in **frames** + stated fps | **Co-occupancy** |
| **Severity** | ≤1.0s CRITICAL / ≤2.0s WARNING | Δ=0 frames CRITICAL / Δ=1 WARNING | Same-frame = CONFLICT |
| **UI must display** | `ΔT 0.72s` | `Δ 1 frame @ 0.5 fps (≈2.0s)` | `Both in conflict zone, same frame` |
| **Honesty** | Full | Full, coarse | Full, coarsest |

**All three variants emit the identical event schema, drive the identical state machine, and produce the identical demo narrative.** Only the `observation` block and the severity mapping differ. Build the engine so the variant is a **config flag**, not a rewrite:

```json
{ "temporal_mode": "seconds" | "frames" | "cooccupancy", "measured_fps": 0.5 }
```

### The one rule about this

Whatever variant you land on, **the UI states the measured frame rate and the temporal mode.** A system that says "Δ 1 frame at 0.5 fps" is more credible than one that says "ΔT 0.72s" with nothing behind it. Judges reward honest instrumentation; they punish fake precision.

---

# 7. Product principles

### Rule 1 — Detection must produce an action

Never `detect → draw box`. Always `detect → understand state → determine event → act`. This is what makes it an agent rather than a viewer.

### Rule 2 — Deterministic beats clever

No LLM in the core conflict path. Geometry is handled by `tracking + zones + timestamps + rules`.

### Rule 3 — Explainability beats arbitrary scoring

There is **no** weighted risk formula. No `0.35 * proximity + 0.25 * overlap + ...`. Those weights cannot be justified in three hours and cannot survive a follow-up question. Instead: observable zone entry, observable temporal separation, stated thresholds, labeled as heuristics.

### Rule 4 — The happy path must always be demo-able

Live preferred. Labeled replay through the identical pipeline is **mandatory**, not a nice-to-have.

### Rule 5 — Sponsor integrations must have real responsibilities

```text
Roboflow      → SEE
RightHook     → DECIDE
Cloud Run     → ACT / SERVE
Veris AI      → VERIFY
NYC Open Data → CONTEXT
```

### Rule 6 — Reliability before sophistication

A working 5-component system beats a half-built 15-component system. The most important metric in this document is §26.

### Rule 7 — State your units *(new in v4)*

Every number on screen carries its measurement basis. Frame rate, temporal mode, and the heuristic disclaimer are always visible.

---

# 8. Architecture

```text
                        ┌──────────────────────────┐
                        │   NYC DOT CAMERA         │
                        │   primary + 2 backups    │
                        └────────────┬─────────────┘
                                     │  JPEG stills / frames
                                     ▼
                        ┌──────────────────────────┐
                        │        ROBOFLOW          │
                        │         (SEE)            │
                        │  pretrained detection    │
                        │  class filter            │
                        │  ByteTrack               │
                        │  polygon zones           │
                        └────────────┬─────────────┘
                                     │  TrackObservation[]
                                     ▼
                        ┌──────────────────────────┐
                        │    RIGHTHOOK ENGINE      │
                        │        (DECIDE)          │
                        │  zone state              │
                        │  temporal separation     │
                        │  severity mapping        │
                        │  deduplication           │
                        └────────────┬─────────────┘
                                     ▼
                          ┌────────────────────┐
                          │   AGENT STATE      │
                          │ NORMAL → WATCH →   │
                          │ CONFLICT → ALERTED │
                          └─────────┬──────────┘
                                    ▼
                     ┌───────────────────────────────┐
                     │        AGENT ACTIONS          │
                     │  create_safety_event()        │
                     │  get_intersection_context()   │
                     │  switch_camera()              │
                     └───┬───────────────────────┬───┘
                         ▼                       ▼
              ┌──────────────────┐    ┌────────────────────┐
              │  NYC OPEN DATA   │    │   EVENT STORE      │
              │    (CONTEXT)     │    │  in-memory deque   │
              │  precomputed     │    │                    │
              └────────┬─────────┘    └─────────┬──────────┘
                       └───────────┬────────────┘
                                   ▼
                      ┌──────────────────────────┐
                      │   GOOGLE CLOUD RUN       │
                      │       (ACT/SERVE)        │
                      │  FastAPI + engine + UI   │
                      │  ONE service             │
                      └──────────────────────────┘
                                   ▲
                                   │  test path only
                      ┌──────────────────────────┐
                      │       pytest → VERIS     │
                      │        (VERIFY)          │
                      └──────────────────────────┘
```

**Veris is never in the real-time path.** It calls the deployed API from outside. This protects demo latency.

---

# 9. Perception layer — Roboflow

Roboflow owns exactly one question: *what objects exist, where are they, and which tracked object is which?*

## Classes

**Vehicle (subject):** `car`, `truck`, `bus`, `motorcycle`

**VRU (object) — both are P0:**

| Class | Role | Why |
|---|---|---|
| `bicycle` | Narrative primary | The right-hook story, the name, the pitch |
| `person` | Frequency primary | Turning-vehicle × pedestrian-in-crosswalk conflicts occur constantly; this is what fires on stage |

> **This is the single change most likely to convert "we demoed on replay" into "it fired live."** v3.0 listed `person` as optional and deferred pedestrian conflicts to a stretch goal. Invert that. The cyclist keeps the headline; the pedestrian keeps the demo alive.

Do not detect twenty classes. Filter hard at the workflow level.

## No model training

Pretrained only. Do not collect, annotate, train, or tune. That is an immediate scope failure. Roboflow Universe has thousands of pretrained models — use one. Only reconsider if pretrained detection fundamentally cannot see bicycles or vehicles on the selected feed.

## Confidence floor

If the probe (§6) shows VRUs under ~25 px tall, set a class-specific confidence floor and say so in the README. Small-object recall on `bicycle` is the known weak point; `person` degrades more gracefully.

## Workflow shape

```text
Input → Pretrained Detection → Class Filter → ByteTrack
      → Polygon Zone Logic → Box Visualization → Structured Output
```

Structured output:

```json
{
  "track_id": 34,
  "class": "car",
  "confidence": 0.91,
  "bbox": [142, 81, 248, 193],
  "zone": "vehicle_turn_approach",
  "observed_at": "2026-08-07T21:24:02.412Z"
}
```

Use a **Roboflow Workflow**, not a bare model call. It's what the platform is built for in a one-evening build, it keeps the Cloud Run container light, and the hosted inference API pairs cleanly with Cloud Run — which is the handbook's own recommendation.

---

# 10. Scene calibration

Manual. Three polygons per camera. **No automatic intersection understanding.**

```text
                       VEHICLE
                          ↓
                          ↓
                  ┌──────────────┐
 VRU ───────────→ │   CONFLICT   │
                  │     ZONE     │
                  └──────────────┘
                           ↘
                              VEHICLE TURNS
```

| Zone | Meaning |
|---|---|
| `vru_approach` | Where cyclists/pedestrians enter the corridor |
| `vehicle_turn_approach` | Where vehicles likely to cross that corridor are observed |
| `conflict_zone` | The image region where the two paths overlap |

**Timebox camera selection to 15 minutes.** Hunting for the perfect view is how people lose an hour. Pick a camera with a visible crosswalk, a visible turn movement, and a stable frame.

---

# 11. Conflict algorithm

Deliberately, embarrassingly understandable.

## Observation

```python
if vru enters vru_approach:            remember vru track
if vehicle enters vehicle_turn_approach: remember vehicle track

if vru enters conflict_zone:      record vru_conflict_time
if vehicle enters conflict_zone:  record vehicle_conflict_time
```

**ΔT is the gap between two *observed* zone-entry timestamps — never a predicted time-to-arrival.** This is the single most important design choice in the document: it requires no homography, no pixel-to-metre calibration, no velocity model, and no ground plane. You are reporting something you actually watched happen.

```python
delta = abs(vru_conflict_time - vehicle_conflict_time)
```

## Event criterion

```python
if (
    vru.was_in_vru_approach
    and vehicle.was_in_vehicle_turn_approach
    and vru.entered_conflict_zone
    and vehicle.entered_conflict_zone
    and within_threshold(delta)
):
    create_safety_event()
```

That is the MVP. **Do not make it smarter until this works.**

---

# 12. Severity — variant-conditional

Severity mapping is a lookup keyed on `temporal_mode` from §6.

### Variant A — `temporal_mode: "seconds"`

| ΔT | Severity |
|---|---|
| ≤ 1.0 s | **CRITICAL** |
| 1.0 – 2.0 s | **WARNING** |
| > 2.0 s | no event |

### Variant B — `temporal_mode: "frames"`

| Δ frames | Severity | Displayed as |
|---|---|---|
| 0 | **CRITICAL** | `Δ 0 frames @ 0.5 fps` |
| 1 | **WARNING** | `Δ 1 frame @ 0.5 fps (≈2.0s)` |
| ≥ 2 | no event | — |

### Variant C — `temporal_mode: "cooccupancy"`

| Condition | Severity |
|---|---|
| Vehicle and VRU both inside `conflict_zone` in the same frame, both having passed through their approach zones | **CONFLICT** |
| Otherwise | no event |

### WATCH — all variants

`WATCH` is not a third ΔT band. It is a UI/state condition: **both an approaching vehicle and an approaching VRU are present in their respective approach zones, and neither has entered the conflict zone yet.** It drives the state machine and gives the demo a visible build-up before the alert.

## Scientific disclaimer — must appear in UI and README

RightHook must **never** claim "83% crash probability" or "this was definitely a near miss." The permitted phrasing is:

> **Potential vehicle–VRU conflict detected using spatial and temporal heuristics. Thresholds are hackathon heuristics and have not been calibrated as crash-risk probabilities.**

This is not hedging. It is what makes the project defensible under questioning, and it directly serves the Technical Execution criterion.

---

# 13. Agent state machine

```text
                ┌─────────┐
                │ NORMAL  │◄──────────────┐
                └────┬────┘               │
                     │                    │
     both approach zones occupied         │ TTL expiry /
                     │                    │ tracks leave
                     ▼                    │
                ┌─────────┐               │
                │  WATCH  │───────────────┤
                └────┬────┘               │
                     │                    │
        both entered conflict_zone        │
        within threshold                  │
                     ▼                    │
               ┌──────────┐               │
               │ CONFLICT │               │
               └────┬─────┘               │
                    │                     │
             create_safety_event()        │
                    ▼                     │
             ┌───────────────┐            │
             │ ALERT_CREATED │────────────┘
             └───────────────┘
```

This exists because it is the proof that **perception causes a system decision**. When a judge asks "why is this an agent?", this diagram is the answer.

---

# 14. Agent actions

Exactly three. No generic tools, no browser agent, no chat, no RAG, no multi-agent architecture.

| Action | Trigger | Effect |
|---|---|---|
| `create_safety_event()` | Valid conflict passes threshold + dedup | Emits the §15 event, appends to store, flips UI |
| `get_intersection_context()` | On event creation | Attaches §16 context; **failure is non-fatal** |
| `switch_camera()` | Camera health check fails | Advances the §17 fallback ladder |

---

# 15. Deduplication

ByteTrack keeps the same participants visible across many frames. Without dedup:

```text
frame 1 → ALERT   frame 2 → ALERT   frame 3 → ALERT   ← bad
```

```python
event_key = f"{vehicle_track_id}:{vru_track_id}"
if event_key in recently_emitted:   # TTL 5–10 seconds
    ignore
```

**Under Variant B/C, use a shorter TTL (5s) but also key on zone-entry epoch**, because unstable track IDs at low fps can produce a *new* key for the same real-world interaction. If IDs are thrashing, add a secondary suppression: no more than one event per conflict zone per 5 seconds regardless of key.

---

# 16. Safety event schema

The canonical artifact. **This JSON is one of your most valuable demo assets** — it proves the project is a perception system, not a visualization.

```json
{
  "event_id": "rh_01J9XYZ",
  "event_type": "potential_turning_conflict",
  "timestamp": "2026-08-07T21:24:03Z",

  "camera": {
    "id": "nyc_cam_01",
    "mode": "live",
    "measured_fps": 0.5,
    "temporal_mode": "frames"
  },

  "participants": {
    "vehicle": { "track_id": 34, "class": "car" },
    "vru":     { "track_id": 51, "class": "bicycle" }
  },

  "observation": {
    "vehicle_entered_turn_zone": true,
    "vru_entered_approach_zone": true,
    "both_entered_conflict_zone": true,
    "temporal_gap_frames": 1,
    "temporal_gap_seconds_estimate": 2.0,
    "measurement_basis": "observed zone-entry timestamps"
  },

  "decision": {
    "severity": "warning",
    "action": "create_safety_event"
  },

  "location": {
    "intersection": "Example Ave & Example St",
    "latitude": 40.0000,
    "longitude": -73.0000
  },

  "context": {
    "status": "available",
    "bike_infrastructure": true,
    "facility_type": "protected bike lane",
    "historical_cyclist_collisions": 14
  },

  "disclaimer": "Heuristic conflict detection. Not a calibrated crash-risk probability."
}
```

Under Variant A, `temporal_gap_frames` is omitted and `temporal_gap_seconds` is exact. Under Variant C, both are omitted and `observation.same_frame_cooccupancy: true` is present.

---

# 17. NYC Open Data — precompute, don't query live

## The change from v3.0

v3.0 budgeted live queries against two datasets. **That's ~75 minutes you don't have.** You have already chosen your camera by 5:45. So:

**Before writing any data code, look up the numbers once for that one intersection and paste them into config.**

```json
{
  "id": "nyc_cam_01",
  "intersection": "Example Ave & Example St",
  "context": {
    "bike_infrastructure": true,
    "facility_type": "protected bike lane",
    "historical_cyclist_collisions": 14,
    "source": "NYC Motor Vehicle Collisions, 250m radius, 2020-2025",
    "retrieved_at": "2026-08-07T18:10:00Z"
  }
}
```

**15 minutes instead of 90. AC-11 still passes. NYC Relevance still scores.** The README documents the query used so the pipeline is reproducible — which is what the handbook actually rewards.

Live Socrata querying is **P2**. Do it only if you are complete before 8:00.

## Open data must not determine live severity

```text
BAD                              GOOD

live conflict                    LIVE OBSERVATION
+ historic crashes                 Δ 1 frame · WARNING
= danger score
                                 HISTORICAL CONTEXT
                                   14 nearby cyclist collisions
                                   protected bike lane present
```

Two distinct layers, rendered in two distinct UI regions. History never modifies an individual event's severity. This separation is sophisticated and a transportation-literate judge will notice it.

---

# 18. Camera resilience

```text
        PRIMARY
           │
      available?
      ┌────┴────┐
     YES        NO
      │          ↓
     USE     BACKUP 1
                 ↓
            available?
            ┌────┴────┐
           YES        NO
            │          ↓
           USE     BACKUP 2
                       ↓
                  available?
                  ┌────┴────┐
                 YES        NO
                  │          ↓
                 USE   ● DEMO REPLAY
```

```json
{ "camera_id": "nyc_cam_01", "status": "healthy", "mode": "live", "last_frame_at": "..." }
```

Statuses: `healthy` · `degraded` · `offline` · `fallback`.

## Demo replay — mandatory

You must have **one known-positive clip** containing a visible vehicle, a visible VRU, and an interaction. Capture it during the build; do not leave this to 8:15.

It passes through **the same Roboflow pipeline**. Prerecorded *input*, not prerecorded *inference*. That distinction is what keeps the demo honest and you should say it out loud on stage.

UI labels `● LIVE` or `● DEMO REPLAY`, always. **Never present prerecorded footage as live.**

---

# 19. Google Cloud Run

## Build task #1 — before anything else

```text
GET https://<service>.run.app/health
→ { "service": "righthook-nyc", "status": "healthy" }
```

**The eligibility gate is binary. Nothing else in this document matters if this fails.** Target: deployed by 5:45 PM. If it isn't working by 5:45, walk to the Google Cloud engineers on-site immediately — do not debug it alone at 8:00.

## One service

```text
Cloud Run service
├── FastAPI
├── RightHook engine
├── camera manager
├── context (from config)
├── in-memory event store
└── static UI  ← served from the same container
```

**Avoid:** separate Vercel frontend + Cloud Run backend + separate inference backend + database + Redis. There is no time, and v3.0 was right to drop the Next.js frontend that v1.0 specified.

## Stack

```text
Python 3.11+ · FastAPI · Pydantic · Roboflow SDK · OpenCV · NumPy · httpx · uvicorn
Optional: Shapely (point-in-polygon)
```

Do not add LangChain because the word "agent" appears in the challenge.

---

# 20. API surface

Keep it tiny.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness. **Open Data availability must not affect this.** |
| `GET /api/status` | Camera, mode, agent state, measured fps, temporal mode |
| `GET /api/events` | Recent events |
| `GET /api/events/{id}` | Single event |
| `POST /api/perception` | Roboflow structured output enters here |
| `POST /api/agent/event` | Synthetic observation → decision. **The Veris/pytest entry point.** |
| `GET /api/context` | Intersection context |
| `POST /api/camera/failover` | Force failover (used by test scenario 5) |

`POST /api/agent/event` is the highest-value endpoint for judging: it lets anyone reproduce the decision logic without a camera.

---

# 21. Verification — pytest first, Veris second

## Why this order changed

v3.0 allocated 20 minutes to Veris. Veris is a sponsor tool but it is **not a judging criterion**; Open Source and Technical Execution are. So write the scenarios as **pytest tests against the deployed API first** — that artifact lands in the repo, scores on two criteria, and takes ~12 minutes. Then, if the clock allows, point Veris at the same endpoint. The tests are the deliverable; Veris is the amplifier.

## The six scenarios

| # | Input | Expected | Proves |
|---|---|---|---|
| 1 | Both in conflict zone, Δ below critical threshold | `severity: critical`, one event | Core path |
| 2 | Both in conflict zone, Δ in warning band | `severity: warning`, one event | Threshold correctness |
| 3 | VRU in conflict zone, vehicle not | no event | No false positives |
| 4 | Same pair sent 5× | **1 event, not 5** | Dedup (§15) |
| 5 | Primary camera unavailable | `switch_camera()`, backup selected | Resilience |
| 6 | NYC data API returns 503 | `live_detection: continue`, `context.status: unavailable` | Graceful degradation |

Maximum six. Do not build fifty.

**Scenario 6 encodes the failure philosophy:** never fail live safety detection because optional enrichment is down.

## Failure philosophy

```text
CRITICAL          NON-CRITICAL
Cloud Run         NYC historical data
Roboflow          Fancy UI
Camera/Replay     Event persistence
```

`NYC API failed` must surface as *"Historical context unavailable"*, never as a 500.

---

# 22. Frontend

One screen. No navigation, no landing page, no settings, no auth.

```text
┌───────────────────────────────────────────────────────────┐
│ RIGHTHOOK NYC                                    ● LIVE   │
│ Proactive vehicle–VRU conflict detection                  │
│ 0.5 fps · frame-delta mode                                │
├────────────────────────────────┬──────────────────────────┤
│                                │ INTERSECTION STATE       │
│                                │                          │
│                                │       WARNING            │
│       LIVE CAMERA              │                          │
│                                │  Δ 1 frame @ 0.5 fps     │
│  CAR #34                       │        (≈2.0s)           │
│       ↘                        │                          │
│       [CONFLICT] ← BIKE #51    │  SAFETY EVENT CREATED    │
│                                │                          │
├────────────────────────────────┴──────────────────────────┤
│ NYC CONTEXT                                               │
│ Bike infrastructure ✓   Historical cyclist collisions 14  │
├───────────────────────────────────────────────────────────┤
│ RECENT EVENTS                                             │
│ 20:31  CRITICAL  Car #34 × Bike #51   Δ 0 frames          │
│ 20:27  WARNING   Car #21 × Ped #45    Δ 1 frame           │
├───────────────────────────────────────────────────────────┤
│ SYSTEM   Roboflow ✓   Cloud Run ✓   Tests 6/6 PASS        │
├───────────────────────────────────────────────────────────┤
│ Heuristic detection · not a calibrated crash probability  │
└───────────────────────────────────────────────────────────┘
```

## Overlays on the camera panel

Bounding boxes · class labels · track IDs · the three zones · conflict zone highlighted on event. Trajectory trails only if Roboflow gives them nearly free.

## The judge's eye should move

```text
1. CAMERA → 2. CONFLICT ZONE → 3. SEVERITY → 4. Δ + UNITS
→ 5. EVENT CREATED → 6. CONTEXT → 7. SYSTEM STATUS
```

## Design direction

Professional civic-operations aesthetic: dark neutral background, large camera panel, strong typography, minimal glass cards, small operational indicators, high-contrast warning state. **No animations, no 3D, no decorative AI particles, no JARVIS.** It should look like something a transportation operations centre could plausibly run.

**Do not bury the vision system behind charts. The CV is the hero.**

---

# 23. Open source — a scored criterion

Budget 20 minutes. This is P0, not cleanup.

## Repository

Public GitHub, on a **personal account** — the `@gcplab.me` project is destroyed at end of event.

```text
righthook-nyc/
├── README.md
├── LICENSE                    ← Apache-2.0 or MIT. Present at push time.
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env.example               ← NEVER commit real keys
│
├── app/
│   ├── main.py
│   ├── vision/     roboflow_client.py · tracks.py · zones.py
│   ├── agent/      engine.py · state.py · actions.py · dedup.py
│   ├── cameras/    manager.py · health.py
│   ├── context/    intersection.py
│   ├── models/     perception.py · event.py
│   ├── api/        routes.py
│   └── static/     index.html · app.js · styles.css
│
├── config/
│   └── cameras.json           ← zones, context, temporal_mode
├── demo/
│   └── righthook-demo.mp4
├── tests/
│   ├── test_conflict.py · test_dedup.py · test_camera_failover.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── DECISIONS.md           ← the frame-rate fork, why Variant X
└── .veris/
```

## README must contain

1. **The one-sentence pitch** and the problem framing (§1–2)
2. **Architecture diagram** (§8)
3. **Measured frame rate and chosen variant, stated plainly** — this is your credibility
4. **The heuristic disclaimer** (§12)
5. **`docker run` instructions** — because the Cloud Run URL dies with the event
6. **Data sourcing**: exact endpoints, the Open Data query used, retrieval timestamp
7. **Privacy statement** (§24)
8. **Honest limitations section** — single camera, uncalibrated, heuristic thresholds, low frame rate. Judges reward this; the handbook says the README should tell the story, not sell it.

## Before 8:30

- [ ] Repo public, LICENSE present, no keys in history
- [ ] README complete
- [ ] Demo screen-recorded
- [ ] Sample event JSON committed to `demo/`
- [ ] Anything worth keeping copied out of the `@gcplab.me` environment

---

# 24. Privacy and data handling

Explicitly called out as scoring: *clear sourcing, privacy-aware handling, reproducible pipelines. Faces and plates in public feeds deserve care.*

**Commit to and state publicly:**

- No face recognition. No licence-plate recognition. No re-identification across cameras or across time.
- Track IDs are ephemeral and scoped to a single camera session. They are not identities.
- No frame is persisted beyond the in-memory event buffer; nothing is written to durable storage.
- Detection classes are limited to `car/truck/bus/motorcycle/bicycle/person`. No attribute inference of any kind.
- DOT stills are low-resolution; at the working distances involved, faces and plates are not resolvable. Say this rather than assuming the judges know it.
- The system produces **observations about traffic geometry**, never observations about individuals. No enforcement output.

Put this in the README **and** say one sentence of it on stage. It takes eight seconds and it differentiates you.

---

# 25. Execution plan — wall clock

| Time | Task | P0 acceptance |
|---|---|---|
| **4:45–5:15** | Cloud Run workshop. Start the hello-world during it. | — |
| **5:15–5:45** | **CLOUD RUN FIRST.** FastAPI, `/`, `/health`, Dockerfile, deploy. | Public `.run.app` URL responds |
| **5:45–6:00** | **§6 FRAME-RATE PROBE.** Commit to a variant. Pick the camera. | `temporal_mode` written to config |
| **6:00–6:35** | Roboflow perception. Frames → detections → track IDs. | `CAR #34` and `BIKE #51` visible |
| **6:35–7:00** | Zones. Configure three polygons, verify transitions. | Objects report correct `zone` |
| **7:00–7:20** | **Conflict engine.** Zone state + timestamps + Δ → event. | `SEVERITY` + `SAFETY EVENT CREATED` |
| | | **← AT THIS POINT YOU HAVE THE PRODUCT** |
| **7:20–7:35** | Camera resilience + capture the replay clip. Test one deliberate failure. | Failover works, clip recorded |
| **7:35–7:45** | Open data context from config. | `context` block populates |
| **7:45–8:00** | pytest scenarios 1–6. Veris only if ahead. | 6/6 green |
| **8:00–8:20** | UI cleanup. **No redesign.** | One screen, units visible |
| **8:20–8:30** | **FREEZE.** README, LICENSE, push, screen-record, rehearse ×3. | Repo public, recording exists |
| **8:30** | **SUBMISSION LOCK** | |

Dinner at 7:00 — eat while the conflict engine runs.

---

# 26. Degradation ladder — decide by clock, not by feeling

Each rung is a **complete, honest, demo-able product**. Dropping down is not failure; it is the plan.

| Time | If you don't have… | Drop to |
|---|---|---|
| 5:45 | Cloud Run URL | **Stop everything. Get sponsor help.** Nothing else counts. |
| 6:35 | Stable detections on live feed | Switch primary input to the replay clip. Same pipeline, label it. |
| 7:00 | Stable track IDs | **Variant C.** Drop tracking, drop ΔT, use same-frame co-occupancy. |
| 7:20 | Any event firing end-to-end | Relax to co-occupancy in the conflict zone only — drop the approach-zone precondition. |
| 7:45 | Open data working | Ship `context.status: "unavailable"`. Scenario 6 already covers it; it becomes a feature. |
| 8:00 | Tests green | Ship the tests as-is with honest results in the README. A visible failing test beats a hidden one. |

**The floor is: one camera, boxes on screen, both classes in the conflict zone in one frame, an event JSON, and a Cloud Run URL.** That is still a working demo, still NYC-relevant, still uses Cloud Run, still open source. Knowing you have a floor is what lets you push the ceiling.

---

# 27. Acceptance criteria

| ID | Criterion |
|---|---|
| AC-01 | A public Google Cloud Run URL exists and responds |
| AC-02 | At least one NYC feed (live or replay) reaches Roboflow |
| AC-03 | Vehicles and VRUs are detected |
| AC-04 | Objects receive tracking IDs *(waived under Variant C — README states this)* |
| AC-05 | Camera-specific polygons are configured and visible |
| AC-06 | RightHook detects valid spatial + temporal overlap |
| AC-07 | Detection causes `CREATE_SAFETY_EVENT` |
| AC-08 | Repeated frames do not create duplicate events |
| AC-09 | A failed camera produces fallback behaviour |
| AC-10 | Demo replay runs through the *same* inference pipeline |
| AC-11 | At least one NYC Open Data source is attached as context |
| AC-12 | Test scenarios execute and results are reported honestly |
| AC-13 | UI visibly differentiates `● LIVE` from `● DEMO REPLAY` |
| AC-14 | The full demo runs repeatedly without manual code changes |
| AC-15 | **Measured frame rate and temporal mode are displayed in the UI** |
| AC-16 | **Public repo with README, LICENSE, and no committed keys** |

## The one metric that matters

```text
successful full demos
─────────────────────     TARGET: 10 / 10
attempted full demos
```

Run it ten times before you present. That matters more than any additional feature.

---

# 28. Demo script — three acts, three minutes

## Opening

> "Crash data tells us where somebody already got hurt. But a dangerous intersection can generate hundreds of unsafe interactions before a single crash ever becomes a record."

## Act 1 — Reality (45s)

Show `● LIVE`.

> "This is a live NYC DOT traffic camera. Roboflow detects and tracks road users. We're sampling at 0.5 frames per second — that's what the city's public feed gives you, and everything on this screen is honest about that."

Point at `CAR #34`, `BIKE #51`.

## Act 2 — Intelligence (75s)

Switch to replay if needed, and say why:

> "To show the conflict path deterministically, I'll run a recorded NYC sequence through the *exact same* inference pipeline. This is prerecorded input, not prerecorded inference."

State goes `NORMAL → WATCH`. Then the alert.

> "The vehicle entered the turn approach. The cyclist entered the bike corridor. Both entered the conflict zone within one frame of each other."

**`WARNING` · `Δ 1 frame @ 0.5 fps` · `SAFETY EVENT CREATED`**

> "The detection doesn't just draw a box. It changes the state of the agent and causes an action."

*(This sentence is the most important one in the demo. Do not rush it.)*

Show the event JSON. Then the context panel:

> "Separately — not as part of the severity — NYC Open Data tells us this intersection has 14 prior cyclist collisions and a protected bike lane. History gives context. It never modifies the live observation."

## Act 3 — Reliability (45s)

> "One good video doesn't prove an agent is reliable, so we test its behaviour."

```text
VALID CONFLICT      PASS
SAFE INTERACTION    PASS
DUPLICATE EVENT     PASS
CAMERA FAILURE      PASS
DATA API FAILURE    PASS
```

Trigger the camera failure live: `PRIMARY OFFLINE → BACKUP SELECTED`.

> "RightHook doesn't depend on one camera or one perfect happy path. And it never runs face or plate recognition — it observes traffic geometry, not people."

## Close

> "Roboflow sees the road. RightHook decides. Cloud Run serves it. NYC Open Data gives context. **Crash data tells cities where people were hurt. RightHook shows them the interactions happening before that.**"

Then stop.

---

# 29. Judging Q&A

**"Why is this an agent?"**
> Because the vision output changes system state and triggers actions. It observes tracked road users, reasons over spatial-temporal state, transitions through NORMAL → WATCH → CONFLICT, creates safety events, fetches context, and handles camera failover.

**"Where did your risk score come from?"**
> There isn't one. There's no weighted formula we couldn't justify. We use directly observable zone entry and observable temporal separation between those entries. The thresholds are explicitly hackathon heuristics, not calibrated crash probabilities.

**"Isn't 0.5 fps too slow for this?"**
> It is too slow for sub-second precision, which is exactly why we don't claim it. We measured the feed, reported the frame rate on screen, and expressed temporal separation in the units we can actually observe. Sub-second resolution is a video-rate feed away, not an algorithm change.

**"Why don't you just use crash data?"**
> Crash datasets are lagging indicators. This measures a leading behavioural indicator.

**"Why this specific interaction?"**
> We deliberately narrowed to one interpretable conflict class so we could build and validate the full perception-to-action loop instead of a shallow citywide dashboard.

**"What about privacy?"**
> No face recognition, no plate recognition, no re-identification, no persistence. Track IDs are ephemeral and camera-scoped. We observe traffic geometry, not people.

**"What happens if the camera dies?"**
> The camera manager tries the next configured feed and ultimately falls back to a clearly labelled replay. That failure path is one of our six test scenarios.

**"Does this scale?"**
> The engine is per-camera and stateless between cameras. Scaling is a fan-out problem, not a modelling problem. But we scoped tonight to one intersection deliberately.

---

# 30. Banned today

```text
authentication · user accounts · Supabase · Postgres · Redis · Kafka · Kubernetes
RAG · LangChain · LangGraph · LLM reasoning in the core loop · multi-agent architecture
vector databases · custom model training · fine-tuning · RL · citywide orchestration
predictive crash models · mobile app · complex maps · notifications · SMS · email
admin dashboards · analytics suites · automatic camera calibration · homography
multi-camera tracking · separate frontend deployment
```

If you catch yourself building one: **stop.**

---

# 31. Post-hackathon

Do not build tonight. Mention if asked about scale.

```text
1 camera, 1 behaviour
        ↓
hundreds of cameras
        ↓
conflict frequency per intersection
        ↓
intersection-level safety profiles
        ↓
temporal heatmaps · before/after bike-lane redesign
        ↓
proactive Vision Zero analytics
```

Future metrics: conflicts/hour · critical conflicts per 1,000 cyclists · time-of-day patterns · intersection ranking.

Adjacent artifacts worth extracting after the event: the pairwise conflict-analytics engine as a standalone permissively-licensed package, and a Roboflow Workflow block wrapping it.

---

# 32. One-screen source of truth

When you get confused during the build, come back here.

```text
                      RIGHTHOOK NYC

                    NYC LIVE CAMERA
                           │
                           ▼
                    ┌─────────────┐
                    │  ROBOFLOW   │
                    │     SEE     │
                    └──────┬──────┘
                           │  tracked objects
                           ▼
                    ┌─────────────┐
                    │  RIGHTHOOK  │
                    │   DECIDE    │
                    └──────┬──────┘
                           │
                  spatial + temporal
                      conflict?
                           │
                 ┌─────────┴─────────┐
                NO                  YES
                 │                   │
              NORMAL                 ▼
                          CREATE SAFETY EVENT
                                     │
                     ┌───────────────┴──────────────┐
                     ▼                              ▼
              NYC OPEN DATA                    CLOUD RUN
                 CONTEXT                      ACT / SERVE
                                                   ▲
                                                   │
                                            ┌──────────────┐
                                            │ pytest/VERIS │
                                            │   VERIFY     │
                                            └──────────────┘


              SEE → DECIDE → ACT → VERIFY
```

**Roboflow → SEE · RightHook → DECIDE · Cloud Run → ACT/SERVE · pytest+Veris → VERIFY · NYC Open Data → CONTEXT**

That is the architecture. That is the pitch. **That is all you build.**

---

### Final instruction

The single biggest mistake available to you tonight is adding sophistication.

**Cloud Run first. Probe the frame rate. Get Roboflow tracking a vehicle and a VRU. Get one temporal-zone conflict to emit one real event. Add failover. Wire the tests around that exact production interface. Push the repo.**

Once those work, the project is hackathon-valid and demo-worthy. Everything after that is polish — and polish is what you cut at 8:00.

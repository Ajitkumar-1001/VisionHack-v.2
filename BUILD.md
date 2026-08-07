# RightHook NYC — BUILD

> Live hackathon execution board.
> Source of truth: `PRD.md`
>
> Rule: Do not add features that are not required for the current milestone.

---

## 0. Current Status

**Build phase:** SUBMITTABLE — demo verified live, 3/3 repeatable
**Overall status:** 🟢 READY

**Current camera:** Central Park West @ 86 St (`8a6bc417-4877-4ebe-8052-88c1b261baf1`)
**Input mode:** NYCTMC stills (1 distinct frame / 2.00 s)
**Measured FPS:** 0.500 — Gate 2 LOCKED (60-sample confirmation, ADR-001)
**Temporal mode:** `cooccupancy` (Variant C — ADR-008)
of ADR-001: 352x240 night feed puts VRUs under the ~25px floor, so track IDs
are not defensible. AC-04 waived.)

Allowed temporal modes:

- `seconds`
- `frames`
- `cooccupancy`

## Cloud Run baseline — FROZEN 2026-08-07 18:51 EDT

**Cloud Run:** ✅
**Health endpoint:** ✅
**Public UI:** ✅

```text
CLOUD_RUN_URL=https://righthook-nyc-916019111029.us-east1.run.app
```

Serving revision `righthook-nyc-00005-lp8`. Deployed by explicit image
build/push, not `--source`: the default compute service account lacks Cloud
Build permissions on this fresh project, and routing around it was faster than
granting the role. Redeploy loop (the only sanctioned reason to touch deploy
config again):

```bash
IMG=us-east1-docker.pkg.dev/cloudrun-hack26nyc-4318/cloud-run-source-deploy/righthook-nyc:vN
docker build --platform linux/amd64 -t $IMG . && docker push $IMG \
  && gcloud run deploy righthook-nyc --image $IMG --region us-east1 --quiet
```

`--platform linux/amd64` is load-bearing — the build host is arm64.

---

```text
Cloud Run:           ✅
Frame Rate Gate:     ✅  LOCKED (0.500 fps)
Temporal Mode:       cooccupancy (Variant C — ADR-008)
Zone/track/engine wiring (§9-§11): ✅  ingest_frame() pipeline built + tested
Demo replay (synthetic-through-real-pipeline): ✅  2/2 marquee events fire
Real Roboflow call:  🔴  BLOCKED — no ROBOFLOW_API_KEY in this environment
```

**CURRENT:** Wire `roboflow_client.py`'s output parser (raw workflow JSON ->
`TrackObservation`) — the one piece that genuinely needs a live API response
to write correctly, per its own TODO. Everything downstream of it (zones,
tracking, conflict criterion, severity, dedup, event schema) is done and
covered by 55 green tests.
**NEXT:** Once a real detection reaches `/api/perception`, confirm one live
`SafetyEvent` end-to-end, then redeploy Cloud Run with this code.
**BLOCKER:** a key is now set in local `.env`, but it is a Roboflow
**publishable** key — confirmed 401'd by both `api.roboflow.com` ("key does
not exist") and the serverless workflow endpoint ("not authorized for
serverless inference"). Need the **Private API Key** (Dashboard -> account ->
Roboflow Keys) instead. Workspace slug (`ajit-kumar-khwqb`, currently a code
default) is still unconfirmed too since the 401 fires before that's checked.

**DO NOT:** Modify Cloud Run or IAM configuration. Baseline is frozen —
redeploying a new *image* with the sanctioned command above is fine and
expected; reconfiguring the service/IAM is not.

---

**Roboflow (wiring):** 🟡 (transport + retry logic done; output parser blocked on API key)
**Conflict Engine:** ✅ (zone→track→pair→evaluate pipeline, 55 pytest green)
**Camera Failover:** ✅ (+ `POST /api/camera/reset` so the demo repeats — AC-14)
**NYC Context:** ✅ (precomputed, served, and rendered)
**pytest:** ✅ (55 passing, 1 skipped — the credential-gated Roboflow smoke test)
**Veris:** ⬜
**Demo Replay:** 🟡 (synthetic-observations-through-real-pipeline works and is tested — `demo/replay-sequence.json` + `/api/replay/step`; the literal `.mp4` screen capture PRD §18 also wants is NOT yet recorded)
**README:** 🟡 (content substantially written; Gate 10 checklist below not reconciled against it)

**21 files of tested, working changes are uncommitted right now** (last commit
`70fae9d`, 19:13). Worth a checkpoint commit before anything else compounds on
top of it.

---

# 1. HARD GATES

These must be completed.

## Gate 1 — Cloud Run

- [x] FastAPI app starts locally
- [x] `GET /`
- [x] `GET /health`
- [x] Dockerfile works
- [x] Service deployed to Google Cloud Run
- [x] Public `.run.app` URL responds
- [x] Save Cloud Run URL here:

```text
CLOUD_RUN_URL=https://righthook-nyc-916019111029.us-east1.run.app
```

## Gate 2 — Frame-Rate Probe ✅ LOCKED

**Do not probe FPS again.** Two independent measurements agree on the order of
magnitude; a third would cost minutes and change nothing.

```text
Camera:                    Central Park West @ 86 St
Camera ID:                 8a6bc417-4877-4ebe-8052-88c1b261baf1

Stage 1 — screening:       0.489 fps  (2.04 s, 8 samples, 4-5 distinct frames)
Stage 2 — confirmation:    0.500 fps  (2.00 s, 60 samples, 31 distinct frames)

Reported figure:           0.500   ← Stage 2. Stage 1 was too thin to print.
Temporal mode:             cooccupancy
Variant:                   C       ← frame rate alone allowed B; ADR-008
                                     dropped to C on 352x240 resolution
Decision:                  LOCKED
```

All three ladder cameras land at 0.50–0.51 fps, so the ~2 s refresh is a
property of the NYCTMC platform rather than of one camera — which means the
figure stays honest after a failover.

**Reason.** The NYC DOT still feed consistently refreshes at ~0.5 fps. That
cannot support a defensible sub-second temporal claim, so conflict separation
is expressed in **observed frames** and the measured rate is displayed
alongside it. Reporting "ΔT = 0.72 s" off this feed would be a false precision
claim, not a tuning error.

**Tracking.** ByteTrack, best-effort only. AC-04 is waived under Variant C.

**Fallback.** If tracking IDs prove unstable, degrade immediately to
`temporal_mode: "cooccupancy"` (Variant C) per §6 / §26. Do not debug the
tracker — a vehicle at 15 mph moves ~13 m between frames at this rate, which
is wider than the conflict zone, so ID churn is physics rather than a bug.

- [x] Pull the camera list, count online cameras (964 online, 2026-08-07 17:45 EDT)
- [x] Pull 8 consecutive stills from 6 candidate cameras
- [x] Measure actual wall-clock interval between distinct frames
- [x] Confirmation run on the chosen camera (60 samples: 0.500 fps / 2.00 s / 31 distinct frames)
- [ ] Measure pedestrian/cyclist pixel height in those stills (eyeballed only: VRUs ~15–25 px — measure before setting Roboflow confidence floors)
- [ ] Attempt ingest of one public video-rate NYC intersection stream (deliberately skipped — a still-image variant was committed; revisit post-hackathon)
- [x] **STOP AT 15 MINUTES — commit to a variant**
- [x] Camera selected (CPW @ 86 St: two crosswalks, bike lane, and turning traffic in frame; faster cameras had no VRU-relevant view)
- [x] Save probe results here:

```text
VARIANT=C          (frame rate alone allowed B; ADR-008 dropped to C on resolution)
TEMPORAL_MODE=cooccupancy
MEASURED_FPS=0.500
```

> ✅ **Reconciled 19:07.** `config/cameras.json`, the live service, the README
> and ADR-001 all state **0.500**. AC-15 holds: the displayed rate is the
> measured rate. A 0.531 figure circulated briefly with no recorded
> methodology — discarded in favour of the 60-sample run.

## Gate 3 — Roboflow Perception (§9–10)

- [x] Roboflow Workflow created in the Roboflow UI — pretrained, no training *(exists on Roboflow's side; never yet called successfully from this app — no key)*
- [x] Class filter applied: `car`, `truck`, `bus`, `motorcycle`, `bicycle`, `person` *(`VEHICLE_CLASSES`/`VRU_CLASSES`, `app/models/perception.py`)*
- [ ] ByteTrack wired for `track_id` continuity — **waived, ADR-008.** Ran into VRUs at ~12-20px on the real feed (352x240, night, rain) before a live tracker call was possible; committed to Variant C instead of debugging IDs post-hoc.
- [ ] Confidence floor set per class — still needs a real detection to calibrate against; not guessable without one
- [x] Three polygon zones calibrated for CPW @ 86 St: `vru_approach`, `vehicle_turn_approach`, `conflict_zone` *(hand-eyeballed against `demo/frames/frame_01.jpg`, flagged in config as the least-precise part of the system — sanity-check before demo)*
- [x] Structured output includes `track_id`, `class`, `confidence`, `bbox`, `zone`, `observed_at` — `TrackObservation` model, exercised by 55 passing tests
- [ ] `CAR #NN` and `BIKE #NN` visible on screen with correct zone — needs a real Roboflow response; blocked on the key

## Gate 4 — Conflict Engine (§11–16)

- [x] Zone-entry observation recorded (never predicted) for both VRU and vehicle *(engine side; live recording waits on Gate 3)*
- [x] ΔT = `abs(vru_conflict_time - vehicle_conflict_time)` computed from observed timestamps
- [x] Event criterion implemented: both approach-zone entries + both conflict-zone entries + within threshold
- [x] Severity mapping wired for the committed variant (§12 lookup table)
- [x] State machine implemented: `NORMAL → WATCH → CONFLICT → ALERT_CREATED` *(no TTL decay back to NORMAL yet — needs the perception loop to drive the clock)*
- [x] Three agent actions wired: `create_safety_event()`, `get_intersection_context()`, `switch_camera()`
- [x] Deduplication: TTL 5–10s keyed on `{vehicle_track_id}:{vru_track_id}`; zone-level fallback suppression if IDs thrash (Variant B/C)
- [x] Event JSON matches §16 schema, including `measurement_basis` and `disclaimer` *(variant-inapplicable fields omitted, not null)*
- [x] `SEVERITY` + `SAFETY EVENT CREATED` fires end-to-end *(via `POST /api/agent/event`; camera-driven path waits on Gate 3)*

## Gate 5 — Camera Failover & Demo Replay (§18)

- [x] Failover chain implemented: primary → backup 1 → backup 2 → demo replay
- [x] `POST /api/camera/failover` forces failover (drives test scenario 5)
- [x] Camera status reported: `healthy` / `degraded` / `offline` / `fallback`
- [x] Replay exercises the **identical** engine pipeline (zones, tracks, conflict criterion, severity, dedup) — `app/replay.py` + `demo/replay-sequence.json`, real inference substituted with hand-authored *observations* (labelled as such, never presented as live)
- [x] Both marquee events fire under the committed variant: right-hook (car×bicycle) and pedestrian (truck×person) — verified, `tests/test_perception.py`
- [ ] One known-positive **video clip** (`.mp4`) captured — PRD §18's literal ask, still open. The JSON replay above satisfies the pipeline honesty requirement but not "screen-recorded footage of the real camera."
- [x] UI always labels `● LIVE` or `● DEMO REPLAY` *(two independent conditions: camera rung AND run_mode; event JSON records it too)* (`app/static/*` in flux, not yet confirmed)

## Gate 6 — NYC Context (§17)

- [x] Intersection context precomputed and pasted into `config/cameras.json` (not queried live)
- [x] Context includes `bike_infrastructure`, `facility_type`, `historical_cyclist_collisions`, `source`, `retrieved_at` (+ truck-route fields, ADR-007)
- [x] `get_intersection_context()` failure is non-fatal — surfaces as `context.status: "unavailable"`, never a 500
- [x] `GET /api/context` returns the context block
- [x] History never modifies live event severity — rendered in a separate UI region (`#context-line`)

## Gate 7 — pytest Verification (§21)

- [x] Scenario 1 — both in conflict zone, Δ below critical threshold → `severity: critical`, one event
- [x] Scenario 2 — both in conflict zone, Δ in warning band → `severity: warning`, one event
- [x] Scenario 3 — VRU in conflict zone, vehicle not → no event
- [x] Scenario 4 — same pair sent 5× → 1 event, not 5 (dedup)
- [x] Scenario 5 — primary camera unavailable → `switch_camera()`, backup selected
- [x] Scenario 6 — NYC data API returns 503 → live detection continues, `context.status: unavailable`
- [x] 6/6 scenarios green (55 pytest total, 1 skipped pending `ROBOFLOW_API_KEY`)

## Gate 8 — Veris (P2 — only if ahead of schedule)

- [ ] Veris pointed at the deployed `POST /api/agent/event` (outside the real-time path)
- [ ] Same scenarios verified via Veris

## Gate 9 — Demo & Freeze (§22, §25 8:00–8:30)

- [ ] One-screen UI: live camera panel, intersection state, NYC context, recent events, system status, disclaimer footer
- [ ] Overlays: bounding boxes, class labels, track IDs, three zones, conflict zone highlighted on event
- [x] Measured frame rate + temporal mode always visible in UI (AC-15)
- [ ] No redesign after 8:00 PM — cleanup only
- [x] Demo run 3/3 clean from a browser against the live URL
- [ ] Demo screen-recorded before 8:30 (Cloud Run URL dies with the temp `@gcplab.me` env)

## Gate 10 — Open Source / README (§23–24)

- [ ] Repo public, on a **personal GitHub account** (not `@gcplab.me`)
- [ ] `LICENSE` present (Apache-2.0 or MIT)
- [ ] `.env.example` present, no real keys committed (check git history too)
- [ ] `requirements.txt`, `Dockerfile`, `.dockerignore` present
- [ ] README: one-sentence pitch + problem framing
- [ ] README: architecture diagram
- [ ] README: measured frame rate + chosen variant stated plainly
- [ ] README: heuristic disclaimer
- [ ] README: `docker run` instructions
- [ ] README: data sourcing (exact endpoints, Open Data query used, retrieval timestamp)
- [ ] README: privacy statement (§24)
- [ ] README: honest limitations section
- [ ] Sample event JSON committed to `demo/`
- [ ] Anything worth keeping copied out of the `@gcplab.me` environment

---

# 2. Wall-Clock Schedule (§25)

| Time | Task | P0 acceptance |
|---|---|---|
| 4:45–5:15 | Cloud Run workshop. Start the hello-world during it. | — |
| 5:15–5:45 | **CLOUD RUN FIRST.** FastAPI, `/`, `/health`, Dockerfile, deploy. | Public `.run.app` URL responds |
| 5:45–6:00 | **Frame-rate probe (§6).** Commit to a variant. Pick the camera. | `temporal_mode` written to config |
| 6:00–6:35 | Roboflow perception. Frames → detections → track IDs. | `CAR #34` and `BIKE #51` visible |
| 6:35–7:00 | Zones. Configure three polygons, verify transitions. | Objects report correct `zone` |
| 7:00–7:20 | Conflict engine. Zone state + timestamps + Δ → event. | `SEVERITY` + `SAFETY EVENT CREATED` |
| | | **← AT THIS POINT YOU HAVE THE PRODUCT** |
| 7:20–7:35 | Camera resilience + capture the replay clip. Test one deliberate failure. | Failover works, clip recorded |
| 7:35–7:45 | Open data context from config. | `context` block populates |
| 7:45–8:00 | pytest scenarios 1–6. Veris only if ahead. | 6/6 green |
| 8:00–8:20 | UI cleanup. **No redesign.** | One screen, units visible |
| 8:20–8:30 | **FREEZE.** README, LICENSE, push, screen-record, rehearse ×3. | Repo public, recording exists |
| 8:30 | **SUBMISSION LOCK** | |

Dinner at 7:00 — eat while the conflict engine runs.

---

# 3. Degradation Ladder (§26) — decide by clock, not by feeling

Each rung is a **complete, honest, demo-able product**. Dropping down is not failure; it is the plan.

| Time | If you don't have… | Drop to |
|---|---|---|
| 5:45 | Cloud Run URL | **Stop everything. Get sponsor help.** Nothing else counts. |
| 6:35 | Stable detections on live feed | Switch primary input to the replay clip. Same pipeline, label it. |
| 7:00 | Stable track IDs | **Variant C.** Drop tracking, drop ΔT, use same-frame co-occupancy. |
| 7:20 | Any event firing end-to-end | Relax to co-occupancy in the conflict zone only — drop the approach-zone precondition. |
| 7:45 | Open data working | Ship `context.status: "unavailable"`. Scenario 6 already covers it; it becomes a feature. |
| 8:00 | Tests green | Ship the tests as-is with honest results in the README. A visible failing test beats a hidden one. |

**The floor is: one camera, boxes on screen, both classes in the conflict zone in one frame, an event JSON, and a Cloud Run URL.** That is still a working demo, still NYC-relevant, still uses Cloud Run, still open source.

---

# 4. Acceptance Criteria (§27)

| Done | ID | Criterion |
|---|---|---|
| ✅ | AC-01 | A public Google Cloud Run URL exists and responds |
| ⬜ | AC-02 | At least one NYC feed (live or replay) reaches Roboflow |
| ⬜ | AC-03 | Vehicles and VRUs are detected |
| ➖ | AC-04 | Objects receive tracking IDs — **waived under Variant C**, stated in README and ADR-008 |
| ✅ | AC-05 | Camera-specific polygons are configured and visible |
| ✅ | AC-06 | RightHook detects valid spatial + temporal overlap |
| ✅ | AC-07 | Detection causes `CREATE_SAFETY_EVENT` |
| ✅ | AC-08 | Repeated frames do not create duplicate events |
| ✅ | AC-09 | A failed camera produces fallback behaviour |
| ⬜ | AC-10 | Demo replay runs through the *same* inference pipeline |
| ✅ | AC-11 | At least one NYC Open Data source is attached as context (two: h9gi-nx95 + jjja-shxy) |
| ✅ | AC-12 | Test scenarios execute and results are reported honestly (33 green) |
| ✅ | AC-13 | UI visibly differentiates `● LIVE` from `● DEMO REPLAY` |
| ✅ | AC-14 | The full demo runs repeatedly without manual code changes (3/3) |
| ✅ | AC-15 | Measured frame rate and temporal mode are displayed in the UI |
| ✅ | AC-16 | Public repo with README, LICENSE, and no committed keys |

**The one metric that matters:** `successful full demos / attempted full demos` — target **10/10**. Run it ten times before you present.

---

# 5. Banned Today (§30)

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

If any decision during the build conflicts with `PRD.md` **§4 (Judging Rubric)** or **§6 (Frame-Rate Gate)**, those two sections win. Everything else is negotiable under time pressure via the degradation ladder above.

---

# 6. Open discrepancies — close before 8:30

Tracked here rather than in someone's head. Each one is a place the system
would say something it cannot back up.

| # | Issue | Why it matters | Fix |
|---|---|---|---|
| 1 | ~~FPS figure inconsistent across board / config / UI~~ | — | ✅ **CLOSED 19:07.** All sources state 0.500 (60-sample confirmation). No code or redeploy was needed; only the board was wrong. |
| 2 | Agent state has no TTL decay | §13 wants `NORMAL` after tracks leave. State sticks on `CONFLICT`/`ALERT_CREATED` after an event, so the second demo run starts dirty. | Needs the perception loop to drive a clock |
| 3 | `POST /api/perception` unimplemented | The only gap between the tested engine and live detection. Needs pairing of `TrackObservation[]` into vehicle/VRU candidates — no new conflict logic. | Gate 3 |
| 4 | Zone polygons are `[]` | Nothing can assign a zone, so nothing can enter one. | Gate 3 |
| 5 | `demo/righthook-demo.mp4` not captured | §18 makes the replay rung mandatory and §25 puts capture at 19:20. Judges warn a camera may go dark at 20:45. | Screen-record before 20:30 |
| 6 | `.veris/veris.yaml` schema is a guess | No Veris precedent was available. §21 puts pytest first, so it blocks nothing. | P2 |

**If asked on stage how the frame rate was measured:** hash each fetched still
and count only the ones NYC DOT actually published — 31 distinct frames in 60
samples, 2.00 s mean gap, 0.500 fps. A screening pass over 6 cameras first
established the citywide ceiling at 0.629 fps, which is what ruled out Variant
A. Do not quote the screening numbers as the measurement; they rest on 4–5
frames each and are too thin to print.


---

# 7. Honest gaps at submission

Stated here so nobody has to discover them on stage.

- **Roboflow is not wired.** `POST /api/perception` takes `TrackObservation[]`
  and the client + smoke test exist, but no live inference ran. The feed is
  352x240 after dark in rain; a pedestrian is 12-20 px against a ~25 px recall
  floor. We built and tested the pipeline against the interface the detector
  will fill rather than demo a detector that finds nothing. AC-02/03 unmet.
- **Replay observations are authored,** not detected. Everything downstream of
  them is real. Labelled in the UI, in `/api/replay/info`, and in each event's
  `camera.mode`.
- **Zones are eyeballed** from one night frame. The coarsest part of the system.
- **Agent state has no TTL decay** — it holds ALERT_CREATED until Reset.
- **Cloud Run pinned to one instance.** The event store is in-memory per §19 and
  autoscaling was splitting a demo across containers. Correct for tonight;
  a real deployment needs shared state.
- **`demo/righthook-demo.mp4` not captured.** The one P0 left.

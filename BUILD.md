# RightHook NYC — BUILD

> Live hackathon execution board.
> Source of truth: `PRD.md`
>
> Rule: Do not add features that are not required for the current milestone.

---

## 0. Current Status

**Build phase:** Phase 3 — Roboflow perception (engine + context already landed)
**Overall status:** 🟡 IN PROGRESS

**Current camera:** Central Park West @ 86 St (`8a6bc417-4877-4ebe-8052-88c1b261baf1`)
**Input mode:** NYCTMC stills (1 distinct frame / 2.00 s)
**Measured FPS:** 0.500 (31 distinct frames over 60 s)
**Temporal mode:** `frames` (Variant B)

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

Serving revision `righthook-nyc-00002-kzq`. Deployed by explicit image
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

**CURRENT:** Gate 3 — Roboflow perception. `POST /api/perception` is the last
gap to live detection; it needs pairing only, not new conflict logic.
**NEXT:** Calibrate the three zone polygons for CPW @ 86 St (still `[]`).
**DO NOT:** Modify Cloud Run or IAM configuration. Baseline is frozen.

> Gate 2 (measure effective FPS → choose temporal mode) closed at 17:45:
> **0.500 fps, Variant B, `temporal_mode: frames`**. Recorded in ADR-001 and
> `config/cameras.json`.

---

**Roboflow:** ⬜
**Conflict Engine:** ✅ (33 pytest green)
**Camera Failover:** ✅ (+ `POST /api/camera/reset` so the demo repeats — AC-14)
**NYC Context:** ✅ (precomputed, served, and rendered)
**pytest:** ✅ (33 passing; all six §21 scenarios)
**Veris:** ⬜
**Demo Replay:** ⬜
**README:** ⬜

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

## Gate 2 — Frame-Rate Probe (§6)

**Run this before any conflict-engine code is written. Hard timebox: 15 minutes.**

- [x] Pull the camera list, count online cameras (964 online, 2026-08-07 17:45 EDT)
- [x] Pull 8 consecutive stills from 6 candidate cameras
- [x] Measure actual wall-clock interval between distinct frames (best 1.59 s; chosen camera 2.04 s)
- [ ] Measure pedestrian/cyclist pixel height in those stills (eyeballed only: VRUs ~15–25 px — measure before setting Roboflow confidence floors)
- [ ] Attempt ingest of one public video-rate NYC intersection stream (deliberately skipped — Variant B committed; revisit post-hackathon)
- [x] **STOP AT 15 MINUTES — commit to a variant**
- [x] Camera selected (CPW @ 86 St: two crosswalks, bike lane, and turning traffic in frame; faster cameras had no VRU-relevant view)
- [x] Save probe results here:

```text
VARIANT=B
TEMPORAL_MODE=frames
MEASURED_FPS=0.500
```

## Gate 3 — Roboflow Perception (§9–10)

- [ ] Roboflow Workflow created — pretrained detection only, no training
- [ ] Class filter applied: `car`, `truck`, `bus`, `motorcycle`, `bicycle`, `person`
- [ ] ByteTrack wired for `track_id` continuity
- [ ] Confidence floor set per class if VRUs are under ~25px tall (documented in README)
- [ ] Three polygon zones calibrated for the chosen camera: `vru_approach`, `vehicle_turn_approach`, `conflict_zone`
- [ ] Structured output includes `track_id`, `class`, `confidence`, `bbox`, `zone`, `observed_at`
- [ ] `CAR #NN` and `BIKE #NN` visible on screen with correct zone

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
- [ ] One known-positive demo replay clip captured (visible vehicle + VRU + interaction)
- [ ] Replay clip runs through the **identical** Roboflow pipeline (prerecorded input, not prerecorded inference)
- [ ] UI always labels `● LIVE` or `● DEMO REPLAY` — never presents replay as live

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
- [x] 6/6 green (33 pytest total)

## Gate 8 — Veris (P2 — only if ahead of schedule)

- [ ] Veris pointed at the deployed `POST /api/agent/event` (outside the real-time path)
- [ ] Same scenarios verified via Veris

## Gate 9 — Demo & Freeze (§22, §25 8:00–8:30)

- [ ] One-screen UI: live camera panel, intersection state, NYC context, recent events, system status, disclaimer footer
- [ ] Overlays: bounding boxes, class labels, track IDs, three zones, conflict zone highlighted on event
- [ ] Measured frame rate + temporal mode always visible in UI (AC-15)
- [ ] No redesign after 8:00 PM — cleanup only
- [ ] Full demo rehearsed end-to-end — target 10/10 successful runs (§27)
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
| ⬜ | AC-04 | Objects receive tracking IDs *(waived under Variant C — README states this)* |
| ⬜ | AC-05 | Camera-specific polygons are configured and visible |
| ⬜ | AC-06 | RightHook detects valid spatial + temporal overlap |
| ✅ | AC-07 | Detection causes `CREATE_SAFETY_EVENT` |
| ✅ | AC-08 | Repeated frames do not create duplicate events |
| ✅ | AC-09 | A failed camera produces fallback behaviour |
| ⬜ | AC-10 | Demo replay runs through the *same* inference pipeline |
| ✅ | AC-11 | At least one NYC Open Data source is attached as context (two: h9gi-nx95 + jjja-shxy) |
| ✅ | AC-12 | Test scenarios execute and results are reported honestly (33 green) |
| ⬜ | AC-13 | UI visibly differentiates `● LIVE` from `● DEMO REPLAY` |
| ⬜ | AC-14 | The full demo runs repeatedly without manual code changes |
| ⬜ | AC-15 | Measured frame rate and temporal mode are displayed in the UI |
| ⬜ | AC-16 | Public repo with README, LICENSE, and no committed keys |

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

# RightHook NYC

Real-time computer vision that flags vehicle–cyclist right-hook conflicts at NYC
intersections — before they become crash statistics.

> **An agent that watches an NYC intersection and takes an action when it
> observes a potential vehicle–cyclist conflict.**

Built for NYC Vision Hack v.2 · 7 August 2026.

---

## The problem

NYC crash datasets are lagging indicators. They record where somebody already
got hurt.

They do not capture the far larger population of interactions where a cyclist
nearly gets cut off by a turning vehicle, where a turning vehicle crosses an
occupied bike lane, or where two road users occupy the same conflict area
seconds apart. An intersection can behave unsafely for years before enough
severe crashes accumulate to form a statistically meaningful signal.

RightHook exposes that missing layer.

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
```

## Architecture

`SEE → DECIDE → ACT → VERIFY` — full diagram in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

| Layer | Owner |
|---|---|
| SEE | Roboflow — pretrained detection, class filter, ByteTrack, polygon zones |
| DECIDE | RightHook engine — zone state, temporal separation, severity, dedup |
| ACT / SERVE | Google Cloud Run — one service: FastAPI + engine + UI |
| VERIFY | pytest → Veris — six behavioural scenarios against the deployed API |
| CONTEXT | NYC Open Data — precomputed intersection history |

## How the detection works

Deliberately, embarrassingly understandable:

1. A VRU (cyclist or pedestrian) is observed entering `vru_approach`.
2. A vehicle is observed entering `vehicle_turn_approach`.
3. Both are observed entering `conflict_zone`.
4. If the gap between those two entries is within threshold, a safety event is
   created.

**ΔT is the gap between two _observed_ zone-entry timestamps — never a predicted
time-to-arrival.** That removes any need for homography, pixel-to-metre
calibration, a velocity model or a ground plane. The system reports something it
actually watched happen.

There is **no weighted risk score**. No `0.35 * proximity + 0.25 * overlap`.
Those weights could not be justified honestly, so they do not exist.

## Measured frame rate and temporal mode

> **Shipped as Variant C, `temporal_mode: "cooccupancy"`.**
> The chosen camera publishes **0.500 fps — one distinct frame every 2.00 s**,
> measured over 31 distinct frames in a 60-second poll at 17:45 EDT
> (`scripts/probe_cameras.py`, which compares image hashes so it counts frames
> NYC DOT actually published, not frames we requested). A screening pass across
> 6 cameras first put the citywide ceiling at 0.629 fps — nowhere near the
> ≥10 fps Variant A needs. No sub-second ΔT is claimable, so none is claimed.
>
> That frame rate alone would allow Variant B (ΔT counted in whole frames).
> We went one step further down to **Variant C** because the feed is
> **352×240, at night, in rain**: a pedestrian is ~12–20 px tall and a cyclist
> smaller, under the ~25 px small-object floor. ByteTrack associates by IoU, so
> objects that small moving that far between 2 s samples churn IDs on physics,
> not on misconfiguration. Rather than count frames off track IDs unlikely to
> survive, the system claims only what it can defend: **a vehicle and a VRU
> occupying the conflict zone in the same observed frame.** AC-04 (tracking IDs)
> is formally waived, which PRD §27 anticipates. Reasoning in ADR-008.
>
> Chosen camera: **Central Park West @ 86 St**
> (`8a6bc417-4877-4ebe-8052-88c1b261baf1`) — two crosswalks, the painted bike
> lane, and turning traffic all in frame. Full probe table in
> [`docs/DECISIONS.md`](docs/DECISIONS.md).

| | Variant A | Variant B | **Variant C — ACTIVE** |
|---|---|---|---|
| Sampling | video-rate ≥10 fps | stills ~0.5 fps | tracking unstable |
| Measurement | ΔT in seconds | ΔT in frames + stated fps | co-occupancy |
| Displayed as | `ΔT 0.72s` | `Δ 1 frame @ 0.5 fps (≈2.0s)` | `both in zone, same frame` |

**Running Variant C** (ADR-008). At 0.500 fps on a 352×240 night feed, ByteTrack
associates by IoU across objects that move further than their own size between
samples — ID continuity is not defensible, so no temporal gap is claimed at all.
AC-04 (tracking IDs) is waived accordingly. The variant is a config flag: the
engine implements all three and the test suite asserts against whichever is
active.

Whatever the feed gives us, the UI states the measured frame rate and the
temporal mode. A system that says "Δ 1 frame at 0.5 fps" is more credible than
one that says "ΔT 0.72s" with nothing behind it.

## What is and is not real

The single most important section in this README. Every claim below is
verifiable from the repo or the live URL.

| Component | Status |
|---|---|
| NYC DOT camera feed | **Real.** Live stills from `webcams.nyctmc.org`, polled and displayed. |
| Measured frame rate | **Real.** 0.500 fps, measured by image-hash dedup over 60 samples. |
| Zone polygons | **Real,** hand-calibrated by eye against a captured frame. Coarse. |
| Conflict engine | **Real.** Zone assignment, track state, criterion, severity, dedup — all execute. |
| NYC Open Data context | **Real.** Two datasets, precomputed, query and retrieval timestamp recorded. |
| Event JSON | **Real,** emitted by the engine. |
| Camera failover | **Real.** Three-rung ladder plus a replay rung. |
| **Roboflow detection** | **NOT WIRED.** The client and smoke test exist; no live inference ran. |
| **Demo replay observations** | **Synthetic.** Hand-authored bounding boxes, not detector output. |

The replay feeds *authored observations* through the *real* pipeline. Zone
assignment, tracking, the conflict criterion, severity mapping, dedup, the
event schema and context attachment all run for real against them — but a
detector did not produce the boxes. The UI labels any such run `● DEMO REPLAY`,
`/api/replay/info` says so in plain text, and every event emitted during a
replay records `camera.mode: "demo_replay"` in its JSON.

**Why Roboflow is not wired.** The chosen camera publishes **352×240** stills,
and the build window fell after dark in rain. At that resolution a pedestrian
is 12–20 px and a cyclist smaller — below the ~25 px floor where small-object
recall collapses. Rather than demo a detector that finds nothing and call it a
perception system, the pipeline was built and tested against the interface the
detector will fill. `POST /api/perception` accepts `TrackObservation[]` today;
wiring Roboflow means parsing its output into that shape, not new logic.

## Try it

```bash
# The decision path, no camera required:
curl -X POST https://righthook-nyc-916019111029.us-east1.run.app/api/agent/event \
  -H 'content-type: application/json' \
  -d '{"vehicle":{"track_id":34,"class":"car","entered_approach":true,"conflict_entry":100},
       "vru":{"track_id":51,"class":"bicycle","entered_approach":true,"conflict_entry":100}}'

# One frame of the replay through the full pipeline:
curl -X POST 'https://righthook-nyc-916019111029.us-east1.run.app/api/replay/step?frame_index=3'
```

Or open the URL and press **Run demo replay**.

## Disclaimer

> **Potential vehicle–VRU conflict detected using spatial and temporal
> heuristics. Thresholds are hackathon heuristics and have not been calibrated
> as crash-risk probabilities.**

RightHook does not claim crash probabilities and does not assert that any
detected interaction was a near miss.

## Privacy

- No face recognition. No licence-plate recognition. No re-identification across
  cameras or across time.
- Track IDs are ephemeral, scoped to a single camera session. They are not
  identities.
- No frame is persisted beyond the in-memory event buffer. Nothing is written to
  durable storage.
- Detection classes are limited to `car`, `truck`, `bus`, `motorcycle`,
  `bicycle`, `person`. No attribute inference of any kind.
- NYC DOT stills are low-resolution; at the working distances involved, faces
  and plates are not resolvable.
- The system produces **observations about traffic geometry, never observations
  about individuals.** There is no enforcement output.

## Data sources

| Source | Endpoint / dataset | Use |
|---|---|---|
| NYC DOT traffic cameras | `GET https://webcams.nyctmc.org/api/cameras` | Camera list (`isOnline` is the string `"true"`) |
| NYC DOT still frames | `GET https://webcams.nyctmc.org/api/cameras/{id}/image` | JPEG frames, polled every 2s |
| NYC Open Data | Motor Vehicle Collisions – Crashes (`h9gi-nx95`) | Historical VRU-injury collisions near the intersection |
| NYC Open Data | New York City Truck Routes (`jjja-shxy`) | Whether the intersection sits on designated truck routes |

Truck Routes replaced the originally planned Bicycle Routes dataset
([ADR-002](docs/DECISIONS.md)): the camera already shows the bike lane, but
truck-route designation is invisible in the frame and directly modulates the
`truck`/`bus` classes the detector outputs.

At the chosen intersection (250 m radius, 2021-08-07 → 2026-08-07, retrieved
2026-08-07 17:48 EDT): **28 collisions injured a cyclist or pedestrian**
(16 cyclist, 12 pedestrian; 96 collisions total), and the intersection sits
where **two designated Local Truck Routes cross** — Central Park West, West 86
Street, and the 86 St Transverse are all `truckroute=Y` (NYCDOT Traffic Rules
§4-13(d)(2)).

Open Data is **precomputed once** into `config/cameras.json`, not queried live.
The exact query and its retrieval timestamp are recorded in that file so the
pipeline is reproducible. Post-hackathon idea, deliberately skipped tonight:
MTA BusTime GTFS-Realtime to cross-validate detected buses against ground truth.

Historical context is rendered as a separate layer and **never modifies an
individual event's severity.**

## Run it

The Cloud Run URL is tied to a temporary event environment that is decommissioned
after the hackathon, so the container is the durable path:

```bash
docker build -t righthook-nyc .
docker run -p 8080:8080 --env-file .env righthook-nyc
# → http://localhost:8080        the one screen
# → http://localhost:8080/health {"service":"righthook-nyc","status":"healthy"}
```

Local development:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8080
```

Copy `.env.example` to `.env` and add your Roboflow key. **No real keys are ever
committed.**

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness. Open Data availability cannot affect it. |
| `GET /api/status` | Camera, mode, agent state, measured fps, temporal mode |
| `GET /api/events` | Recent events |
| `GET /api/events/{id}` | Single event |
| `POST /api/perception` | Roboflow structured output enters here |
| `POST /api/agent/event` | Synthetic observation → decision |
| `GET /api/context` | Intersection context |
| `POST /api/camera/failover` | Force failover |
| `POST /api/camera/reset` | Climb back to the primary camera (AC-14: the demo repeats) |

`POST /api/agent/event` reproduces the decision logic without a camera. A sample
event is committed at [`demo/sample-event.json`](demo/sample-event.json).

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

| # | Scenario | Proves |
|---|---|---|
| 1 | Both in conflict zone, Δ below critical threshold | Core path |
| 2 | Both in conflict zone, Δ in warning band | Threshold correctness |
| 3 | VRU in conflict zone, vehicle not | No false positives |
| 4 | Same pair sent 5× | Dedup — 1 event, not 5 |
| 5 | Primary camera unavailable | Failover to backup |
| 6 | NYC data API returns 503 | Detection continues, context degrades |

Scenario 6 encodes the failure philosophy: **never fail live safety detection
because optional enrichment is down.** A dead Open Data API surfaces as
"Historical context unavailable", never as a 500.

> **56 passed, 1 skipped** (the skip is the Roboflow smoke test, which needs an
> API key). All six §21 scenarios pass, plus coverage of the bugs found while
> building: stale tracks re-firing after the dedup window lapsed, replay events
> displaying under a LIVE badge, and co-occupancy being evaluated from entry
> history instead of the present frame.

## Limitations

Stated plainly, because they matter more than the demo:

- **One camera, one intersection.** Zones are hand-calibrated per camera; there
  is no automatic intersection understanding and no multi-camera tracking.
- **Uncalibrated.** No homography, no pixel-to-metre mapping. All geometry is
  image-space.
- **Heuristic thresholds.** The ΔT bands are hackathon choices, not values
  derived from crash data.
- **Low frame rate.** The public DOT feed refreshes every couple of seconds, so
  sub-second temporal precision is not claimable — which is why it is not
  claimed. A video-rate feed is a config change, not an algorithm change.
- **Small-object recall.** `bicycle` is the known weak point at these distances;
  `person` degrades more gracefully.
- **Detection is not intent.** A conflict event says two road users occupied the
  same space close in time. It does not say anyone did anything wrong.

## Licence

MIT — see [LICENSE](LICENSE).

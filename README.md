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

> **TBD — pending the §6 probe.** Run `python scripts/probe_cameras.py`, then
> fill in the measured fps and the chosen variant here and in
> `config/cameras.json`. This section is the project's credibility: the UI and
> this README must state the same measured number.

| | Variant A | Variant B | Variant C |
|---|---|---|---|
| Sampling | video-rate ≥10 fps | stills ~0.5 fps | tracking unstable |
| Measurement | ΔT in seconds | ΔT in frames + stated fps | co-occupancy |
| Displayed as | `ΔT 0.72s` | `Δ 1 frame @ 0.5 fps (≈2.0s)` | `both in zone, same frame` |

Whatever the feed gives us, the UI states the measured frame rate and the
temporal mode. A system that says "Δ 1 frame at 0.5 fps" is more credible than
one that says "ΔT 0.72s" with nothing behind it.

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
| NYC Open Data | Motor Vehicle Collisions – Crashes | Historical cyclist collisions near the intersection |
| NYC Open Data | NYC Bicycle Routes | Presence and type of bike infrastructure |

Open Data is **precomputed once** into `config/intersection_context.json`, not
queried live. The exact query and its retrieval timestamp are recorded in that
file so the pipeline is reproducible.

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

> **Current status: scaffold — 5 skipped, 0 passed.** The six scenarios live in
> five test modules and all skip pending the engine. Results are reported here
> honestly as they land; a visible failing test beats a hidden one.

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

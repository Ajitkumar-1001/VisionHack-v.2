# Architecture

`SEE → DECIDE → ACT → VERIFY`

Each sponsor integration owns a real responsibility. None is decorative.

| Layer | Owner | Responsibility |
|---|---|---|
| SEE | Roboflow | What objects exist, where, and which tracked object is which |
| DECIDE | RightHook engine | Zone state, temporal separation, severity, dedup |
| ACT / SERVE | Google Cloud Run | One service: FastAPI + engine + static UI |
| VERIFY | pytest → Veris | Six behavioural scenarios against the deployed API |
| CONTEXT | NYC Open Data | Precomputed intersection history, never severity-affecting |

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

**Veris is never in the real-time path.** It calls the deployed API from
outside, which protects demo latency.

## Why one service

Everything ships in a single Cloud Run container — FastAPI, the engine, the
camera manager, config-backed context, an in-memory event store, and the static
UI. No separate frontend deployment, no database, no Redis. There is no time for
the coordination cost, and the eligibility gate only cares that one service
responds.

## Module map

```
app/
├── main.py              /health (the gate), / (UI), router mount
├── api/routes.py        the eight §20 endpoints
├── vision/              SEE — roboflow_client, tracks, zones, frame_probe
├── agent/               DECIDE — engine, state, actions, severity, dedup
├── cameras/             nyc_dot, manager (fallback ladder), health
├── context/             intersection — precomputed Open Data
├── models/              perception.py, event.py — the boundary contracts
└── static/              the one screen
```

## The load-bearing design choice

ΔT is the gap between two **observed** zone-entry timestamps — never a predicted
time-to-arrival. That single decision removes the need for homography,
pixel-to-metre calibration, a velocity model and a ground plane. The system
reports something it actually watched happen, which is why it can be defended
under questioning in a way a weighted risk score cannot.

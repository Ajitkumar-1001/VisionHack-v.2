# Decisions

Short ADR trail. Each entry is a decision that cost time or closed off an
option, recorded so it can be defended rather than re-litigated.

---

## ADR-001 — Frame-rate fork: which temporal variant?

**Status:** OPEN — pending the §6 probe
**Decide by:** 18:00

The highest-risk unknown in the build. The sanctioned NYC DOT feed serves stills
refreshing every couple of seconds. A 1.0s ΔT threshold cannot be measured at a
2s sampling period: the temporal quantum is 2000ms, every severity bin is
narrower than one frame interval, and a vehicle at 15 mph moves ~13 m between
frames — wider than the conflict zone itself. ByteTrack associates by IoU, so
when displacement exceeds object size, IDs thrash.

Reporting "ΔT = 0.72 sec" from a 0.5 fps source is not a tuning error. It is a
false precision claim, and it is exactly what a judge asks about.

| | Variant A | Variant B | Variant C |
|---|---|---|---|
| Condition | video-rate ≥10 fps | stills, ~0.5 fps | tracking unstable by 19:00 |
| Measurement | ΔT in seconds | ΔT in frames + fps | co-occupancy |
| UI shows | `ΔT 0.72s` | `Δ 1 frame @ 0.5 fps (≈2.0s)` | `both in zone, same frame` |

**Decision:** _pending — run `python scripts/probe_cameras.py`, record the
measured fps here, and set `temporal_mode` in `config/cameras.json`._

**Consequence:** the variant is a config flag, not a rewrite. All three emit the
identical event schema and drive the identical state machine.

---

## ADR-002 — No weighted risk score

**Status:** ACCEPTED

Rejected `0.35 * proximity + 0.25 * overlap + ...`. Those weights cannot be
justified in three hours and cannot survive a follow-up question. Instead:
observable zone entry, observable temporal separation between two watched
events, stated thresholds, explicitly labelled as heuristics.

**Consequence:** the honest answer to "where did your risk score come from?" is
"there isn't one" — which is stronger than a number we invented.

---

## ADR-003 — NYC Open Data precomputed to config, not queried live

**Status:** ACCEPTED

Live Socrata querying against two datasets is ~75 minutes we do not have, and
the camera is chosen by 17:45. The numbers are looked up once for that one
intersection and pasted into `config/intersection_context.json`. The README
documents the exact query so the pipeline stays reproducible.

**Consequence:** 15 minutes instead of 90. AC-11 still passes, NYC Relevance
still scores. Live querying is P2 — only if complete before 20:00.

---

## ADR-004 — Pedestrians promoted to P0 co-primary

**Status:** ACCEPTED

Right-hooks are rare; turning-vehicle-vs-pedestrian conflicts are constant.
`bicycle` keeps the narrative and the project name. `person` carries the live
firing rate and is what actually fires on stage.

**Consequence:** the single change most likely to convert "we demoed on replay"
into "it fired live." Same engine, same zones, same rule — class asymmetry is
preserved in the schema (vehicle is always subject, VRU always object).

---

## ADR-005 — pytest first, Veris second

**Status:** ACCEPTED

Veris is a sponsor tool but not a judging criterion; Open Source and Technical
Execution are. The six scenarios are written as pytest against the deployed API
first — that artifact lands in the repo and scores on two criteria for ~12
minutes of work. Veris then points at the same endpoint if the clock allows.

**Consequence:** the test artifact exists regardless of whether the Veris
integration lands.

---

## ADR-006 — Repo on a personal GitHub account

**Status:** ACCEPTED

The temporary `@gcplab.me` environment and its project are decommissioned at the
end of the event, so the Cloud Run URL dies with it.

**Consequence:** the repo lives on a personal account, the README carries a
`docker run` path so the project is runnable after the URL is gone, and the demo
is screen-recorded before 20:30.

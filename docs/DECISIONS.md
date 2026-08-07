# Decisions

Short ADR trail. Each entry is a decision that cost time or closed off an
option, recorded so it can be defended rather than re-litigated.

---

## ADR-001 — Frame-rate fork: which temporal variant?

**Status:** CLOSED — Variant B (`temporal_mode: "frames"`), 2026-08-07 17:45 EDT
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

**Decision:** Variant B. Two-stage probe, 2026-08-07 (964 cameras online). The
probe compares image hashes, so it counts frames NYC DOT actually *published*,
not frames we requested.

Stage 1 — screening, 6 cameras × 8 samples, to find the citywide ceiling:

| fps | gap (s) | camera |
|---|---|---|
| 0.629 | 1.59 | QBB @ Crescent St |
| 0.553 | 1.81 | Exterior St @ 3 Ave |
| 0.545 | 1.84 | Canal Street @ Chrystie Street |
| 0.489 | 2.04 | **Central Park West @ 86 St ← chosen** |
| 0.322 | 3.10 | Amsterdam Ave @ 60 St |

Ceiling was 0.629 fps — nowhere near Variant A's ≥10 fps, so the fork was
decided here. But those figures rest on 4–5 distinct frames each, which is too
thin to print in a UI.

Stage 2 — confirmation, 60 samples on the chosen camera: **0.500 fps, 2.00 s
mean gap, 31 distinct frames.** That is the number the UI and README state.

Camera chosen on view geometry, verified by inspecting live frames: CPW @ 86 St
(`8a6bc417-4877-4ebe-8052-88c1b261baf1`) shows two zebra crosswalks, the painted
bike lane, turning vehicles and pedestrians. The faster cameras lost on content
— QBB @ Crescent is a bridge deck (no VRUs possible), Canal @ Chrystie faces an
empty approach ramp with no crosswalk in view.

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
intersection and pasted into `config/cameras.json`. The README documents the
exact query so the pipeline stays reproducible.

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

---

## ADR-007 — Truck Routes replaces Bicycle Routes as the second context dataset

**Status:** ACCEPTED — 2026-08-07 17:49 EDT (deviation from PRD §5)

PRD §5 named NYC Bicycle Routes as the secondary context source. Replaced with
**New York City Truck Routes** (`jjja-shxy`). Test applied: does the dataset
tell a judge something the camera cannot already show? Bike-lane presence is
visible in the frame (information gain ≈ 0). Truck-route designation is
invisible in the frame and directly modulates the `truck`/`bus` classes the
detector already outputs — large vehicles are disproportionately lethal in
right-hook conflicts (blind spots + rear-wheel off-tracking).

Spatial query result: the chosen intersection sits where **two designated Local
Truck Routes cross** — Central Park West, West 86 Street, and the 86 St
Transverse are all `truckroute=Y` (NYCDOT Traffic Rules §4-13(d)(2)).

**Consequence:** the pitch upgrades from "we caught an anomaly" to a structural
claim — the city routes heavy vehicles through both axes of an intersection a
protected bike lane crosses, with 28 VRU-injury collisions within 250 m in five
years. Historical context stays context: it never modifies live event severity
(§17).

---

## ADR-008 — Committed to Variant C (`cooccupancy`) without a live ByteTrack run

**Status:** ACCEPTED — 2026-08-07 ~19:30 EDT (revises the tracking side of ADR-001)

ADR-001 locked Variant B (`frames`) on frame rate alone and left the ByteTrack
PASS/FAIL check for later. `scripts/test_feed.py`'s Stage 1 (frame capture,
credential-free) ran and surfaced a second fact ADR-001 didn't have: the feed
is 352x240, captured after dark in rain. At that resolution a pedestrian is
~12-20px tall and a cyclist smaller — under the ~25px small-object recall
floor PRD §9 already flags. ByteTrack associates by IoU; objects this small
moving this far between ~2s samples churn IDs on physics, not misconfiguration
— the exact trigger §6/§26 describe for dropping to Variant C.

Stage 2 (the live PASS/FAIL tabulation against the real tracker) is still
blocked on `ROBOFLOW_API_KEY`, which is not set anywhere in this environment.
Rather than block the conflict-engine milestone on a credential, and given the
resolution/lighting evidence already points at Variant C, made the call now.

**Decision:** `config/cameras.json` → `temporal_mode: "cooccupancy"`. No
engine change required — `severity.py`, `state.py` and `TrackStore` already
handle all three variants as a config lookup, per ADR-001's original design.

**Consequence:** AC-04 (tracking IDs) is formally waived, as PRD §27 already
anticipates. Severity collapses to a single `CONFLICT` band — no
CRITICAL/WARNING split — which is a smaller, more honest claim than a frame
count off IDs unlikely to survive. If Stage 2 later runs and IDs prove stable
after all, this reverts to `frames` in one config edit; nothing else changes.

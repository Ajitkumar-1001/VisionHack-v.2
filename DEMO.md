# Demo script — three acts, three minutes

Read this cold at 20:45. Run the full demo **ten times** before presenting;
that number matters more than any additional feature.

**Before you start:** UI open, `● LIVE` or `● DEMO REPLAY` badge correct, event
list clear, `demo/sample-event.json` open in a second tab.

---

## Opening

> "Crash data tells us where somebody already got hurt. But a dangerous
> intersection can generate hundreds of unsafe interactions before a single
> crash ever becomes a record."

---

## Act 1 — Reality (45s)

Show `● LIVE`.

> "This is a live NYC DOT traffic camera. Roboflow detects and tracks road
> users. We're sampling at **[MEASURED_FPS]** frames per second — that's what
> the city's public feed gives you, and everything on this screen is honest
> about that."

Point at `CAR #34`, `BIKE #51`.

---

## Act 2 — Intelligence (75s)

Switch to replay if needed, **and say why**:

> "To show the conflict path deterministically, I'll run a recorded NYC sequence
> through the *exact same* inference pipeline. This is prerecorded input, not
> prerecorded inference."

State goes `NORMAL → WATCH`. Then the alert.

> "The vehicle entered the turn approach. The cyclist entered the bike corridor.
> Both entered the conflict zone within one frame of each other."

**`WARNING` · `Δ 1 frame @ 0.5 fps` · `SAFETY EVENT CREATED`**

> "The detection doesn't just draw a box. It changes the state of the agent and
> causes an action."

*This is the most important sentence in the demo. Do not rush it.*

Show the event JSON. Then the context panel:

> "Separately — not as part of the severity — NYC Open Data tells us this
> intersection has 14 prior cyclist collisions and a protected bike lane.
> History gives context. It never modifies the live observation."

---

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

> "RightHook doesn't depend on one camera or one perfect happy path. And it
> never runs face or plate recognition — it observes traffic geometry, not
> people."

*That privacy sentence takes eight seconds and it differentiates you.*

---

## Close

> "Roboflow sees the road. RightHook decides. Cloud Run serves it. NYC Open Data
> gives context. **Crash data tells cities where people were hurt. RightHook
> shows them the interactions happening before that.**"

Then stop.

---

## Judging Q&A

**"Why is this an agent?"**
> Because the vision output changes system state and triggers actions. It
> observes tracked road users, reasons over spatial-temporal state, transitions
> through NORMAL → WATCH → CONFLICT, creates safety events, fetches context, and
> handles camera failover.

**"Where did your risk score come from?"**
> There isn't one. There's no weighted formula we couldn't justify. We use
> directly observable zone entry and observable temporal separation between
> those entries. The thresholds are explicitly hackathon heuristics, not
> calibrated crash probabilities.

**"Isn't 0.5 fps too slow for this?"**
> It is too slow for sub-second precision, which is exactly why we don't claim
> it. We measured the feed, reported the frame rate on screen, and expressed
> temporal separation in the units we can actually observe. Sub-second
> resolution is a video-rate feed away, not an algorithm change.

**"Why don't you just use crash data?"**
> Crash datasets are lagging indicators. This measures a leading behavioural
> indicator.

**"Why this specific interaction?"**
> We deliberately narrowed to one interpretable conflict class so we could build
> and validate the full perception-to-action loop instead of a shallow citywide
> dashboard.

**"What about privacy?"**
> No face recognition, no plate recognition, no re-identification, no
> persistence. Track IDs are ephemeral and camera-scoped. We observe traffic
> geometry, not people.

**"What happens if the camera dies?"**
> The camera manager tries the next configured feed and ultimately falls back to
> a clearly labelled replay. That failure path is one of our six test scenarios.

**"Does this scale?"**
> The engine is per-camera and stateless between cameras. Scaling is a fan-out
> problem, not a modelling problem. But we scoped tonight to one intersection
> deliberately.

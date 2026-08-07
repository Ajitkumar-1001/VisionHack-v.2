# RightHook NYC — demo script

Live: **https://righthook-nyc-916019111029.us-east1.run.app**
Repo: **https://github.com/Ajitkumar-1001/VisionHack-v.2**

Everything below matches what the system actually does as of 19:45, 7 Aug 2026.
If a number here disagrees with the screen, the screen wins — say so out loud.

---

## The idea, in one sentence

> **An agent that watches an NYC intersection and takes an action when it
> observes a potential vehicle–cyclist conflict.**

Not "AI traffic monitoring." Not "a traffic dashboard."

---

## The concept — 60 seconds, no screen

Say this before you show anything.

> "Every city plans street safety from crash data. Crash data is a **lagging
> indicator** — it only exists after somebody has already been hurt.
>
> But an intersection doesn't become dangerous on the day of the crash. It's
> been generating near-misses for years: a turning van cutting across an
> occupied bike lane, a cyclist and a car arriving in the same box a second
> apart. Hundreds of those happen before one of them becomes a police report.
>
> **That entire layer is invisible.** Nobody records it, because recording it
> would mean a human watching a camera all day.
>
> RightHook watches instead. It takes a public NYC DOT traffic camera, watches
> one intersection, and when a turning vehicle and a cyclist or pedestrian
> occupy the same conflict area, it doesn't just draw a box — it **changes
> state and creates a structured safety event**.
>
> Crash data tells you where people *were* hurt. This measures the behaviour
> happening *before* that."

### The one diagram

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

### Why it's an *agent*, not a viewer

```text
NORMAL → WATCH → CONFLICT → ALERT_CREATED
```

Perception changes system state, and state change triggers an action:
`create_safety_event()`, `get_intersection_context()`, `switch_camera()`.
Detection that only draws a box is a viewer. Detection that causes a decision
is an agent.

---

## Demo — three acts, three minutes

**Before you start:** open the URL, press **Reset**, have the repo in a second tab.

### Act 1 — the intersection (40s)

Point at the camera panel.

> "This is a live NYC DOT camera at **Central Park West and 86th Street**. It's
> a real public feed, and it's refreshing right now.
>
> The three coloured polygons are the whole calibration: green is where
> cyclists and pedestrians enter the crossing, blue is where turning vehicles
> come from, red is the conflict zone where those two paths overlap. Three
> polygons, drawn by hand. No homography, no camera calibration, no 3D."

Point at the header.

> "**0.5 frames per second, co-occupancy mode.** That's not a limitation we're
> hiding — it's printed on the screen. This public feed publishes one new
> still roughly every two seconds. We measured it: 31 distinct frames out of
> 60 samples."

### Act 2 — the conflict (80s)

Press **Run demo replay**. Narrate as it steps.

> "Watch the state panel."

`NORMAL → WATCH`

> "**WATCH.** A vehicle is in the turn approach and a cyclist is at the kerb.
> Both approaching, neither in the conflict zone yet."

`CONFLICT` + `SAFETY EVENT CREATED`

> "Both are now in the conflict zone in the same observed frame. The agent
> changed state and created a safety event.
>
> **That sentence is the whole project.** The detection doesn't just draw a
> box — it changes the state of the agent and causes an action."

*(Do not rush that line.)*

Then the honesty beat — say it, don't let them find it:

> "And I want to be precise about what you're watching. This is a **replay**,
> and the badge says so. The bounding boxes in this sequence are authored, not
> produced by a detector. Everything downstream of them is real: the zone
> assignment, the tracking state, the conflict rule, the severity mapping, the
> deduplication, the event JSON. Every event created this way records
> `mode: demo_replay` in its own JSON so it can never be mistaken for a live
> detection later.
>
> The reason is on the screen: this feed is **352 by 240 pixels**, and it's
> dark and raining. A pedestrian in that crosswalk is about fifteen pixels
> tall. We could have pointed a detector at it and shown you an empty box —
> instead we built and tested the decision pipeline against the interface the
> detector plugs into."

Point at the context strip.

> "Separately — and this matters — NYC Open Data tells us this intersection
> has **16 cyclist-injury collisions within 250 metres since 2021**, a painted
> bike lane, and it sits where **three designated truck routes cross**.
>
> That's rendered in its own region and it **never touches severity**. History
> gives context. It does not modify a live observation. Those are two different
> claims and we keep them apart."

### Act 3 — reliability (45s)

> "One good clip doesn't prove an agent works, so we test its behaviour."

Press **Force camera failure**.

> "Primary camera down, fallback to the next in the ladder — and the ladder
> ends at a labelled replay, so the demo can never go dark."

> "**56 automated tests**, covering all six behavioural scenarios: valid
> conflict, safe interaction, duplicate suppression, camera failure, and the
> NYC data API going down — where live detection continues and the context
> block degrades to *unavailable* rather than throwing a 500.
>
> And it never runs face or plate recognition. No re-identification. No frames
> stored. It observes traffic **geometry**, not people."

### Close

> "Roboflow's role is to see. RightHook decides. Cloud Run serves it. NYC Open
> Data gives context.
>
> **Crash data tells cities where people were hurt. RightHook shows them the
> interactions happening before that.**"

Stop talking.

---

## The hard questions

**"Where did your risk score come from?"**
> There isn't one. No weighted formula we couldn't justify. We use directly
> observable zone entry and observable co-occupancy. The thresholds are
> explicitly hackathon heuristics, not calibrated crash probabilities.

**"So the detection isn't real?"**
> The *decision system* is real and tested end to end. The detector is not
> wired — the feed is 352×240 after dark in rain, where a pedestrian is 12 to
> 20 pixels, below the point where small-object recall holds up. Wiring
> Roboflow means parsing its output into the `TrackObservation` shape
> `POST /api/perception` already accepts. It's a parser, not new logic. We'd
> rather tell you that than show you a detector finding nothing.

**"Isn't 0.5 fps too slow?"**
> Too slow for sub-second precision, which is exactly why we don't claim it.
> We measured the feed and expressed separation in the only unit we can
> actually observe: same frame, or not. A faster feed is a config flag —
> `temporal_mode` — not an algorithm change.

**"Why is this an agent?"**
> Vision output changes system state and triggers actions. It transitions
> NORMAL → WATCH → CONFLICT → ALERT_CREATED, creates events, fetches context,
> and handles camera failover.

**"Why not just use crash data?"**
> Crash datasets are lagging indicators. This measures a leading behavioural
> one.

**"What about privacy?"**
> No face recognition, no plate recognition, no re-identification, no
> persistence. Track IDs are ephemeral and camera-scoped. Traffic geometry,
> not people.

**"Does it scale?"**
> The engine is per-camera and stateless between cameras, so it's a fan-out
> problem, not a modelling one. Tonight it's pinned to a single instance
> because the event store is in-memory — a real deployment needs shared state.

**"What would you do next?"**
> Wire the detector against a daylight feed, then measure conflicts per hour
> per intersection. That number is what turns this from a demo into a Vision
> Zero planning input.

---

## Reproduce it without the UI

```bash
# The decision path, no camera needed:
curl -X POST https://righthook-nyc-916019111029.us-east1.run.app/api/agent/event \
  -H 'content-type: application/json' \
  -d '{"vehicle":{"track_id":34,"class":"car","entered_approach":true,"conflict_entry":100},
       "vru":{"track_id":51,"class":"bicycle","entered_approach":true,"conflict_entry":100}}'
```

---

## If something breaks on stage

- **Camera panel blank** — the DOT feed dropped a frame. Keep talking; the
  replay does not depend on it.
- **No events after replay** — press **Reset**, then **Run demo replay** again.
- **URL dead** — `docker run -p 8080:8080 righthook-nyc`, instructions in the
  README. The Cloud Run project is decommissioned at end of event; the repo
  and the container are the durable artifacts.

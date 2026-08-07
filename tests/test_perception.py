"""Perception -> zones -> tracks -> conflict. PRD §9-§11, AC-02/03/05/06/07/10.

The replay sequence is the end-to-end fixture: it exercises the real zone
assignment, track store, conflict criterion, severity map and dedup.
"""

from __future__ import annotations

import pytest

from app.models.perception import PerceptionFrame, Zone
from app.replay import load_sequence
from app.vision.tracks import TrackStore


def run_replay(client) -> dict:
    client.post("/api/run/reset")
    total = len(load_sequence()["frames"])
    for i in range(total):
        client.post(f"/api/replay/step?frame_index={i}")
    return client.get("/api/events").json()


def test_replay_produces_exactly_two_events(client):
    """One right-hook (car x bicycle) and one pedestrian conflict."""
    events = run_replay(client)
    assert events["count"] == 2

    by_pair = {
        (e["participants"]["vehicle"]["class"], e["participants"]["vru"]["class"]): e
        for e in events["events"]
    }
    assert ("car", "bicycle") in by_pair
    assert ("truck", "person") in by_pair


def test_right_hook_fires_with_the_active_variant_semantics(client, engine):
    """The variant is a config flag (§6), so the assertion follows the mode
    rather than hardcoding one. What must hold in every mode: the approach
    preconditions were observed and both parties reached the conflict zone."""
    events = run_replay(client)
    hook = next(
        e for e in events["events"] if e["participants"]["vru"]["class"] == "bicycle"
    )
    obs = hook["observation"]
    assert obs["both_entered_conflict_zone"] is True
    assert obs["vehicle_entered_turn_zone"] is True
    assert obs["vru_entered_approach_zone"] is True

    mode = engine.temporal_mode.value
    if mode == "frames":
        assert hook["decision"]["severity"] in ("warning", "critical")
        assert obs["temporal_gap_frames"] is not None
    elif mode == "cooccupancy":
        # §12 Variant C: no temporal gap is claimable, so none is reported.
        assert hook["decision"]["severity"] == "conflict"
        assert obs["same_frame_cooccupancy"] is True
        assert "temporal_gap_frames" not in obs
        assert "temporal_gap_seconds" not in obs
    else:
        assert obs["temporal_gap_seconds"] is not None


def test_same_frame_pedestrian_conflict_is_the_most_severe_bin(client, engine):
    """Truck and pedestrian enter the crossing on the SAME frame — the worst
    case the active variant can express."""
    events = run_replay(client)
    ped = next(
        e for e in events["events"] if e["participants"]["vru"]["class"] == "person"
    )
    mode = engine.temporal_mode.value
    expected = {"frames": "critical", "seconds": "critical", "cooccupancy": "conflict"}
    assert ped["decision"]["severity"] == expected[mode]


def test_state_machine_reaches_watch_before_alert(client):
    """§13: the demo needs a visible build-up, not an alert from nowhere."""
    client.post("/api/run/reset")
    states = [
        client.post(f"/api/replay/step?frame_index={i}").json()["agent_state"]
        for i in range(len(load_sequence()["frames"]))
    ]
    assert "WATCH" in states
    assert states.index("WATCH") < states.index("ALERT_CREATED")


def test_repeat_frame_is_deduped(client):
    """Frame 4 repeats the same pair still in the zone — no second event."""
    client.post("/api/run/reset")
    for i in range(4):
        client.post(f"/api/replay/step?frame_index={i}")
    after_hook = client.get("/api/events").json()["count"]

    client.post("/api/replay/step?frame_index=4")
    assert client.get("/api/events").json()["count"] == after_hook


def test_stale_tracks_do_not_refire_after_dedup_expires(client):
    """A pair that has left the scene must not re-emit when its dedup window
    lapses — candidates are scoped to the current frame."""
    events = run_replay(client)
    pairs = [
        (e["participants"]["vehicle"]["track_id"], e["participants"]["vru"]["track_id"])
        for e in events["events"]
    ]
    assert len(pairs) == len(set(pairs)), f"a pair fired twice: {pairs}"


def test_perception_endpoint_assigns_zones_from_polygons(client):
    """AC-05: a bare detector with no zone field still gets zones."""
    r = client.post(
        "/api/perception",
        json={
            "camera_id": "test",
            "frame_index": 0,
            "observed_at": "",
            "observations": [
                {
                    "track_id": 1,
                    "class": "person",
                    "confidence": 0.8,
                    "bbox": [96, 168, 110, 202],
                    "observed_at": "",
                }
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["detections"][0]["zone"] == "conflict_zone"


def test_approach_credit_is_role_specific():
    """A pedestrian standing in the roadway must not satisfy a vehicle's
    approach precondition, and vice versa."""
    store = TrackStore()
    obs = PerceptionFrame.model_validate(
        {
            "camera_id": "c",
            "frame_index": 0,
            "observed_at": "",
            "observations": [
                {"track_id": 1, "class": "person", "confidence": 0.9,
                 "bbox": [0, 0, 1, 1], "zone": Zone.VEHICLE_TURN_APPROACH, "observed_at": ""},
                {"track_id": 2, "class": "car", "confidence": 0.9,
                 "bbox": [0, 0, 1, 1], "zone": Zone.VEHICLE_TURN_APPROACH, "observed_at": ""},
            ],
        }
    ).observations

    person = store.update(obs[0], 0)
    car = store.update(obs[1], 0)
    assert person.entered_approach is False
    assert car.entered_approach is True


def test_conflict_entry_records_first_entry_only():
    """A vehicle sitting in the zone entered once. Re-stamping every frame
    would drag ΔT to zero and manufacture CRITICALs out of stopped traffic."""
    store = TrackStore()
    for frame in (3, 4, 5):
        obs = PerceptionFrame.model_validate(
            {
                "camera_id": "c", "frame_index": frame, "observed_at": "",
                "observations": [
                    {"track_id": 7, "class": "car", "confidence": 0.9,
                     "bbox": [0, 0, 1, 1], "zone": Zone.CONFLICT_ZONE, "observed_at": ""}
                ],
            }
        ).observations[0]
        st = store.update(obs, frame)
    assert st.conflict_entry_frame == 3


@pytest.mark.parametrize("endpoint", ["/api/detections", "/api/replay/info"])
def test_ui_support_endpoints_respond(client, endpoint):
    assert client.get(endpoint).status_code == 200


def test_replay_info_states_the_observations_are_synthetic(client):
    """AC-13 / §18: the distinction between real inference and authored
    observations must be explicit, not implicit."""
    info = client.get("/api/replay/info").json()
    assert info["source"] == "synthetic observations"
    assert "not" in info["honesty"].lower()


def test_replay_flips_run_mode_so_the_badge_cannot_claim_live(client):
    """AC-13, regression. `cameras.mode` says which camera rung is selected and
    stays 'live' through a replay — so a replay driven from another tab or by
    curl used to leave replay events on screen under a LIVE badge. `run_mode`
    is the second, independent condition the UI requires before claiming LIVE.
    """
    assert client.get("/api/status").json()["run_mode"] == "live"

    client.post("/api/replay/step?frame_index=0")
    s = client.get("/api/status").json()
    assert s["run_mode"] == "replay"
    assert s["mode"] == "live", "camera rung is unchanged; only the run source differs"

    client.post("/api/run/reset")
    assert client.get("/api/status").json()["run_mode"] == "live"


def test_cooccupancy_requires_both_in_zone_right_now(client, engine):
    """§12 Variant C is present-tense. Two road users whose first entries
    coincided but who are no longer sharing the box must not fire."""
    if engine.temporal_mode.value != "cooccupancy":
        pytest.skip("only meaningful under Variant C")

    def frame(idx, veh_bbox, vru_bbox):
        return {
            "camera_id": "c", "frame_index": idx, "observed_at": "",
            "observations": [
                {"track_id": 1, "class": "car", "confidence": 0.9,
                 "bbox": veh_bbox, "observed_at": ""},
                {"track_id": 2, "class": "person", "confidence": 0.9,
                 "bbox": vru_bbox, "observed_at": ""},
            ],
        }

    client.post("/api/run/reset")
    # Both through their approach zones first.
    client.post("/api/perception", json=frame(0, [246, 96, 286, 128], [24, 176, 44, 208]))
    # Both in the crossing together -> fires.
    client.post("/api/perception", json=frame(1, [128, 150, 178, 188], [96, 168, 110, 202]))
    fired = client.get("/api/events").json()["count"]
    assert fired == 1

    # Vehicle leaves the box; the pair no longer co-occupies. Well past the
    # dedup window in scene time, so only the present-tense check can stop it.
    client.post("/api/perception", json=frame(9, [246, 96, 286, 128], [96, 168, 110, 202]))
    assert client.get("/api/events").json()["count"] == fired


def test_replay_events_are_labelled_demo_replay_in_the_json(client):
    """AC-13. The event JSON outlives the demo — a replay-produced event that
    records mode 'live' is a false record, not just a UI slip."""
    client.post("/api/run/reset")
    for i in range(4):
        client.post(f"/api/replay/step?frame_index={i}")

    event = client.get("/api/events").json()["events"][0]
    assert event["camera"]["mode"] == "demo_replay"

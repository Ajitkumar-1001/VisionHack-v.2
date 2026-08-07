"""PRD §21 scenarios 1-3. Core path, threshold correctness, no false positives.

Driven through POST /api/agent/event — the endpoint that reproduces the
decision logic without a camera.
"""

from __future__ import annotations

from tests.conftest import conflict


def test_scenario_1_critical_conflict_creates_one_event(client):
    """Both in conflict zone, Δ below the critical threshold -> critical."""
    r = client.post("/api/agent/event", json=conflict(delta_frames=0))
    assert r.status_code == 200
    body = r.json()

    assert body["decision"]["severity"] == "critical"
    assert body["event"] is not None
    assert body["agent_state"] == "ALERT_CREATED"

    assert client.get("/api/events").json()["count"] == 1


def test_scenario_2_warning_band(client):
    """Δ of one frame lands in the warning band, not critical."""
    body = client.post("/api/agent/event", json=conflict(delta_frames=1)).json()

    assert body["decision"]["severity"] == "warning"
    assert body["event"]["observation"]["temporal_gap_frames"] == 1


def test_scenario_3_vru_alone_creates_no_event(client):
    """VRU in the conflict zone, vehicle not -> no event. No false positives."""
    payload = conflict()
    payload["vehicle"]["conflict_entry"] = None

    body = client.post("/api/agent/event", json=payload).json()

    assert body["decision"] is None
    assert body["event"] is None
    assert client.get("/api/events").json()["count"] == 0


def test_beyond_threshold_creates_no_event(client):
    """Δ of two frames is outside the band entirely (§12)."""
    body = client.post("/api/agent/event", json=conflict(delta_frames=2)).json()

    assert body["decision"] is None
    assert "outside threshold" in body["reason"]


def test_approach_precondition_required(client):
    """A vehicle that never passed through its turn approach is not a conflict.

    This is the precondition §26 says to relax only as a degradation rung — so
    it must be genuinely enforced until then.
    """
    payload = conflict()
    payload["vehicle"]["entered_approach"] = False

    assert client.post("/api/agent/event", json=payload).json()["event"] is None


def test_event_carries_its_measurement_basis(client):
    """AC-15 / §7 rule 7: every number ships with how it was measured."""
    event = client.post("/api/agent/event", json=conflict(delta_frames=1)).json()["event"]

    assert event["camera"]["temporal_mode"] == "frames"
    assert event["camera"]["measured_fps"] is not None
    assert event["observation"]["measurement_basis"] == "observed zone-entry timestamps"
    # §12: the disclaimer is part of the artifact, not just the UI.
    assert "not a calibrated crash-risk probability" in event["disclaimer"].lower()

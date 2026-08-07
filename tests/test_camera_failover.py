"""PRD §21 scenario 5 + §18. A failed camera produces fallback behaviour."""

from __future__ import annotations

from app.cameras.manager import CameraManager


def test_scenario_5_failover_selects_backup(client):
    before = client.get("/api/status").json()
    assert before["mode"] == "live"

    switched = client.post("/api/camera/failover").json()

    assert switched["switched"] is True
    after = client.get("/api/status").json()
    assert after["camera"]["id"] != before["camera"]["id"]


def test_ladder_terminates_at_demo_replay():
    """§18: the ladder always ends somewhere demo-able. The replay rung is
    mandatory — judges warn a camera may go dark at 20:45."""
    m = CameraManager()
    for _ in range(len(m.ladder) + 2):
        m.switch_camera()

    assert m.current_id == "demo_replay"
    assert m.is_replay


def test_mode_label_tracks_the_ladder(client):
    """AC-13: never present prerecorded footage as live. The label is derived
    from ladder position, so it cannot drift out of sync by hand."""
    m = CameraManager()
    assert m.mode == "live"

    while not m.is_replay:
        m.switch_camera()

    assert m.mode == "demo_replay"


def test_failover_at_the_last_rung_does_not_crash():
    m = CameraManager()
    while not m.is_replay:
        m.switch_camera()

    result = m.switch_camera()
    assert result["switched"] is False
    assert m.current_id == "demo_replay"


def test_reset_returns_to_primary(client):
    """AC-14: the demo runs repeatedly. Failover is one-way, so without a reset
    the second rehearsal starts on a backup camera."""
    primary = client.get("/api/status").json()["camera"]["id"]
    client.post("/api/camera/failover")
    assert client.get("/api/status").json()["camera"]["id"] != primary

    client.post("/api/camera/reset")

    after = client.get("/api/status").json()
    assert after["camera"]["id"] == primary
    assert after["camera"]["status"] == "healthy"
    assert after["mode"] == "live"

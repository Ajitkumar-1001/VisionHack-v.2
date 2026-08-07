"""PRD §21 scenario 4 + §15. Same pair sent 5x produces 1 event, not 5."""

from __future__ import annotations

from app.agent.dedup import Dedup
from tests.conftest import conflict


def test_scenario_4_five_identical_conflicts_emit_one_event(client):
    for _ in range(5):
        client.post("/api/agent/event", json=conflict(delta_frames=0))

    assert client.get("/api/events").json()["count"] == 1


def test_suppressed_repeat_reports_honestly(client):
    """A suppressed repeat is still a real conflict — say so, don't pretend
    the criterion failed."""
    client.post("/api/agent/event", json=conflict(delta_frames=0))
    body = client.post("/api/agent/event", json=conflict(delta_frames=0)).json()

    assert body["event"] is None
    assert body["reason"] == "duplicate suppressed"
    assert body["severity_if_emitted"] == "critical"


def test_pair_key_expires_after_ttl():
    d = Dedup(ttl_s=5.0, zone_floor_s=5.0)
    assert d.should_suppress(34, 51, "conflict_zone", now=100.0) is False
    assert d.should_suppress(34, 51, "conflict_zone", now=102.0) is True
    assert d.should_suppress(34, 51, "conflict_zone", now=106.0) is False


def test_zone_floor_catches_thrashing_track_ids():
    """§15: at low fps, IDs thrash and the same real interaction reappears
    under a NEW pair key. The per-zone floor is what catches that."""
    d = Dedup(ttl_s=5.0, zone_floor_s=5.0)

    assert d.should_suppress(34, 51, "conflict_zone", now=100.0) is False
    # Different IDs, same interaction, same zone, one second later.
    assert d.should_suppress(35, 52, "conflict_zone", now=101.0) is True


def test_distinct_zones_are_independent():
    d = Dedup(ttl_s=5.0, zone_floor_s=5.0)
    assert d.should_suppress(34, 51, "conflict_zone", now=100.0) is False
    assert d.should_suppress(70, 80, "other_zone", now=100.5) is False

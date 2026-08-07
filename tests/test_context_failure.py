"""PRD §21 scenario 6. Optional enrichment failing must never stop detection.

This encodes the failure philosophy (§21):

    CRITICAL          NON-CRITICAL
    Cloud Run         NYC historical data
    Roboflow          Fancy UI
    Camera/Replay     Event persistence

"NYC API failed" surfaces as "Historical context unavailable", never a 500.
"""

from __future__ import annotations

from app.context.intersection import get_intersection_context
from tests.conftest import conflict


def test_scenario_6_missing_context_does_not_stop_detection(client, engine):
    """Strip the context block, then confirm a conflict still fires."""
    cam = engine.cameras.current_camera()
    saved = cam.pop("context", None)
    try:
        body = client.post("/api/agent/event", json=conflict(delta_frames=0)).json()

        # Detection continues.
        assert body["decision"]["severity"] == "critical"
        # And degrades honestly rather than fabricating numbers.
        assert body["event"]["context"]["status"] == "unavailable"
    finally:
        if saved is not None:
            cam["context"] = saved


def test_context_endpoint_degrades_not_500(client, engine):
    cam = engine.cameras.current_camera()
    saved = cam.pop("context", None)
    try:
        r = client.get("/api/context")
        assert r.status_code == 200
        assert r.json()["status"] == "unavailable"
    finally:
        if saved is not None:
            cam["context"] = saved


def test_malformed_context_is_swallowed():
    """An enrichment bug must not take down detection."""
    assert get_intersection_context(None).status == "unavailable"
    assert get_intersection_context({}).status == "unavailable"
    assert get_intersection_context({"context": {}}).status == "unavailable"


def test_health_is_independent_of_context(client, engine):
    """§20: Open Data availability must not affect /health."""
    cam = engine.cameras.current_camera()
    saved = cam.pop("context", None)
    try:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"service": "righthook-nyc", "status": "healthy"}
    finally:
        if saved is not None:
            cam["context"] = saved


def test_context_never_modifies_severity(client, engine):
    """§17: history gives context; it never modifies an event's severity."""
    with_ctx = client.post("/api/agent/event", json=conflict(delta_frames=1)).json()
    engine.dedup.reset()

    cam = engine.cameras.current_camera()
    saved = cam.pop("context", None)
    try:
        without_ctx = client.post(
            "/api/agent/event", json=conflict(delta_frames=1)
        ).json()
    finally:
        if saved is not None:
            cam["context"] = saved

    assert with_ctx["decision"]["severity"] == without_ctx["decision"]["severity"]

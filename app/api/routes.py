"""The eight endpoints of PRD §20. Keep it tiny.

Scaffold state: every handler returns an honest placeholder rather than raising.
A 500 from /api/status would make the static UI look broken at the gate, and
§21's failure philosophy is that optional layers degrade instead of failing.

`POST /api/agent/event` is the highest-value endpoint for judging (§20) — it
lets anyone reproduce the decision logic without a camera, and it is the entry
point both pytest (§21) and Veris drive.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter()

# Replaced by config/cameras.json once the §6 probe lands (17:45–18:00).
_PENDING_PROBE = "pending_probe"


@router.get("/status")
def status() -> dict[str, Any]:
    """Camera, mode, agent state, measured fps, temporal mode. §20, AC-15."""
    return {
        "camera": {"id": None, "status": "offline"},
        "mode": "demo_replay",
        "agent_state": "NORMAL",
        "measured_fps": None,
        "temporal_mode": _PENDING_PROBE,
    }


@router.get("/events")
def list_events() -> dict[str, Any]:
    return {"events": [], "count": 0}


@router.get("/events/{event_id}")
def get_event(event_id: str) -> dict[str, Any]:
    return {"event_id": event_id, "found": False}


@router.post("/perception")
def perception(payload: dict[str, Any]) -> dict[str, Any]:
    """Roboflow structured output enters here. §9, §20."""
    # TODO(§11): hand observations to the conflict engine.
    return {"accepted": False, "reason": "engine not implemented"}


@router.post("/agent/event")
def agent_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Synthetic observation -> decision. The pytest/Veris entry point. §21."""
    # TODO(§11-13): run the conflict criterion, severity map and dedup.
    return {"decision": None, "reason": "engine not implemented"}


@router.get("/context")
def context() -> dict[str, Any]:
    """§17. Never fatal — a missing context block is a degraded event, not a 500."""
    return {"status": "unavailable", "reason": "context not loaded"}


@router.post("/camera/failover")
def camera_failover() -> dict[str, Any]:
    """Force failover. Drives §21 scenario 5."""
    # TODO(§18): advance the fallback ladder via switch_camera().
    return {"switched": False, "reason": "camera manager not implemented"}

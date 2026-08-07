"""The eight endpoints of PRD §20. Keep it tiny.

Thin on purpose: every handler translates Engine output into JSON. No conflict
logic lives here.

`POST /api/agent/event` is the highest-value endpoint for judging (§20) — it
lets anyone reproduce the decision logic without a camera, and it is the entry
point both pytest (§21) and Veris drive.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.agent.engine import AgentEventRequest, Engine
from app.context.intersection import get_intersection_context
from app.models.perception import PerceptionFrame
from app.replay import load_sequence

router = APIRouter()

# One engine per process. Holds configuration and the in-memory event buffer,
# not per-request state (§19: stateless across instances, nothing on disk).
_engine = Engine()


@router.get("/status")
def status() -> dict[str, Any]:
    """Camera, mode, agent state, measured fps, temporal mode. §20, AC-15."""
    cam = _engine.cameras.current_camera()
    return {
        "camera": {
            "id": _engine.cameras.current_id,
            "name": cam.get("name"),
            "intersection": cam.get("intersection"),
            "image_url": cam.get("image_url"),
            "status": _engine.cameras.status,
        },
        # AC-13: both derived, never hand-set. `mode` is which camera rung is
        # selected; `run_mode` is where the pixels and events on screen came
        # from. The UI may only show LIVE when both agree.
        "mode": _engine.cameras.mode,
        "run_mode": _engine.run_mode,
        "agent_state": _engine.state,
        # AC-15: the measured basis travels with every status poll.
        "measured_fps": _engine.measured_fps,
        "temporal_mode": _engine.temporal_mode,
        "severity": _engine.last_severity,
        "delta_display": _engine.last_delta_display,
        "event_count": len(_engine.events),
    }


@router.get("/events")
def list_events() -> dict[str, Any]:
    events = [e.model_dump(by_alias=True, exclude_none=True) for e in _engine.events]
    return {"events": events, "count": len(events)}


@router.get("/events/{event_id}")
def get_event(event_id: str) -> dict[str, Any]:
    for e in _engine.events:
        if e.event_id == event_id:
            return e.model_dump(by_alias=True, exclude_none=True)
    return {"event_id": event_id, "found": False}


@router.post("/perception")
def perception(frame: PerceptionFrame) -> dict[str, Any]:
    """Roboflow structured output enters here. §9, §20.

    Assigns zones from the camera polygons, updates track state, and hands
    each vehicle x VRU pair to the conflict criterion.
    """
    return _engine.ingest_frame(frame)


@router.get("/detections")
def detections() -> dict[str, Any]:
    """Last frame's boxes, for the UI overlay. §22."""
    cam = _engine.cameras.current_camera()
    return {
        "frame_index": _engine.frame_index,
        "frame_size": cam.get("frame_size", [352, 240]),
        "zones": cam.get("zones", {}),
        "detections": _engine.last_detections,
    }


@router.post("/replay/step")
def replay_step(frame_index: int = 0) -> dict[str, Any]:
    """Feed one frame of the §18 replay sequence through the real pipeline.

    Prerecorded INPUT, not prerecorded inference — zone assignment, tracking,
    the conflict criterion, severity and dedup all run for real. The
    observations themselves are synthetic and the UI says so; see
    /api/replay/info.
    """
    seq = load_sequence()
    frames = seq["frames"]
    if frame_index == 0:
        _engine.reset_run()
    _engine.run_mode = "replay"
    if frame_index >= len(frames):
        return {"done": True, "frame_index": frame_index, "total": len(frames)}

    raw = frames[frame_index]
    result = _engine.ingest_frame(
        PerceptionFrame.model_validate(
            {
                "camera_id": seq["camera_id"],
                "frame_index": raw["frame_index"],
                "observed_at": "",
                "observations": [
                    {**o, "observed_at": ""} for o in raw["observations"]
                ],
            }
        )
    )
    result["note"] = raw.get("note")
    result["total"] = len(frames)
    result["done"] = frame_index >= len(frames) - 1
    return result


@router.get("/replay/info")
def replay_info() -> dict[str, Any]:
    """What the replay is and is not. Surfaced in the UI so the distinction
    between real inference and authored observations is never implicit."""
    seq = load_sequence()
    return {
        "frames": len(seq["frames"]),
        "source": "synthetic observations",
        "honesty": seq["_honesty"],
    }


@router.post("/run/reset")
def run_reset() -> dict[str, Any]:
    """Clear events, tracks and dedup so the demo repeats (AC-14)."""
    _engine.reset_run()
    _engine.cameras.reset()
    return {"reset": True}


@router.post("/agent/event")
def agent_event(req: AgentEventRequest) -> dict[str, Any]:
    """Synthetic observation -> decision. The pytest/Veris entry point. §21."""
    return _engine.evaluate(req)


@router.get("/context")
def context() -> dict[str, Any]:
    """§17. Never fatal — a missing context block degrades, it does not 500."""
    cam = _engine.cameras.current_camera()
    ctx = get_intersection_context(cam)
    return ctx.model_dump()


@router.post("/camera/failover")
def camera_failover() -> dict[str, Any]:
    """Force failover. Drives §21 scenario 5. §14 switch_camera()."""
    return _engine.cameras.switch_camera()


@router.post("/camera/reset")
def camera_reset() -> dict[str, Any]:
    """Climb back to the primary. AC-14: the demo must run repeatedly without
    manual code changes, and failover is a one-way ladder — without this, a
    single scenario-5 demo strands the process on a backup until redeploy."""
    _engine.cameras.reset()
    return {
        "camera_id": _engine.cameras.current_id,
        "mode": _engine.cameras.mode,
        "status": _engine.cameras.status,
    }

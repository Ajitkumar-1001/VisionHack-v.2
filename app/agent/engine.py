"""The conflict algorithm — DECIDE. PRD §11.

Deliberately, embarrassingly understandable:

    if vru enters vru_approach:              remember vru track
    if vehicle enters vehicle_turn_approach: remember vehicle track
    if vru enters conflict_zone:             record vru_conflict_time
    if vehicle enters conflict_zone:         record vehicle_conflict_time

    delta = abs(vru_conflict_time - vehicle_conflict_time)

ΔT is the gap between two OBSERVED zone-entry timestamps — never a predicted
time-to-arrival. That single choice removes any need for homography,
pixel-to-metre calibration, a velocity model or a ground plane. We report
something we actually watched happen.

No LLM in the core path (§7 rule 2). No weighted risk formula (§7 rule 3).
"""

from __future__ import annotations

import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.agent import severity as sev
from app.agent.dedup import Dedup
from app.agent.state import AgentState, next_state
from app.cameras.manager import CameraManager
from app.context.intersection import get_intersection_context
from app.models.perception import PerceptionFrame
from app.vision.tracks import TrackStore
from app.vision.zones import zone_for
from app.models.event import (
    CameraBlock,
    Decision,
    Location,
    Observation,
    Participant,
    Participants,
    SafetyEvent,
    TemporalMode,
)

# §19: in-memory only. Nothing is written to durable storage (§24 privacy).
EVENT_BUFFER = 50


class ParticipantInput(BaseModel):
    """One road user's observed zone history for a single interaction."""

    track_id: int
    cls: str = Field(validation_alias="class", serialization_alias="class")
    # Did it pass through its own approach zone before the conflict zone?
    entered_approach: bool = True
    # When it entered the conflict zone. Seconds under Variant A, frame index
    # under Variant B/C. None means it never entered.
    conflict_entry: float | None = None


class AgentEventRequest(BaseModel):
    """Synthetic observation -> decision. The pytest/Veris entry point (§20)."""

    vehicle: ParticipantInput
    vru: ParticipantInput
    # Optional override so tests can pin the mode independently of config.
    temporal_mode: TemporalMode | None = None


class Engine:
    def __init__(self, cameras: CameraManager | None = None):
        self.cameras = cameras or CameraManager()
        self.dedup = Dedup()
        self.events: deque[SafetyEvent] = deque(maxlen=EVENT_BUFFER)
        self.state = AgentState.NORMAL
        self.last_delta_display: str | None = None
        self.last_severity: str | None = None
        self.tracks = TrackStore()
        self.frame_index = 0
        self.last_detections: list[dict[str, Any]] = []
        # AC-13. Whether what is currently ON SCREEN came from the live feed or
        # from the replay sequence. Distinct from cameras.mode, which describes
        # which camera rung is selected. Both must say "live" before the badge
        # may claim it — otherwise replay-produced events sit under a LIVE
        # label, which is the one thing §18 forbids outright.
        self.run_mode = "live"

    def ingest_frame(self, frame: PerceptionFrame) -> dict[str, Any]:
        """One frame of Roboflow output -> zone assignment -> conflict check.

        §9-§11. This is the only path between perception and the decision
        engine, and it adds no conflict logic of its own — it assigns zones,
        updates track state, then hands each vehicle x VRU pair to evaluate().
        """
        cam = self.cameras.current_camera()
        zones = cam.get("zones", {})
        self.frame_index = frame.frame_index

        seen = []
        for obs in frame.observations:
            # Trust a zone the workflow already assigned; otherwise compute it
            # from the polygons so the engine works with a bare detector too.
            if obs.zone is None:
                obs.zone = zone_for(obs.bbox, zones)
            st = self.tracks.update(obs, frame.frame_index)
            seen.append(
                {
                    "track_id": obs.track_id,
                    "class": obs.cls,
                    "bbox": obs.bbox,
                    "zone": obs.zone.value if obs.zone else None,
                    "entered_approach": st.entered_approach,
                }
            )
        self.last_detections = seen
        self.tracks.evict(frame.frame_index)

        vehicles, vrus = self.tracks.candidates(frame.frame_index)

        # §12 Variant C asks a present-tense question — are both IN the conflict
        # zone in THIS frame — not whether their first entries happened to
        # coincide. Answering it from entry history would fire on two road users
        # who merely arrived on the same frame and have since separated, and
        # would miss the pair actually sharing the box right now.
        cooccupancy = self.temporal_mode is TemporalMode.COOCCUPANCY
        if cooccupancy:
            in_zone = lambda t: t.last_zone == "conflict_zone"
            vehicles = [t for t in vehicles if in_zone(t)]
            vrus = [t for t in vrus if in_zone(t)]

        results = []
        for v in vehicles:
            for u in vrus:
                req = AgentEventRequest(
                    vehicle=ParticipantInput.model_validate(
                        {
                            "track_id": v.track_id,
                            "class": v.cls,
                            "entered_approach": v.entered_approach,
                            "conflict_entry": frame.frame_index
                            if cooccupancy
                            else v.conflict_entry_frame,
                        }
                    ),
                    vru=ParticipantInput.model_validate(
                        {
                            "track_id": u.track_id,
                            "class": u.cls,
                            "entered_approach": u.entered_approach,
                            "conflict_entry": frame.frame_index
                            if cooccupancy
                            else u.conflict_entry_frame,
                        }
                    ),
                )
                # Dedup must run on SCENE time, not wall time. Frames are
                # ~2s apart in the world but arrive in milliseconds during a
                # replay, which would let the §15 zone floor suppress a
                # genuinely separate interaction minutes later in scene terms.
                fps = self.measured_fps or 0.5
                out = self.evaluate(req, now=frame.frame_index / fps)
                if out.get("event"):
                    results.append(out)

        # WATCH is a UI/state condition, not a ΔT band (§12): both roles are
        # approaching and neither has reached the conflict zone yet.
        if not results and self.state is not AgentState.ALERT_CREATED:
            approaching_v = any(
                t.entered_approach and t.conflict_entry_frame is None
                for t in self.tracks.tracks.values()
                if t.is_vehicle
            )
            approaching_u = any(
                t.entered_approach and t.conflict_entry_frame is None
                for t in self.tracks.tracks.values()
                if not t.is_vehicle
            )
            self.state = (
                AgentState.WATCH if (approaching_v and approaching_u) else AgentState.NORMAL
            )

        return {
            "frame_index": frame.frame_index,
            "detections": seen,
            "events_created": len(results),
            "agent_state": self.state,
        }

    def reset_run(self) -> None:
        """Clear per-run state so the demo repeats without a redeploy (AC-14)."""
        self.tracks.clear()
        self.dedup.reset()
        self.events.clear()
        self.state = AgentState.NORMAL
        self.last_delta_display = None
        self.last_severity = None
        self.last_detections = []
        self.frame_index = 0
        self.run_mode = "live"

    @property
    def temporal_mode(self) -> TemporalMode:
        return TemporalMode(self.cameras.config.get("temporal_mode", "frames"))

    @property
    def measured_fps(self) -> float | None:
        return self.cameras.config.get("measured_fps")

    def evaluate(self, req: AgentEventRequest, now: float | None = None) -> dict[str, Any]:
        """Run the §11 criterion. Returns the decision and the event, if any."""
        mode = req.temporal_mode or self.temporal_mode
        vehicle, vru = req.vehicle, req.vru

        both_approaching = vehicle.entered_approach and vru.entered_approach
        both_in_conflict = (
            vehicle.conflict_entry is not None and vru.conflict_entry is not None
        )

        # §11 event criterion. Every clause is something we observed.
        if not (both_approaching and both_in_conflict):
            self.state = next_state(both_approaching, both_in_conflict, False)
            return self._no_event("criterion not met")

        delta = abs(vehicle.conflict_entry - vru.conflict_entry)
        severity = sev.severity_for(delta, mode)
        self.last_delta_display = sev.display(delta, mode, self.measured_fps)

        if severity is None:
            self.state = next_state(both_approaching, both_in_conflict, False)
            return self._no_event(f"outside threshold ({self.last_delta_display})")

        self.state = AgentState.CONFLICT

        # §15. Dedup runs AFTER the criterion so a suppressed repeat still
        # reports honestly that it was a real conflict we chose not to re-emit.
        if self.dedup.should_suppress(
            vehicle.track_id, vru.track_id, "conflict_zone", now
        ):
            return self._no_event("duplicate suppressed", severity=severity)

        event = self._build_event(vehicle, vru, delta, severity, mode)
        self.events.appendleft(event)
        self.state = AgentState.ALERT_CREATED
        self.last_severity = severity
        return {
            "decision": {"severity": severity, "action": "create_safety_event"},
            # §16: fields the active variant cannot measure are OMITTED, not
            # emitted as null. A null temporal_gap_seconds reads like a failed
            # measurement rather than one we never claimed to make.
            "event": event.model_dump(by_alias=True, exclude_none=True),
            "agent_state": self.state,
            "delta_display": self.last_delta_display,
        }

    def _no_event(self, reason: str, severity: Any = None) -> dict[str, Any]:
        return {
            "decision": None,
            "event": None,
            "reason": reason,
            "severity_if_emitted": severity,
            "agent_state": self.state,
            "delta_display": self.last_delta_display,
        }

    def _build_event(
        self,
        vehicle: ParticipantInput,
        vru: ParticipantInput,
        delta: float,
        severity: Any,
        mode: TemporalMode,
    ) -> SafetyEvent:
        cam = self.cameras.current_camera()

        # §16: under Variant A the gap is exact seconds; under B it is whole
        # frames plus a labelled estimate; under C neither is claimable.
        obs = Observation(
            vehicle_entered_turn_zone=vehicle.entered_approach,
            vru_entered_approach_zone=vru.entered_approach,
            both_entered_conflict_zone=True,
        )
        if mode is TemporalMode.SECONDS:
            obs.temporal_gap_seconds = round(delta, 2)
        elif mode is TemporalMode.FRAMES:
            obs.temporal_gap_frames = round(delta)
            if self.measured_fps:
                obs.temporal_gap_seconds_estimate = round(
                    round(delta) / self.measured_fps, 2
                )
        else:
            obs.same_frame_cooccupancy = True

        return SafetyEvent(
            event_id=f"rh_{uuid.uuid4().hex[:10]}",
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            camera=CameraBlock(
                # AC-13 again, and here it matters most: the event JSON is the
                # artifact that outlives the demo. A replay-produced event that
                # says "live" is a false record, so run_mode overrides the
                # camera rung whenever a replay produced the observation.
                id=str(self.cameras.current_id),
                mode="demo_replay" if self.run_mode == "replay" else self.cameras.mode,
                measured_fps=self.measured_fps,
                temporal_mode=mode,
            ),
            participants=Participants(
                vehicle=Participant.model_validate(
                    {"track_id": vehicle.track_id, "class": vehicle.cls}
                ),
                vru=Participant.model_validate(
                    {"track_id": vru.track_id, "class": vru.cls}
                ),
            ),
            observation=obs,
            decision=Decision(severity=severity),
            location=Location(
                intersection=cam.get("intersection", "unknown"),
                latitude=cam.get("latitude") or 0.0,
                longitude=cam.get("longitude") or 0.0,
            ),
            # §17: attached alongside the decision, never fed into it.
            context=get_intersection_context(cam),
        )

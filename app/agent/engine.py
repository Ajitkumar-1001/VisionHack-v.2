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
                id=str(self.cameras.current_id),
                mode=self.cameras.mode,
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

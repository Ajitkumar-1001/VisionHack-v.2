"""The canonical safety event. PRD §16.

This JSON is one of the most valuable demo assets in the build — it is what
proves RightHook is a perception system rather than a visualization. Every
later module writes against these models, so the shape is fixed here first.

The three §6 variants emit the *identical* schema. Only the `observation` block
and the severity mapping differ:

    Variant A (seconds)     temporal_gap_seconds exact, no _frames
    Variant B (frames)      temporal_gap_frames + _seconds_estimate
    Variant C (cooccupancy) neither; same_frame_cooccupancy: true
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

# §12 — must appear in the UI and the README. RightHook never claims a crash
# probability; these thresholds are hackathon heuristics.
DISCLAIMER = (
    "Heuristic conflict detection. Not a calibrated crash-risk probability."
)


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    CONFLICT = "conflict"  # Variant C only


class TemporalMode(StrEnum):
    SECONDS = "seconds"
    FRAMES = "frames"
    COOCCUPANCY = "cooccupancy"


class CameraBlock(BaseModel):
    id: str
    mode: Literal["live", "demo_replay"]
    # AC-15: measured frame rate and temporal mode travel with every event, not
    # just the UI. State your units (§7 rule 7).
    measured_fps: float | None = None
    temporal_mode: TemporalMode


class Participant(BaseModel):
    # Ephemeral and scoped to a single camera session. NOT an identity (§24).
    track_id: int
    cls: str = Field(serialization_alias="class", validation_alias="class")


class Participants(BaseModel):
    vehicle: Participant
    vru: Participant


class Observation(BaseModel):
    """What was actually watched. Never a predicted time-to-arrival (§11)."""

    vehicle_entered_turn_zone: bool
    vru_entered_approach_zone: bool
    both_entered_conflict_zone: bool
    temporal_gap_frames: int | None = None
    temporal_gap_seconds: float | None = None
    temporal_gap_seconds_estimate: float | None = None
    same_frame_cooccupancy: bool | None = None
    measurement_basis: str = "observed zone-entry timestamps"


class Decision(BaseModel):
    severity: Severity
    action: Literal["create_safety_event"] = "create_safety_event"


class Location(BaseModel):
    intersection: str
    latitude: float
    longitude: float


class Context(BaseModel):
    """§17. History gives context; it never modifies an event's severity."""

    status: Literal["available", "unavailable"]
    bike_infrastructure: bool | None = None
    facility_type: str | None = None
    historical_cyclist_collisions: int | None = None
    # ADR-007: truck-route designation is invisible in the frame and modulates
    # the truck/bus classes the detector already outputs.
    on_truck_route: bool | None = None
    truck_route_streets: list[str] | None = None
    # Gate 6: provenance travels with the numbers, or they are just numbers.
    source: str | None = None
    retrieved_at: str | None = None


class SafetyEvent(BaseModel):
    event_id: str
    event_type: Literal["potential_turning_conflict"] = "potential_turning_conflict"
    timestamp: str

    camera: CameraBlock
    participants: Participants
    observation: Observation
    decision: Decision
    location: Location
    context: Context

    disclaimer: str = DISCLAIMER

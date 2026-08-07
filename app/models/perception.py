"""Roboflow structured output — the boundary into the engine. PRD §9.

Roboflow owns exactly one question: what objects exist, where are they, and
which tracked object is which. Everything downstream consumes TrackObservation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

# §9 — filter hard at the workflow level. Do not detect twenty classes.
VEHICLE_CLASSES = frozenset({"car", "truck", "bus", "motorcycle"})
# Both VRU classes are P0. `bicycle` carries the narrative (the right hook);
# `person` carries the live firing rate and is what fires on stage.
VRU_CLASSES = frozenset({"bicycle", "person"})


class Zone(StrEnum):
    """The three manually-calibrated polygons per camera. §10."""

    VRU_APPROACH = "vru_approach"
    VEHICLE_TURN_APPROACH = "vehicle_turn_approach"
    CONFLICT_ZONE = "conflict_zone"


class TrackObservation(BaseModel):
    """One tracked object in one frame."""

    track_id: int
    cls: str = Field(serialization_alias="class", validation_alias="class")
    confidence: float
    bbox: list[int]  # [x1, y1, x2, y2]
    zone: Zone | None = None
    observed_at: str

    @property
    def is_vehicle(self) -> bool:
        return self.cls in VEHICLE_CLASSES

    @property
    def is_vru(self) -> bool:
        return self.cls in VRU_CLASSES


class PerceptionFrame(BaseModel):
    """A frame's worth of detections, plus the frame index Variant B counts."""

    camera_id: str
    frame_index: int
    observed_at: str
    observations: list[TrackObservation] = []

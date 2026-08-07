"""Track lifecycle and zone-entry bookkeeping. PRD §11.

Holds, per track_id, the only two facts the conflict criterion needs:

    1. did it pass through its own approach zone?
    2. at which frame index did it FIRST enter the conflict zone?

That is the whole model. No velocity, no trajectory, no prediction — ΔT is the
gap between two observed entries, so nothing else is required.

"First entry" is deliberate: a vehicle sitting in the conflict zone for six
frames entered once. Re-stamping every frame would drag ΔT toward zero and
manufacture CRITICAL severities out of stationary traffic.

Under Variant B/C, track IDs thrash at 0.5 fps. TTL is short and ID continuity
is best-effort; AC-04 is explicitly waived under Variant C.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.perception import TrackObservation, Zone

# At ~0.5 fps this is ~10 frames — long enough to bridge a missed detection,
# short enough that a stale ID cannot pair with a fresh one minutes later.
DEFAULT_TTL_FRAMES = 10


@dataclass
class TrackState:
    track_id: int
    cls: str
    is_vehicle: bool
    entered_approach: bool = False
    conflict_entry_frame: int | None = None
    last_seen_frame: int = 0
    # Where it is RIGHT NOW, as distinct from where it has ever been. Variant C
    # asks a present-tense question and cannot be answered from history.
    last_zone: str | None = None
    zones_seen: list[str] = field(default_factory=list)


class TrackStore:
    """Per-camera, in-memory. Cleared on camera switch — track IDs are scoped
    to a single camera session and are not identities (§24)."""

    def __init__(self, ttl_frames: int = DEFAULT_TTL_FRAMES):
        self.ttl_frames = ttl_frames
        self.tracks: dict[int, TrackState] = {}

    def update(self, obs: TrackObservation, frame_index: int) -> TrackState:
        st = self.tracks.get(obs.track_id)
        if st is None:
            st = TrackState(
                track_id=obs.track_id, cls=obs.cls, is_vehicle=obs.is_vehicle
            )
            self.tracks[obs.track_id] = st

        st.last_seen_frame = frame_index
        st.last_zone = obs.zone.value if obs.zone else None
        if obs.zone is None:
            return st

        if obs.zone.value not in st.zones_seen:
            st.zones_seen.append(obs.zone.value)

        # The approach precondition is per-role: a vehicle must have been seen
        # in the vehicle turn approach, a VRU in the VRU approach. Crediting
        # either zone to either role would let a pedestrian on the roadway
        # satisfy the vehicle's precondition.
        expected = Zone.VEHICLE_TURN_APPROACH if st.is_vehicle else Zone.VRU_APPROACH
        if obs.zone is expected:
            st.entered_approach = True

        if obs.zone is Zone.CONFLICT_ZONE and st.conflict_entry_frame is None:
            st.conflict_entry_frame = frame_index

        return st

    def evict(self, frame_index: int) -> None:
        self.tracks = {
            tid: st
            for tid, st in self.tracks.items()
            if frame_index - st.last_seen_frame <= self.ttl_frames
        }

    def candidates(self, frame_index: int) -> tuple[list[TrackState], list[TrackState]]:
        """Tracks in the conflict zone AND observed in the current frame.

        The current-frame requirement is load-bearing. Without it, a pair that
        already fired lingers in the store for the TTL and re-emits the moment
        the dedup window expires — reporting a conflict between two road users
        who left the scene several frames ago.
        """
        ready = [
            t
            for t in self.tracks.values()
            if t.conflict_entry_frame is not None and t.last_seen_frame == frame_index
        ]
        return (
            [t for t in ready if t.is_vehicle],
            [t for t in ready if not t.is_vehicle],
        )

    def clear(self) -> None:
        self.tracks.clear()

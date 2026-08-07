"""Event deduplication. PRD §15.

ByteTrack keeps the same participants visible across many frames, so without
dedup one real interaction emits an alert on every frame:

    frame 1 → ALERT   frame 2 → ALERT   frame 3 → ALERT   ← bad

Two layers, because one is not enough at low frame rates:

1. Pair key `vehicle_track_id:vru_track_id` with a TTL.
2. A per-conflict-zone floor. Under Variant B/C, track IDs thrash — the same
   real-world interaction reappears under a *new* pair key and slips past
   layer 1. So: no more than one event per zone per window, regardless of key.
"""

from __future__ import annotations

import time

# §15: TTL 5-10s. Variant B/C sit at the short end because IDs are unstable.
DEFAULT_TTL_S = 5.0


class Dedup:
    """In-memory suppression window. Per-process, like the event store (§19)."""

    def __init__(self, ttl_s: float = DEFAULT_TTL_S, zone_floor_s: float = DEFAULT_TTL_S):
        self.ttl_s = ttl_s
        self.zone_floor_s = zone_floor_s
        self._pairs: dict[str, float] = {}
        self._zones: dict[str, float] = {}

    def _now(self, now: float | None) -> float:
        return time.monotonic() if now is None else now

    def should_suppress(
        self, vehicle_track_id: int, vru_track_id: int, zone: str, now: float | None = None
    ) -> bool:
        """True if this conflict is a repeat of one already emitted."""
        t = self._now(now)
        self._evict(t)

        key = f"{vehicle_track_id}:{vru_track_id}"
        if key in self._pairs or zone in self._zones:
            return True

        self._pairs[key] = t
        self._zones[zone] = t
        return False

    def _evict(self, t: float) -> None:
        self._pairs = {k: v for k, v in self._pairs.items() if t - v < self.ttl_s}
        self._zones = {k: v for k, v in self._zones.items() if t - v < self.zone_floor_s}

    def reset(self) -> None:
        self._pairs.clear()
        self._zones.clear()

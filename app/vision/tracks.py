"""Track lifecycle and zone-entry bookkeeping. PRD §11.

Holds, per track_id: which approach zone it passed through and the timestamp
(and frame index) at which it first entered the conflict zone. That is all the
conflict criterion needs — no velocity model, no homography, no ground plane.

Under Variant B/C, track IDs thrash at low fps. Keep TTLs short and treat ID
continuity as best-effort (AC-04 is explicitly waived under Variant C).
"""

from __future__ import annotations

# TODO(§11): TrackState dataclass + a store keyed on track_id with TTL expiry.

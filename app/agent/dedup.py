"""Event deduplication. PRD §15.

ByteTrack keeps the same participants visible across many frames, so without
dedup one interaction emits an alert every frame.

    event_key = f"{vehicle_track_id}:{vru_track_id}"   # TTL 5-10s

Under Variant B/C use a shorter TTL (5s) AND key on the zone-entry epoch:
unstable track IDs at low fps produce a *new* key for the same real-world
interaction. If IDs thrash, add a secondary suppression — no more than one
event per conflict zone per 5 seconds regardless of key.
"""

from __future__ import annotations

# TODO(§15): TTL cache + the secondary per-zone suppression. Scenario 4 (§21)
# sends the same pair 5x and expects exactly 1 event.

"""NYC DOT traffic camera feed. PRD §5.

    All cameras   GET https://webcams.nyctmc.org/api/cameras
    Single still  GET https://webcams.nyctmc.org/api/cameras/{id}/image

Gotcha: `isOnline` is the STRING "true", not a boolean.
Be polite: one poll every 2s per camera, no parallel hammering.
"""

from __future__ import annotations

CAMERA_LIST_URL = "https://webcams.nyctmc.org/api/cameras"
POLL_INTERVAL_S = 2.0

# TODO(§5): list_online() and fetch_frame(camera_id) -> JPEG bytes.

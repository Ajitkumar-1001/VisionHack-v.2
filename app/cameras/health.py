"""Camera health check. PRD §18.

    {"camera_id": "...", "status": "healthy", "mode": "live", "last_frame_at": "..."}

Statuses: healthy | degraded | offline | fallback
"""

from __future__ import annotations

from enum import StrEnum


class CameraStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    FALLBACK = "fallback"


# TODO(§18): staleness check on last_frame_at -> CameraStatus.

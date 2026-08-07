"""NYC Open Data context — precomputed, not queried live. PRD §17.

The numbers were looked up once for the chosen intersection and pasted into
config/cameras.json. 15 minutes instead of 90; AC-11 still passes.

Two rules this module exists to enforce:

1. **Failure is non-fatal.** Any error returns status="unavailable". Never fail
   live safety detection because optional enrichment is down (§21 scenario 6).
   A dead source surfaces as "Historical context unavailable", never as a 500.
2. **History never modifies severity.** This returns a Context block that is
   attached *alongside* a decision, never fed into it (§17).
"""

from __future__ import annotations

from typing import Any

from app.models.event import Context


def get_intersection_context(camera: dict[str, Any] | None) -> Context:
    """Context for the active camera. Degrades instead of raising."""
    try:
        raw = (camera or {}).get("context")
        if not raw:
            return Context(status="unavailable")
        return Context(
            status="available",
            bike_infrastructure=raw.get("bike_infrastructure"),
            facility_type=raw.get("facility_type"),
            historical_cyclist_collisions=raw.get("historical_cyclist_collisions"),
        )
    except Exception:
        # Deliberately broad: an enrichment bug must not take down detection.
        return Context(status="unavailable")

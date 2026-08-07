"""Config loading and the camera fallback ladder. PRD §18.

    PRIMARY -> BACKUP 1 -> BACKUP 2 -> DEMO REPLAY

The replay rung is MANDATORY, not a nice-to-have (§7 rule 4) — judges warn a
camera may go dark at 20:45. The clip passes through the SAME Roboflow pipeline:
prerecorded *input*, not prerecorded *inference* (AC-10).

The UI labels ● LIVE or ● DEMO REPLAY at all times. Never present prerecorded
footage as live (AC-13).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.cameras.health import CameraStatus

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "cameras.json"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Read config/cameras.json once. Cached — it never changes at runtime."""
    return json.loads(CONFIG_PATH.read_text())


class CameraManager:
    """Walks the fallback ladder. One camera active at a time."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config if config is not None else load_config()
        self.ladder: list[str] = list(self.config.get("fallback_ladder") or [])
        self._index = 0
        self.status = CameraStatus.HEALTHY

    @property
    def current_id(self) -> str | None:
        return self.ladder[self._index] if self._index < len(self.ladder) else None

    @property
    def is_replay(self) -> bool:
        return self.current_id == "demo_replay"

    @property
    def mode(self) -> str:
        # AC-13. Derived from the ladder position, never set by hand — that is
        # how footage gets mislabelled.
        return "demo_replay" if self.is_replay else "live"

    def current_camera(self) -> dict[str, Any]:
        """The active camera's config block, or the replay stub."""
        cid = self.current_id
        for cam in self.config.get("cameras", []):
            if cam["id"] == cid:
                return cam
        return self.config.get("demo_replay", {"id": cid})

    def switch_camera(self) -> dict[str, Any]:
        """Advance one rung. §14 action, driven by a failed health check."""
        if self._index < len(self.ladder) - 1:
            self._index += 1
            self.status = (
                CameraStatus.FALLBACK if self.is_replay else CameraStatus.DEGRADED
            )
            return {"switched": True, "camera_id": self.current_id, "mode": self.mode}
        # Already on the last rung — the replay clip. There is nowhere further
        # to fall, and that is by design: the ladder always terminates somewhere
        # demo-able.
        return {"switched": False, "camera_id": self.current_id, "mode": self.mode}

    def reset(self) -> None:
        self._index = 0
        self.status = CameraStatus.HEALTHY

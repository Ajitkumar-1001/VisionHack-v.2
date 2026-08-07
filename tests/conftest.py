"""Shared fixtures. PRD §21.

Tests drive the real production interface — the same FastAPI app and the same
Engine that Cloud Run serves. Nothing is mocked except the clock, because a
dedup TTL measured against wall time makes a flaky test.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app


@pytest.fixture
def client() -> TestClient:
    # Engine state is per-process and these tests emit events, so reset the
    # buffer and the dedup window between tests or scenario 4 leaks into 1.
    routes._engine.reset_run()
    routes._engine.cameras.reset()
    return TestClient(app)


@pytest.fixture
def engine():
    routes._engine.reset_run()
    routes._engine.cameras.reset()
    return routes._engine


def conflict(delta_frames: float = 0, **overrides) -> dict:
    """A valid vehicle x VRU conflict separated by `delta_frames`.

    Pinned to `temporal_mode: "frames"` regardless of the active camera config
    (ADR-008 switched that to "cooccupancy") — these scenarios test the
    frames-mode threshold math itself, a property of the code, not of whatever
    variant happens to be configured right now. Override explicitly if a test
    wants a different mode.
    """
    payload = {
        "vehicle": {
            "track_id": 34,
            "class": "car",
            "entered_approach": True,
            "conflict_entry": 100.0,
        },
        "vru": {
            "track_id": 51,
            "class": "bicycle",
            "entered_approach": True,
            "conflict_entry": 100.0 + delta_frames,
        },
        "temporal_mode": "frames",
    }
    payload.update(overrides)
    return payload

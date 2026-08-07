"""Roboflow Workflow smoke test. PRD §9, Gate 3.

Doubles as the grounding tool: with a key set, it prints the workflow's real
output names, which is what the parser in roboflow_client must be written
against. Skips without a key so the suite stays green in CI and on Cloud Run.

    ROBOFLOW_API_KEY=... .venv/bin/python -m pytest tests/test_roboflow_smoke.py -s
"""

from __future__ import annotations

import json
import os

import pytest

from app.cameras.manager import CameraManager
from app.vision.roboflow_client import RoboflowNotConfigured, run_workflow

needs_key = pytest.mark.skipif(
    not os.getenv("ROBOFLOW_API_KEY"), reason="ROBOFLOW_API_KEY not set"
)


def test_missing_key_raises_a_typed_error(monkeypatch):
    """A missing key is a deployment problem and must say so precisely."""
    monkeypatch.delenv("ROBOFLOW_API_KEY", raising=False)

    with pytest.raises(RoboflowNotConfigured):
        run_workflow("https://example.com/frame.jpg")


@needs_key
def test_workflow_returns_output_blocks_for_a_live_frame():
    """One real NYCTMC frame through the hosted workflow. The assertions are
    deliberately shape-only — the output NAMES are what this run discovers."""
    cam = CameraManager().current_camera()
    outputs = run_workflow(cam["image_url"])

    assert isinstance(outputs, list) and outputs, "expected one block per image"
    assert isinstance(outputs[0], dict)

    # The grounding output. Image-shaped values are base64 blobs worth hundreds
    # of KB, so report each key's type and size rather than its content.
    print(f"\nworkflow output keys for {cam['name']}:")
    for key, value in outputs[0].items():
        size = len(json.dumps(value)) if not isinstance(value, str) else len(value)
        print(f"  {key!r}: {type(value).__name__}, {size} bytes")

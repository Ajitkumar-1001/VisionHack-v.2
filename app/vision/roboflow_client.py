"""Roboflow Workflow client — SEE. PRD §9.

Use a Roboflow *Workflow*, not a bare model call: it keeps the Cloud Run
container light and the hosted inference API pairs cleanly with Cloud Run.

Workflow shape:
    Input -> Pretrained Detection -> Class Filter -> ByteTrack
          -> Polygon Zone Logic -> Box Visualization -> Structured Output

PRETRAINED ONLY. Do not collect, annotate, train or tune — that is an immediate
scope failure (§9).

Transport only. This module returns the workflow's raw output blocks; it does
NOT parse them into TrackObservation yet, because the workflow's output names
have not been observed against a real response. Guessing them is exactly the
drift that makes a parser look right and behave wrong — see the TODO below.

`inference-sdk` is deliberately not used: it requires opencv-python, numpy,
pillow and supervision, which requirements.txt defers on purpose to keep the
image small. The hosted workflow is one JSON POST, and httpx is already here.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

API_URL = "https://serverless.roboflow.com"
WORKSPACE = os.getenv("ROBOFLOW_WORKSPACE", "ajit-kumar-khwqb")
WORKFLOW_ID = os.getenv("ROBOFLOW_WORKFLOW_ID", "custom-workflow")

TIMEOUT_S = 20.0
RETRIES = 2
BACKOFF_S = 0.5


class RoboflowError(RuntimeError):
    """Inference failed. Perception is the core path, so this is fatal to a
    frame — unlike §17 context, it does not silently degrade."""


class RoboflowNotConfigured(RoboflowError):
    """No API key in the environment. A deployment problem, not a frame problem."""


def run_workflow(image_url: str) -> list[dict[str, Any]]:
    """POST one frame to the hosted workflow. Returns one output block per image.

    `image_url` must be https — the serverless API rejects plain http, which
    matters because every NYCTMC still URL is https already.
    """
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        raise RoboflowNotConfigured("ROBOFLOW_API_KEY is not set (see .env.example)")

    url = f"{API_URL}/{WORKSPACE}/workflows/{WORKFLOW_ID}"
    payload = {
        "api_key": api_key,
        "inputs": {"image": {"type": "url", "value": image_url}},
    }

    last: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            r = httpx.post(url, json=payload, timeout=TIMEOUT_S)
            r.raise_for_status()
            body = r.json()
            # The serverless API wraps results in {"outputs": [...]}; the SDK
            # unwraps it. Accept either so the shape is confirmed on first run
            # rather than assumed here.
            outputs = body.get("outputs", body) if isinstance(body, dict) else body
            if not isinstance(outputs, list):
                raise RoboflowError(f"expected a list of outputs, got {type(outputs)}")
            return outputs
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
            if attempt < RETRIES:
                time.sleep(BACKOFF_S * (2**attempt))

    # Never include the response body: a Box Visualization block returns a
    # base64 JPEG worth hundreds of KB.
    raise RoboflowError(f"workflow call failed after {RETRIES + 1} attempts: {last}")


# TODO(§9): parse outputs -> list[TrackObservation] once the real output names
# are known. Run tests/test_roboflow_smoke.py with ROBOFLOW_API_KEY set — it
# prints the workflow's actual output keys, which is what the parser must be
# written against. Apply a class-specific confidence floor if the §6 probe shows
# VRUs under ~25px tall, and say so in the README.

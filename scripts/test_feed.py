#!/usr/bin/env python3
"""ByteTrack stability test. PRD §6 fork, §26 rung at 19:00.

Answers exactly one question: **do track IDs survive across consecutive
distinct frames at ~0.5 fps?**

    PASS   frame 1 → ID 12   frame 2 → ID 12   frame 3 → ID 12   → keep Variant B
    FAIL   frame 1 → ID 12   frame 2 → ID 48   frame 3 → ID 91   → Variant C, now

On FAIL do not tune the tracker. A vehicle at 15 mph moves ~13 m between frames
at this sampling rate — wider than the conflict zone itself — so ID churn is
physics, not a misconfiguration. Set `temporal_mode: "cooccupancy"` in
config/cameras.json and move on; the engine already handles all three variants.

Two stages, so the slow half still works without credentials:

  1. Capture N *distinct* frames (image-hash dedup, so we count frames NYC DOT
     actually published rather than requests we made). Always runs.
  2. If ROBOFLOW_API_KEY + ROBOFLOW_WORKSPACE + ROBOFLOW_WORKFLOW_ID are set,
     POST each frame to the hosted workflow and tabulate tracker IDs.
     Otherwise stop after stage 1 and print the saved paths so the frames can
     be dropped into the Roboflow workflow tester by hand.

Usage:
    python scripts/test_feed.py                 # primary camera from config
    python scripts/test_feed.py --frames 4
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo" / "frames"
# Hosted workflow inference. Stage 2 is best-effort: it has not been verified
# against a live workspace, so it fails loudly rather than silently.
SERVERLESS = "https://serverless.roboflow.com/infer/workflows"


def primary_image_url() -> str:
    cfg = json.loads((ROOT / "config" / "cameras.json").read_text())
    pid = cfg["primary"]
    for cam in cfg["cameras"]:
        if cam["id"] == pid:
            return cam["image_url"]
    raise SystemExit(f"primary camera {pid} not found in config/cameras.json")


def capture(url: str, want: int, poll_s: float, timeout_s: float) -> list[Path]:
    """Poll until `want` distinct frames are seen. Distinct == new image hash."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    paths: list[Path] = []
    started = time.monotonic()

    with httpx.Client(follow_redirects=True, timeout=10) as client:
        while len(paths) < want:
            if time.monotonic() - started > timeout_s:
                print(f"! timed out after {timeout_s:.0f}s with {len(paths)}/{want} frames")
                break
            try:
                body = client.get(url).content
            except httpx.HTTPError as e:
                print(f"! fetch failed: {e}")
                time.sleep(poll_s)
                continue

            digest = hashlib.md5(body).hexdigest()
            if digest not in seen:
                seen.add(digest)
                p = OUT_DIR / f"frame_{len(paths) + 1:02d}.jpg"
                p.write_bytes(body)
                paths.append(p)
                elapsed = time.monotonic() - started
                print(f"  frame {len(paths)}/{want}  t+{elapsed:5.1f}s  {p.name}  ({len(body)//1024} KB)")
            time.sleep(poll_s)
    return paths


def run_workflow(client: httpx.Client, path: Path, ws: str, wf: str, key: str) -> list[dict]:
    b64 = base64.b64encode(path.read_bytes()).decode()
    r = client.post(
        f"{SERVERLESS}/{ws}/{wf}",
        json={"api_key": key, "inputs": {"image": {"type": "base64", "value": b64}}},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()

    # Field names vary by workflow shape, so search rather than assume one path.
    def find_predictions(node):
        if isinstance(node, dict):
            if "predictions" in node and isinstance(node["predictions"], list):
                return node["predictions"]
            for v in node.values():
                got = find_predictions(v)
                if got:
                    return got
        elif isinstance(node, list):
            for v in node:
                got = find_predictions(v)
                if got:
                    return got
        return []

    return find_predictions(data)


def track_id(pred: dict):
    for k in ("tracker_id", "track_id", "trackerId", "id"):
        if k in pred and pred[k] is not None:
            return pred[k]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=3, help="distinct frames to capture")
    ap.add_argument("--poll", type=float, default=0.5)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--url", default=None, help="override the camera image URL")
    args = ap.parse_args()

    url = args.url or primary_image_url()
    print(f"camera: {url}\ncapturing {args.frames} distinct frames (~2s apart)...")
    paths = capture(url, args.frames, args.poll, args.timeout)
    if not paths:
        sys.exit("no frames captured — camera may be down; try the next ladder rung")

    key = os.getenv("ROBOFLOW_API_KEY")
    ws = os.getenv("ROBOFLOW_WORKSPACE")
    wf = os.getenv("ROBOFLOW_WORKFLOW_ID")
    if not (key and ws and wf):
        print(f"\n{len(paths)} frames saved to {OUT_DIR.relative_to(ROOT)}/")
        print("Set ROBOFLOW_API_KEY / ROBOFLOW_WORKSPACE / ROBOFLOW_WORKFLOW_ID to")
        print("tabulate tracker IDs automatically, or drop these into the Roboflow")
        print("workflow tester in order and read the IDs off by eye.")
        return

    print("\nrunning workflow on each frame...")
    per_frame: list[list[dict]] = []
    with httpx.Client() as client:
        for p in paths:
            try:
                per_frame.append(run_workflow(client, p, ws, wf, key))
            except Exception as e:
                sys.exit(f"! workflow call failed on {p.name}: {e}")

    print(f"\n{'frame':>6}  {'n':>3}  ids")
    id_sets = []
    for i, preds in enumerate(per_frame, 1):
        ids = [track_id(p) for p in preds]
        ids = [i for i in ids if i is not None]
        id_sets.append(set(ids))
        shown = ", ".join(f"{p.get('class','?')}#{track_id(p)}" for p in preds[:6])
        print(f"{i:>6}  {len(preds):>3}  {shown or '(none)'}")

    if not any(id_sets):
        print("\nNo tracker IDs in the output — ByteTrack is not wired, or it is")
        print("receiving raw model output instead of the filtered predictions.")
        sys.exit(2)

    persisted = set.intersection(*id_sets) if len(id_sets) > 1 else set()
    across_two = set()
    for a, b in zip(id_sets, id_sets[1:]):
        across_two |= a & b

    print(f"\nIDs present in ALL {len(id_sets)} frames: {sorted(persisted) or 'none'}")
    print(f"IDs surviving at least one frame-to-frame step: {sorted(across_two) or 'none'}")

    if persisted or len(across_two) >= 2:
        print("\nPASS — IDs are stable enough. Keep Variant B (temporal_mode: frames).")
    else:
        print("\nFAIL — IDs churn between frames. Do NOT tune the tracker.")
        print('Set "temporal_mode": "cooccupancy" in config/cameras.json (Variant C)')
        print("and note the AC-04 waiver in the README. The engine already supports it.")


if __name__ == "__main__":
    main()

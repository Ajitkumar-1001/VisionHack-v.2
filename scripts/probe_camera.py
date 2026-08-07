#!/usr/bin/env python3
"""Single-camera frame-rate probe. PRD §6.

Confirms/re-checks the fps of one already-selected camera by polling it and
hashing each response — a changed hash means NYC DOT actually published a new
still, not just that we made a new request.

Usage: python scripts/probe_camera.py <image_url> [--duration 30] [--poll 0.5]
"""

from __future__ import annotations

import argparse
import hashlib
import time

import httpx


def frame_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--poll", type=float, default=0.5)

    args = parser.parse_args()

    start = time.monotonic()

    previous_hash = None
    frame_times: list[float] = []
    requests_sent = 0

    while time.monotonic() - start < args.duration:
        response = httpx.get(
            args.url,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            timeout=10,
            follow_redirects=True,
        )
        response.raise_for_status()

        requests_sent += 1

        current_hash = frame_hash(response.content)
        now = time.monotonic()

        if current_hash != previous_hash:
            frame_times.append(now)

            print(
                f"NEW FRAME #{len(frame_times)} "
                f"at {now - start:.2f}s"
            )

            previous_hash = current_hash

        time.sleep(args.poll)

    print("\n--- CAMERA PROBE RESULT ---")
    print(f"Requests sent: {requests_sent}")
    print(f"Unique frames: {len(frame_times)}")

    if len(frame_times) < 2:
        print("Insufficient unique frames to measure FPS.")
        return

    elapsed = frame_times[-1] - frame_times[0]
    transitions = len(frame_times) - 1

    fps = transitions / elapsed
    interval = elapsed / transitions

    print(f"Measured FPS: {fps:.3f}")
    print(f"Average frame interval: {interval:.2f}s")

    if fps >= 5:
        mode = "seconds"
    elif fps >= 0.25:
        mode = "frames"
    else:
        mode = "cooccupancy"

    print(f"Recommended temporal mode: {mode}")


if __name__ == "__main__":
    main()

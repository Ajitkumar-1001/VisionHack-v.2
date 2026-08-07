#!/usr/bin/env python3
"""PRD §6 frame-rate probe. RUN THIS FIRST, 15-MINUTE HARD TIMEBOX.

This is the highest-risk unknown in the build. A 1.0s ΔT threshold cannot be
measured at a 2s sampling period, and reporting "ΔT = 0.72 sec" from a 0.5 fps
source is a false precision claim, not a tuning error.

Measures the real refresh interval of candidate NYC DOT cameras so §12 severity
can be keyed on a temporal_mode we can actually defend:

    >= 10 fps  -> Variant A, temporal_mode "seconds"
    ~0.5 fps   -> Variant B, temporal_mode "frames"
    unstable   -> Variant C, temporal_mode "cooccupancy"

Usage:  python scripts/probe_cameras.py [--cameras N] [--samples N]
Write the answer into config/cameras.json and close ADR-001 in docs/DECISIONS.md.
"""

from __future__ import annotations

import argparse
import hashlib
import time

import httpx

CAMERA_LIST = "https://webcams.nyctmc.org/api/cameras"


def online_cameras(client: httpx.Client) -> list[dict]:
    cams = client.get(CAMERA_LIST, timeout=15).json()
    # Gotcha (§5): isOnline is the STRING "true", not a boolean.
    return [c for c in cams if c.get("isOnline") == "true"]


def probe(client: httpx.Client, cam: dict, samples: int) -> dict:
    """Poll one camera and measure wall-clock gaps between *distinct* frames."""
    url = cam.get("imageUrl") or f"https://webcams.nyctmc.org/api/cameras/{cam['id']}/image"
    seen: list[tuple[float, str]] = []

    for _ in range(samples):
        t = time.monotonic()
        try:
            body = client.get(url, timeout=10).content
        except httpx.HTTPError:
            continue
        digest = hashlib.md5(body).hexdigest()
        # Only a changed image counts as a new frame; the feed serves the same
        # still repeatedly between refreshes.
        if not seen or seen[-1][1] != digest:
            seen.append((t, digest))
        time.sleep(1.0)  # Be polite: no parallel hammering (§5).

    gaps = [b[0] - a[0] for a, b in zip(seen, seen[1:])]
    mean_gap = sum(gaps) / len(gaps) if gaps else None
    return {
        "id": cam.get("id"),
        "name": cam.get("name"),
        "area": cam.get("area"),
        "distinct_frames": len(seen),
        "mean_gap_s": round(mean_gap, 2) if mean_gap else None,
        "measured_fps": round(1 / mean_gap, 3) if mean_gap else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cameras", type=int, default=4, help="candidates to probe")
    ap.add_argument("--samples", type=int, default=10, help="polls per camera")
    ap.add_argument("--match", default="", help="substring filter on camera name")
    args = ap.parse_args()

    with httpx.Client(follow_redirects=True) as client:
        cams = online_cameras(client)
        print(f"online cameras: {len(cams)}")
        if args.match:
            cams = [c for c in cams if args.match.lower() in (c.get("name") or "").lower()]
            print(f"matching {args.match!r}: {len(cams)}")

        results = [probe(client, c, args.samples) for c in cams[: args.cameras]]

    print(f"\n{'fps':>7}  {'gap_s':>6}  {'frames':>6}  name")
    for r in sorted(results, key=lambda r: -(r["measured_fps"] or 0)):
        fps = f"{r['measured_fps']:.3f}" if r["measured_fps"] else "—"
        gap = f"{r['mean_gap_s']:.2f}" if r["mean_gap_s"] else "—"
        print(f"{fps:>7}  {gap:>6}  {r['distinct_frames']:>6}  {r['name']} [{r['id']}]")

    best = max((r["measured_fps"] or 0) for r in results) if results else 0
    variant = "A / seconds" if best >= 10 else "B / frames" if best > 0 else "C / cooccupancy"
    print(f"\nbest measured fps: {best or '—'}  ->  Variant {variant}")
    print("Write this into config/cameras.json and close ADR-001. STOP AT 15 MINUTES.")


if __name__ == "__main__":
    main()

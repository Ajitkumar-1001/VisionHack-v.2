#!/usr/bin/env python3
"""Smoke-test one camera end to end: fetch -> Roboflow -> detections. PRD §6.

Run after probe_cameras.py picks the camera, to confirm the chosen feed
actually yields vehicles and VRUs before wiring the engine to it.
"""

# TODO(§9): fetch one still from the configured primary and print the parsed
# TrackObservation list, so `CAR #34` / `BIKE #51` can be eyeballed.

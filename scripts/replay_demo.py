#!/usr/bin/env python3
"""Drive the demo replay clip through the pipeline. PRD §18, AC-10.

Prerecorded INPUT, not prerecorded inference — the clip goes through the same
Roboflow workflow as the live feed. That distinction keeps the demo honest and
should be said out loud on stage.
"""

# TODO(§18): decode demo/righthook-demo.mp4 frame by frame, POST each to
# /api/perception, and label the UI ● DEMO REPLAY throughout.

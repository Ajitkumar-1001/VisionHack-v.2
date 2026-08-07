"""Camera fallback ladder. PRD §18.

    PRIMARY -> BACKUP 1 -> BACKUP 2 -> DEMO REPLAY

The replay rung is MANDATORY, not a nice-to-have (§7 rule 4). Judges warn a
camera may go dark at 20:45.

The replay clip passes through the SAME Roboflow pipeline — prerecorded *input*,
not prerecorded *inference*. Say that out loud on stage. The UI labels ● LIVE or
● DEMO REPLAY at all times; never present prerecorded footage as live (AC-13).
"""

from __future__ import annotations

# TODO(§18): switch_camera() advancing the ladder, driven by health.py.

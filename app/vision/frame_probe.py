"""In-process frame-rate measurement. PRD §6.

The standalone 15-minute probe lives in scripts/probe_cameras.py and runs once
before any engine code is written. This module is its runtime counterpart: it
keeps measuring the live feed so the UI can display the *current* fps rather
than a number hardcoded at 18:00 (AC-15).
"""

from __future__ import annotations

# TODO(§6): rolling window over distinct-frame arrival times -> measured_fps.

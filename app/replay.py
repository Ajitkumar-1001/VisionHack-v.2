"""Demo replay sequence loader. PRD §18.

The replay rung is mandatory, not a nice-to-have (§7 rule 4) — judges warn a
camera may go dark at 20:45, and at 0.5 fps on a dark, rainy 352x240 feed a
live right-hook is not something you can summon on cue.

**What is real and what is not.** The sequence supplies *observations*. Zone
assignment, track state, the conflict criterion, the severity map, dedup, the
event schema and the context attachment all execute for real against it. The
detections themselves are hand-authored rather than produced by Roboflow, and
the UI labels the run accordingly. Presenting it otherwise would break the one
rule the whole project rests on (§18, AC-13).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SEQUENCE_PATH = Path(__file__).resolve().parents[1] / "demo" / "replay-sequence.json"


@lru_cache(maxsize=1)
def load_sequence() -> dict[str, Any]:
    return json.loads(SEQUENCE_PATH.read_text())

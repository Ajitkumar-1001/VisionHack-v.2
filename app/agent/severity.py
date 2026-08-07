"""Severity mapping — a lookup keyed on temporal_mode. PRD §12.

Variant A "seconds":      <=1.0s CRITICAL | 1.0-2.0s WARNING | >2.0s none
Variant B "frames":       0 frames CRITICAL | 1 frame WARNING | >=2 none
Variant C "cooccupancy":  both in conflict_zone same frame -> CONFLICT

The variant is a CONFIG FLAG, not a rewrite (§6). All three emit the identical
event schema and drive the identical state machine.
"""

from __future__ import annotations

# TODO(§12): severity_for(delta, temporal_mode) -> Severity | None, plus the
# display string the UI shows ("Δ 1 frame @ 0.5 fps (≈2.0s)"). The displayed
# units must match the mode — false precision is the failure to avoid.

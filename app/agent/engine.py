"""The conflict algorithm — DECIDE. PRD §11.

Deliberately, embarrassingly understandable:

    if vru enters vru_approach:              remember vru track
    if vehicle enters vehicle_turn_approach: remember vehicle track
    if vru enters conflict_zone:             record vru_conflict_time
    if vehicle enters conflict_zone:         record vehicle_conflict_time

    delta = abs(vru_conflict_time - vehicle_conflict_time)

ΔT is the gap between two OBSERVED zone-entry timestamps — never a predicted
time-to-arrival. This is the single most important design choice in the PRD: it
needs no homography, no pixel-to-metre calibration, no velocity model and no
ground plane. We report something we actually watched happen.

No LLM in the core path (§7 rule 2). No weighted risk formula (§7 rule 3) —
those weights cannot be justified in three hours or survive a follow-up.
"""

from __future__ import annotations

# TODO(§11): implement the event criterion —
#   vru.was_in_vru_approach and vehicle.was_in_vehicle_turn_approach
#   and vru.entered_conflict_zone and vehicle.entered_conflict_zone
#   and within_threshold(delta)  ->  create_safety_event()
# Do not make it smarter until this works.

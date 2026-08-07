"""The agent state machine. PRD §13.

    NORMAL --(both approach zones occupied)--> WATCH
    WATCH  --(both entered conflict_zone within threshold)--> CONFLICT
    CONFLICT --create_safety_event()--> ALERT_CREATED
    any --(TTL expiry / tracks leave)--> NORMAL

This exists because it is the proof that perception causes a system decision.
When a judge asks "why is this an agent?", this is the answer.
"""

from __future__ import annotations

from enum import StrEnum


class AgentState(StrEnum):
    NORMAL = "NORMAL"
    # Not a third ΔT band — a UI/state condition (§12): an approaching vehicle
    # AND an approaching VRU are present, neither has reached the conflict zone.
    # Gives the demo a visible build-up before the alert.
    WATCH = "WATCH"
    CONFLICT = "CONFLICT"
    ALERT_CREATED = "ALERT_CREATED"


def next_state(
    both_approaching: bool, both_in_conflict: bool, within_threshold: bool
) -> AgentState:
    """Pure transition. No history — the caller owns decay back to NORMAL."""
    if both_in_conflict and within_threshold:
        return AgentState.CONFLICT
    if both_approaching:
        return AgentState.WATCH
    return AgentState.NORMAL

"""The three agent actions. PRD §14.

Exactly three. No generic tools, no browser agent, no chat, no RAG, no
multi-agent architecture (§30).

    create_safety_event()       valid conflict passes threshold + dedup
    get_intersection_context()  on event creation; FAILURE IS NON-FATAL
    switch_camera()             camera health check fails -> next rung
"""

from __future__ import annotations

# TODO(§14): the three callables. get_intersection_context() must swallow its
# own failures and return context.status="unavailable" — never fail live safety
# detection because optional enrichment is down (§21 scenario 6).

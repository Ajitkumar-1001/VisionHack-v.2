"""PRD §21 scenario(s) 4. Same pair sent 5x produces 1 event, not 5

Written against the deployed API surface (§20), driven through
POST /api/agent/event — the endpoint that lets anyone reproduce the decision
logic without a camera. pytest first, Veris second (§21): this artifact lands in
the repo regardless of whether the Veris integration lands, and it scores on
both Technical Execution and Open Source.
"""

import pytest

pytest.skip(
    "§21 scenario(s) 4 — engine not implemented yet (scaffold)",
    allow_module_level=True,
)

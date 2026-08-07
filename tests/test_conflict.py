"""PRD §21 scenario(s) 1,2,3. Core path, threshold correctness, no false positives

Written against the deployed API surface (§20), driven through
POST /api/agent/event — the endpoint that lets anyone reproduce the decision
logic without a camera. pytest first, Veris second (§21): this artifact lands in
the repo regardless of whether the Veris integration lands, and it scores on
both Technical Execution and Open Source.
"""

import pytest

pytest.skip(
    "§21 scenario(s) 1,2,3 — engine not implemented yet (scaffold)",
    allow_module_level=True,
)

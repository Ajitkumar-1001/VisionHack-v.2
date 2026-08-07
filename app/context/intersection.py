"""NYC Open Data context — precomputed, not queried live. PRD §17.

v3.0 budgeted live Socrata queries against two datasets: ~75 minutes we do not
have. The camera is chosen by 17:45, so the numbers are looked up ONCE for that
one intersection and pasted into config/intersection_context.json.
15 minutes instead of 90. AC-11 still passes.

Open data must NOT determine live severity. Two distinct layers, two distinct UI
regions. History gives context; it never modifies an individual event's
severity. A transportation-literate judge will notice the separation.
"""

from __future__ import annotations

# TODO(§17): load config/intersection_context.json and return a Context. Any
# failure returns Context(status="unavailable") — surfaced in the UI as
# "Historical context unavailable", never as a 500 (§21).

"""Roboflow Workflow client — SEE. PRD §9.

Use a Roboflow *Workflow*, not a bare model call: it keeps the Cloud Run
container light and the hosted inference API pairs cleanly with Cloud Run.

Workflow shape:
    Input -> Pretrained Detection -> Class Filter -> ByteTrack
          -> Polygon Zone Logic -> Box Visualization -> Structured Output

PRETRAINED ONLY. Do not collect, annotate, train or tune — that is an immediate
scope failure (§9).
"""

from __future__ import annotations

# TODO(§9): POST frame bytes to the hosted workflow, parse the structured
# output into list[TrackObservation]. Apply a class-specific confidence floor if
# the §6 probe shows VRUs under ~25px tall, and say so in the README.

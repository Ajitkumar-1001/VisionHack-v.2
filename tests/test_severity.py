"""PRD §12 severity mapping across all three variants.

The variant is a config flag, not a rewrite (§6) — so the mapping is unit
tested directly, independent of the API.
"""

from __future__ import annotations

import pytest

from app.agent.severity import display, severity_for
from app.models.event import Severity


@pytest.mark.parametrize(
    "delta,expected",
    [(0.0, Severity.CRITICAL), (1.0, Severity.CRITICAL), (1.5, Severity.WARNING),
     (2.0, Severity.WARNING), (2.1, None)],
)
def test_variant_a_seconds(delta, expected):
    assert severity_for(delta, "seconds") == expected


@pytest.mark.parametrize(
    "delta,expected",
    [(0, Severity.CRITICAL), (1, Severity.WARNING), (2, None), (5, None)],
)
def test_variant_b_frames(delta, expected):
    assert severity_for(delta, "frames") == expected


def test_variant_c_cooccupancy():
    assert severity_for(0, "cooccupancy") == Severity.CONFLICT
    assert severity_for(1, "cooccupancy") is None


def test_display_never_claims_unmeasured_precision():
    """§6: the displayed unit must match the mode we actually measured in."""
    # Variant B must not render a bare second figure as if it were observed.
    out = display(1, "frames", 0.489)
    assert "1 frame" in out
    assert "0.489 fps" in out
    assert "≈" in out  # the seconds figure is explicitly an estimate

    # Variant A is the only mode allowed to state exact seconds.
    assert display(0.72, "seconds", 10.0) == "ΔT 0.72s"

    # Variant C makes no temporal claim at all.
    assert "same frame" in display(0, "cooccupancy", 0.5)


def test_display_pluralises_correctly():
    assert "Δ 0 frames" in display(0, "frames", 0.5)
    assert "Δ 1 frame @" in display(1, "frames", 0.5)

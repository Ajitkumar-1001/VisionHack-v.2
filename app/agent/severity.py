"""Severity mapping — a lookup keyed on temporal_mode. PRD §12.

The variant is a CONFIG FLAG, not a rewrite (§6). All three modes emit the
identical event schema and drive the identical state machine; only the band
edges and the displayed units differ.

Rule 7 (§7): every number on screen carries its measurement basis. `display()`
exists so the UI can never show a bare number in units we did not measure.
"""

from __future__ import annotations

from app.models.event import Severity, TemporalMode

# §12 Variant A. Seconds, exact — only claimable on a video-rate feed.
CRITICAL_SECONDS = 1.0
WARNING_SECONDS = 2.0


def severity_for(delta: float, temporal_mode: TemporalMode | str) -> Severity | None:
    """Map an observed temporal separation to a severity, or None for no event.

    `delta` is in whatever unit the mode measures: seconds for Variant A,
    whole frames for Variant B, and ignored for Variant C (co-occupancy is
    already a same-frame assertion by the time it reaches here).
    """
    mode = TemporalMode(temporal_mode)

    if mode is TemporalMode.SECONDS:
        if delta <= CRITICAL_SECONDS:
            return Severity.CRITICAL
        if delta <= WARNING_SECONDS:
            return Severity.WARNING
        return None

    if mode is TemporalMode.FRAMES:
        frames = round(delta)
        if frames == 0:
            return Severity.CRITICAL
        if frames == 1:
            return Severity.WARNING
        return None

    # Variant C: same frame or nothing. There is no band to fall into.
    return Severity.CONFLICT if round(delta) == 0 else None


def display(
    delta: float, temporal_mode: TemporalMode | str, measured_fps: float | None
) -> str:
    """The exact string the UI shows. Never a unit we did not measure (§6).

    A system that says "Δ 1 frame @ 0.5 fps" is more credible than one that
    says "ΔT 0.72s" with nothing behind it.
    """
    mode = TemporalMode(temporal_mode)

    if mode is TemporalMode.SECONDS:
        return f"ΔT {delta:.2f}s"

    if mode is TemporalMode.FRAMES:
        frames = round(delta)
        unit = "frame" if frames == 1 else "frames"
        if not measured_fps:
            return f"Δ {frames} {unit}"
        # The seconds figure is an ESTIMATE derived from the measured refresh
        # interval, and is labelled ≈ so it is never mistaken for a measurement.
        return f"Δ {frames} {unit} @ {measured_fps:g} fps (≈{frames / measured_fps:.1f}s)"

    return "Both in conflict zone, same frame"

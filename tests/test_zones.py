"""PRD §10 zone assignment."""

from __future__ import annotations

from app.cameras.manager import CameraManager
from app.models.perception import Zone
from app.vision.zones import bbox_ground_point, point_in_polygon, zone_for

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]


def test_point_in_polygon_basics():
    assert point_in_polygon((5, 5), SQUARE)
    assert not point_in_polygon((15, 5), SQUARE)
    assert not point_in_polygon((5, 15), SQUARE)


def test_empty_polygon_contains_nothing():
    """Uncalibrated zones must not silently match everything."""
    assert not point_in_polygon((5, 5), [])
    assert not point_in_polygon((5, 5), [[0, 0], [1, 1]])


def test_ground_point_is_bottom_centre_not_centroid():
    """A tall object's centroid floats above the road; its feet do not."""
    assert bbox_ground_point([100, 50, 140, 150]) == (120.0, 150.0)


def test_conflict_zone_wins_overlap():
    """conflict_zone is drawn inside the approach areas. If an approach won,
    an object reaching the conflict area would still report as approaching and
    no event could ever fire."""
    zones = {
        "vru_approach": [[0, 0], [100, 0], [100, 100], [0, 100]],
        "conflict_zone": [[40, 40], [60, 40], [60, 60], [40, 60]],
        "vehicle_turn_approach": [],
    }
    # Feet at (50, 50) — inside both.
    assert zone_for([45, 40, 55, 50], zones) == Zone.CONFLICT_ZONE
    # Feet at (10, 10) — only the approach.
    assert zone_for([5, 0, 15, 10], zones) == Zone.VRU_APPROACH


def test_outside_all_zones_is_none():
    assert zone_for([300, 300, 310, 310], {"conflict_zone": SQUARE}) is None


def test_configured_camera_has_three_usable_polygons():
    """AC-05. Calibrated by eye against demo/frames/frame_01.jpg (352x240)."""
    cam = CameraManager().current_camera()
    zones = cam["zones"]

    for name in ("vru_approach", "vehicle_turn_approach", "conflict_zone"):
        assert len(zones[name]) >= 3, f"{name} is not a usable polygon"


def test_crosswalk_centre_lands_in_conflict_zone():
    """A pedestrian standing mid-crosswalk must read as conflict_zone."""
    cam = CameraManager().current_camera()
    # Feet mid-crosswalk in the 352x240 frame.
    assert zone_for([120, 165, 132, 190], cam["zones"]) == Zone.CONFLICT_ZONE

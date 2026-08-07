"""Point-in-polygon zone assignment. PRD §10.

Three manually-configured polygons per camera. NO automatic intersection
understanding and no homography — §30 bans both.

    vru_approach            where cyclists/pedestrians enter the corridor
    vehicle_turn_approach   where turning vehicles are observed
    conflict_zone           the image region where the two paths overlap

The test point is the bbox **bottom-centre** — where the object meets the
roadway — not the centroid, which floats above the road for tall objects and
would put a bus in the wrong zone.

Ray casting rather than Shapely: it is ~15 lines, and Shapely would add a
compiled dependency to an image kept deliberately small (§19).
"""

from __future__ import annotations

from app.models.perception import Zone

Point = tuple[float, float]
Polygon = list[list[float]]


def bbox_ground_point(bbox: list[int]) -> Point:
    """Bottom-centre of [x1, y1, x2, y2] — the object's contact with the road."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, float(max(y1, y2)))


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """Standard even-odd ray cast. Empty/degenerate polygons contain nothing."""
    if not polygon or len(polygon) < 3:
        return False

    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        # Does the edge straddle the horizontal ray through y?
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_cross:
                inside = not inside
    return inside


def zone_for(bbox: list[int], zones: dict[str, Polygon]) -> Zone | None:
    """Which zone this detection occupies, or None.

    `conflict_zone` is tested first and wins any overlap: it is the smaller,
    more specific region and is usually drawn inside the approach areas. If an
    approach zone won instead, an object entering the conflict area would keep
    reporting as merely approaching and no event would ever fire.
    """
    point = bbox_ground_point(bbox)
    for zone in (Zone.CONFLICT_ZONE, Zone.VRU_APPROACH, Zone.VEHICLE_TURN_APPROACH):
        if point_in_polygon(point, zones.get(zone.value, [])):
            return zone
    return None

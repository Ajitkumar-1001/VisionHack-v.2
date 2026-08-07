"""Point-in-polygon zone assignment. PRD §10.

Three manually-configured polygons per camera. NO automatic intersection
understanding and no homography (§30 bans both).

    vru_approach            where cyclists/pedestrians enter the corridor
    vehicle_turn_approach   where turning vehicles are observed
    conflict_zone           the image region where the two paths overlap

Test point is the bbox bottom-centre — the object's contact with the roadway —
not the centroid, which floats above the road for tall objects.
"""

from __future__ import annotations

# TODO(§10): load polygons from config/cameras.json, expose
# zone_for(bbox) -> Zone | None. Shapely is optional; a ray-cast is ~15 lines.

"""
Synthetic/theoretical raster scenario -- no real geospatial data, just
to exercise disslucc.allocation.AllocationClueLike end to end.

Replaces what, in the original repository, would come from
`load_dataset()` + `vector_to_raster_backend()` (a real shapefile/gpkg).
Here it's just deterministic np.random.
"""
from __future__ import annotations

import numpy as np
from dissmodel.geo import RasterBackend

LAND_USE_TYPES = ["forest", "agriculture", "urban"]
COMPLEMENTAR_LU = "forest"


def build_backend(height: int = 30, width: int = 30, seed: int = 42) -> RasterBackend:
    """Builds a RasterBackend with synthetic drivers (dist_road, slope)
    and an initial land use state (mostly forest, a small urban seed
    near the 'road')."""
    rng = np.random.default_rng(seed)

    # horizontal "road" on the middle row -- dist_road grows with
    # distance to it, normalized [0,1]
    road_row = height // 2
    rows = np.arange(height, dtype=np.float32)[:, None]
    dist_road = np.repeat(np.abs(rows - road_row), width, axis=1)
    dist_road = dist_road / dist_road.max()

    # smooth synthetic terrain (sum of sinusoids + light noise), [0,1]
    yy, xx = np.mgrid[0:height, 0:width]
    slope = (
        np.sin(xx / 4.0) * 0.5 + np.cos(yy / 5.0) * 0.5
        + rng.normal(0, 0.05, size=(height, width))
    ).astype(np.float32)
    slope = (slope - slope.min()) / (slope.max() - slope.min())

    backend = RasterBackend(shape=(height, width))
    backend.set("dist_road", dist_road.astype(np.float32))
    backend.set("slope", slope)

    urban = np.zeros((height, width), dtype=np.float32)
    urban[road_row, width // 2] = 1.0  # a seed cell
    agriculture = np.zeros((height, width), dtype=np.float32)
    forest = 1.0 - urban - agriculture

    backend.set("urban", urban)
    backend.set("agriculture", agriculture)
    backend.set("forest", forest)

    return backend


def build_demand(n_steps: int, height: int = 30, width: int = 30) -> list[list[float]]:
    """
    Matrix [step][land_use], SAME ORDER as LAND_USE_TYPES
    (forest, agriculture, urban). Grows urban and agriculture linearly;
    forest is whatever's left -- keeps the sum equal to the total cell
    count, which is what CLUE expects from a well-formed demand table.
    """
    total = height * width
    demand = []
    for step in range(n_steps):
        urban_target = 1 + 3 * step
        agri_target  = 1 * step
        forest_target = total - urban_target - agri_target
        demand.append([float(forest_target), float(agri_target), float(urban_target)])
    return demand

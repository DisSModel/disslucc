"""
tests/_lab15_helpers.py
-------------------------
Shared scenario, run and metrics helpers for the Lab15 (discrete,
raster) tests. Factored out of examples/run_lab15_validation.py so the
same, already-verified pipeline backs both the reproducibility script
and the pytest suite.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import AllocationDClueSLike, DemandPreComputedValues, PotentialDLogisticRegression
from disslucc.schemas import LogisticRegressionSpec
from disslucc.validation.pontius import confusion_metrics, pontius_millones

ROOT = Path(__file__).resolve().parent.parent
CS_MOJU_ZIP = ROOT / "data" / "cs_moju.zip"
TERRAME_ZIP = ROOT / "benchmark" / "data" / "Lab15_2004.zip"

LAND_USE_TYPES = ["f", "d", "o"]
N_STEPS = 6
CELL_AREA = 1.0

ANNUAL_DEMAND: list[list[float]] = [
    [5706, 205, 3], [5658, 253, 3], [5611, 300, 3],
    [5563, 348, 3], [5516, 395, 3], [5468, 443, 3],
]

DEFAULT_POTENTIAL_DATA: list[list[LogisticRegressionSpec]] = [[
    LogisticRegressionSpec(const=-2.34187976925989, elasticity=0.0, betas={
        "media_decl": -0.0272710076327129, "dist_area_": 4.30977432375496,
        "dist_br": 3.10319957497883, "dist_curua": 0.445414024051873,
        "dist_rios_": 47.3556329553235, "dist_estra": 38.4966894254506,
    }),
    LogisticRegressionSpec(const=-0.100351497277102, elasticity=0.6, betas={
        "media_decl": 0.0581358851690861, "dist_area_": -0.974998890251365,
        "dist_br": -2.51650696123426, "dist_curua": -1.26742746441679,
        "dist_rios_": -40.3646901047482, "dist_estra": -23.0841140199094,
    }),
    LogisticRegressionSpec(const=0.01, elasticity=0.5, betas={}),
]]

TRANSITION_MATRIX = [[[1, 1, 0], [0, 1, 0], [0, 0, 1]]]  # irreversible deforestation

data_available = CS_MOJU_ZIP.exists() and TERRAME_ZIP.exists()


def build_backend_by_rowcol(gdf: gpd.GeoDataFrame) -> tuple[RasterBackend, np.ndarray, np.ndarray]:
    rows = gdf["lin"].astype(int).values
    cols = gdf["col"].astype(int).values
    n_rows, n_cols = int(rows.max()) + 1, int(cols.max()) + 1

    backend = RasterBackend(shape=(n_rows, n_cols))
    mask = np.zeros((n_rows, n_cols), dtype=np.float32)
    mask[rows, cols] = 1.0
    backend.set("mask", mask)

    driver_cols = ["media_decl", "dist_area_", "dist_br", "dist_curua", "dist_rios_", "dist_estra"]
    for col in LAND_USE_TYPES + driver_cols:
        arr = np.zeros((n_rows, n_cols), dtype=np.float32)
        arr[rows, cols] = gdf[col].astype(float).values
        backend.set(col, arr)

    return backend, rows, cols


def load_gdf_input() -> gpd.GeoDataFrame:
    return gpd.read_file(CS_MOJU_ZIP)


def load_gdf_terrame() -> gpd.GeoDataFrame:
    return gpd.read_file(TERRAME_ZIP)


def run_lab15_raster(
    potential_data: list[list[LogisticRegressionSpec]] | None = None,
    annual_demand: list[list[float]] | None = None,
) -> tuple[RasterBackend, np.ndarray, np.ndarray]:
    """Run the raster Lab15 (discrete CLUE-S-like) scenario; return the
    backend plus the (row, col) arrays used to build it."""
    gdf = load_gdf_input()
    backend, rows, cols = build_backend_by_rowcol(gdf)

    demand_table = annual_demand or ANNUAL_DEMAND
    env = Environment(end_time=len(demand_table) - 1)

    demand = DemandPreComputedValues(annual_demand=demand_table, land_use_types=LAND_USE_TYPES)
    PotentialDLogisticRegression(
        backend=backend, potential_data=potential_data or DEFAULT_POTENTIAL_DATA,
        land_use_types=LAND_USE_TYPES,
    )
    AllocationDClueSLike(
        backend=backend, demand=demand, land_use_types=LAND_USE_TYPES,
        transition_matrix=TRANSITION_MATRIX, cell_area=CELL_AREA,
        max_difference=10.0, max_iteration=1000, factor_iteration=0.0001,
    )
    env.run()
    return backend, rows, cols


def metrics_vs_terrame(backend: RasterBackend, rows: np.ndarray, cols: np.ndarray) -> dict:
    """Pontius & Millones decomposition plus confusion metrics for
    class 'd', aligned against the real TerraME reference."""
    import pandas as pd

    terrame = load_gdf_terrame()
    ours_df = pd.DataFrame({
        "lin": rows, "col": cols, "d_ours": backend.get("d")[rows, cols],
    }).set_index(["lin", "col"])
    terrame_df = pd.DataFrame({
        "lin": terrame["lin"].astype(int).values,
        "col": terrame["col"].astype(int).values,
        "d_terrame": terrame["d_out"].astype(float).values,
    }).set_index(["lin", "col"])
    aligned = ours_df.join(terrame_df, how="inner")

    m = pontius_millones(aligned["d_ours"].values, aligned["d_terrame"].values)
    m.update(confusion_metrics(aligned["d_ours"].values, aligned["d_terrame"].values))
    return m

"""
Real validation: runs disslucc (ours, raster-only) over the real Lab1
scenario and compares cell by cell against the TerraME reference
(benchmark/data/LUCCME_Lab1_2014.zip from disslucc-continuous), using
the continuous Pontius & Millones decomposition
(disslucc.validation.pontius).

Unlike run_lab1_real.py: here the raster grid is built via DIRECT
row/col mapping (the way csAC.shp already comes, each polygon already
has row/col from the original grid) -- not spatial resampling by
resolution. It's the same method
disslucc_continuous.executors.lucc_benchmark_executor._build_mock_raster
uses to compare against TerraME; resampling by resolution (as
run_lab1_real.py does) introduces alignment error that doesn't exist
here.
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import (
    AllocationClueLike,
    DemandPreComputedValues,
    PotentialLinearRegression,
)
from disslucc.components.demand import load_demand_csv
from disslucc.schemas import AllocationSpec, RegressionSpec
from disslucc.validation.pontius import pontius_millones

ROOT = Path(__file__).resolve().parent.parent
CSAC_ZIP = ROOT / "data" / "input" / "csAC.zip"
TERRAME_ZIP = ROOT / "benchmark" / "data" / "LUCCME_Lab1_2014.zip"
DEMAND_CSV = ROOT / "data" / "input" / "examples_demand_lab1.csv"

LAND_USE_TYPES = ["f", "d", "outros"]
DRIVER_COLS = ["assentamen", "uc_us", "uc_pi", "ti", "dist_riobr", "fertilidad", "rodovias"]
N_STEPS = 7
CELL_AREA = 25.0


def build_backend_by_rowcol(gdf: gpd.GeoDataFrame) -> tuple[RasterBackend, np.ndarray, np.ndarray]:
    """Same method as the real benchmark's _build_mock_raster: each
    polygon already knows its (row, col) in the original grid -- use
    that directly, no spatial resampling."""
    rows = gdf["row"].astype(int).values
    cols = gdf["col"].astype(int).values
    n_rows, n_cols = int(rows.max()) + 1, int(cols.max()) + 1

    backend = RasterBackend(shape=(n_rows, n_cols))
    mask = np.zeros((n_rows, n_cols), dtype=np.float32)
    mask[rows, cols] = 1.0
    backend.set("mask", mask)

    for col in LAND_USE_TYPES + DRIVER_COLS:
        arr = np.zeros((n_rows, n_cols), dtype=np.float32)
        arr[rows, cols] = gdf[col].astype(float).values
        backend.set(col, arr)

    return backend, rows, cols


def load_terrame_reference(zip_path: Path) -> gpd.GeoDataFrame:
    with zipfile.ZipFile(zip_path) as z, z.open("Lab1_2014.dbf") as f:
        data = f.read()
    with tempfile.NamedTemporaryFile(suffix=".dbf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        gdf = gpd.read_file(tmp_path)
    finally:
        os.unlink(tmp_path)
    return gdf


# ── 1. real data + grid aligned by row/col ────────────────────────────────────
# csAC.zip is read directly -- GDAL opens a single-layer shapefile zip
# without manual extraction, same as the tests in disslucc-continuous do.

gdf = gpd.read_file(CSAC_ZIP)
backend, rows, cols = build_backend_by_rowcol(gdf)
print(f"Backend: shape={backend.shape}, {len(rows):,} valid cells")

annual_demand = load_demand_csv(DEMAND_CSV.read_text(), LAND_USE_TYPES)

# ── 2. run our disslucc, same coefficients as always ──────────────────────────

env = Environment(end_time=N_STEPS - 1)

demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=LAND_USE_TYPES)

potential = PotentialLinearRegression(
    backend=backend, demand=demand, land_use_types=LAND_USE_TYPES,
    land_use_no_data="outros",
    potential_data=[[
        RegressionSpec(const=0.7392, betas={
            "assentamen": -0.2193, "uc_us": 0.1754, "uc_pi": 0.09708,
            "ti": 0.1207, "dist_riobr": 0.0000002388, "fertilidad": -0.1313,
        }),
        RegressionSpec(const=0.267, betas={
            "rodovias": -0.0000009922, "assentamen": 0.2294,
            "uc_us": -0.09867, "dist_riobr": -0.0000003216, "fertilidad": 0.1281,
        }),
        RegressionSpec(const=0.0),
    ]],
)

allocation = AllocationClueLike(
    backend=backend, demand=demand, potential=potential,
    land_use_types=LAND_USE_TYPES,
    static={"f": -1, "d": -1, "outros": 1},
    complementar_lu="f", cell_area=CELL_AREA,
    allocation_data=[
        AllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),
        AllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),
        AllocationSpec(static=1, min_value=0, max_value=1, min_change=0, max_change=1),
    ],
)

env.run()

# ── 3. compare cell by cell against the real TerraME reference ───────────────

terrame = load_terrame_reference(TERRAME_ZIP)
terrame_row = terrame["row"].astype(int).values
terrame_col = terrame["col"].astype(int).values
terrame_d = terrame["d_out"].astype(float).values

our_d = backend.get("d")[rows, cols]  # our grid, same row order as csAC.shp

# align by (row,col) -- csAC and the TerraME reference may not be in
# the same row order, so join by key, not by position
import pandas as pd

ours_df = pd.DataFrame({"row": rows, "col": cols, "d_ours": our_d}).set_index(["row", "col"])
terrame_df = pd.DataFrame({"row": terrame_row, "col": terrame_col, "d_terrame": terrame_d}).set_index(["row", "col"])
aligned = ours_df.join(terrame_df, how="inner")
print(f"Aligned cells (common row,col): {len(aligned):,}")

m = pontius_millones(aligned["d_ours"].values, aligned["d_terrame"].values)
print("\nPontius & Millones -- disslucc (ours) vs real TerraME, class 'd' (deforestation):")
for k, v in m.items():
    print(f"  {k:>24}: {v}")

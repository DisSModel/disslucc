"""
tests/_lab1_helpers.py
-----------------------
Shared scenario, run and metrics helpers for the Lab1 (continuous,
raster) tests. Factored out of examples/run_lab1_validation.py so the
same, already-verified pipeline backs both the reproducibility script
and the pytest suite.
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import AllocationClueLike, DemandPreComputedValues, PotentialLinearRegression
from disslucc.components.demand import load_demand_csv
from disslucc.schemas import AllocationSpec, RegressionSpec
from disslucc.validation.pontius import pontius_millones

ROOT = Path(__file__).resolve().parent.parent
CSAC_ZIP = ROOT / "examples" / "data" / "input" / "csAC.zip"
TERRAME_ZIP = ROOT / "benchmark" / "data" / "LUCCME_Lab1_2014.zip"
DEMAND_CSV = ROOT / "examples" / "data" / "input" / "examples_demand_lab1.csv"

LAND_USE_TYPES = ["f", "d", "outros"]
DRIVER_COLS = ["assentamen", "uc_us", "uc_pi", "ti", "dist_riobr", "fertilidad", "rodovias"]
N_STEPS = 7
CELL_AREA = 25.0
TOLERANCE = 0.01

# Values transcribed from the original LuccME script (lab1_submodel.lua),
# same as disslucc-continuous/tests/test_benchmark_discriminance.py.
LUCCME_MAX_DIFFERENCE = 1643.0  # AllocationCClueLike, area units
LUCCME_DEMAND_D_2014 = 21607.38493  # D1.annualDemand, last row, class "d"

# Official, calibrated regression coefficients (same as examples/run_lab1_validation.py).
DEFAULT_POTENTIAL_DATA: list[list[RegressionSpec]] = [[
    RegressionSpec(const=0.7392, betas={
        "assentamen": -0.2193, "uc_us": 0.1754, "uc_pi": 0.09708,
        "ti": 0.1207, "dist_riobr": 0.0000002388, "fertilidad": -0.1313,
    }),
    RegressionSpec(const=0.267, betas={
        "rodovias": -0.0000009922, "assentamen": 0.2294,
        "uc_us": -0.09867, "dist_riobr": -0.0000003216, "fertilidad": 0.1281,
    }),
    RegressionSpec(const=0.0),
]]

DEFAULT_ALLOCATION_DATA: list[AllocationSpec] = [
    AllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),
    AllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),
    AllocationSpec(static=1, min_value=0, max_value=1, min_change=0, max_change=1),
]

data_available = CSAC_ZIP.exists() and TERRAME_ZIP.exists() and DEMAND_CSV.exists()


def build_backend_by_rowcol(gdf: gpd.GeoDataFrame) -> tuple[RasterBackend, np.ndarray, np.ndarray]:
    """Each polygon already knows its (row, col) in the original grid --
    use that directly, no spatial resampling. Same method as
    disslucc_continuous.executors.lucc_benchmark_executor._build_mock_raster."""
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


def load_terrame_reference(zip_path: Path = TERRAME_ZIP) -> gpd.GeoDataFrame:
    with zipfile.ZipFile(zip_path) as z:
        with z.open("Lab1_2014.dbf") as f:
            data = f.read()
    with tempfile.NamedTemporaryFile(suffix=".dbf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        gdf = gpd.read_file(tmp_path)
    finally:
        os.unlink(tmp_path)
    return gdf


def full_metrics(pred: np.ndarray, ref: np.ndarray, tolerance: float = TOLERANCE) -> dict:
    """Pontius & Millones decomposition plus RMSE and match_pct, same
    fields as disslucc_continuous's LUCCBenchmarkExecutor._metrics."""
    m = pontius_millones(pred, ref)
    diff = np.abs(np.asarray(pred, dtype=np.float64) - np.asarray(ref, dtype=np.float64))
    m["rmse"] = float(np.sqrt((diff ** 2).mean()))
    m["match_pct"] = float((diff <= tolerance).mean() * 100)
    return m


def run_lab1(potential_data: list[list[RegressionSpec]] | None = None, n_steps: int = N_STEPS) -> dict:
    """Run the raster Lab1 scenario and return the metrics dict for
    class 'd' (deforestation) against the real TerraME reference."""
    gdf = gpd.read_file(CSAC_ZIP)
    backend, rows, cols = build_backend_by_rowcol(gdf)

    annual_demand = load_demand_csv(DEMAND_CSV.read_text(), LAND_USE_TYPES)
    env = Environment(end_time=n_steps - 1)

    demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=LAND_USE_TYPES)
    potential = PotentialLinearRegression(
        backend=backend, demand=demand, land_use_types=LAND_USE_TYPES,
        land_use_no_data="outros",
        potential_data=potential_data or DEFAULT_POTENTIAL_DATA,
    )
    AllocationClueLike(
        backend=backend, demand=demand, potential=potential,
        land_use_types=LAND_USE_TYPES,
        static={"f": -1, "d": -1, "outros": 1},
        complementar_lu="f", cell_area=CELL_AREA,
        allocation_data=DEFAULT_ALLOCATION_DATA,
    )
    env.run()

    terrame = load_terrame_reference()
    terrame_row = terrame["row"].astype(int).values
    terrame_col = terrame["col"].astype(int).values
    terrame_d = terrame["d_out"].astype(float).values

    our_d = backend.get("d")[rows, cols]
    ours_df = pd.DataFrame({"row": rows, "col": cols, "d_ours": our_d}).set_index(["row", "col"])
    terrame_df = pd.DataFrame(
        {"row": terrame_row, "col": terrame_col, "d_terrame": terrame_d}
    ).set_index(["row", "col"])
    aligned = ours_df.join(terrame_df, how="inner")

    return full_metrics(aligned["d_ours"].values, aligned["d_terrame"].values)

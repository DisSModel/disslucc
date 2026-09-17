"""
Real validation of the (new, raster) discrete port against the real
TerraME reference for Lab15 (cs_moju, 1999-2004) -- same
coefficients/transition matrix as
disslucc_discrete.executors.lucc_validation_executor.

DISCRIMINANCE WARNING (inherited from the original repository,
benchmark/validate_lab15.py): the Lab15 scenario is nearly
non-discriminative -- a trivial static ranking by (prob_d - prob_f),
with no CLUE-S, no iteration, no time steps, already reproduces the
same cell-by-cell output. This validation confirms the logistic
regression coefficients were transcribed correctly, NOT necessarily
that the allocation algorithm itself is faithful (see
disslucc-discrete/tests/test_benchmark_discriminance.py, not ported
here).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import geopandas as gpd
from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import DemandPreComputedValues, PotentialDLogisticRegression, AllocationDClueSLike
from disslucc.schemas import LogisticRegressionSpec
from disslucc.validation.pontius import pontius_millones, confusion_metrics

CS_MOJU_SHP = "/tmp/moju/cs_moju.shp"
TERRAME_SHP = "/tmp/lab15_ref/Lab6_2004.shp"

LAND_USE_TYPES = ["f", "d", "o"]
N_STEPS = 6
CELL_AREA = 1.0

ANNUAL_DEMAND: list[list[float]] = [
    [5706, 205, 3], [5658, 253, 3], [5611, 300, 3],
    [5563, 348, 3], [5516, 395, 3], [5468, 443, 3],
]

POTENTIAL_DATA: list[list[LogisticRegressionSpec]] = [[
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


# ── 1. real data + grid aligned by (lin, col) ─────────────────────────────────

gdf = gpd.read_file(CS_MOJU_SHP)
backend, rows, cols = build_backend_by_rowcol(gdf)
print(f"Backend: shape={backend.shape}, {len(rows):,} valid cells")

# ── 2. run our raster discrete port ───────────────────────────────────────────

env = Environment(end_time=N_STEPS - 1)

demand = DemandPreComputedValues(annual_demand=ANNUAL_DEMAND, land_use_types=LAND_USE_TYPES)

PotentialDLogisticRegression(
    backend=backend, potential_data=POTENTIAL_DATA, land_use_types=LAND_USE_TYPES,
)

AllocationDClueSLike(
    backend=backend, demand=demand, land_use_types=LAND_USE_TYPES,
    transition_matrix=TRANSITION_MATRIX, cell_area=CELL_AREA,
    max_difference=10.0, max_iteration=1000, factor_iteration=0.0001,
)

env.run()

for i, lu in enumerate(LAND_USE_TYPES):
    n = int((backend.get(lu)[backend.get("mask").astype(bool)] == 1).sum())
    dem = ANNUAL_DEMAND[-1][i]
    print(f"  {lu}: allocated={n}  demand={dem}  diff={n - dem:+d}")

# ── 3. compare cell by cell against the real TerraME reference ───────────────

terrame = gpd.read_file(TERRAME_SHP)

ours_df = pd.DataFrame({
    "lin": rows, "col": cols, "d_ours": backend.get("d")[rows, cols],
}).set_index(["lin", "col"])
terrame_df = pd.DataFrame({
    "lin": terrame["lin"].astype(int).values,
    "col": terrame["col"].astype(int).values,
    "d_terrame": terrame["d_out"].astype(float).values,
}).set_index(["lin", "col"])
aligned = ours_df.join(terrame_df, how="inner")
print(f"\nAligned cells: {len(aligned):,}")

m = pontius_millones(aligned["d_ours"].values, aligned["d_terrame"].values)
print("\nPontius & Millones -- disslucc discrete (new raster) vs real TerraME, class 'd':")
for k, v in m.items():
    print(f"  {k:>24}: {v}")

c = confusion_metrics(aligned["d_ours"].values, aligned["d_terrame"].values)
print(f"\nAccuracy: {c['accuracy']:.4f}%   F1: {c['f1']:.4f}   (TP={c['tp']} TN={c['tn']} FP={c['fp']} FN={c['fn']})")

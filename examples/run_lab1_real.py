"""
Runs the same disslucc package (raster-only) used in run_script.py, but
with REAL Lab1 data from disslucc-continuous -- csAC.zip shapefile
(real region, 6574 cells), coefficients calibrated from model.toml,
real demand from examples_demand_lab1.csv.

Scenario: f (forest) / d (deforestation) / outros -- the classic
LuccME/TerraME Amazon deforestation dynamics tutorial.

Requires geopandas (already a transitive dissmodel dependency).
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from dissmodel.core import Environment
from dissmodel.io.convert import vector_to_raster_backend

from disslucc import (
    AllocationClueLike,
    DemandPreComputedValues,
    PotentialLinearRegression,
)
from disslucc.components.demand import load_demand_csv
from disslucc.schemas import AllocationSpec, RegressionSpec

ROOT = Path(__file__).resolve().parent.parent
CSAC_ZIP = ROOT / "data" / "input" / "csAC.zip"
DEMAND_CSV = ROOT / "data" / "input" / "examples_demand_lab1.csv"

LAND_USE_TYPES = ["f", "d", "outros"]
DRIVER_COLS = ["assentamen", "uc_us", "uc_pi", "ti", "dist_riobr", "fertilidad", "rodovias"]
COMPLEMENTAR_LU = "f"
N_STEPS = 7
RESOLUTION = 5000.0
CELL_AREA = 25.0

# ── 1. load the real shapefile and rasterize (same call as the real executor) ─

gdf = gpd.read_file(CSAC_ZIP)
attrs = {lu: 0.0 for lu in LAND_USE_TYPES}
attrs.update({col: 0.0 for col in DRIVER_COLS})

backend = vector_to_raster_backend(
    source=gdf, resolution=RESOLUTION, attrs=attrs, nodata_value=-1,
)
print(f"Rasterized: shape={backend.shape}, valid cells={int(backend.get('mask').sum()):,}")

# ── 2. real demand from the CSV ───────────────────────────────────────────────

demand_raw = DEMAND_CSV.read_text()
annual_demand = load_demand_csv(demand_raw, LAND_USE_TYPES)

# ── 3. builds Demand -> Potential -> Allocation with the real coefficients ────

env = Environment(end_time=N_STEPS - 1)

demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=LAND_USE_TYPES)

potential = PotentialLinearRegression(
    backend=backend,
    demand=demand,
    land_use_types=LAND_USE_TYPES,
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
    backend=backend,
    demand=demand,
    potential=potential,
    land_use_types=LAND_USE_TYPES,
    static={"f": -1, "d": -1, "outros": 1},
    complementar_lu=COMPLEMENTAR_LU,
    cell_area=CELL_AREA,
    allocation_data=[
        AllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),
        AllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),
        AllocationSpec(static=1, min_value=0, max_value=1, min_change=0, max_change=1),
    ],
)

env.run()

print("\nLast-step demand target vs allocated area (ha, cell_area=25):")
for i, lu in enumerate(LAND_USE_TYPES):
    target = annual_demand[-1][i]
    mask = backend.get("mask").astype(bool)
    actual = float(backend.get(lu)[mask].sum()) * CELL_AREA
    print(f"  {lu:>8}: target={target:12.1f}  allocated={actual:12.1f}  diff={abs(target - actual):8.1f}")

# ── quicklook -----------------------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np

mask = backend.get("mask").astype(bool)
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for ax, lu in zip(axes, LAND_USE_TYPES):
    arr = np.where(mask, backend.get(lu), np.nan)
    im = ax.imshow(arr, cmap="viridis", vmin=0, vmax=1)
    ax.set_title(lu)
    ax.axis("off")
fig.colorbar(im, ax=axes, shrink=0.7, label="cell fraction")
fig.suptitle(f"csAC (real data) — land use after {N_STEPS - 1} steps")
fig.savefig("quicklook_lab1_real.png", dpi=120)
plt.close(fig)
print("\nquicklook saved to: quicklook_lab1_real.png")

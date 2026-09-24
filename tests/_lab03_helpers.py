"""
tests/_lab03_helpers.py
-----------------------
Shared by the tests of PotentialSpatialLagRegression and
AllocationClueLikeSaturation against the LuccME goldens of lab03 and lab06
(benchmark/goldens/, from LambdaGeo/terrame-docker v0.1.1).

Both labs: DemandPreComputedValues + PotentialCSpatialLagRegression +
AllocationCClueLikeSaturation on csAC (data/input/csAC.zip), 2008–2014, the same
coefficients, demand and allocation data (luccme/tests/functional/lab03.lua,
lab06.lua). lab06 also replaces `ti` from csAC_2009 in 2009 (`updateYears`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from dissmodel.core import Environment, Model
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import (
    AllocationClueLikeSaturation,
    DemandPreComputedValues,
    PotentialSpatialLagRegression,
    SaturationAllocationSpec,
    SpatialLagRegressionSpec,
)
from disslucc.components.potential.spatial_lag import spatial_lag_regression

ROOT = Path(__file__).resolve().parent.parent
GOLDENS = ROOT / "benchmark" / "goldens"
INPUT = ROOT / "data" / "input"
LAND_USES = ["f", "d", "outros"]
NO_DATA = "outros"
YEARS = list(range(2008, 2015))
# luccme/tests/functional/lab03.lua and lab06.lua (identical in both)
DEMAND = [
    [137878.1691, 19982.62882, 6489.202049],
    [137622.2199, 20238.57805, 6489.202049],
    [137366.2707, 20494.52729, 6489.202049],
    [137110.3214, 20750.47652, 6489.202049],
    [136824.6853, 21036.11265, 6489.202049],
    [136539.0492, 21321.74879, 6489.202049],
    [136253.4130, 21607.38493, 6489.202049],
]
UPDATES = {"lab03": {}, "lab06": {2009: "csAC_2009.zip"}}


def specs() -> list[SpatialLagRegressionSpec]:
    return [
        SpatialLagRegressionSpec(
            const=0.05266679,
            ro=0.9124615,
            betas={"uc_us": 0.03789872, "uc_pi": 0.04141921, "ti": 0.04455667},
        ),
        SpatialLagRegressionSpec(
            const=0.01431553,
            ro=0.9019253,
            betas={
                "assentamen": 0.0443537,
                "uc_us": -0.01454847,
                "fertilidad": 0.01701601,
                "dist_riobr": -0.00000002262071,
            },
        ),
        SpatialLagRegressionSpec(const=0, ro=0, betas={}),
    ]


class Lab:
    """csAC on a raster by (row, col), the golden, and the dynamic-variable updates."""

    def __init__(self, name: str):
        self.name = name
        self.cells = gpd.read_file(INPUT / "csAC.zip")
        self.rows = self.cells["row"].astype(int).values
        self.cols = self.cells["col"].astype(int).values
        self.shape = (self.rows.max() + 1, self.cols.max() + 1)
        self.valid = self.grid(np.ones(len(self.cells))) > 0
        self.golden = pd.read_csv(GOLDENS / name / f"{name}.csv.gz")
        self.manifest = json.loads((GOLDENS / name / "manifest.json").read_text())
        self.drivers_used = sorted({d for s in specs() for d in s.betas})

    def grid(self, values) -> np.ndarray:
        a = np.zeros(self.shape)
        a[self.rows, self.cols] = np.asarray(values, dtype=np.float64)
        return a

    def initial(self, column: str) -> np.ndarray:
        return self.grid(self.cells[column].astype(float).values)

    def drivers(self, year: int, pair_by: str = "position") -> dict[str, np.ndarray]:
        """Drivers in effect in `year`. LuccME's updateYears copies the columns
        of the <layer>_<year> file into the cells *by position* (forEachCellPair),
        although csAC_2009 is not in the same order as csAC; `pair_by="id"`
        pairs by object_id0 instead (used to show the difference matters)."""
        cells = self.cells.copy()
        for upd_year, file in sorted(UPDATES[self.name].items()):
            if year >= upd_year:
                new = gpd.read_file(INPUT / file)
                if pair_by == "id":
                    new = cells[["object_id0"]].merge(
                        new.drop(columns="geometry"), on="object_id0", how="left"
                    )
                for col in new.columns:
                    if col in cells.columns and col not in ("geometry", "object_id0"):
                        cells[col] = new[col].values
        return {d: self.grid(cells[d].astype(float).values) for d in self.drivers_used}

    def golden_year(self, year: int) -> pd.DataFrame:
        return self.golden[self.golden["year"] == year].set_index(["row", "col"])

    def past(self, year: int) -> dict[str, np.ndarray]:
        """Land use at the start of `year`: initial attributes, then the golden's previous year."""
        if year == YEARS[0]:
            return {lu: self.initial(lu) for lu in LAND_USES}
        prev = self.golden_year(year - 1).reindex(list(zip(self.rows, self.cols)))
        return {lu: self.grid(prev[f"{lu}_out"].values) for lu in LAND_USES}


def adapted_consts(cumulative: bool = True) -> dict[int, list[float]]:
    """const in effect each year. LuccME writes the adapted constant back into
    `const`, so the adaptation accumulates; `cumulative=False` is the other
    reading of the code, kept to show the golden tells them apart."""
    base = [s.const for s in specs()]
    out, cur = {}, list(base)
    for t, year in enumerate(YEARS):
        if t > 0:
            start = cur if cumulative else base
            cur = [
                start[i] + 0.01 * (DEMAND[t][i] - DEMAND[t - 1][i]) / DEMAND[t - 1][i]
                for i in range(len(LAND_USES))
            ]
        out[year] = list(cur)
    return out


def max_errors(lab: Lab, cumulative: bool = True, pair_by: str = "position") -> dict[tuple[int, str], float]:
    consts = adapted_consts(cumulative)
    errors = {}
    for year in YEARS:
        past = lab.past(year)
        drivers = lab.drivers(year, pair_by)
        ref = lab.golden_year(year)
        r = ref.index.get_level_values("row").values
        c = ref.index.get_level_values("col").values
        for i, (lu, spec) in enumerate(zip(LAND_USES, specs(), strict=True)):
            spec.const = consts[year][i]
            _, pot = spatial_lag_regression(spec, past[lu], drivers, lab.valid, past[NO_DATA])
            errors[(year, lu)] = float(np.abs(pot[r, c] - ref[f"{lu}_pot"].values).max())
    return errors


CELL_AREA = 25  # lab03.lua / lab06.lua: cellArea = 25
# lab03.lua / lab06.lua allocationData, region 1
ALLOCATION = [
    SaturationAllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),  # f
    SaturationAllocationSpec(static=-1, min_value=0, max_value=1, min_change=0, max_change=1),  # d
    SaturationAllocationSpec(static=1, min_value=0, max_value=1, min_change=0, max_change=1),  # outros
]


def terrame_log(name: str) -> dict[int, tuple[int, float]]:
    """year → (iterations, maximum error) from the golden's TerraME log."""
    text = (GOLDENS / name / "terrame.log").read_text()
    pattern = (
        r"Demand allocated correctly in (\d+)\s+Number of iterations: (\d+)\s+Maximum error: ([\d.eE+-]+)"
    )
    return {int(y): (int(n), float(e)) for y, n, e in re.findall(pattern, text)}


def run(lab: Lab, order: str = "file"):
    """Run the model from 2008 to 2014; return per-year snapshots and the allocation."""
    backend = RasterBackend(shape=lab.shape)
    for lu in LAND_USES:
        backend.set(lu, lab.initial(lu))
    for name, arr in lab.drivers(YEARS[0]).items():
        backend.set(name, arr)
    backend.set("mask", lab.valid.astype(np.float32))
    # the order in which TerraME visits the cells: the layer's (file) order
    visit = (
        np.arange(len(lab.cells)) if order == "file" else np.random.default_rng(0).permutation(len(lab.cells))
    )
    backend.set("order", lab.grid(visit))

    class Updates(Model):
        """LuccME's updateYears: this year's drivers, before demand and potential."""

        def execute(self):
            year = YEARS[0] + int(self.env.now())
            for name, arr in lab.drivers(year).items():
                backend.set(name, arr)

    snaps: dict[int, dict[str, np.ndarray]] = {}

    class Record(Model):
        def execute(self):
            year = YEARS[0] + int(self.env.now())
            snaps[year] = {
                **{f"{lu}_out": backend.get(lu).copy() for lu in LAND_USES},
                **{f"{lu}_pot": backend.get(f"{lu}_pot").copy() for lu in LAND_USES},
            }

    env = Environment(end_time=len(YEARS) - 1)
    Updates()
    demand = DemandPreComputedValues(annual_demand=DEMAND, land_use_types=LAND_USES)
    potential = PotentialSpatialLagRegression(
        backend=backend,
        potential_data=[specs()],
        demand=demand,
        land_use_types=LAND_USES,
        land_use_no_data=NO_DATA,
    )
    allocation = AllocationClueLikeSaturation(
        backend=backend,
        demand=demand,
        potential=potential,
        land_use_types=LAND_USES,
        allocation_data=[ALLOCATION],
        complementar_lu="f",
        cell_area=CELL_AREA,
        land_use_no_data=NO_DATA,
        attr_protection="uc_pi",
        max_difference=1643,
        max_iteration=1000,
        initial_elasticity=0.1,
        min_elasticity=0.001,
        max_elasticity=1.5,
        order_attr="order",
    )
    Record()
    env.run()
    return snaps, allocation


def worst_per_column(lab: Lab, snaps) -> dict[str, tuple[int, float]]:
    worst: dict[str, tuple[int, float]] = {}
    for year in YEARS:
        ref = lab.golden_year(year)
        r = ref.index.get_level_values("row").values
        c = ref.index.get_level_values("col").values
        for col, arr in snaps[year].items():
            err = float(np.abs(arr[r, c] - ref[col].values).max())
            if col not in worst or err > worst[col][1]:
                worst[col] = (year, err)
    return worst



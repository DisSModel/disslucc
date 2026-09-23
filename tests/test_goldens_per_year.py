"""
tests/test_goldens_per_year.py
--------------------------------
Year-by-year comparison against the LuccME goldens in benchmark/goldens/
(TerraME 2.0.1 + LuccME 6244dd4, generated with LambdaGeo/terrame-docker).

For each scenario, every simulated year is checked, not only the last one:
  * the convergence-loop iteration count per year must equal TerraME's
    (an integer that is very sensitive to the loop: elasticity/iter_vec updates);
  * `<lu>_out` and `<lu>_pot` of every class must match (MAE per year < 1e-6;
    what remains is float32 noise, ~1e-8).

Scenarios: the package labs (lab01: maxDifference 5000, lab15: 300), whose
allocation is accepted at the first pass every year, and the variants
lab01_md1643 / lab15_md10 (terrame-docker's benchmark/references/), which iterate
8-26 and 56-67 times per year and so exercise the convergence loop.

Continuous (CClueLike): LuccME's correctCellChange never runs. Its guard is
`if (cell.regionregionAloc == rNumber)` (AllocationCClueLike.lua:503, a typo for
regionAloc), which is always false. disslucc runs the correction by default
(`cell_correction=True`, the intended algorithm); with `cell_correction=False` it
reproduces TerraME in every year and every iteration count, which is what the
comparison tests below use.
"""
from __future__ import annotations

import _lab1_helpers as L1
import _lab15_helpers as L15
import geopandas as gpd
import pytest
from _golden_helpers import (
    YearRecorder,
    golden_available,
    golden_iterations,
    load_golden,
    per_year_frame,
    per_year_mae,
)
from dissmodel.core import Environment

from disslucc import (
    AllocationClueLike,
    AllocationDClueSLike,
    DemandPreComputedValues,
    PotentialDLogisticRegression,
    PotentialLinearRegression,
)
from disslucc.components.demand import load_demand_csv

MAE_TOL = 1e-6


def run_lab1(max_difference: float, cell_correction: bool):
    gdf = gpd.read_file(L1.CSAC_ZIP)
    backend, rows, cols = L1.build_backend_by_rowcol(gdf)
    annual_demand = load_demand_csv(L1.DEMAND_CSV.read_text(), L1.LAND_USE_TYPES)
    env = Environment(end_time=L1.N_STEPS - 1)

    demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=L1.LAND_USE_TYPES)
    potential = PotentialLinearRegression(
        backend=backend, demand=demand, land_use_types=L1.LAND_USE_TYPES,
        land_use_no_data="outros", potential_data=L1.DEFAULT_POTENTIAL_DATA,
    )
    allocation = AllocationClueLike(
        backend=backend, demand=demand, potential=potential,
        land_use_types=L1.LAND_USE_TYPES,
        static={"f": -1, "d": -1, "outros": 1},
        complementar_lu="f", cell_area=L1.CELL_AREA,
        allocation_data=L1.DEFAULT_ALLOCATION_DATA,
        max_difference=max_difference,
        cell_correction=cell_correction,
    )
    recorder = YearRecorder(backend=backend, rows=rows, cols=cols, land_use_types=L1.LAND_USE_TYPES)
    env.run()
    return allocation, per_year_frame(recorder, list(range(2008, 2015)))


def run_lab15(max_difference: float):
    gdf = L15.load_gdf_input()
    backend, rows, cols = L15.build_backend_by_rowcol(gdf)
    env = Environment(end_time=len(L15.ANNUAL_DEMAND) - 1)

    demand = DemandPreComputedValues(annual_demand=L15.ANNUAL_DEMAND, land_use_types=L15.LAND_USE_TYPES)
    PotentialDLogisticRegression(
        backend=backend, potential_data=L15.DEFAULT_POTENTIAL_DATA, land_use_types=L15.LAND_USE_TYPES,
    )
    allocation = AllocationDClueSLike(
        backend=backend, demand=demand, land_use_types=L15.LAND_USE_TYPES,
        transition_matrix=L15.TRANSITION_MATRIX, cell_area=L15.CELL_AREA,
        max_difference=max_difference, max_iteration=1000, factor_iteration=0.0001,
    )
    recorder = YearRecorder(backend=backend, rows=rows, cols=cols, land_use_types=L15.LAND_USE_TYPES)
    env.run()
    return allocation, per_year_frame(recorder, list(range(1999, 2005)))


def assert_matches_golden(name: str, allocation, ours) -> None:
    golden, manifest = load_golden(name)

    assert allocation.iterations_per_step == golden_iterations(manifest), (
        f"{name}: iterations per year differ from TerraME -- "
        f"disslucc {allocation.iterations_per_step}, TerraME {golden_iterations(manifest)}"
    )
    for column in ours.columns:
        mae = per_year_mae(ours, golden, column)
        worst_year = max(mae, key=lambda y: mae[y])
        assert mae[worst_year] < MAE_TOL, (
            f"{name}: {column} diverges from TerraME, first in "
            f"{min(y for y, v in mae.items() if v >= MAE_TOL)} (MAE per year: {mae})"
        )


# ── discrete (CLUE-S-like) ────────────────────────────────────────────────────

@pytest.mark.skipif(not L15.data_available, reason="Lab15 input data not found")
@pytest.mark.parametrize("name, max_difference", [("lab15", 300.0), ("lab15_md10", 10.0)])
def test_lab15_matches_terrame_every_year(name: str, max_difference: float) -> None:
    if not golden_available(name):
        pytest.skip(f"golden {name} not found")
    allocation, ours = run_lab15(max_difference)
    assert_matches_golden(name, allocation, ours)


# ── continuous (CLUE-like) ────────────────────────────────────────────────────

@pytest.mark.skipif(not L1.data_available, reason="Lab1 input data not found")
@pytest.mark.parametrize("name, max_difference", [("lab01", 5000.0), ("lab01_md1643", 1643.0)])
def test_lab1_matches_terrame_every_year_without_cell_correction(name: str, max_difference: float) -> None:
    if not golden_available(name):
        pytest.skip(f"golden {name} not found")
    allocation, ours = run_lab1(max_difference, cell_correction=False)
    assert_matches_golden(name, allocation, ours)


@pytest.mark.skipif(not L1.data_available, reason="Lab1 input data not found")
def test_lab1_default_cell_correction_deviates_from_terrame() -> None:
    """Characterisation, not a requirement: the default (`cell_correction=True`,
    the intended algorithm) deliberately differs from TerraME, which never runs
    correctCellChange. Pins the size of that deviation so a change to the
    correction step, or to the default, does not go unnoticed. The final-year
    numbers are the ones in docs/validation.md (MAE 0.003583)."""
    if not golden_available("lab01_md1643"):
        pytest.skip("golden lab01_md1643 not found")
    allocation, ours = run_lab1(1643.0, cell_correction=True)
    golden, _ = load_golden("lab01_md1643")

    assert allocation.iterations_per_step == [0, 0, 0, 14, 17, 16, 16]
    mae = per_year_mae(ours, golden, "d_out")
    assert mae[2008] == pytest.approx(0.0, abs=MAE_TOL)
    assert mae[2009] > MAE_TOL  # the correction acts from the first year with change
    assert mae[2014] == pytest.approx(0.003583, abs=5e-7)

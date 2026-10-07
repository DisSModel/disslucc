"""
tests/test_demand_dates.py
---------------------------
DemandComputeTwoDates / DemandComputeThreeDates (LuccME demand interpolated
from the land-use layers).

The expected tables below are what these components produce on the layers in
data/input; with them lab04, lab05, lab16 and lab17 reproduce the TerraME
goldens (disslucc-benchmark), so they are the demand LuccME computes.
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import DemandComputeThreeDates, DemandComputeTwoDates
from disslucc.components.demand.dates import interpolate_three_dates, interpolate_two_dates

DATA = Path(__file__).resolve().parent.parent / "data" / "input"


# ── the interpolation itself ─────────────────────────────────────────────────────────────────

def test_rounding_accumulates_on_the_rounded_previous_year():
    # LuccME adds the step to the already rounded demand: 10 + 0.4 -> 10 every year,
    # then the final year is set exactly. Exact linear interpolation would give 10, 11, 11, 12.
    assert interpolate_two_dates([10], [12], final_offset=5, n_years=6) == [[10], [10], [10], [10], [10], [12]]


def test_rounds_half_up():
    # step 0.5: 0 -> floor(0.5 + 0.5) = 1 (Python's round() would give 0)
    assert interpolate_two_dates([0], [1], final_offset=2, n_years=3) == [[0], [1], [1]]


def test_direction_from_the_data_and_static_class():
    rows = interpolate_two_dates([100, 50, 7], [110, 40, 7], final_offset=2, n_years=3)
    assert rows == [[100, 50, 7], [105, 45, 7], [110, 40, 7]]


def test_given_direction_overrides_the_sign():
    # "Decrease" on a growing class steps down, then the final year is set exactly (as in LuccME)
    rows = interpolate_two_dates([100], [110], final_offset=2, n_years=3, direction=["Decrease"])
    assert rows == [[100], [95], [110]]
    # anything else than Increase / Decrease means stable
    rows = interpolate_two_dates([100], [110], final_offset=2, n_years=3, direction=["Stable"])
    assert rows == [[100], [100], [110]]


def test_keeps_the_same_step_after_the_final_year():
    assert interpolate_two_dates([0], [10], final_offset=2, n_years=5) == [[0], [5], [10], [15], [20]]


def test_stops_before_the_final_year():
    assert interpolate_two_dates([0], [10], final_offset=5, n_years=3) == [[0], [2], [4]]


def test_three_dates_two_segments():
    rows = interpolate_three_dates([0], [10], [14], middle_offset=2, final_offset=4, n_years=5)
    assert rows == [[0], [5], [10], [12], [14]]


def test_three_dates_final_year_after_the_end_of_the_run():
    # lab17: the final year (2007) is later than the last simulated year (2004)
    rows = interpolate_three_dates([0], [10], [14], middle_offset=2, final_offset=4, n_years=3)
    assert rows == [[0], [5], [10]]


@pytest.mark.parametrize("call", [
    lambda: interpolate_two_dates([1], [2], final_offset=0, n_years=3),
    lambda: interpolate_three_dates([1], [2], [3], middle_offset=3, final_offset=3, n_years=5),
    lambda: interpolate_three_dates([1], [2], [3], middle_offset=0, final_offset=3, n_years=5),
])
def test_invalid_years_are_rejected(call):
    with pytest.raises(ValueError):
        call()


# ── the components: areas read from the layers ───────────────────────────────────────────────

def _backend(layers: dict, mask=None) -> RasterBackend:
    shape = np.asarray(next(iter(layers.values()))).shape
    backend = RasterBackend(shape=shape)
    backend.set("mask", np.ones(shape, bool) if mask is None else mask)
    for name, arr in layers.items():
        backend.set(name, np.asarray(arr, dtype=np.float64))
    return backend


def test_two_dates_sums_cell_area_over_valid_cells_only():
    mask = np.array([[True, True], [True, False]])
    backend = _backend({
        "f": [[1, 1], [0, 1]], "d": [[0, 0], [1, 0]],     # the unmasked cell is ignored
        "f9": [[1, 0], [0, 1]], "d9": [[0, 1], [1, 0]],
    }, mask)
    Environment(end_time=2)
    demand = DemandComputeTwoDates(
        backend=backend, land_use_types=["f", "d"], final_land_use_types=["f9", "d9"],
        start_year=2000, end_year=2002, final_year=2002, cell_area=25.0,
    )
    # start: f = 2 cells (50), d = 1 cell (25); final: f = 1 cell (25), d = 2 cells (50); step 12.5,
    # applied to the rounded previous year: 50 - 12.5 = 37.5 -> 38 and 25 + 12.5 = 37.5 -> 38
    assert demand.annual_demand == [[50, 25], [38, 38], [25, 50]]


def test_the_mask_matters():
    layers = {"f": [[1, 1], [0, 1]], "f9": [[1, 0], [0, 1]]}
    Environment(end_time=1)
    full = DemandComputeTwoDates(backend=_backend(layers), land_use_types=["f"], final_land_use_types=["f9"],
                                 start_year=0, end_year=1, final_year=1, cell_area=1.0)
    assert full.annual_demand == [[3], [2]]


def test_component_exposes_the_demand_protocol():
    backend = _backend({"f": [[4]], "d": [[0]], "f9": [[2]], "d9": [[2]]})
    env = Environment(end_time=1)
    demand = DemandComputeTwoDates(backend=backend, land_use_types=["f", "d"], final_land_use_types=["f9", "d9"],
                                   start_year=0, end_year=1, final_year=1, cell_area=1.0)
    env._now = 1
    demand.execute()
    assert demand.get_current_lu_demand(0) == 2 and demand.get_previous_lu_demand(0) == 4
    assert demand.get_current_lu_direction(0) == -1 and demand.get_current_lu_direction(1) == 1


def test_mismatched_layer_lists_are_rejected():
    backend = _backend({"f": [[1]], "d": [[1]], "f9": [[1]]})
    Environment(end_time=1)
    with pytest.raises(ValueError):
        DemandComputeTwoDates(backend=backend, land_use_types=["f", "d"], final_land_use_types=["f9"],
                              start_year=0, end_year=1, final_year=1, cell_area=1.0)
    with pytest.raises(ValueError):
        DemandComputeThreeDates(backend=backend, land_use_types=["f"], middle_land_use_types=["f9"],
                                final_land_use_types=["f9"], start_year=0, end_year=2, middle_year=1, final_year=2,
                                cell_area=1.0, direction_for_interpolation=["Increase", "Decrease"])


# ── LuccME labs 04, 05, 16, 17 on the layers in data/input ───────────────────────────────────

def _layer_backend(name: str, columns: list[str]) -> RasterBackend:
    cells = gpd.read_file(DATA / f"{name}.zip")
    rows = cells["row" if "row" in cells else "lin"].astype(int).values
    cols = cells["col"].astype(int).values
    shape = (rows.max() + 1, cols.max() + 1)
    backend = RasterBackend(shape=shape)
    mask = np.zeros(shape, bool)
    mask[rows, cols] = True
    backend.set("mask", mask)
    for c in columns:
        arr = np.zeros(shape)
        arr[rows, cols] = cells[c].astype(float).values
        backend.set(c, arr)
    return backend


CSAC = ["f", "d", "outros", "f2011", "d2011", "f2014", "d2014"]
MOJU = ["f", "d", "o", "f04", "d04", "f07", "d07"]


def test_lab04_two_dates_csac():
    backend = _layer_backend("csAC", CSAC)
    Environment(end_time=6)
    demand = DemandComputeTwoDates(
        backend=backend, land_use_types=["f", "d", "outros"], final_land_use_types=["f2014", "d2014", "outros"],
        start_year=2008, end_year=2014, final_year=2014, cell_area=25.0)
    assert demand.annual_demand == [
        [137878, 19983, 6489], [137607, 20254, 6489], [137336, 20525, 6489], [137065, 20796, 6489],
        [136794, 21067, 6489], [136523, 21338, 6489], [136253, 21607, 6489]]


def test_lab05_three_dates_csac():
    backend = _layer_backend("csAC", CSAC)
    Environment(end_time=6)
    demand = DemandComputeThreeDates(
        backend=backend, land_use_types=["f", "d", "outros"], middle_land_use_types=["f2011", "d2011", "outros"],
        final_land_use_types=["f2014", "d2014", "outros"], start_year=2008, end_year=2014, middle_year=2011,
        final_year=2014, cell_area=25.0)
    assert demand.annual_demand == [
        [137878, 19983, 6489], [137622, 20239, 6489], [137366, 20495, 6489], [137110, 20750, 6489],
        [136824, 21036, 6489], [136538, 21322, 6489], [136253, 21607, 6489]]


MOJU_TABLE = [[5706, 205, 3], [5658, 253, 3], [5610, 301, 3], [5562, 349, 3], [5514, 397, 3], [5468, 443, 3]]


def test_lab16_two_dates_moju():
    backend = _layer_backend("cs_moju", MOJU)
    Environment(end_time=5)
    demand = DemandComputeTwoDates(
        backend=backend, land_use_types=["f", "d", "o"], final_land_use_types=["f04", "d04", "o"],
        start_year=1999, end_year=2004, final_year=2004, cell_area=1.0)
    assert demand.annual_demand == MOJU_TABLE


def test_lab17_three_dates_moju_final_year_after_the_run():
    backend = _layer_backend("cs_moju", MOJU)
    Environment(end_time=5)
    demand = DemandComputeThreeDates(
        backend=backend, land_use_types=["f", "d", "o"], middle_land_use_types=["f04", "d04", "o"],
        final_land_use_types=["f07", "d07", "o"], start_year=1999, end_year=2004, middle_year=2004,
        final_year=2007, cell_area=1.0)
    assert demand.annual_demand == MOJU_TABLE

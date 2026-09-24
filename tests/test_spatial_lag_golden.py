"""
PotentialSpatialLagRegression against the LuccME goldens of lab03 and lab06.

Goldens (benchmark/goldens/, from LambdaGeo/terrame-docker v0.1.1): the state of every
cell at the end of every year, 2008–2014, with <lu>_out and <lu>_pot. Both labs
use DemandPreComputedValues + PotentialCSpatialLagRegression +
AllocationCClueLikeSaturation; lab06 also replaces `ti` from csAC_2009 in 2009.

To test the potential alone, each year starts from the golden's own land use of
the year before (what LuccME's `cell.past` holds) — so an error cannot come from
the allocation. The allocation can still shift `newconst` by ±0.1 during a year
(`modify`); in these two labs it never does, so the potential must match exactly
(the golden keeps 12 decimals: tolerance 1e-10).
"""

from __future__ import annotations

import numpy as np
import pytest
from _lab03_helpers import DEMAND, LAND_USES, NO_DATA, YEARS, Lab, max_errors, specs
from dissmodel.core import Environment, Model
from dissmodel.geo.raster.backend import RasterBackend

from disslucc import DemandPreComputedValues, PotentialSpatialLagRegression, SpatialLagRegressionSpec
from disslucc.components.potential.spatial_lag import spatial_lag_regression

TOL = 1e-10


@pytest.fixture(scope="module", params=["lab03", "lab06"])
def lab(request) -> Lab:
    return Lab(request.param)


def test_golden_is_the_expected_run(lab):
    assert lab.manifest["status"] == "ok"
    assert lab.manifest["years"] == [YEARS[0], YEARS[-1]]
    assert lab.manifest["n_cells"] == len(lab.cells) == len(lab.golden_year(2008))


def test_potential_matches_golden_every_year_and_class(lab):
    errors = max_errors(lab)
    worst = max(errors, key=errors.get)
    assert errors[worst] < TOL, f"{lab.name}: worst {worst} = {errors[worst]:.3e}"


def test_clipping_is_exercised(lab):
    """The golden constrains the clip branch only if some cells hit it: count the
    cells whose value changes when the bounds are removed."""
    past, drivers = lab.past(2008), lab.drivers(2008)
    clipped = 0
    for lu, spec in zip(LAND_USES, specs(), strict=True):
        free = SpatialLagRegressionSpec(
            const=spec.const, ro=spec.ro, betas=spec.betas, min_reg=-np.inf, max_reg=np.inf
        )
        reg, _ = spatial_lag_regression(spec, past[lu], drivers, lab.valid, past[NO_DATA])
        reg_free, _ = spatial_lag_regression(free, past[lu], drivers, lab.valid, past[NO_DATA])
        clipped += int((np.abs(reg - reg_free)[lab.valid] > 1e-12).sum())
    assert clipped > 0


def test_non_cumulative_adaptation_is_rejected(lab):
    errors = max_errors(lab, cumulative=False)
    assert max(v for (y, _), v in errors.items() if y >= 2010) > 1e-4


def test_updates_pair_cells_by_position_not_by_id():
    lab = Lab("lab06")
    by_id = max_errors(lab, pair_by="id")
    assert max(v for (y, _), v in by_id.items() if y >= 2009) > 1e-2


def test_component_matches_golden(lab):
    """The dissmodel component (what moves to disslucc), stepped in an Environment.

    A replay model runs before it each year and puts the golden's land use of the
    year before into the backend, plus the drivers of that year."""
    backend = RasterBackend(shape=lab.shape)
    for lu in LAND_USES:
        backend.set(lu, lab.initial(lu))
    for name, arr in lab.drivers(YEARS[0]).items():
        backend.set(name, arr)
    backend.set("mask", lab.valid.astype(np.float32))

    class Replay(Model):
        def setup(self):
            self.year = YEARS[0]

        def execute(self):
            self.year = YEARS[0] + int(self.env.now())
            if self.year > YEARS[0]:
                for lu, arr in lab.past(self.year).items():
                    backend.set(lu, arr)
                    backend.set(lu + "_past", arr.copy())
                for name, arr in lab.drivers(self.year).items():
                    backend.set(name, arr)

    got: dict[int, dict[str, np.ndarray]] = {}

    class Record(Model):
        def execute(self):
            year = YEARS[0] + int(self.env.now())
            got[year] = {lu: backend.get(lu + "_pot").copy() for lu in LAND_USES}

    env = Environment(end_time=len(YEARS) - 1)
    demand = DemandPreComputedValues(annual_demand=DEMAND, land_use_types=LAND_USES)
    Replay()
    PotentialSpatialLagRegression(
        backend=backend,
        potential_data=[specs()],
        demand=demand,
        land_use_types=LAND_USES,
        land_use_no_data=NO_DATA,
    )
    Record()
    env.run()

    assert sorted(got) == YEARS
    for year in YEARS:
        ref = lab.golden_year(year)
        r = ref.index.get_level_values("row").values
        c = ref.index.get_level_values("col").values
        for lu in LAND_USES:
            err = np.abs(got[year][lu][r, c] - ref[f"{lu}_pot"].values).max()
            assert err < TOL, f"{lab.name} {year} {lu}: {err:.3e}"

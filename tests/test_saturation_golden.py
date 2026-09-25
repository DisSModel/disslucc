"""
AllocationClueLikeSaturation + PotentialSpatialLagRegression against the LuccME
goldens of lab03 and lab06: the whole model, run from 2008 on its own (no replay).

Checked every year, 2008–2014:
- every cell's land use (<lu>_out) and potential (<lu>_pot) against the golden;
- the maximum error against the demand, and the iteration count, against the
  TerraME log (terrame.log: "Maximum error: …", "Number of iterations: …").

The saturation branch is not reached in these labs (change_limiar_value = 1),
so it is not constrained here; everything else in the allocation is.
"""

from __future__ import annotations

import pytest
from _lab03_helpers import ALLOCATION, YEARS, Lab, run, terrame_log, worst_per_column

TOL = 1e-9


@pytest.fixture(scope="module", params=["lab03", "lab06"])
def result(request):
    lab = Lab(request.param)
    snaps, allocation = run(lab)
    return lab, snaps, allocation


def test_land_use_and_potential_match_golden_every_year(result):
    lab, snaps, _ = result
    worst = worst_per_column(lab, snaps)
    bad = {col: w for col, w in worst.items() if w[1] >= TOL}
    assert not bad, f"{lab.name}: {bad}"


def test_iterations_and_error_match_terrame_log(result):
    lab, _, allocation = result
    log = terrame_log(lab.name)
    assert sorted(log) == YEARS
    assert allocation.iterations_per_step == [log[y][0] for y in YEARS]
    for year, ours in zip(YEARS, allocation.max_error_per_step, strict=True):
        assert ours == pytest.approx(log[year][1], rel=1e-9), year


def test_what_the_goldens_do_not_reach(monkeypatch):
    """In lab03 no cell ever needs correctCellChange (the classes always sum to
    1 ± 0.005 before it) and no cell is saturated (change_limiar_value = 1): the
    goldens say nothing about those parts, and the cells' visiting order has no
    effect. They are checked against the Lua itself in test_lua_differential.py."""
    import disslucc.components.allocation.saturation as sat

    stats: dict = {}
    original = sat.correct_cell_change
    monkeypatch.setattr(sat, "correct_cell_change", lambda v, p, s, d: original(v, p, s, d, stats))
    lab = Lab("lab03")
    run(lab)
    assert stats["need"] == 0
    assert all(s.change_limiar_value >= 1 for s in ALLOCATION)

    monkeypatch.setattr(sat, "correct_cell_change", original)
    snaps, _ = run(lab, order="shuffled")
    assert max(err for _, err in worst_per_column(lab, snaps).values()) < TOL

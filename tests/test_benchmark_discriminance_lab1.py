"""
tests/test_benchmark_discriminance_lab1.py
=============================================
Measures the **discriminative power** of the Lab1 benchmark. Ported
from disslucc-continuous/tests/test_benchmark_discriminance.py,
raster-only (disslucc has no vector substrate).

The question here is not "does the model reproduce TerraME?" but "can the
benchmark tell a correct implementation from an incorrect one?". Reproducing the
reference is necessary but not sufficient: if the test still passes with wrong
coefficients, it does not constrain the implementation.

Known state (inherited from disslucc-continuous, 2026-07-27)
--------------------------------------------------------------
**Lab1 is discriminative.** Every perturbation tested on the regression
coefficients breaks the tolerance criterion, including zeroing the drivers and
halving the betas. A do-nothing baseline fails too. Unlike the Lab15 scenario
in disslucc-discrete, there is no trivial shortcut.

On the convergence tolerance
------------------------------
The original LuccME script (``lab1.lua`` / ``lab1_submodel.lua``) declares
``maxDifference = 1643`` in ``AllocationCClueLike`` -- in area units, against a
2014 demand of 21607.38 for class ``d``. That is a **7.6% convergence band**,
and the Python defaults match it exactly.

This band is wide enough that the reference itself stops 1001.45 area units
short of the demand it declares, which is legitimate rather than a defect. It
also means Python and TerraME can each halt at different, equally valid points
inside the band -- which is why the fit varies non-monotonically with the
number of steps. See ``test_reference_gap_within_luccme_tolerance``.
"""
from __future__ import annotations

import copy

import geopandas as gpd
import numpy as np
import pytest
from _lab1_helpers import (
    CELL_AREA,
    CSAC_ZIP,
    DEFAULT_POTENTIAL_DATA,
    LUCCME_DEMAND_D_2014,
    LUCCME_MAX_DIFFERENCE,
    TOLERANCE,
    data_available,
    load_terrame_reference,
    run_lab1,
)

skip_if_no_data = pytest.mark.skipif(not data_available, reason="Lab1 data files not found")


def _scaled_potential_data(factor: float) -> list[list]:
    """Regression coefficients with every beta multiplied by ``factor``."""
    perturbed = copy.deepcopy(DEFAULT_POTENTIAL_DATA)
    for spec in perturbed[0]:
        if spec.betas:
            spec.betas = {c: v * factor for c, v in spec.betas.items()}
    return perturbed


# ══════════════════════════════════════════════════════════════════════════════
# 1. Discriminance -- perturbing the coefficients must break the test
# ══════════════════════════════════════════════════════════════════════════════

@skip_if_no_data
@pytest.mark.parametrize(
    "factor,description",
    [
        (0.0, "betas zeroed (no drivers)"),
        (0.5, "betas halved"),
        (2.0, "betas doubled"),
        (-1.0, "betas sign-flipped"),
    ],
)
def test_perturbed_coefficients_fail_tolerance(factor, description):
    """With wrong coefficients the benchmark must fail.

    If it passed, the tolerance would be too loose to constrain the
    implementation -- and the reported parity would carry no evidential weight.
    """
    m = run_lab1(potential_data=_scaled_potential_data(factor))

    assert m["mae"] >= TOLERANCE or m["rmse"] >= TOLERANCE, (
        f"With {description}, the benchmark still passed "
        f"(MAE={m['mae']:.6f}, RMSE={m['rmse']:.6f}). "
        "The tolerance does not constrain the implementation."
    )


@skip_if_no_data
def test_do_nothing_baseline_fails():
    """Keeping `d` at its initial value must fail the tolerance criterion."""
    gdf = gpd.read_file(str(CSAC_ZIP))
    ref = load_terrame_reference()

    d_initial = gdf["d"].values.astype(float)
    d_out = ref["d_out"].values.astype(float)
    mae = float(np.abs(d_initial - d_out).mean())

    assert mae >= TOLERANCE, (
        f"The do-nothing baseline has MAE={mae:.6f}, below the {TOLERANCE} "
        "tolerance. The benchmark would be satisfied without simulating anything."
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Characterisation -- what the benchmark does NOT cover
# ══════════════════════════════════════════════════════════════════════════════

@skip_if_no_data
def test_match_pct_is_reported_alongside_mae():
    """A low MAE coexists with a sizeable tail outside tolerance.

    This test imposes no floor on `match_pct` -- it records that the two numbers
    tell different stories, and that reporting MAE alone overstates agreement.
    """
    m = run_lab1()

    assert m["mae"] < TOLERANCE, "regression: the model no longer meets the criterion"
    assert m["match_pct"] < 100.0, (
        "If match_pct reached 100%, cell-by-cell agreement can be claimed -- it "
        "currently is not exact."
    )


@skip_if_no_data
def test_pontius_identity_holds():
    """quantity + allocation must reproduce MAE exactly."""
    m = run_lab1()
    total = m["quantity_disagreement"] + m["allocation_disagreement"]
    assert total == pytest.approx(m["mae"], abs=1e-12), (
        f"Pontius identity violated ({total:.9f} != {m['mae']:.9f})"
    )
    assert m["allocation_disagreement"] >= -1e-12, "negative allocation disagreement -- impossible"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Convergence tolerance -- why the fit varies with the number of steps
# ══════════════════════════════════════════════════════════════════════════════

@skip_if_no_data
def test_reference_gap_within_luccme_tolerance():
    """The reference falls short of its declared demand -- legitimately.

    ``AllocationCClueLike`` in the original script declares
    ``maxDifference = 1643`` area units. The reference stops ~1001 units short
    of the 2014 demand for ``d``, which is inside that band. This is correct
    behaviour, not a defect in the reference.
    """
    ref = load_terrame_reference()
    ref_area = float(ref["d_out"].values.astype(float).sum()) * CELL_AREA
    gap = abs(ref_area - LUCCME_DEMAND_D_2014)

    assert gap < LUCCME_MAX_DIFFERENCE, (
        f"The reference misses its declared demand by {gap:.2f} area units, "
        f"beyond the maxDifference={LUCCME_MAX_DIFFERENCE} declared in the "
        "LuccME script. That would indicate a genuine problem in the reference "
        "rather than ordinary convergence slack."
    )


@skip_if_no_data
def test_quantity_error_dominates_allocation_error():
    """Most of the residual is *how much*, not *where*.

    At the official configuration the error decomposes into roughly 90%
    quantity and 10% allocation: the model places deforestation in nearly the
    right cells and misses on the total. If this ever inverts -- allocation
    dominating -- the cause is spatial and warrants investigation, because the
    convergence band does not explain it.
    """
    m = run_lab1()
    assert m["quantity_disagreement"] > m["allocation_disagreement"], (
        f"Allocation disagreement ({m['allocation_disagreement']:.6f}) now "
        f"exceeds quantity ({m['quantity_disagreement']:.6f}). The residual is "
        "spatial and is no longer explained by the convergence tolerance."
    )

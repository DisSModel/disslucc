"""
tests/test_benchmark_discriminance_lab15.py
===============================================
Measures the **discriminative power** of the Lab15 benchmark. Ported
from disslucc-discrete/tests/test_benchmark_discriminance.py, adapted
from the vector substrate to disslucc's raster port.

The question these tests answer is not "does the model reproduce TerraME?" but
"can the benchmark tell a correct CLUE-S-like implementation from one that does
not implement CLUE-S at all?".

Reproducing the reference is necessary but not sufficient. If a trivial baseline
reaches the same parity, the benchmark is not measuring the algorithm.

Known state (inherited from disslucc-discrete, 2026-07-27)
--------------------------------------------------------------
The naive baseline -- a static ranking by ``prob_d - prob_f``, with no CLUE-S, no
iteration and no time steps -- reproduces the TerraME output **exactly**, cell for
cell, 5914/5914. The Lab15 scenario therefore validates only the transcription of
the logistic regression coefficients, **not** the allocation algorithm.

That is why ``test_benchmark_is_discriminative`` and
``test_trajectory_affects_result`` are marked as strict xfail, same as upstream.
If either ever XPASSes, the scenario has stopped being trivially reducible --
that is an improvement, and the marker should be removed.
"""
from __future__ import annotations

import pytest
from _lab15_helpers import (
    ANNUAL_DEMAND,
    DEFAULT_POTENTIAL_DATA,
    data_available,
    load_gdf_input,
    load_gdf_terrame,
    run_lab15_raster,
)

from disslucc.validation.naive_baseline import naive_allocation

skip_if_no_data = pytest.mark.skipif(not data_available, reason="Lab15 data files not found")


def _reference_binary(gdf_terrame):
    col = "d_out" if "d_out" in gdf_terrame.columns else "d"
    return (gdf_terrame[col].values >= 0.5).astype(int)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Characterisation -- does the naive baseline reproduce the reference?
# ══════════════════════════════════════════════════════════════════════════════

@skip_if_no_data
def test_naive_baseline_reproduces_terrame():
    """Records that a trivial static ranking already reproduces TerraME.

    This is NOT a requirement on the model -- it characterises a limitation of
    the benchmark scenario. If it ever fails, the scenario has stopped being
    trivially reducible, which would be an improvement.
    """
    gdf_input = load_gdf_input()
    gdf_terrame = load_gdf_terrame()
    ref = _reference_binary(gdf_terrame)

    pred = naive_allocation(gdf_input, n_target=int(ref.sum()), potential_data=DEFAULT_POTENTIAL_DATA)
    agreement = float((pred == ref).mean()) * 100

    assert agreement == pytest.approx(100.0, abs=1e-9), (
        f"The naive baseline agrees with TerraME on {agreement:.4f}% of cells. "
        "If this is no longer 100%, the scenario has changed -- revisit "
        "test_benchmark_is_discriminative, which may have stopped being xfail."
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. Discriminance -- does the benchmark tell CLUE-S-like from non-CLUE-S?
# ══════════════════════════════════════════════════════════════════════════════

@skip_if_no_data
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known limitation, inherited from disslucc-discrete: in the Lab15 "
        "scenario every covariate is static, the elasticity of f is 0.0 and d "
        "is irreversible, so allocation collapses into a static threshold. The "
        "naive baseline ties with CLUE-S-like. Making the benchmark "
        "discriminative requires a scenario with a dynamic covariate (for "
        "example, distance to deforestation updated every step), a reversible "
        "d->f transition, or multiple regions."
    ),
)
def test_benchmark_is_discriminative():
    """Full raster CLUE-S-like should outperform the naive baseline.

    While the two tie, the benchmark does not constrain the allocation
    algorithm -- it merely checks that the regression coefficients were
    transcribed correctly.
    """
    gdf_input = load_gdf_input()
    gdf_terrame = load_gdf_terrame()
    ref_full = _reference_binary(gdf_terrame)

    backend, rows, cols = run_lab15_raster()
    pred_clue = (backend.get("d")[rows, cols] >= 0.5).astype(int)

    # Align the raster result back onto gdf_input's row order via (lin, col).
    import pandas as pd
    idx_pred = pd.MultiIndex.from_arrays([rows, cols], names=["lin", "col"])
    s_pred = pd.Series(pred_clue, index=idx_pred)
    idx_terrame = pd.MultiIndex.from_arrays(
        [gdf_terrame["lin"].astype(int).values, gdf_terrame["col"].astype(int).values],
        names=["lin", "col"],
    )
    aligned_pred = s_pred.reindex(idx_terrame).values
    agreement_clue = float((aligned_pred == ref_full).mean()) * 100

    pred_naive = naive_allocation(gdf_input, n_target=int(ref_full.sum()), potential_data=DEFAULT_POTENTIAL_DATA)
    agreement_naive = float((pred_naive == ref_full).mean()) * 100

    assert agreement_clue > agreement_naive, (
        f"CLUE-S-like={agreement_clue:.4f}% vs naive baseline={agreement_naive:.4f}%. "
        "The benchmark cannot tell the algorithm from a trivial static ranking."
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. Sensitivity -- does the demand trajectory influence the result?
# ══════════════════════════════════════════════════════════════════════════════

@skip_if_no_data
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known limitation, inherited from disslucc-discrete: because d is "
        "irreversible and demand is monotonic, the final state depends only on "
        "the final demand, not on the path. Changing the intermediate "
        "trajectory does not change the result."
    ),
)
def test_trajectory_affects_result():
    """A different demand trajectory should produce a different result.

    If the final state is identical whether running 6 steps or 2 steps with an
    invented intermediate demand, the benchmark validates no temporal dynamics
    at all.
    """
    backend_official, rows, cols = run_lab15_raster(annual_demand=ANNUAL_DEMAND[:6])
    official = (backend_official.get("d")[rows, cols] >= 0.5).astype(int)

    # Same final demand, arbitrary intermediate path.
    first, last = ANNUAL_DEMAND[0], ANNUAL_DEMAND[5]
    midpoint = [(a + b) / 2 for a, b in zip(first, last)]
    backend_alt, rows_alt, cols_alt = run_lab15_raster(annual_demand=[first, midpoint, last])
    alternative = (backend_alt.get("d")[rows_alt, cols_alt] >= 0.5).astype(int)

    differing = int((official != alternative).sum())
    assert differing > 0, (
        "The intermediate trajectory does not affect the final result "
        f"({differing} differing cells). The benchmark validates no temporal "
        "dynamics."
    )

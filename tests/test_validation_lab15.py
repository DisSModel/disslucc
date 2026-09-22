"""
tests/test_validation_lab15.py
---------------------------------
Integration test: verifies 100% cell-level parity between disslucc's
raster CLUE-S-like port and the TerraME/LuccME reference (Lab15,
cs_moju, 1999-2004). Ported from
disslucc-discrete/tests/test_validation_lab15.py, adapted from the
vector to the raster substrate.

Kappa is not asserted: it is deprecated across the ecosystem in favour
of the Pontius & Millones (2011) decomposition. See also
``test_benchmark_discriminance_lab15.py`` -- this scenario is
reproduced by a trivial static ranking, so it validates coefficient
transcription rather than the allocation algorithm.
"""
import pytest
from _lab15_helpers import (
    ANNUAL_DEMAND,
    LAND_USE_TYPES,
    data_available,
    metrics_vs_terrame,
    run_lab15_raster,
)


@pytest.mark.skipif(not data_available, reason="Lab15 data files not found -- skipping integration test")
def test_lab15_parity():
    """The raster CLUE-S-like port must achieve 100% cell-level agreement with TerraME."""
    backend, rows, cols = run_lab15_raster()
    m = metrics_vs_terrame(backend, rows, cols)

    assert m["accuracy"] == pytest.approx(100.0, abs=1e-4), (
        f"Expected accuracy=100%, got {m['accuracy']:.4f}%"
    )
    # Pontius & Millones (2011) -- replaces kappa as the parity criterion.
    assert m["quantity_disagreement"] == pytest.approx(0.0, abs=1e-9), (
        f"Quantity disagreement={m['quantity_disagreement']:.6f}, expected 0"
    )
    assert m["allocation_disagreement"] == pytest.approx(0.0, abs=1e-9), (
        f"Allocation disagreement={m['allocation_disagreement']:.6f}, expected 0"
    )
    assert m["f1"] == pytest.approx(1.0, abs=1e-4), f"Expected F1=1.0, got {m['f1']:.4f}"
    assert m["fp"] == 0, f"Expected FP=0, got {m['fp']}"
    assert m["fn"] == 0, f"Expected FN=0, got {m['fn']}"

    # Final demand must be met within tolerance
    n_d = int((backend.get("d")[rows, cols] == 1).sum())
    expected_d = int(ANNUAL_DEMAND[-1][LAND_USE_TYPES.index("d")])
    assert abs(n_d - expected_d) <= 10, (
        f"Final d allocation={n_d}, demand={expected_d}, diff={n_d - expected_d:+d}"
    )

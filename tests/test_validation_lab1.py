"""
tests/test_validation_lab1.py
-------------------------------
Regression test for the raster Lab1 scenario: asserts MAE and RMSE
against the real TerraME/LUCCME reference stay within the official
0.01 tolerance (disslucc-continuous/tests/test_benchmark_validation.py's
own criterion). Turns examples/run_lab1_validation.py's printed numbers
into something CI can fail on.
"""
import pytest
from _lab1_helpers import TOLERANCE, data_available, run_lab1


@pytest.mark.skipif(not data_available, reason="Lab1 data files not found")
class TestValidationLab1:
    @pytest.fixture(scope="class")
    @classmethod
    def metrics(cls):
        return run_lab1()

    def test_raster_vs_terrame_mae(self, metrics):
        assert metrics["mae"] < TOLERANCE, (
            f"Raster_vs_TerraME MAE={metrics['mae']:.6f} exceeds tolerance={TOLERANCE}"
        )

    def test_raster_vs_terrame_rmse(self, metrics):
        assert metrics["rmse"] < TOLERANCE, (
            f"Raster_vs_TerraME RMSE={metrics['rmse']:.6f} exceeds tolerance={TOLERANCE}"
        )

"""
Same scenario as run_continuous_real_data.py (csAC region, 6,574 cells), but
through the ModelExecutor lifecycle (validate -> load -> run -> save) instead
of direct construction: the result is the same, and it adds provenance
(ExperimentRecord, input checksum, timings).

The same experiment as TOML: examples/dissmodel-configs/lucc_continuous.toml
(tests/test_executor_toml.py checks that both give the same output file).
Agreement with TerraME (LuccME's Lab 1): LambdaGeo/disslucc-benchmark.
"""
from __future__ import annotations

from pathlib import Path

from dissmodel.executor import ExperimentRecord
from dissmodel.executor.runner import execute_lifecycle

from disslucc.executors import LuccContinuousExecutor

ROOT = Path(__file__).resolve().parent.parent
CSAC_ZIP = ROOT / "data" / "input" / "csAC.zip"
DEMAND_CSV = ROOT / "data" / "input" / "examples_demand_lab1.csv"

record = ExperimentRecord(
    model_name=LuccContinuousExecutor.name,
    source={"uri": str(CSAC_ZIP)},
    parameters={
        "land_use_types": ["f", "d", "outros"],
        "complementar_lu": "f",
        "demand_csv": str(DEMAND_CSV),
        "land_use_no_data": "outros",
        "static": {"f": -1, "d": -1, "outros": 1},
        "cell_area": 25.0,
        "n_steps": 7,
        "resolution": 5000.0,
        "potential_data": [
            {"const": 0.7392, "betas": {
                "assentamen": -0.2193, "uc_us": 0.1754, "uc_pi": 0.09708,
                "ti": 0.1207, "dist_riobr": 0.0000002388, "fertilidad": -0.1313,
            }},
            {"const": 0.267, "betas": {
                "rodovias": -0.0000009922, "assentamen": 0.2294,
                "uc_us": -0.09867, "dist_riobr": -0.0000003216, "fertilidad": 0.1281,
            }},
            {"const": 0.0},
        ],
        "allocation_data": [
            {"static": -1, "min_value": 0, "max_value": 1, "min_change": 0, "max_change": 1},
            {"static": -1, "min_value": 0, "max_value": 1, "min_change": 0, "max_change": 1},
            {"static": 1, "min_value": 0, "max_value": 1, "min_change": 0, "max_change": 1},
        ],
    },
)

executor = LuccContinuousExecutor()
record, timings = execute_lifecycle(executor, record)

print("status:    ", record.status)
print("metrics:   ", record.metrics)
print("logs:      ", record.logs)
print("timings:   ", timings)
print("artifacts: ", record.artifacts)
print("input checksum (source.checksum):", record.source.checksum)

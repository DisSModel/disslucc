"""
Same Lab15 scenario as run_lab15_validation.py, through the real
ModelExecutor lifecycle.
"""
from __future__ import annotations

from pathlib import Path

from dissmodel.executor import ExperimentRecord
from dissmodel.executor.runner import execute_lifecycle

from disslucc.executors import LuccDiscreteExecutor

ROOT = Path(__file__).resolve().parent.parent
CS_MOJU_ZIP = ROOT / "data" / "input" / "cs_moju.zip"

record = ExperimentRecord(
    model_name=LuccDiscreteExecutor.name,
    source={"uri": str(CS_MOJU_ZIP)},
    parameters={
        "land_use_types": ["f", "d", "o"],
        "demand_csv": None,  # replaced below -- inline via a temp file
        "cell_area": 1.0,
        "n_steps": 6,
        "resolution": 0.00455,  # cs_moju is in EPSG:4618 (degrees); ~84x92 cells
        "max_difference": 100.0,  # looser tolerance than run_lab15_validation.py: the
                                    # resolution-based rasterization (production, new
                                    # dataset) doesn't reproduce TerraME's exact cell
                                    # count (that only happens with direct row/col
                                    # alignment -- see run_lab15_validation.py, which
                                    # uses that method for exact validation instead of
                                    # general use)
        "factor_iteration": 0.0001,
        "potential_data": [
            {"const": -2.34187976925989, "elasticity": 0.0, "betas": {
                "media_decl": -0.0272710076327129, "dist_area_": 4.30977432375496,
                "dist_br": 3.10319957497883, "dist_curua": 0.445414024051873,
                "dist_rios_": 47.3556329553235, "dist_estra": 38.4966894254506,
            }},
            {"const": -0.100351497277102, "elasticity": 0.6, "betas": {
                "media_decl": 0.0581358851690861, "dist_area_": -0.974998890251365,
                "dist_br": -2.51650696123426, "dist_curua": -1.26742746441679,
                "dist_rios_": -40.3646901047482, "dist_estra": -23.0841140199094,
            }},
            {"const": 0.01, "elasticity": 0.5},
        ],
        "transition_matrix": [[[1, 1, 0], [0, 1, 0], [0, 0, 1]]],
    },
)

demand_path = "/tmp/demand_lab15.csv"
with open(demand_path, "w") as f:
    f.write("f,d,o\n")
    for row in [[5706, 205, 3], [5658, 253, 3], [5611, 300, 3],
                [5563, 348, 3], [5516, 395, 3], [5468, 443, 3]]:
        f.write(",".join(str(v) for v in row) + "\n")
record.parameters["demand_csv"] = demand_path

executor = LuccDiscreteExecutor()
record, timings = execute_lifecycle(executor, record)

print("status:    ", record.status)
print("metrics:   ", record.metrics)
print("logs:      ", record.logs)
print("timings:   ", timings)

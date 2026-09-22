"""
disslucc.executors.discrete
------------------------------
Same reasoning as executors/continuous.py: automatic reproducibility
for the discrete (CLUE-S) model, coexisting with script-first.

Inherits from `LuccExecutorBase` -- the base's `load()` already
rasterizes and returns the backend ready to use; `run()` just runs the
model on top of it. See `continuous.py`'s docstring and
`executors/base.py` for the reasoning behind when/why to extract a base
(measured, not assumed).
"""
from __future__ import annotations
from typing import Any
import pathlib
import time

import numpy as np

from dissmodel.core import Environment
from dissmodel.geo import RasterBackend
from dissmodel.executor import ExperimentRecord

from .base import LuccExecutorBase
from ..components.demand import DemandPreComputedValues, load_demand_csv
from ..components.potential import PotentialDLogisticRegression
from ..components.allocation import AllocationDClueSLike
from ..schemas import LogisticRegressionSpec


def _spec_from_dict(d: dict[str, Any]) -> LogisticRegressionSpec:
    return LogisticRegressionSpec(
        const=d["const"], elasticity=d.get("elasticity", 0.0), betas=d.get("betas", {}),
    )


class LuccDiscreteExecutor(LuccExecutorBase):
    """
    Parameters expected in `record.parameters`
    ---------------------------------------------
    land_use_types      : list[str]
    demand_csv           : str
    potential_data       : list[dict]  -- one per class, {"const","elasticity","betas"}
    transition_matrix    : list[list[list[int]]]  -- [region][from][to]
    cell_area, n_steps, resolution, max_difference, factor_iteration : as expected by the components
    """

    name = "lucc_discrete"
    required_parameters = ["land_use_types", "demand_csv", "potential_data", "transition_matrix"]

    def run(self, data: RasterBackend, record: ExperimentRecord) -> dict:
        p = record.parameters
        land_use_types = p["land_use_types"]
        n_steps = int(p.get("n_steps", 6))
        cell_area = float(p.get("cell_area", 1.0))
        backend = data  # already rasterized by LuccExecutorBase.load()

        annual_demand = load_demand_csv(pathlib.Path(p["demand_csv"]).read_text(), land_use_types)

        env = Environment(end_time=n_steps - 1)

        demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=land_use_types)

        PotentialDLogisticRegression(
            backend=backend, land_use_types=land_use_types,
            potential_data=[[_spec_from_dict(d) for d in p["potential_data"]]],
        )
        AllocationDClueSLike(
            backend=backend, demand=demand, land_use_types=land_use_types,
            transition_matrix=p["transition_matrix"], cell_area=cell_area,
            max_difference=float(p.get("max_difference", 10.0)),
            factor_iteration=float(p.get("factor_iteration", 0.0001)),
        )

        t0 = time.perf_counter()
        env.run()
        elapsed_ms = (time.perf_counter() - t0) * 1000 / n_steps
        record.add_log(f"Ran {n_steps} steps ({elapsed_ms:.1f} ms/step)")

        mask = backend.get("mask").astype(bool) if "mask" in backend.arrays else np.ones(backend.shape, dtype=bool)
        counts = {lu: int((backend.get(lu)[mask] == 1).sum()) for lu in land_use_types}

        return {
            "backend": backend,
            "land_use_types": land_use_types,
            "metrics": {f"final_{lu}_cells": c for lu, c in counts.items()} | {"ms_per_step": elapsed_ms},
            "final_log": f"Final counts: {counts}",
        }


if __name__ == "__main__":
    # `python -m disslucc.executors.discrete run --toml ... --input ...`
    # -- see continuous.py's __main__ block and
    # examples/dissmodel-configs/lucc_discrete.toml.
    from dissmodel.executor.cli import run_cli
    run_cli(LuccDiscreteExecutor)

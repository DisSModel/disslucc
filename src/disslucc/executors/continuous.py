"""
disslucc.executors.continuous
--------------------------------
Brings back `ModelExecutor`/`ExperimentRecord` -- automatic
reproducibility is the central argument of `dissmodel` (see the
paper's Statement of Need), and a plain script on its own doesn't
produce that.

Coexists with script-first, doesn't replace it: `examples/run_script.py`
and `examples/run_lab1_real.py` keep working exactly as before -- this
executor is a SECOND entry point.

Inherits from `LuccExecutorBase` (validate/load/save shared with
`LuccDiscreteExecutor`, extracted after measuring the real duplication
between the two -- see `executors/base.py`). The base's `load()`
already rasterizes and returns the backend ready to use -- `run()`
just runs the model on top of it. Only `run()` lives here: it's where
continuous and discrete genuinely diverge (which
Demand/Potential/Allocation to build).
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
from ..components.potential import PotentialLinearRegression
from ..components.allocation import AllocationClueLike
from ..schemas import RegressionSpec, AllocationSpec


def _spec_from_dict(d: dict[str, Any]) -> RegressionSpec:
    return RegressionSpec(
        const=d["const"], betas=d.get("betas", {}), is_log=d.get("is_log", False),
    )


def _alloc_from_dict(d: dict[str, Any]) -> AllocationSpec:
    return AllocationSpec(
        static=d.get("static", -1),
        min_value=d.get("min_value", 0.0), max_value=d.get("max_value", 1.0),
        min_change=d.get("min_change", 0.0), max_change=d.get("max_change", 1.0),
    )


class LuccContinuousExecutor(LuccExecutorBase):
    """
    Parameters expected in `record.parameters`
    ---------------------------------------------
    land_use_types      : list[str]
    complementar_lu      : str
    demand_csv           : str  -- path to the demand CSV (columns = land_use_types)
    potential_data       : list[dict]  -- one dict per class, in land_use_types order
                                          {"const": .., "betas": {...}, "is_log": False}
    static                : dict[str, int]
    allocation_data       : list[dict]  -- one dict per class (same fields as AllocationSpec)
    cell_area, n_steps, resolution, max_difference : as expected by the components
    land_use_no_data (optional)

    `record.source.uri` points to the input shapefile/GeoDataFrame.
    """

    name = "lucc_continuous"
    required_parameters = [
        "land_use_types", "demand_csv", "potential_data",
        "static", "complementar_lu", "allocation_data",
    ]

    def run(self, data: RasterBackend, record: ExperimentRecord) -> dict:
        p = record.parameters
        land_use_types = p["land_use_types"]
        n_steps = int(p.get("n_steps", 7))
        cell_area = float(p.get("cell_area", 25.0))
        backend = data  # already rasterized by LuccExecutorBase.load()

        annual_demand = load_demand_csv(pathlib.Path(p["demand_csv"]).read_text(), land_use_types)

        env = Environment(end_time=n_steps - 1)

        demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=land_use_types)

        # Potential must exist BEFORE Allocation (Allocation reads
        # backend.get(lu+"_pot"), which only exists after Potential.setup()).
        potential = PotentialLinearRegression(
            backend=backend, demand=demand, land_use_types=land_use_types,
            potential_data=[[_spec_from_dict(d) for d in p["potential_data"]]],
            land_use_no_data=p.get("land_use_no_data"),
        )
        AllocationClueLike(
            backend=backend, demand=demand, potential=potential, land_use_types=land_use_types,
            static=p["static"], complementar_lu=p["complementar_lu"], cell_area=cell_area,
            max_difference=float(p.get("max_difference", 1643)),
            allocation_data=[_alloc_from_dict(d) for d in p["allocation_data"]],
        )

        t0 = time.perf_counter()
        env.run()
        elapsed_ms = (time.perf_counter() - t0) * 1000 / n_steps
        record.add_log(f"Ran {n_steps} steps ({elapsed_ms:.1f} ms/step)")

        mask = backend.get("mask").astype(bool) if "mask" in backend.arrays else np.ones(backend.shape, dtype=bool)
        areas = {lu: float(backend.get(lu)[mask].sum()) * cell_area for lu in land_use_types}

        return {
            "backend": backend,
            "land_use_types": land_use_types,
            "metrics": {f"final_{lu}_area": a for lu, a in areas.items()} | {"ms_per_step": elapsed_ms},
            "final_log": f"Final areas: {areas}",
        }

"""
disslucc.executors.saturation
-----------------------------
`LuccSaturationExecutor` -- the continuous model of LuccME-BR (Bezerra et
al. 2022) as an executor: `DemandPreComputedValues` +
`PotentialSpatialLagRegression` + `AllocationClueLikeSaturation`, with
parameters per class and per region, from a model TOML
(`examples/dissmodel-configs/lucc_saturation.toml`).

Differs from `LuccContinuousExecutor` in three ways, each because of what
this model needs:

- **raster input.** `record.source.uri` may be a GeoTIFF whose bands are
  named (a `name` tag per band, as `dissmodel.io.save_geotiff` writes them):
  the land uses, the drivers and, optionally, `mask`, `region`,
  `regionAloc` and the cell order. A continental cellular space is built
  once as a raster; rasterizing a vector at every run would be the wrong
  way round. A vector input still goes through the base's `load()`.
- **regions.** Each `potential_data`/`allocation_data` entry names its
  class (`lu`) and, optionally, its `region` (default 1); the executor
  groups them into the `[region][class]` lists the components take.
- **intermediate years.** `save_steps` lists steps to write besides the
  last, as `<output stem>_step<k>.tif`, to compare a run against maps of
  intermediate years.
"""
from __future__ import annotations

import pathlib
import time
from typing import Any, ClassVar

import numpy as np
from dissmodel.core import Environment, Model
from dissmodel.executor import ExperimentRecord
from dissmodel.geo import RasterBackend
from dissmodel.io import load_dataset
from dissmodel.io.raster import save_geotiff

from ..components.allocation import AllocationClueLikeSaturation
from ..components.demand import DemandPreComputedValues, load_demand_csv
from ..components.potential import PotentialSpatialLagRegression
from ..schemas import SaturationAllocationSpec, SpatialLagRegressionSpec
from .base import LuccExecutorBase

RASTER_SUFFIXES = (".tif", ".tiff")


def _by_region(entries: list[dict[str, Any]], land_use_types: list[str], build) -> list[list[Any]]:
    """[{lu, region?, ...}, ...] -> [[spec of each class, in land_use_types order] per region]."""
    regions = sorted({int(e.get("region", 1)) for e in entries})
    if regions != list(range(1, len(regions) + 1)):
        raise ValueError(f"regions must be 1..n, got {regions}")
    out = []
    for r in regions:
        of_region = {e["lu"]: e for e in entries if int(e.get("region", 1)) == r}
        missing = [lu for lu in land_use_types if lu not in of_region]
        if missing:
            raise ValueError(f"region {r}: no entry for {missing}")
        out.append([build(of_region[lu]) for lu in land_use_types])
    return out


def _potential_spec(d: dict[str, Any]) -> SpatialLagRegressionSpec:
    return SpatialLagRegressionSpec(
        const=d["const"], ro=d["ro"], betas=dict(d.get("betas", {})), is_log=d.get("is_log", False),
        min_reg=d.get("min_reg", 0.0), max_reg=d.get("max_reg", 1.0),
    )


def _allocation_spec(d: dict[str, Any]) -> SaturationAllocationSpec:
    return SaturationAllocationSpec(
        static=d.get("static", -1),
        min_value=d.get("min_value", 0.0), max_value=d.get("max_value", 1.0),
        min_change=d.get("min_change", 0.0), max_change=d.get("max_change", 1.0),
        change_limiar_value=d.get("change_limiar_value", 1.0),
        max_change_above_limiar=d.get("max_change_above_limiar", 0.0),
    )


class LuccSaturationExecutor(LuccExecutorBase):
    """
    Parameters expected in `record.parameters`
    ---------------------------------------------
    land_use_types       : list[str]
    complementar_lu      : str
    demand_csv           : str  -- path to the demand CSV (columns = land_use_types), one row per step
    potential_data       : list[dict]  -- {"lu", "region"?, "const", "ro", "betas", "is_log"?, "min_reg"?, "max_reg"?}
    allocation_data      : list[dict]  -- {"lu", "region"?, "static", "min_value", "max_value", "min_change",
                                           "max_change", "change_limiar_value", "max_change_above_limiar"}
    land_use_no_data, attr_protection, saturation_indicator, order_attr (optional)
    cell_area, n_steps, max_difference, max_iteration, initial/min/max_elasticity (optional)
    save_steps           : list[int] (optional) -- steps written besides the last

    `record.source.uri`: a GeoTIFF with named bands (see module docstring), or
    a vector file rasterized by the base (`resolution`).
    """

    name = "lucc_continuous_saturation"
    required_parameters: ClassVar[list[str]] = [
        "land_use_types", "demand_csv", "potential_data", "complementar_lu", "allocation_data",
    ]

    def load(self, record: ExperimentRecord) -> RasterBackend:
        uri = record.source.uri
        if not uri.lower().endswith(RASTER_SUFFIXES):
            return super().load(record)
        (backend, meta), checksum = load_dataset(uri, fmt="raster")
        record.source.checksum = checksum
        backend.transform = meta["transform"]
        backend.crs = meta["crs"]
        p = record.parameters
        needed = set(p["land_use_types"]) | {k for d in p["potential_data"] for k in d.get("betas", {})}
        missing = sorted(needed - set(backend.arrays))
        if missing:
            raise ValueError(f"{uri}: bands missing: {missing}")
        record.add_log(f"Loaded raster: shape={backend.shape}, {len(backend.arrays)} bands")
        return backend

    def run(self, data: RasterBackend, record: ExperimentRecord) -> dict:
        p = record.parameters
        land_use_types = p["land_use_types"]
        backend = data
        annual_demand = load_demand_csv(pathlib.Path(p["demand_csv"]).read_text(), land_use_types)
        n_steps = int(p.get("n_steps", len(annual_demand)))
        cell_area = float(p.get("cell_area", 1.0))
        save_steps = sorted({int(s) for s in p.get("save_steps", [])})
        if "mask" not in backend.arrays:
            total = np.sum([np.asarray(backend.get(lu), dtype=np.float64) for lu in land_use_types], axis=0)
            backend.set("mask", (total > 0).astype(np.float32))

        env = Environment(end_time=n_steps - 1)
        demand = DemandPreComputedValues(annual_demand=annual_demand, land_use_types=land_use_types)
        potential = PotentialSpatialLagRegression(
            backend=backend, demand=demand, land_use_types=land_use_types,
            potential_data=_by_region(p["potential_data"], land_use_types, _potential_spec),
            land_use_no_data=p.get("land_use_no_data"),
        )
        allocation = AllocationClueLikeSaturation(
            backend=backend, demand=demand, potential=potential, land_use_types=land_use_types,
            allocation_data=_by_region(p["allocation_data"], land_use_types, _allocation_spec),
            complementar_lu=p["complementar_lu"], cell_area=cell_area,
            land_use_no_data=p.get("land_use_no_data"),
            attr_protection=p.get("attr_protection"),
            saturation_indicator=p.get("saturation_indicator", "saturationLimiar"),
            max_difference=float(p.get("max_difference", 1643)),
            max_iteration=int(p.get("max_iteration", 1000)),
            initial_elasticity=float(p.get("initial_elasticity", 0.1)),
            min_elasticity=float(p.get("min_elasticity", 0.001)),
            max_elasticity=float(p.get("max_elasticity", 1.5)),
            order_attr=p.get("order_attr"),
        )

        snapshots: dict[int, dict[str, np.ndarray]] = {}

        class Snapshot(Model):
            def execute(self) -> None:
                step = int(self.env.now())
                if step in save_steps:
                    snapshots[step] = {lu: backend.get(lu).copy() for lu in land_use_types}

        Snapshot()
        t0 = time.perf_counter()
        env.run()
        seconds = time.perf_counter() - t0
        record.add_log(f"Ran {n_steps} steps ({seconds:.1f} s); iterations per step: {allocation.iterations_per_step}")

        mask = backend.get("mask").astype(bool)
        areas = {lu: float(backend.get(lu)[mask].sum()) * cell_area for lu in land_use_types}
        return {
            "backend": backend,
            "land_use_types": land_use_types,
            "snapshots": snapshots,
            "metrics": {f"final_{lu}_area": a for lu, a in areas.items()}
            | {
                "seconds": seconds,
                "iterations_per_step": allocation.iterations_per_step,
                "max_error_per_step": allocation.max_error_per_step,
            },
            "final_log": f"Final areas: {areas}",
        }

    def save(self, result: dict, record: ExperimentRecord) -> ExperimentRecord:
        """The base's save() for the last step, plus one GeoTIFF per `save_steps` entry."""
        record = super().save(result, record)
        backend, land_use_types = result["backend"], result["land_use_types"]
        stem = pathlib.Path(record.output_path)
        for step, arrays in sorted(result["snapshots"].items()):
            snap = RasterBackend(shape=backend.shape, transform=backend.transform, crs=backend.crs)
            for lu, arr in arrays.items():
                snap.set(lu, arr)
            snap.set("mask", backend.get("mask"))
            uri = str(stem.with_name(f"{stem.stem}_step{step}{stem.suffix or '.tif'}"))
            band_spec = [(lu, str(arrays[lu].dtype), -1.0) for lu in land_use_types] + [
                ("mask", str(backend.get("mask").dtype), 0.0)
            ]
            record.artifacts[f"step{step}"] = save_geotiff(
                (snap, {"crs": backend.crs, "transform": backend.transform}), uri, band_spec=band_spec,
            )
            record.add_log(f"Saved step {step} to {uri}")
        return record


if __name__ == "__main__":
    # python -m disslucc.executors.saturation run --toml ... --input cellspace.tif --param demand_csv=...
    from dissmodel.executor.cli import run_cli
    run_cli(LuccSaturationExecutor)

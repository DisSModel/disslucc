"""
disslucc.executors.base
--------------------------
Behavior shared by the LUCC raster executors (continuous and discrete)
-- extracted after measuring the real duplication between
LuccContinuousExecutor and LuccDiscreteExecutor (`diff` showed
validate()/load() nearly identical, save() with the same skeleton).
This is not an attempt to generalize Demand/Potential/Allocation
themselves -- that was already tried and reverted (generic
Pipeline/StageRegistry, see architecture.md, "What was considered and
dropped"). Here only the Executor had enough real duplication to
justify a base.

`load()` already returns the RasterBackend, not the GeoDataFrame --
same convention as the real `LUCCRasterExecutor`
(disslucc-continuous/executors/clue_like_raster_executor.py), checked
against the source, not from memory: there, `load()` calls
`vector_to_raster_backend` and returns the backend; `run(self, data, ...)`
receives `data` already rasterized. Rasterizing inside load() (not
run()) genuinely matters because load() runs only once in the
Executor's lifecycle -- rasterizing is expensive, and the real
executor's comment is explicit about never running it twice.

This fixes an inversion that existed in an earlier version of this
file: `load()` returned the raw GeoDataFrame and each `run()`
rasterized on its own (`_rasterize()` was called from inside `run()`)
-- a workaround for testing with vector data while no real raster
backend had been generated yet. The package is raster-only; `run()`
should receive the backend ready, full stop.

`run()` remains abstract on purpose -- it's the only part that
genuinely differs between continuous and discrete (which components to
build, with which parameters). This is a method template, not dynamic
dispatch by name: each subclass is plain, readable Python code, no
registry or string resolution.
"""
from __future__ import annotations

from dissmodel.executor import ExperimentRecord, ModelExecutor
from dissmodel.geo import RasterBackend
from dissmodel.io import load_dataset
from dissmodel.io.convert import vector_to_raster_backend


class LuccExecutorBase(ModelExecutor):
    """
    Subclasses declare `required_parameters` (list of required keys in
    `record.parameters`, must include `land_use_types` and
    `potential_data` -- `load()` uses both to build the backend) and
    implement `run(data, record)` receiving the RasterBackend already
    built. `save()` has a default that serves both cases today --
    subclasses can override it if they need something different.
    """

    required_parameters: list[str] = []

    def validate(self, record: ExperimentRecord) -> None:
        if not record.source or not record.source.uri:
            raise ValueError("record.source.uri is empty -- point it at the input shapefile")
        missing = [p for p in self.required_parameters if p not in record.parameters]
        if missing:
            raise ValueError(f"Missing parameters: {missing}")

    def load(self, record: ExperimentRecord) -> RasterBackend:
        """Loads the input vector AND ALREADY RASTERIZES -- returns the
        RasterBackend ready to use, not the GeoDataFrame. `run()` just
        runs the model on top of whatever arrives here."""
        p = record.parameters
        land_use_types = p["land_use_types"]
        driver_names = {k for spec in p["potential_data"] for k in spec.get("betas", {})}

        gdf, checksum = load_dataset(record.source.uri, fmt="vector")
        record.source.checksum = checksum
        if record.column_map:
            gdf = gdf.rename(columns={v: k for k, v in record.column_map.items()})
        record.add_log(f"Loaded: {len(gdf):,} features")

        attrs = {lu: 0.0 for lu in land_use_types}
        attrs.update({d: 0.0 for d in driver_names})
        backend = vector_to_raster_backend(
            source=gdf, resolution=float(p.get("resolution", 5000.0)), attrs=attrs, nodata_value=-1,
        )
        record.add_log(f"Rasterized: shape={backend.shape}")
        return backend

    def run(self, data: RasterBackend, record: ExperimentRecord) -> dict:
        raise NotImplementedError("Subclasses implement run() -- this is where continuous and discrete genuinely diverge")

    def save(self, result: dict, record: ExperimentRecord) -> ExperimentRecord:
        record.metrics.update(result["metrics"])
        record.artifacts["output"] = self._sha256(
            b"".join(result["backend"].get(lu).tobytes() for lu in result["land_use_types"])
        )
        record.status = "completed"
        record.add_log(result["final_log"])
        return record

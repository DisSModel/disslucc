# Quickstart — disslucc

## Install

```bash
pip install disslucc                 # from PyPI
pip install "disslucc[examples]"     # + matplotlib, for the examples
```

From a clone, for development: `pip install -e ".[dev]"`.

`dissmodel` comes as a dependency (brings `geopandas`/`rasterio`
along). `matplotlib` is optional, only for the examples that generate
a quicklook.

## The minimal model

Three components, each a `dissmodel.core.Model` -- they register
themselves in the active `Environment` when constructed, in the order
they appear in the script:

```python
from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend
from disslucc import DemandInline, PotentialLinearRegression, AllocationClueLike
from disslucc.schemas import RegressionSpec, AllocationSpec

# 1. your raster (synthetic here -- in a real application it would come
#    from a GeoTIFF or from vector_to_raster_backend() over a shapefile)
backend = RasterBackend(shape=(30, 30))
backend.set("dist_road", ...)   # your drivers
backend.set("forest", ...)      # your initial land use, 0..1 fraction per class
backend.set("urban", ...)

env = Environment(end_time=7)

demand = DemandInline(
    values=[[899, 1], [883, 17], ...],   # [step][class], same order as land_use_types
    land_use_types=["forest", "urban"],
)

potential = PotentialLinearRegression(
    backend=backend, demand=demand, land_use_types=["forest", "urban"],
    potential_data=[[
        RegressionSpec(const=-0.2, betas={"dist_road": 0.4}),   # forest
        RegressionSpec(const=0.3, betas={"dist_road": -0.7}),   # urban
    ]],
)

allocation = AllocationClueLike(
    backend=backend, demand=demand, potential=potential,
    land_use_types=["forest", "urban"],
    static={"forest": 0, "urban": -1},
    complementar_lu="forest", cell_area=1.0,
    allocation_data=[AllocationSpec(static=0), AllocationSpec(static=-1)],
)

env.run()

print(backend.get("urban").sum())  # final urban area
```

No `ModelExecutor`, no TOML, no CLI -- "script-first": the whole script
is the experiment, reproducible with
`git clone && pip install -e . && python3 script.py`.

## The ready-made examples

| Script | What | Data |
|---|---|---|
| `examples/run_script.py` | full continuous model | synthetic |
| `examples/run_continuous_real_data.py` | continuous model | real (csAC.zip) |
| `examples/run_continuous_executor.py` | same, through the executor (provenance) | real (csAC.zip) |
| `examples/run_discrete_executor.py` | discrete model, through the executor | real (cs_moju.zip) |
| `examples/dissmodel-configs/*.toml` | the same experiments as TOML, run with the CLI | real |

Run any of them from inside `examples/`:

```bash
cd examples && python3 run_script.py
```

## Notebooks

Prefer to read and run cell by cell rather than as a script? Two
small, fully synthetic notebooks -- no shapefiles, no vendored data --
walk through the same mechanics one step at a time:
[continuous (CLUE)](examples/notebooks/continuous_synthetic.ipynb) and
[discrete (CLUE-S)](examples/notebooks/discrete_synthetic.ipynb).

## Next steps

- [`api.md`](api.md) -- reference for every class and parameter
- [`architecture.md`](architecture.md) -- what's faithful to the original
  `disslucc-continuous`/`disslucc-discrete`, what was simplified, what's new
- [`validation.md`](validation.md) -- how disslucc is checked against
  TerraME (the disslucc-benchmark repository)
- [`decisions.md`](decisions.md) -- full history of decisions, tests,
  and findings throughout development

## With automatic provenance (Executor)

For production/CI, where tracking input checksums, exact parameters,
and timing matters more than script simplicity, use `disslucc.executors`
instead of direct construction -- same components underneath, same
math, identical result:

```bash
python3 run_continuous_executor.py   # continuous, with ExperimentRecord
python3 run_discrete_executor.py     # discrete, with ExperimentRecord
```

Details in [`api.md`](api.md#executors-dissluccexecutors).

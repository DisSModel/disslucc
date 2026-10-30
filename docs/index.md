# disslucc

**Land Use and Cover Change (LUCC) modeling, raster-only, on top of [`dissmodel`](https://dissmodel.github.io/dissmodel/)**

LuccME's components -- demand, potential and allocation -- in Python:
continuous (CLUE-like), discrete (CLUE-S-like), spatial-lag potential and
saturation. Agreement with the original TerraME/LuccME is checked in
[disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark);
see [Validation](validation.md).

```bash
pip install disslucc                 # from PyPI
pip install "disslucc[examples]"     # + matplotlib, for the examples
```

From a clone, for development: `pip install -e ".[dev]"`.

```python
from dissmodel.core import Environment
from disslucc import DemandInline, PotentialLinearRegression, AllocationClueLike
from disslucc.schemas import RegressionSpec, AllocationSpec

demand = DemandInline(values=[...], land_use_types=["forest", "urban"])
potential = PotentialLinearRegression(backend=backend, demand=demand, ...)
allocation = AllocationClueLike(backend=backend, demand=demand, potential=potential, ...)

Environment(end_time=7).run()
```

No `ModelExecutor`, no TOML, no CLI -- the script is the complete
experiment. When automatic provenance matters more (production, CI),
`disslucc.executors` brings `ModelExecutor`/`ExperimentRecord` back as
a second entry point, with a CLI, same math -- see
[API Reference](api.md#executors-dissluccexecutors).

---

## Where to go next

- **[Quickstart](quickstart.md)** -- installing, the first model, ready-made examples
- **[API Reference](api.md)** -- reference for every public class and parameter
- **[Architecture](architecture.md)** -- what's faithful to the
  original repositories, what was simplified, what's new
- **[Validation](validation.md)** -- where the comparison with TerraME
  lives (disslucc-benchmark) and what is checked in this repository
- **[Decisions](decisions.md)** -- full history of decisions and
  tests throughout development
- **Notebooks** -- two small, fully synthetic (no shapefiles, no
  vendored data) examples you can read top to bottom and run cell by
  cell: [continuous (CLUE)](examples/notebooks/continuous_synthetic.ipynb)
  and [discrete (CLUE-S)](examples/notebooks/discrete_synthetic.ipynb).
  Start here if you want to understand the mechanics before running the
  real, validated examples in `examples/`.

## The DisSModel ecosystem

| Package | Role | Documentation |
|:---|:---|:---|
| [**dissmodel**](https://github.com/DisSModel/dissmodel) | Core framework: clock, spatial substrates, executor, I/O, visualization | [dissmodel.github.io/dissmodel](https://dissmodel.github.io/dissmodel/) |
| [**disscube**](https://github.com/DisSModel/disscube) | Declarative pipelines that turn raster and vector sources into model-ready grids | [dissmodel.github.io/disscube](https://dissmodel.github.io/disscube/) |
| [**disslucc**](https://github.com/DisSModel/disslucc) | Land use and cover change: demand, potential and allocation | [dissmodel.github.io/disslucc](https://dissmodel.github.io/disslucc/) |
| [dissmodel-ca](https://github.com/DisSModel/dissmodel-ca), [dissmodel-sysdyn](https://github.com/DisSModel/dissmodel-sysdyn), [dissmodel-abm](https://github.com/DisSModel/dissmodel-abm) | Ready-to-use cellular automata, system dynamics and agent-based models | GitHub |

Developed by the [LambdaGeo](https://github.com/LambdaGeo) group at the Federal University of Maranhão (UFMA). MIT licence.

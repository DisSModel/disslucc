# disslucc

**Land Use and Cover Change (LUCC) modeling, raster-only, on top of [`dissmodel`](https://dissmodel.github.io/dissmodel/)**

Continuous (CLUE) and discrete (CLUE-S) allocation, both validated
against the original TerraME reference on real data: Lab1 (continuous)
within the official 0.01 MAE tolerance, Lab15 (discrete) at exact,
100% cell-by-cell agreement -- see [Validation](validation.md) for
both results and what each one does and doesn't prove.

```bash
pip install -e ".[examples]"
```

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
- **[Validation](validation.md)** -- validation results against
  TerraME (Lab1 continuous, Lab15 discrete) and the engineering vs.
  scientific validation distinction
- **[Decisions](decisions.md)** -- full history of decisions and
  tests throughout development
- **Notebooks** -- two small, fully synthetic (no shapefiles, no
  vendored data) examples you can read top to bottom and run cell by
  cell: [continuous (CLUE)](examples/notebooks/continuous_synthetic.ipynb)
  and [discrete (CLUE-S)](examples/notebooks/discrete_synthetic.ipynb).
  Start here if you want to understand the mechanics before running the
  real, validated examples in `examples/`.

## Part of the DisSModel ecosystem

`disslucc` is a satellite package built on
[`dissmodel`](https://github.com/DisSModel/dissmodel), the core
discrete spatial modeling framework. See the
[dissmodel documentation](https://dissmodel.github.io/dissmodel/) for
the underlying `Environment`/`Model`/`RasterBackend` concepts this
package builds on.

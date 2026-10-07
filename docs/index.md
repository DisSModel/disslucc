# disslucc

**Land Use and Cover Change (LUCC) modeling, raster-only, on top of [`dissmodel`](https://dissmodel.github.io/dissmodel/)**

LuccME's components -- demand, potential and allocation -- in Python:
continuous (CLUE-like), discrete (CLUE-S-like), spatial-lag potential and
saturation. Agreement with the original TerraME/LuccME is checked in
[disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark);
see [Validation](validation.md).

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

## Part of the DisSModel ecosystem

`disslucc` is a satellite package built on
[`dissmodel`](https://github.com/DisSModel/dissmodel), the core
discrete spatial modeling framework. See the
[dissmodel documentation](https://dissmodel.github.io/dissmodel/) for
the underlying `Environment`/`Model`/`RasterBackend` concepts this
package builds on.

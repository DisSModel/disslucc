# disslucc

Land use and land cover change (LUCC) modeling, raster-only,
script-first, on top of [`dissmodel`](https://github.com/DisSModel/dissmodel).
Unified port of
[`disslucc-continuous`](https://github.com/DisSModel/disslucc-continuous)
(continuous CLUE) and [`disslucc-discrete`](https://github.com/DisSModel/disslucc-discrete)
(discrete CLUE-S), validated cell by cell against the original TerraME
reference in both cases — see [`docs/validation.md`](docs/validation.md).

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

No `ModelExecutor`, no TOML, no CLI — the script is the complete
experiment, reproducible with `git clone && pip install -e . && python3 script.py`.
When automatic provenance matters more than simplicity (production,
CI), `disslucc.executors` brings `ModelExecutor`/`ExperimentRecord`
back as a second entry point — same math, identical result, see
[`api.md`](docs/api.md#executors-dissluccexecutors).

## Documentation

- **[quickstart.md](docs/quickstart.md)** — installing, the first model, ready-made examples
- **[api.md](docs/api.md)** — reference for every class and parameter
- **[architecture.md](docs/architecture.md)** — what's faithful to the
  original repositories, what was simplified, what's new
- **[validation.md](docs/validation.md)** — validation results against
  TerraME (Lab1 continuous, Lab15 discrete) and the engineering vs.
  scientific validation distinction
- **[decisions.md](docs/decisions.md)** — full history of decisions and
  tests throughout development

Wider ecosystem context: chapter 26 (*Land Use and Cover Change
Modeling*) of the *Geospatial Modeling with Python* book (LambdaGeo) --
still a draft, but where "DisSLUCC" as a family name is documented for
the first time.

## Development

```bash
pip install -e ".[dev]"
mypy src/disslucc
```

## Structure

```
disslucc/
├── src/disslucc/
│   ├── protocols.py, schemas.py
│   ├── components/     # same convention as the original repositories
│   │   ├── demand/      #   shared continuous + discrete
│   │   ├── potential/    #   linear.py (continuous) + logistic.py (discrete)
│   │   └── allocation/   #   clue.py (continuous) + clue_s.py (discrete)
│   ├── validation/      # shared continuous + discrete (outside components/, see architecture.md)
│   └── executors/        # ModelExecutor -- automatic provenance, second entry point
├── examples/          # ready-made scripts, synthetic, real data, and via Executor
└── docs/
```

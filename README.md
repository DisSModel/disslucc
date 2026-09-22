# disslucc

[![Tests](https://github.com/DisSModel/disslucc/actions/workflows/tests.yml/badge.svg)](https://github.com/DisSModel/disslucc/actions/workflows/tests.yml)

Land use and land cover change (LUCC) modeling, raster-only,
script-first, on top of [`dissmodel`](https://github.com/DisSModel/dissmodel).
Continuous (CLUE) and discrete (CLUE-S) allocation, validated against
the original TerraME reference on real data for both: Lab1
(continuous) within the official 0.01 MAE tolerance, Lab15 (discrete)
at exact, 100% cell-by-cell agreement — see
[`docs/validation.md`](docs/validation.md) for both results and what
each one does and doesn't prove.

## Migration status: becoming the single successor repository

`disslucc` is migrating from two separately maintained repositories
(`disslucc-continuous`, `disslucc-discrete`) into **one single
repository**, mirroring how the original
[`terrame/luccme`](https://github.com/terrame/luccme) is itself one
repository with continuous and discrete components side by side,
instead of split by paradigm. Two reasons:

1. **Efficiency.** As more Demand/Potential/Allocation strategies are
   developed, maintaining two parallel implementations (vector +
   raster, continuous repo + discrete repo, each with its own
   Demand/validation code duplicated) doesn't scale and gets confusing
   fast. Consolidating into one raster-only package, with Demand and
   Pontius & Millones validation shared across both paradigms, removes
   that duplication.
2. **One clear reference.** A single repository is a much stronger
   "LuccME in Python" story than pointing people at two packages that
   together replicate it.

This repository is moving from `github.com/LambdaGeo/disslucc` to
`github.com/DisSModel/disslucc`, alongside `dissmodel`,
`disslucc-continuous`, and `disslucc-discrete`. The two source
repositories will be released, tagged, archived, and kept citable once
this migration completes — see
[`docs/decisions.md`](docs/decisions.md) for the full reasoning,
status, and what's still pending (this does not happen before
`dissmodel`'s JOSS review concludes, so existing citations aren't
disrupted mid-review).

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
[`api.md`](docs/api.md#executors-dissluccexecutors). This is also
the entry point registered in
[`dissmodel-configs`](https://github.com/DisSModel/dissmodel-configs)
to run on `dissmodel-platform`, and it comes with a CLI, via
`dissmodel.executor.cli.run_cli`:

```bash
python -m disslucc.executors.continuous run \
  --toml examples/dissmodel-configs/lucc_continuous.toml \
  --input data/input/csAC.zip \
  --param demand_csv=data/input/examples_demand_lab1.csv \
  --output outputs/result.tif   # local path or s3://bucket/key (MinIO)

python -m disslucc.executors.discrete run \
  --toml examples/dissmodel-configs/lucc_discrete.toml \
  --input data/input/cs_moju.zip \
  --param demand_csv=data/input/demand_moju.csv \
  --output outputs/result.tif
```

`--output` writes a GeoTIFF with one band per land-use class (+ `mask`),
georeferenced from the input's CRS/extent -- open it directly in QGIS,
locally or straight from MinIO.

Both commands above run end-to-end as written -- `pyproject.toml` pins
`dissmodel>=0.6.4`, which merges `[model]`-level spec into
`record.parameters` for local `--toml` runs (this used to require an
unreleased fix; see `docs/decisions.md` for that history if you're
curious).

`examples/dissmodel-configs/` has a TOML config per executor
([continuous](examples/dissmodel-configs/lucc_continuous.toml),
[discrete](examples/dissmodel-configs/lucc_discrete.toml)), each
encoding the same coefficients as its `examples/run_*_via_executor.py`
counterpart — see [`api.md`](docs/api.md#registering-with-dissmodel-configs-toml)
for the full explanation.

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
pytest tests/ -v
```

CI (`.github/workflows/tests.yml`) runs the same test suite on every push
and pull request. `tests/` includes the Lab1/Lab15 validation numbers as
real assertions, plus the discriminance suites ported from
`disslucc-continuous`/`disslucc-discrete` -- these check whether the
benchmark itself can tell a correct implementation from a wrong one, not
just whether it reproduces the reference.

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
│   │   └── naive_baseline.py  # discriminance baseline for Lab15
│   └── executors/        # ModelExecutor -- automatic provenance, second entry point
├── examples/          # ready-made scripts, synthetic, real data, and via Executor
├── data/input/        # vendored Lab1 + Lab15 input shapefiles and demand CSVs
├── benchmark/
│   ├── data/          # vendored TerraME reference outputs (Lab1, Lab15)
│   └── reference/     # vendored original LuccME .lua scripts (provenance)
├── tests/             # pytest suite -- validation + discriminance, run by CI
└── docs/
```

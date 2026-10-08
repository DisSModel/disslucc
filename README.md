# disslucc

[![Tests](https://github.com/DisSModel/disslucc/actions/workflows/tests.yml/badge.svg)](https://github.com/DisSModel/disslucc/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/disslucc.svg)](https://pypi.org/project/disslucc/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23219338.svg)](https://doi.org/10.5281/zenodo.23219338)

Land use and land cover change (LUCC) modeling, raster-only,
script-first, on top of [`dissmodel`](https://github.com/DisSModel/dissmodel).
LuccME's components -- demand, potential, allocation -- in Python:
continuous (CLUE-like), discrete (CLUE-S-like), spatial-lag potential,
saturation, and demand computed from land-use layers. It is an alternative
that you can run next to TerraME/LuccME, not a replacement for them.

**Agreement with TerraME/LuccME** (iteration counts, per-year error, timings,
10 of the 21 LuccME labs so far) is checked in
[LambdaGeo/disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark),
which pins the release of disslucc it ran against. This repository is the
package and the examples to learn it with.

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
encoding the same coefficients as its `examples/run_*_executor.py`
counterpart — see [`api.md`](docs/api.md#registering-with-dissmodel-configs-toml)
for the full explanation.

## Documentation

- **[quickstart.md](docs/quickstart.md)** — installing, the first model, ready-made examples
- **[api.md](docs/api.md)** — reference for every class and parameter
- **[architecture.md](docs/architecture.md)** — what's faithful to the
  original repositories, what was simplified, what's new
- **[validation.md](docs/validation.md)** — where the comparison with
  TerraME lives: [disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark)
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

CI (`.github/workflows/tests.yml`) runs ruff, mypy and the tests on every push
and pull request. `tests/` covers the demand components and checks that each
example TOML, run through the CLI, produces the same output file as the
equivalent hand-built experiment. **Agreement with TerraME/LuccME is not tested
here**: it is the job of
[disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark), which pins
the disslucc release it ran against.

## Citing

Use the DOI of the release you used (Zenodo, badge above once published) and
`CITATION.cff`.

## Structure

```
disslucc/
├── src/disslucc/
│   ├── protocols.py, schemas.py
│   ├── components/     # same convention as the original repositories
│   │   ├── demand/      #   shared continuous + discrete
│   │   ├── potential/    #   linear.py (continuous) + logistic.py (discrete)
│   │   └── allocation/   #   clue.py (continuous) + clue_s.py (discrete)
│   ├── validation/      # Pontius & Millones metrics, naive baseline (outside components/, see architecture.md)
│   └── executors/        # ModelExecutor -- automatic provenance, second entry point
├── examples/          # ready-made scripts: synthetic, real data, executor, TOML configs
├── data/input/        # vendored example inputs (csAC, cs_moju) and demand CSVs
├── tests/             # pytest suite: demand components, TOML == executor
└── docs/
```

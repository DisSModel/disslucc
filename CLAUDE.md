# CLAUDE.md

Guidance for Claude Code (or any AI coding agent) working in this
repository. Read this before making changes -- several mistakes here have
already been made once and corrected; don't repeat them.

## What this repository is

`disslucc` is a **raster-only, script-first port** of the continuous
(CLUE-like) and discrete (CLUE-S-like) LUCC allocation algorithms from
`disslucc-continuous` and `disslucc-discrete`, built on top of
[`dissmodel`](https://github.com/DisSModel/dissmodel). It exists to
eventually become the single successor to those two split repositories
(see `docs/decisions.md`, "Roadmap: disslucc as the single successor,
post-JOSS" -- not yet decided, conditions listed there).

Two deliberate design decisions, documented at the top of
`docs/decisions.md` -- don't "fix" these without reading that file first:
1. **Raster only.** Vector substrate was deliberately dropped.
2. **Script-first**, with `ModelExecutor`/`ExperimentRecord` as a second
   entry point (`src/disslucc/executors/`), not a replacement for the
   plain-script path (`examples/run_script.py`).

## Structure

```
src/disslucc/
  components/{demand,potential,allocation}/  # demand + validation shared across
  validation/                                # continuous/discrete; potential + allocation are not
  executors/                                 # ModelExecutor (base.py, continuous.py, discrete.py)
data/input/            # vendored real input data (shapefiles + demand CSVs)
benchmark/goldens/     # TerraME reference results, year by year (copy from LambdaGeo/terrame-docker)
examples/               # runnable scripts: synthetic, real data, via Executor
tests/                  # pytest -- validation (exact numbers) + discriminance (does the
                         # benchmark actually constrain the implementation?)
docs/
  validation.md          # the numbers -- cited in dissmodel's JOSS paper, see below
  architecture.md         # what's faithful to the original vs. simplified vs. new
  decisions.md            # running decision log ("why"), append here, don't rewrite history
```

## Rules that exist because they were violated once

**Never hardcode absolute paths** (`/home/claude/...`, `/tmp/csAC`,
pre-extracted shapefile directories). Every example/test resolves paths
relative to the repo root:
```python
ROOT = Path(__file__).resolve().parent.parent
CSAC_ZIP = ROOT / "data" / "input" / "csAC.zip"
```
and reads zips directly with `gpd.read_file(path_to_zip)` -- GDAL handles
a single-layer shapefile inside a zip with no manual extraction. This
repo was fixed twice for the same class of bug (initial validation
scripts, then three more `examples/*.py` files found later) -- grep for
`/home/`, `/tmp/` before assuming a script is portable.

**Data provenance is not "whatever GitHub script has a matching name."**
The reference results live in `benchmark/goldens/`, a copy of the goldens
generated in [LambdaGeo/terrame-docker](https://github.com/LambdaGeo/terrame-docker)
v0.1.1, which keeps the generating scripts, the original TerraME outputs, the
generator and goldens for all 21 LuccME labs. This repository keeps only the
goldens its tests use (`lab01`, `lab15`, `lab03`, `lab06`: the LuccME package's labs;
`lab01_md1643`, `lab15_md10`); add one together with the component and test
that need it, never ahead of time. `lab01_md1643` and `lab15_md10` are the scenarios behind `docs/validation.md`
(same coefficients and demand as `lab01`/`lab15`, but `maxDifference` 1643
and 10 instead of 5000 and 300). **Read terrame-docker's
`benchmark/references/README.md` before citing or changing any
`max_difference`/`maxDifference` value.** Never edit a golden by hand --
regenerate it there and copy it (see `benchmark/README.md`).
A empirical validation number that stops matching (e.g. MAE jumping from
0.0036 to above 0.01) is stronger evidence of a wrong parameter than a
GitHub script that merely looks similar.

**`docs/validation.md`'s numbers are cited outside this repository** --
in `dissmodel`'s `paper.md`/`paper.bib` (JOSS submission). If a change
alters a Lab1 or Lab15 result, update `docs/validation.md` in the same
PR/commit and say so explicitly -- don't let it drift silently.

## Working here

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[examples,dev]"
pytest tests/ -v          # expect: 70 passed, 2 xfailed (35 passed, 1 skipped without lupa)
mypy src/disslucc         # expect: clean
```

`AllocationClueLike(cell_correction=True)` (the default) deliberately differs
from TerraME: LuccME's `correctCellChange` never runs (a `regionregionAloc`
typo). Tests that compare against the continuous goldens use
`cell_correction=False`; don't "fix" the default to make them pass.

The 2 `xfail`s in `tests/test_benchmark_discriminance_lab15.py` are
intentional and documented (the Lab15 scenario is near-non-discriminative
by design -- a trivial static ranking reproduces the same output). Don't
"fix" them by loosening assertions; the fix, if one ever lands, is a
dynamic-covariate scenario (see `docs/decisions.md`).

Before changing a `max_difference`/convergence value, a demand table, or
a regression coefficient anywhere in `src/`, `tests/_lab*_helpers.py`, or
`examples/`: check the golden's `manifest.json` and the scripts in
terrame-docker's `benchmark/references/` first. If the change isn't
traceable to those `.lua` files, it's very likely wrong even if it looks
locally reasonable.

`CONTRIBUTING.md` has the full contribution workflow (branching,
PR/issue templates, coding standards). `docs/decisions.md` is the
running log of "why" -- append to it, don't summarize over past entries.

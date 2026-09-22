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
benchmark/data/        # vendored TerraME *reference outputs* (expected results)
benchmark/reference/   # vendored original LuccME .lua *scripts* (provenance) + README.md
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
`terrame/luccme`'s public `tests/functional/lab01.lua` and `lab15.lua`
share calibrated coefficients and demand trajectories with the scripts
that actually generated this repo's reference data, but declare
different `maxDifference` values (5000 and 300, vs. the 1643 and 10
actually used) and did **not** generate `benchmark/data/`'s zips. The
real generating scripts are vendored, unmodified, at
`benchmark/reference/` -- **read `benchmark/reference/README.md` before
citing or changing any `max_difference`/`maxDifference` value.**
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
pytest tests/ -v          # expect: 14 passed, 2 xfailed
mypy src/disslucc         # expect: clean
```

The 2 `xfail`s in `tests/test_benchmark_discriminance_lab15.py` are
intentional and documented (the Lab15 scenario is near-non-discriminative
by design -- a trivial static ranking reproduces the same output). Don't
"fix" them by loosening assertions; the fix, if one ever lands, is a
dynamic-covariate scenario (see `docs/decisions.md`).

Before changing a `max_difference`/convergence value, a demand table, or
a regression coefficient anywhere in `src/`, `tests/_lab*_helpers.py`, or
`examples/`: check `benchmark/reference/` first. If the change isn't
traceable to those `.lua` files, it's very likely wrong even if it looks
locally reasonable.

`CONTRIBUTING.md` has the full contribution workflow (branching,
PR/issue templates, coding standards). `docs/decisions.md` is the
running log of "why" -- append to it, don't summarize over past entries.

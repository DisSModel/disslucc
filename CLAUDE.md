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
examples/               # runnable scripts: synthetic, real data, executor, TOML configs
tests/                  # pytest -- demand components, TOML == executor (same output SHA-256)
docs/
  validation.md          # pointer to LambdaGeo/disslucc-benchmark (no numbers live here)
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

**Agreement with TerraME lives in
[LambdaGeo/disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark)**,
not here (since 0.5.0; the goldens, Lua differential and discriminance tests are
in the `v0.4.0` tag if you need to look at them). The benchmark pins a disslucc
release. If you change numerical behavior in `src/`, run the benchmark against
your branch (`pip install -e ../disslucc` there, `make benchmark`) before
merging, and say in the PR what changed. A number that stops matching is stronger
evidence of a wrong parameter than a script that merely looks similar.

**Before changing a `max_difference`/convergence value, a demand table, or a
regression coefficient** in `src/` or `examples/`, check the reference scripts
in terrame-docker's `benchmark/references/` (and its README) first. If the
change isn't traceable to those `.lua` files, it's very likely wrong even if it
looks locally reasonable.

**Published papers cite benchmark ids, not this repository's numbers**
(`lab01_md1643`, `lab15_md10`, in dissmodel's JOSS paper). Keep those ids
stable in the benchmark.

## Working here

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[examples,dev]"
pytest tests/ -v          # expect: all passed
mypy src/disslucc         # expect: clean
```

`AllocationClueLike(cell_correction=True)` (the default) deliberately differs
from TerraME: LuccME's `correctCellChange` never runs (a `regionregionAloc`
typo). `cell_correction=False` follows the reference run; the benchmark uses it
and also reports the default. Don't "fix" the default to make a comparison pass.

`CONTRIBUTING.md` has the full contribution workflow (branching,
PR/issue templates, coding standards). `docs/decisions.md` is the
running log of "why" -- append to it, don't summarize over past entries.

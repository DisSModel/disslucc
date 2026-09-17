# Decision history — disslucc


> This file is the "why": decisions made, tests already run, what was
> tried and dropped. For "how to use it", see [`quickstart.md`](quickstart.md)
> and [`api.md`](api.md). For "what's faithful/simplified/new relative
> to the original repositories", see [`architecture.md`](architecture.md).
Simplified port of [`disslucc-continuous`](https://github.com/DisSModel/disslucc-continuous),
**`main` branch** (not `decoupling` -- that one was experimental:
introduced `PotentialProtocol.get_potential()`, `from_spec()`/TOML, a
registry with a parameter schema. None of that is here on purpose).

Two deliberate decisions:

1. **Raster only.** The original repository keeps vector and raster in
   parallel; the decision here was to drop vector -- for LUCC models
   with large data, raster is the better path, and keeping both
   substrates creates complication without proportional payoff right
   now.
2. **Script-first.** No `ModelExecutor`/`ExperimentRecord`/TOML/CLI --
   a Python script builds the components directly, the way an
   original LuccME `.lua` script built `P1 = PotentialCLinearRegression{...};
   LuccMEModel{potential=P1, ...}`. See `examples/run_script.py`.

## What's faithful to the original, and what was dropped

**Faithful, not simplified**: the CLUE algorithm itself --
`AllocationClueLike` (elasticity, iterative convergence, proportional
correction between classes, `complementar_lu`) and
`PotentialLinearRegression` (regression + `_adapt_constants` +
`modify`) are near byte-for-byte ports of
`components/allocation/raster/clue.py` and
`components/potential/raster/linear.py` from `main`. The science
didn't change.

**Dropped, on purpose**: `from_spec()`/TOML, `ModelExecutor`,
`components/registry.py` (doesn't even exist on `main`),
`schemas/params.py` (Pydantic, only on `decoupling`). A much simpler
`registry.py` (a plain name→class dict, no registry class) was added
here as an optional convenience -- doesn't exist in the original, it's
just a catalog for when/if a TOML or GUI needs to resolve name→class.

**Detail that only shows up when comparing branches**: on `decoupling`,
`AllocationClueLike` reads the potential via
`self.potential.get_potential(lu)` (indirection through a Protocol).
On `main` -- and here -- it reads `self.backend.get(lu + "_pot")`
directly. More coupled, but it's what's in production; that's why
`PotentialProtocol` only declares `modify`, not `get_potential`.

## Structure

Each role (demand/potential/allocation) became a package (a folder,
an `__init__.py` re-exporting) instead of a single file -- same
convention as the original repository
(`components/potential/raster/__init__.py` re-exporting from
`linear.py`), just without the `raster/` level because only one
substrate exists now. Reason: the real LuccME has more than one
strategy per role (`PotentialCLinearRegression`,
`PotentialCSpatialLagRegression`, `PotentialCSampleBased`, ...) -- one
file per strategy keeps this extensible without reopening an
already-large file every time a new one comes in.

```
disslucc/
├── src/disslucc/
│   ├── protocols.py         # DemandProtocol, PotentialProtocol
│   ├── schemas.py            # RegressionSpec, AllocationSpec, LogisticRegressionSpec
│   ├── registry.py           # plain name->class dict (doesn't exist in the original)
│   ├── demand/                     # shared continuous+discrete
│   │   ├── precomputed.py    # DemandPreComputedValues (faithful to main)
│   │   └── inline.py         # DemandInline (my own convenience, doesn't exist on main)
│   ├── validation/                  # shared continuous+discrete
│   │   └── pontius.py        # Pontius & Millones, generalized for continuous fraction
│   ├── potential/
│   │   ├── linear.py         # PotentialLinearRegression (continuous, faithful to main)
│   │   └── logistic.py        # PotentialDLogisticRegression (discrete, new raster)
│   └── allocation/
│       ├── clue.py           # AllocationClueLike (continuous, faithful to main)
│       └── clue_s.py          # AllocationDClueSLike (discrete, new raster)
└── examples/
    ├── scenario.py                 # synthetic/theoretical raster scenario (no real data)
    ├── run_script.py               # direct script, synthetic data (continuous)
    ├── run_lab1_real.py            # direct script, REAL Lab1 data (csAC.zip)
    ├── run_lab1_validation.py       # validates against real TerraME (continuous)
    └── run_lab15_validation.py      # validates against real TerraME (discrete, new)
```

Each strategy folder is the only place that changes when a new one
comes in -- `registry.py` gains one line in the dict, the rest of the
package doesn't need to know it exists.

## Running it

```bash
pip install -e ".[examples]"
cd examples && python3 run_script.py
```

Scenario: 30x30 grid, synthetic drivers (`dist_road`, `slope`), 3
classes (`forest` complementary, `agriculture`, `urban`), growing
demand over 8 steps. No real geospatial data -- just to prove the
algorithm runs end to end.

Typical result (`max_difference=5.0`, convergence tolerance): urban
converges almost exactly on target; agriculture stays within
tolerance. `quicklook.png` shows the continuous spatial pattern --
smooth gradient around the "road", not discrete blocks, because the
change is proportional to potential at every cell, not a hard cutoff
by ranking (unlike the discrete version that existed in an earlier
prototype in this conversation).

## Shared layer: `demand/` and `validation/`

`demand/` already was, with no changes needed: I checked with `diff`
that `DemandPreComputedValues` is byte-for-byte identical (only
formatting differs) between `disslucc-continuous` and
`disslucc-discrete` -- the two real repositories already duplicate this
class today. Here it exists only once.

`validation/pontius.py` is new: the Pontius & Millones (2011)
decomposition into quantity + allocation disagreement, generalized for
CONTINUOUS maps (0-1 fraction per cell), not just 0/1 categorical. The
real `disslucc-discrete` only has the binarized version
(`lucc_validation_executor.py::_discrete_metrics`, 0.5 threshold
before comparing); `disslucc-continuous` has no validation at all. The
version here proves by algebraic identity that it reduces exactly to
the classic discrete formula when the data is pure 0/1 (test embedded
in the file) -- and happens to already match the continuous formula
that `lucc_benchmark_executor.py::_metrics` (also real, also not
ported before) already used to compare Vector/Raster/TerraME on Lab1.

**Real validation, not just a self-test**:
`examples/run_lab1_validation.py` runs our disslucc over the full Lab1
scenario and compares cell by cell against the real TerraME reference
(`benchmark/data/LUCCME_Lab1_2014.zip`), using the same `row`/`col`
alignment method as the original benchmark (not the resolution-based
resampling `run_lab1_real.py` uses -- that introduces alignment error
the direct comparison doesn't have).

Result: **MAE = 0.0036** -- within the 0.01 tolerance that
`test_benchmark_validation.py` uses to consider something "equivalent
to TerraME". `quantity_disagreement` (0.0032) dominates over
`allocation_disagreement` (0.0004): the spatial pattern matches almost
perfectly, the small difference is in total quantity, not location.

```bash
cd examples && python3 run_lab1_validation.py
```

## Bringing discrete into this repository

`disslucc-discrete` (a separate repository) only existed in vector --
`potential/vector/logistic_regression.py`,
`allocation/vector/clue_s.py`. I ported both to raster here (not a
literal translation like the continuous modules "faithful to main" --
they're rewritten following the same mask/backend pattern already used
in `potential/linear.py`/`allocation/clue.py`, because no original
raster version exists to copy):

- `potential/logistic.py` — `PotentialDLogisticRegression` (logistic
  regression + spatial lock-in elasticity, CLUE-S)
- `allocation/clue_s.py` — `AllocationDClueSLike` (cell-by-cell
  competition with transition matrix + global correction vector)
- `LogisticRegressionSpec` added to `schemas.py` (alongside
  `RegressionSpec`/`AllocationSpec`, which were already shared)

`demand/` and `validation/` needed nothing -- they were already
shared, and that's exactly why the move paid off:
`DemandPreComputedValues` and `pontius_millones()` serve both without
duplication.

**Real validation against TerraME** (`examples/run_lab15_validation.py`,
real Lab15/cs_moju data + `benchmark/data/Lab15_2004.zip` from
`disslucc-discrete`, same coefficients/transition matrix as the
original executor): **MAE = 0.0, 100% cell-by-cell agreement, F1 = 1.0**
-- exactly the result documented in the original `disslucc-discrete`.

**Discriminance warning, inherited from the original repository** (not
my own achievement, it's a caveat that already existed there,
`benchmark/validate_lab15.py`): the Lab15 scenario is nearly
non-discriminative -- a trivial static ranking by `(prob_d - prob_f)`,
with no CLUE-S, no iteration at all, already reproduces the same
cell-by-cell output. This result confirms the logistic regression
coefficients were transcribed correctly -- it is NOT proof that the
allocation algorithm (CLUE-S with iteration/convergence) is faithful.
Proving that would require a scenario where allocation genuinely needs
to compete/iterate to converge, and comparing the iteration count
against the TerraME log (which `disslucc-discrete` also documents:
61-67 iterations per step) -- I didn't do that check here.

```bash
cd examples && python3 run_lab15_validation.py
```

## What would be left for later, if this path holds up

- **`confusion_metrics()`** (accuracy/precision/recall/F1, binarized)
  exists in `validation/pontius.py` but hasn't been exercised against
  real data yet -- only makes sense for categorical comparison.
- **`DemandInline` doesn't exist on `main`** (only on `decoupling`) --
  kept it because it's small and genuinely useful for scripts (no CSV
  needed), but it's my own addition, not a port.
- **If `disslucc-discrete` migrates to this base**, `demand/` and
  `validation/` would already serve it with no change -- that's
  exactly the design that motivated separating them from the rest.

## The Executor came back

After noticing, while reviewing the JOSS paper draft, that "automatic
reproducibility via `ExperimentRecord`" is cited as a central
`dissmodel` argument (Statement of Need and Summary, twice) -- and
that this package had dropped that entirely in favor of script-first
only -- I reintroduced `ModelExecutor` as a SECOND entry point,
without removing the first.

`executors/continuous.py` (`LuccContinuousExecutor`) and
`executors/discrete.py` (`LuccDiscreteExecutor`) follow the same
`validate -> load -> run -> save` contract as the real
`LUCCRasterExecutor`, but resolve `potential_data`/`allocation_data`
from `record.parameters` as plain dicts (TOML/JSON-compatible) instead
of hardcoded module constants -- more general than the original
executor, which hardcodes the Lab1 coefficients directly in the Python
file.

Tested by running the SAME already-validated Lab1/Lab15 scenarios
against TerraME, now through the Executor:

- **Lab1** (`examples/run_lab1_via_executor.py`): final areas
  `f=134724.38, d=23136.42, outros=6489.21` -- identical, digit for
  digit, to the direct script's result (`run_lab1_real.py`). Gains
  input checksum, per-phase timing (`validate/load/run/save`), logs,
  output checksum.
- **Lab15** (`examples/run_lab15_via_executor.py`): converged with
  `max_difference=100` instead of `10` -- resolution-based
  rasterization (`vector_to_raster_backend`, the production path for a
  new dataset) doesn't reproduce TerraME's exact original grid cell
  count (5,842 vs 5,914 valid cells), so the convergence tolerance
  calibrated for the exact grid (`run_lab15_validation.py`, direct
  `row`/`col` alignment) doesn't apply here without adjustment.
  Documented in the script itself -- not a regression, a difference in
  rasterization method.

Also found and fixed a `RuntimeWarning: overflow in exp` in
`potential/logistic.py`: cells outside the mask (filled with nodata,
e.g. -1) produced extreme `z` with Lab15's real coefficients. Added
`np.clip(z, -50, 50)` before the sigmoid -- doesn't change any result
(the sigmoid already saturates well before that), just silences the
warning. Retested `run_lab15_validation.py` after the fix: MAE still
0.0, F1 still 1.0.

## registry.py removed

Asked "what's the registry for", I checked with `grep` and found that
nothing in the package did a lookup by name in the dicts
(`DEMAND_STRATEGIES`/`POTENTIAL_STRATEGIES`/`ALLOCATION_STRATEGIES`)
-- not even `executors/`, which import `PotentialLinearRegression` etc.
directly in Python code. It was infrastructure built "for when it's
needed", with no real consumer -- the same problem that had already
brought down the generic `StageRegistry` before it.

Removed: `src/disslucc/registry.py` and the re-export line in
`__init__.py`. Comes back if/when `executors/` starts resolving
`potential_strategy`/`allocation_strategy` by name from
`record.parameters` instead of importing the class directly -- a
natural candidate (it's where choosing by name coming from the
outside, TOML or an API, makes sense), but not implemented yet.

## validation/pontius.py identified as a dissmodel candidate

Asked whether `pontius_millones()`/`confusion_metrics()` are generic
enough for `dissmodel` instead of `disslucc`, I checked with `grep`:
zero code reference to `land_use_types`/`backend`/Demand/Potential/
Allocation -- it only takes two arrays. Same test we'd already used to
separate `pipeline_core.py` (generic) from `protocols.py` (knows
LUCC) in an earlier prototype.

Found stronger evidence than any earlier candidate: the JOSS paper
draft already cites Pontius & Millones validating
`brmangue-dissmodel` (a different domain -- coastal dynamics, not
LUCC). A second real consumer already exists, satisfying the criterion
`dissmodel`'s issue #128 uses to decide on extraction.

Not moved now -- same three reasons as `_generic` before: waiting on
JOSS, `brmangue-dissmodel` isn't this team's, one-repo-per-fellow
structure. Only documented in `architecture.md`.

## demand/potential/allocation moved into components/

A suggestion to match the real convention of the two original
repositories exactly: `disslucc_continuous/components/demand/`,
`components/potential/raster/`, `components/allocation/raster/` --
"components" was already the name used there, just without the extra
`raster/` level (which we'd already dropped before, being raster-only).

Moved: `demand/`, `potential/`, `allocation/` into `components/`.
`validation/` stayed OUTSIDE on purpose -- there's no "validation
component" in the original repositories (Pontius & Millones lived
inside the executor, not as a reusable module), and we'd already
identified `validation/pontius.py` as a `dissmodel` candidate, not a
LUCC component -- mixing it inside `components/` would hide that
difference. `protocols.py`/`schemas.py` stay loose at the package root
(in the originals they live inside a `schemas/` folder, but that
wasn't asked for, didn't touch it).

Fixed: relative imports in each moved file (`..` -> `...`), the
top-level `__init__.py`, both `executors/`, and two example scripts
that imported `disslucc.demand` directly instead of going through
`disslucc.components.demand` (`run_lab1_real.py`,
`run_lab1_validation.py` -- only those two, the others already
imported via `from disslucc import ...` at the top level, which
doesn't change).

Retested the six example scripts after the change -- all OK, identical
result (same MAE/F1 as always).

## mypy added -- protocols.py stops being just a promise

Asked whether `protocols.py` was actually used: yes, but only as a type
hint in `AllocationClueLike`/`AllocationDClueSLike` -- no real
`isinstance()` anywhere, and with no mypy configured, the annotation
had no enforcement at all. Added `[tool.mypy]` to `pyproject.toml` and
`mypy` as an optional (`dev`) dependency.

Running it for the first time: 12 real errors, not noise. Fixed:
- `load_demand_csv` didn't handle `reader.fieldnames is None` (empty
  CSV) -- crashed with an ugly `TypeError`; now a clear `ValueError`.
- `RegressionSpec.newconst` was created dynamically, never declared --
  **the real disslucc-continuous has exactly the same problem**
  (checked on the real main, same `spec.newconst = spec.const` pattern
  with the field not declared). Declared the field explicitly here;
  doesn't change behavior, just describes what was already happening.
- Two `_mask()` functions returning `Any` instead of `np.ndarray` --
  explicit `cast()`.

After: `mypy src/disslucc` clean (0 errors, 18 files). Retested the
six example scripts -- Lab1 checksum identical
(`853e0e1e65f3ea12c9b49a33f45a4c3521c6d4de8a1b3249c486c2bd95fec90d`),
Lab1/Lab15 MAE/F1 unchanged. Zero regression, three real bugs fixed --
one of them inherited from the original repository itself.

## executors/base.py -- shared base, extracted after measuring first

Question: without generalizing Demand/Potential/Allocation, wouldn't
similar executors explode into duplication? I measured the two
existing executors with `diff -y` before deciding: `validate()`/`load()`
were identical, `save()` had the same skeleton. Real duplication, not
hypothetical -- unlike the `Pipeline`/`StageRegistry` we'd already
reverted (that one generalized Demand/Potential/Allocation themselves,
with only 2-3 classes per role, with no real code duplication to
justify it).

Extracted `executors/base.py` (`LuccExecutorBase`): `validate()`,
`load()`, `_rasterize()` (helper for building the raster backend), and
`save()` (with a default) in the base; `run()` stays abstract in each
subclass, because that's where continuous and discrete genuinely
diverge (which Demand/Potential/Allocation to build). Common method
template, no dispatch by name, no registry.

Honest number: total executor line count went up (237 -> 286),
`base.py`'s docstring is heavy. The gain isn't "less code" -- it's zero
duplication of identical logic between the two files (`diff -y`
afterward shows only the ~60 lines that genuinely diverge, against
several dozen identical lines before).

Retested the six example scripts after the refactor -- identical
result, digit for digit (same Lab1 checksum
`853e0e1e65f3ea12c9b49a33f45a4c3521c6d4de8a1b3249c486c2bd95fec90d`,
same MAE 0.0035832335619405574, same F1 1.0). `mypy src/disslucc`
clean (19 files now, was 18).

## load() returns the backend, not the GeoDataFrame -- fixed after being asked

Asked why `_rasterize()` existed inside `run()` instead of `load()`,
given the package is raster-only: it really was a workaround, admitted
as such at the time -- a way to test with vector data while no real
raster backend had been generated yet. I checked the real
`LUCCRasterExecutor` source (disslucc-continuous) instead of trusting
memory: there, `load()` already calls `vector_to_raster_backend` and
returns the `RasterBackend`; `run(self, data, ...)` receives `data`
already rasterized. The comment in the real code is explicit:
rasterizing is expensive, `load()` runs only once in the Executor's
lifecycle, never run it twice.

Fixed: `LuccExecutorBase.load()` now rasterizes and returns the
backend; `_rasterize()` as a separate method is gone (the logic moved
into `load()`); `run()` on both subclasses receives `data` already as
the backend, with nothing left to call to rasterize.

Good, unexpected side effect: `ExperimentRecord`'s timing became more
honest. Before, the expensive rasterization cost counted inside
`time_run_sec`, hiding where the time went. Now it shows up in
`time_load_sec` (Lab1: 3.08s) and `time_run_sec` drops to the real
cost of running the model (Lab1: 0.21s) -- the automatic provenance
that motivated bringing the Executor back became more accurate because
of the fix.

Retested the six scripts -- identical result (same Lab1 checksum
`853e0e1e65f3ea12c9b49a33f45a4c3521c6d4de8a1b3249c486c2bd95fec90d`,
same Lab15 counts). `mypy src/disslucc` clean.

## data: Any -> data: RasterBackend

Asked whether `data` could be typed instead of left as `Any` -- it
could, it was just not done yet: `RasterBackend` is already importable
(`from dissmodel.geo import RasterBackend`) and already used in the
example scripts. Swapped `Any` for `RasterBackend` in
`LuccExecutorBase.load()`'s return type and in both subclasses'
`run()` (`data` parameter). `Any` stays imported where it still makes
sense (`_spec_from_dict(d: dict[str, Any])`, parsing a loose dict
coming from TOML/JSON).

`mypy src/disslucc` clean after the change. Retested the six scripts --
Lab1 checksum identical, Lab1/Lab15 MAE/accuracy unchanged.

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

## Roadmap: `disslucc` as the single successor, post-JOSS (decided 2026-09-22)

Originally recorded 2026-09-19 as intent, not yet decided. As of
2026-09-22, two of the three open questions below **are now decided**;
what remains is timing and execution, not whether.

**The decision.** `disslucc` is becoming the single successor
repository to `disslucc-continuous` and `disslucc-discrete`, mirroring
`terrame/luccme` itself -- one repository, with continuous and discrete
as components side by side, instead of split by paradigm. Two reasons,
stated plainly:

1. **Efficiency.** As more Demand/Potential/Allocation strategies get
   developed, maintaining two parallel implementations (vector +
   raster, continuous repo + discrete repo, each duplicating its own
   Demand/validation code) doesn't scale and gets confusing. A single
   raster-only package, with Demand and Pontius & Millones validation
   already shared across both paradigms (see "Bringing discrete into
   this repository" above), removes that duplication going forward.
2. **One clear reference.** A single repository citable as "LuccME in
   Python" is a stronger story than two packages that together
   replicate it -- and after the LICENSE/CI/`pytest`/`CITATION.cff`/
   `ModelExecutor`/provenance work already done here, `disslucc` isn't
   behind the two separate repos on engineering grounds anymore.

**Also decided 2026-09-22: raster stays permanent, not provisional.**
The "raster only" choice at the top of this file was originally framed
as a pragmatic simplification for this port. It is now the ecosystem's
permanent direction, precisely *because* new algorithms are coming:
keeping a vector substrate alive in parallel while the component
catalog grows would mean duplicating every new strategy twice and
testing both, for a substrate whose main advantage (fidelity to how
LuccME/TerraME originally worked) is bought at a real, recurring
maintenance cost. Consequence: `paper.md`'s `Vector vs Raster`
cross-substrate check (from `disslucc-continuous`) is retired going
forward, not replaced -- see the Research Impact rewrite item below.

**What's still pending -- timing and execution, not the decision
itself:**

1. `paper.md`'s Lab1 section reports `Vector vs TerraME` *and*
   `Raster vs TerraME` (both 87.37%), plus a `Vector vs Raster`
   cross-substrate consistency check. That comes from
   `disslucc-continuous`, which keeps both substrates. Now that raster
   is decided as permanent, dropping the vector comparison from the
   paper needs to be *an explicit rewrite*, not an accidental loss.
2. The paper's "Research Impact Statement" uses the fact that
   `disslucc-continuous`, `disslucc-discrete`, `brmangue-dissmodel` and
   `disscube` are independently owned repositories as evidence that
   the `ModelExecutor` contract generalizes across packages without
   core changes -- tied to H1 in the CNPq proposal (fellow-owned
   repos). Collapsing them weakens that specific argument unless the
   text is rewritten alongside the migration.
3. `dissmodel` is currently under JOSS review citing
   `disslucc-continuous`/`disslucc-discrete` by name
   (`[@DisSLUCCDiscrete]` in `paper.bib`). Changing what's cited
   mid-review is friction worth avoiding.

**Conditions to revisit this:**

- [ ] JOSS review of `dissmodel` reaches a final decision (accept or
      otherwise) -- don't touch the citation while it's still open.
      This is the main thing execution is still waiting on.
- [x] ~~Decide, explicitly, whether the vector substrate is ever
      coming back to `disslucc`~~ -- decided 2026-09-22: raster only,
      permanently, for the whole ecosystem going forward. See above.
- [ ] Move the repository from `github.com/LambdaGeo/disslucc` to
      `github.com/DisSModel/disslucc` (GitHub's transfer preserves the
      old URL as a redirect, so this is low-risk once done -- but
      needs an org owner to actually run it; not something a patch can
      do). Update `CITATION.cff`'s `repository-code` and
      `CONTRIBUTING.md`'s clone/PR-target URLs alongside it (done
      ahead of the actual transfer in this commit, since GitHub
      redirects the old URL either way).
- [ ] If unifying: release a final tagged version of
      `disslucc-continuous` and `disslucc-discrete`, mint a Zenodo DOI
      for each, then archive (not delete) both -- so every citation
      already printed in the accepted paper keeps resolving.
- [ ] Rewrite the paper's Research Impact paragraph to describe
      `disslucc` as the unified successor, without losing the
      "independently owned packages" evidence for H1 -- possibly by
      keeping `brmangue-dissmodel`/`disscube` as the examples for that
      specific claim instead.
- [ ] Lab15's discriminance gap (a trivial static ranking currently
      reproduces the TerraME output cell-for-cell) is a weaker spot to
      have in the flagship repo than in a secondary one; the planned
      dynamic-covariate scenario should probably land before `disslucc`
      becomes the primary citation, not after.

## TOML config example added for the executors path (2026-09-22)

Clarified a point of confusion: dropping TOML in the "Two deliberate
decisions" section at the top of this file was about the default,
script-first path only (`examples/run_script.py`) -- not about
`src/disslucc/executors/`. The executors path already exists
specifically to be registered in
[`dissmodel-configs`](https://github.com/DisSModel/dissmodel-configs)
and run through `dissmodel-platform`, and that registration is a TOML
file by convention (see `dissmodel-configs/models/*.toml` for the
sibling packages). There was no example of that TOML for `disslucc`
in this repo, unlike `disslucc-continuous`/`disslucc-discrete`, which
is what prompted this entry.

Added `examples/dissmodel-configs/lucc_continuous.toml`, adapted from
`disslucc-continuous`'s `lucc_continuous_vector.toml` (real file in
`dissmodel-configs`) to this repo's actual executor: `name`/`class`
become `"lucc_continuous"` (`LuccContinuousExecutor.name`, raster-only
-- no `lucc_vector`/`lucc_raster` split here), `executor_module =
"disslucc.executors"`, `package = "git+https://github.com/DisSModel/disslucc@main"`.
Encodes the same Lab1 coefficients as
`examples/run_lab1_via_executor.py`'s hand-built `ExperimentRecord`,
so the two are directly comparable.

**Open item, not fixed here**: `dissmodel.executor.cli.run_cli`'s local
`--toml` loader (`dissmodel/executor/cli.py`, `_load_toml`) only lifts
`[model.parameters]` into `record.parameters` -- everything else under
`[model]` (`land_use_types`, `[[model.potential]]`,
`[[model.allocation]]`, `[model.static]`) lands only in
`record.resolved_spec`. `LuccContinuousExecutor`/`LuccDiscreteExecutor`
read `land_use_types`/`potential_data`/`static`/`allocation_data`
directly from `record.parameters` (confirmed against
`src/disslucc/executors/continuous.py` and `discrete.py`), matching
`ModelExecutor.run()`'s documented contract that it "receives record
with resolved_spec and parameters already merged" -- but that merge is
platform-side (`dissmodel-platform`, not in this repo or in
`dissmodel` itself). So `examples/dissmodel-configs/lucc_continuous.toml`
is correct for platform registration, but is **not** yet a working
`--toml` argument for `python -m disslucc.executors.continuous run
--toml ...` locally -- that would need either `dissmodel`'s local CLI
to do the same resolved_spec merge, or the executors here to read
`record.resolved_spec["model"]` as a fallback. Left open; affects
`dissmodel` (the CLI), not `disslucc` alone.

## Discrete TOML example + README/api.md cross-links added

Follow-up to "TOML config example added for the executors path":
that entry only covered `LuccContinuousExecutor`, and neither the
README nor `docs/api.md` pointed at `examples/dissmodel-configs/`,
so it was easy to miss even after landing.

Added `examples/dissmodel-configs/lucc_discrete.toml`, same
convention as the continuous one, encoding the same Lab15/Moju
coefficients as `examples/run_lab15_via_executor.py` (`transition_matrix`,
three `[[model.potential]]` entries with `elasticity`). Verified
end-to-end (not just parsed): loaded both TOMLs with `tomllib`,
simulated the platform-side `resolved_spec` -> `parameters` merge by
hand, ran `LuccContinuousExecutor`/`LuccDiscreteExecutor` through
`execute_lifecycle`, and diffed the resulting `record.metrics` against
the corresponding `run_*_via_executor.py` script run in the same
environment -- identical in both cases (continuous: same three final
areas to the full float; discrete: same `final_f_cells`/`final_d_cells`/
`final_o_cells` -- 5474/365/3).

Cross-linked from both README.md (the `disslucc.executors` paragraph)
and `docs/api.md` (new "Registering with dissmodel-configs (TOML)"
subsection under Executors), so the TOML path is discoverable from
where a reader already learns the executors exist, not just from this
log.

## Resolved: local CLI now wired up, upstream fix sent to `dissmodel`

Follow-up closing the open item from the two entries above. Two
separate problems had to be fixed, one in each repository:

**In `dissmodel` (upstream, not this repo).** Confirmed the gap
against a *fresh* `git clone` of `DisSModel/dissmodel@main` (not a
possibly-stale local copy) -- `dissmodel/executor/cli.py`'s
`_load_toml`/`_build_record` only ever copied `[model.parameters]`
into `record.parameters`; every other `[model]`-level key
(`land_use_types`, `[[model.potential]]`, ...) landed only in
`record.resolved_spec`, contradicting `ModelExecutor.run()`'s own
docstring ("receives record with resolved_spec and parameters already
merged") and `dissmodel`'s own `docs/api/executor/cli.md`, whose
`model.toml` example already showed a `[[model.potential]]` section
with no explanation of how it would reach the executor. Wrote a fix
(`_load_toml` now merges `[model]` keys other than a fixed metadata
set -- `executor_module`/`name`/`class`/`description`/`package`/
`dissmodel` -- into `params`, `[model.parameters]` still winning on
overlap, `--param` still winning over both), 11 new regression tests
in `tests/executor/test_cli.py`, and updated
`docs/api/executor/cli.md`. Full `dissmodel` suite: 441 -> 449 passed,
2 skipped, `mypy dissmodel` clean, `mkdocs build --strict` clean. Not
yet merged/released -- `disslucc` still pins `dissmodel==0.6.3`
exactly, which predates the fix. (Shipped in `dissmodel` 0.6.4;
`disslucc` now pins `dissmodel>=0.6.4` -- see README.md/`api.md` for
the current, working state rather than this entry's snapshot.)

**In `disslucc` (this repo).** Once the upstream fix made local
`--toml` runs reach `validate()`, it surfaced a second, independent
problem: `examples/dissmodel-configs/*.toml` used `[[model.potential]]`/
`[[model.allocation]]` (copied from the real `dissmodel-configs` entry
for `disslucc-continuous` given as a reference), but
`LuccContinuousExecutor`/`LuccDiscreteExecutor`'s `required_parameters`
expect `potential_data`/`allocation_data` -- this package's own
parameter names, unrelated to the CLI merge fix. Renamed the TOML
table names (data only, no code change) to match. Also added
`if __name__ == "__main__": run_cli(...)` to both
`src/disslucc/executors/continuous.py` and `discrete.py` -- neither
had one, so `python -m disslucc.executors.<name> run ...` didn't work
at all before this, independent of both TOML issues.

**Verified together, not separately**: built a `dissmodel` venv with
the fix installed, ran both commands for real --
`python -m disslucc.executors.continuous run --toml
examples/dissmodel-configs/lucc_continuous.toml --input
data/input/csAC.zip --param demand_csv=data/input/examples_demand_lab1.csv`
and the discrete equivalent -- end to end through the actual CLI
(not a hand-simulated merge like the previous two entries). Continuous
output checksum: `853e0e1e65f3ea12c9b49a33f45a4c3521c6d4de8a1b3249c486c2bd95fec90d`
-- identical to the Lab1 checksum recorded in `CLAUDE.md`. Discrete
final counts: `{'f': 5474, 'd': 365, 'o': 3}` -- identical to
`run_lab15_via_executor.py`. `disslucc`'s own suite (against the fixed
`dissmodel`): 14 passed, 2 xfailed, unchanged.

README.md and `docs/api.md` updated with the real, working command --
with an explicit callout that it needs a `dissmodel` release past
0.6.3, since `pip install -e .` today still installs the pinned,
unfixed 0.6.3.

## `save()` now actually writes the output raster

Found while answering a question about `--output`: `LuccExecutorBase.save()`
never wrote anything to disk. It hashed the backend's raw array bytes
in memory into `record.artifacts["output"]`, set `status="completed"`,
and returned -- `record.output_path`/`--output` were accepted and
echoed in the CLI's summary (`output: outputs/result_<id>.tif`) but no
such file was ever created. Confirmed by re-running a prior `--output`
test and checking the path with `ls` afterward: not found.

Checked how `brmangue-dissmodel` (a sibling package, further along --
this is where a QGIS plugin was built reading simulation output
straight from MinIO) solves this, against its actual source, not from
memory: `RasterExecutor.save()` calls
`dissmodel.io.raster.save_geotiff((backend, meta), uri, band_spec=...)`,
which writes a local file or, for an `s3://` URI, uploads via
`dissmodel.io._storage.get_default_client().put_object(...)`. `meta`
there comes from `load_geotiff()`. `disslucc`'s own `load()` uses
`vector_to_raster_backend()` instead, which doesn't return a separate
meta dict -- but it does set `crs`/`transform` directly as attributes
on the `RasterBackend` it constructs (checked against
`dissmodel/io/convert.py`), so `save()` can build the
`{"crs": backend.crs, "transform": backend.transform}` dict itself
from the backend already in hand, with no change needed to `load()`.

Fixed: `LuccExecutorBase.save()` now calls `save_geotiff` with a
`band_spec` built from `result["land_use_types"]` (+ `"mask"` if
present in the backend), writes to `record.output_path` (defaulting to
`output_<experiment_id[:8]>.tif` if `--output` wasn't given, same
convention as `brmangue`'s `default_output_uri`), and stores the
checksum of the actual written file in `record.artifacts["output"]`.

**Side effect worth flagging explicitly**: the checksum value changes.
Before, `record.artifacts["output"]` hashed raw NumPy bytes; now it
hashes the written GeoTIFF (different framing/compression -- same
data, different bytes). The Lab1 checksum narrated across this file
(`853e0e1e65f3ea12c9b49a33f45a4c3521c6d4de8a1b3249c486c2bd95fec90d`)
is the *old* (in-memory-bytes) value and is not reproduced by a fresh
run with this fix -- confirmed nothing in `tests/` asserts that exact
string (only this file's own narrative history cites it, left as-is).
A new run with `--output` now produces a real file whose checksum can
be cited instead, going forward.

Verified: ran both executors via the real CLI with `--output`, opened
the resulting `.tif` with `rasterio` -- correct CRS (`EPSG:29101`
continuous / `EPSG:4618` discrete), correct transform (5000 m
resolution for continuous, matching the TOML), correct shape matching
the rasterized backend, one band per land-use class tagged with its
name (`dst.update_tags(i, name=name)`, e.g. `{"name": "f"}`) plus a
`mask` band whose sum equals the loaded feature count exactly (6,574
for Lab1 -- matches `Loaded: 6,574 features` in the same run's log).
pytest: 14 passed, 2 xfailed, unchanged (no test exercises `save()`'s
disk I/O). mypy: same 3 pre-existing, unrelated errors.

## Third reason to migrate: bugs found this session would otherwise need fixing three times

Adds to "Roadmap: `disslucc` as the single successor, post-JOSS" above,
not a new decision -- concrete evidence for one already made.

This session found and fixed three real, independent bugs in the
executors/CLI/output path: no local CLI entry point at all (no
`if __name__ == "__main__"`), TOML table names not matching
`required_parameters` (`potential`/`allocation` vs. this package's
`potential_data`/`allocation_data`), and `save()` never writing the
output raster to disk (accepted `--output`/`record.output_path`,
silently did nothing with them -- see "`save()` now actually writes
the output raster" above). None of these are `disslucc`-specific
science bugs; they're the same executor-lifecycle plumbing
(`ModelExecutor`/`ExperimentRecord`/CLI) that `disslucc-continuous`
and `disslucc-discrete` each carry their own copy of. Staying split
means each of those two would need the same three fixes applied and
verified separately -- not a reason to migrate on its own, but a
concrete cost of *not* migrating that wasn't part of the original
two-reason case (Efficiency, One clear reference).

Weighed against the one real cost of migrating before JOSS concludes
(`dissmodel`'s paper currently cites `disslucc-continuous`/
`disslucc-discrete` by name mid-review -- see "Conditions to revisit
this" above): judged worth accepting that citation noise rather than
fixing the same three bugs three times. This doesn't by itself check
off the JOSS-review condition in the list above -- that's still an
external, ongoing process -- but it does mean the cost side of that
tradeoff is now backed by a concrete, first-hand instance, not just
the general "duplication doesn't scale" argument from the original
entry.

## `dissmodel` paper/README citations consolidated to `disslucc`; review stall changes the calculus

The JOSS reviewer for `dissmodel`'s paper stalled; the editor is
likely to reassign. Given that, plus `disslucc-continuous`/
`disslucc-discrete` being unused by anyone else and carrying the
three plumbing bugs fixed this session (see above), decided the
"citation noise mid-review" cost accepted in the previous entry is no
longer worth avoiding -- `dissmodel`'s `paper.md`/`paper.bib` and
`README.md` now cite/list `disslucc` only, not the two source repos.
This is `dissmodel`-repo work, not `disslucc`-repo work; noted here
because it's the trigger for the next step below.

Changes made in `dissmodel` (separate repo, own commits/patches):
`paper.bib` merges the two `@software` entries into one `@DisSLUCC`
entry pointing at `github.com/DisSModel/disslucc`; `paper.md` updates
all prose mentions (Summary, Lab1/Lab15 paragraphs, Research Impact
Statement, Author Contributions -- `J.M.P.A.` now credited for
`disslucc`, AI Usage Disclosure) accordingly, including replacing the
Lab15 discrete speed figure (56.8 ms/step, measured on
`disslucc-discrete`'s vector-only executor -- not valid for
`disslucc`'s raster path, so dropped rather than kept or fabricated)
with 10.3 ms/step, measured fresh against `disslucc`'s own
`examples/dissmodel-configs/lucc_discrete.toml` (Lab15/Moju, 6 steps,
0.062s run phase via the CLI's profiling report -- ModelExecutor
lifecycle `run` phase only, not load/save). `README.md`'s specialized
model libraries table merges the two rows into one, pointing at
`github.com/LambdaGeo/disslucc` (not yet `DisSModel/disslucc` --
matches this repo's current, not future, location).

Next: the user (maintainer) plans to archive `disslucc-continuous`
and `disslucc-discrete` separately (own repos, not tracked in this
decision log) with a note in each that there's no guarantee of
compatibility with newer `dissmodel` releases and that development
moved to `disslucc` -- the same treatment `terrame/luccme` itself
received when TerraME/LuccME's own active development moved on. Not
yet done as of this entry; this repo's own migration status section
in `README.md` already anticipates it ("will be released, tagged,
archived, and kept citable once this migration completes").

## Readability pass on `potential/`, for PIBIC onboarding: `scipy.special.expit` adopted, `numpy.ma` and `tensordot` rejected

Requested while preparing onboarding material for PIBIC students who
will read `potential/linear.py` and `potential/logistic.py`: "does
anything here have an obvious simplification using something the
Python/NumPy/SciPy community already provides?" Three candidates were
tried; only one was kept, for reasons worth recording so they aren't
re-litigated later.

**Adopted -- `logistic.py`'s hand-rolled sigmoid replaced with
`scipy.special.expit`.** The code manually clipped `z` to
`[-50, 50]` before `1 / (1 + exp(-z))`, with a comment explaining the
clip exists only to avoid `exp()` overflow on nodata cells. `expit`
is SciPy's numerically stable sigmoid -- exactly what that comment
was working around by hand -- so the clip and the manual formula both
go away. `scipy` was already an installed, transitive dependency (via
`dissmodel`'s own deps), but was not a *declared* one; added it
directly to `pyproject.toml`'s `dependencies`, since `disslucc` now
imports it itself rather than relying on an accident of what
`dissmodel` happens to pull in. Verified bit-for-bit identical output
on both Lab1 and Lab15 (same `mae`/`rmse`/`quantity_disagreement`/
`allocation_disagreement` to full float precision, not just "within
tolerance") before and after -- `docs/validation.md` needs no update.

**Rejected -- `numpy.ma` for `land_use_no_data` in `linear.py`.** The
suggestion was to replace `reg = reg * (1.0 - no_data_arr)` with a
masked array, on the reasoning that `land_use_no_data` sounds like a
binary "missing data" flag. Checked the actual values behind it first
(`data/input/csAC.zip`'s `outros` column, as loaded for the Lab1
scenario): real-valued, 2183 distinct values between ~0 and 1, not a
0/1 mask. It's the *fraction* of a cell already committed to a
non-transitionable "other" class, and potential is scaled down
proportionally -- not zeroed out. `numpy.ma` is for hard/boolean
masking; using it here would have silently changed the science despite
looking like a pure refactor. Left the line as-is, added a comment
recording this so the next person doesn't repeat the same
name-implies-semantics mistake. Good example, for the PIBIC material
itself, of why to check the data before trusting a parameter's name.

**Rejected (for now) -- vectorizing `const + sum(beta_k * driver_k)`
with `np.stack`/`np.tensordot` instead of the Python `for col, beta in
spec.betas.items()` loop.** Mathematically the same linear
combination, and arguably more idiomatic NumPy for a small number of
drivers. Tried it in both `linear.py` and `logistic.py` and reran the
full validation: Lab15 (binary, exact-match assertions) was
unaffected, but Lab1's `mae` moved from `0.0035832335619405574` to
`0.003583233421432411` -- floating-point summation reordering, not a
bug, and still far inside the `0.01` tolerance both
`tests/test_validation_lab1.py` and `disslucc-continuous`'s own
criterion use. Reverted anyway: this repo's own rule (see top of this
file, and `docs/validation.md`'s header) is that `docs/validation.md`'s
numbers are cited in `dissmodel`'s JOSS paper, and "the rounded number
published doesn't change" is a weaker bar than "bit-identical unless a
change is deliberately about the science." A cosmetic vectorization
isn't worth even a last-decimal-digit drift here. Revisit only if a
real performance need shows up (many drivers, large rasters) that
would justify accepting that tradeoff explicitly and re-publishing
`docs/validation.md`'s numbers alongside it.

## Same pass, `allocation/clue.py`: two safe cosmetic fixes, one documented-not-fixed dead branch

Continuation of the readability pass above, this time over
`AllocationClueLike` (the CLUE-like continuous allocator). Same
discipline: verify bit-for-bit identical Lab1/Lab15 output, run the
full suite, before keeping any change.

**Applied -- two zero-risk stylistic fixes in `_correct_cell_change`.**
`flat = lambda lu: ...` (a lambda assigned to a name -- PEP 8 E731, and
it shows as `<lambda>` in tracebacks instead of a real function name)
became a nested `def flat(lu: str) -> np.ndarray: ...`. Needed a
`cast(np.ndarray, ...)` inside it to keep mypy clean (`self.backend.get()`
returns `Any`), matching the pattern `_mask()` already uses just above
it. `[self.allocation_data[i].min_value for i in range(len(lus))]` (and
the `max_value` line next to it) became
`[spec.min_value for spec in self.allocation_data]` -- `allocation_data`
is already in `land_use_types` order, so indexing through `range(len(...))`
bought nothing. Verified identical Lab1 `mae`/`rmse` and Lab15
disagreement to full float precision before/after; `pytest`/`mypy`/`ruff`
all clean.

**Found, documented, deliberately not fixed -- the `no_data` exclusion
in `_apply_complementar`'s deficit-correction branch is dead on two
levels.** `no_data = getattr(self, "land_use_no_data", None)`: that
attribute is a `PotentialLinearRegression.setup()` parameter (see
`potential/linear.py`) that `AllocationClueLike.setup()` never accepts
-- so `no_data` is always `None`, and `lu != None` is always `True` for
a class name, meaning the `eligible = [lu for lu in others if lu !=
no_data]` filter never actually excludes anything. Traced the likely
original intent by checking Lab1's real config
(`examples/run_lab1_real.py`): `land_use_no_data="outros"` (on
`Potential`) and `static["outros"] == 1` (on `Allocation`) name the
same class, so this was almost certainly meant to protect the
region's fixed/static class from this branch's deficit correction --
the same protection `_compute_change`/`_correct_cell_change` already
give `static == 1` classes elsewhere in this same file, just spelled
with the wrong variable here. Also instrumented all 7 Lab1 steps:
`deficit.any()` was never `True` once -- this whole branch is
unexercised by every scenario in the repository, with no test proving
either the current or a fixed version behaves correctly.

Decided not to fix this now, on both counts: (1) the correct fix
isn't "wire `land_use_no_data` through" -- it's changing the criterion
to `self.static[lu] != 1`, a different and more invasive change than
it looks like at first; (2) there is zero test coverage of this
branch, current or fixed, and this repository's whole discipline
(`docs/validation.md` numbers cited in `dissmodel`'s JOSS paper) is
built on not changing unverified behavior without a benchmark to
check it against. A synthetic scenario that forces `deficit.any()`
would be the right way to close this gap, but that's new test-writing
work, not a readability pass. Recorded here, and as an inline comment
at the call site, so the next person doesn't need to re-derive this
from scratch, and doesn't mistake "wiring `land_use_no_data` through"
for the actual fix.

## Same pass, `allocation/clue_s.py`: one applied, two considered and rejected

Continuation of the readability pass, now over `AllocationDClueSLike`
(discrete CLUE-S allocation). Same discipline as the two entries above:
bit-for-bit Lab1/Lab15 comparison before keeping anything.

**Applied.** `max_diff = float(np.max(np.abs(list(diff.values()))))` --
`diff` is a plain `dict[str, float]` with one scalar per land-use class
(a handful of classes, not per-cell). Round-tripping a handful of
Python floats through `list -> np.array -> np.abs -> np.max -> float`
buys nothing; `max(abs(v) for v in diff.values())` is the same value,
plain stdlib. Verified bit-for-bit identical Lab1/Lab15 metrics;
`pytest`/`mypy`/`ruff` all clean.

**Considered, rejected -- `numpy.ma` for the masked argmax
(`scores = np.where(allowed, scores, -np.inf); np.argmax(scores, axis=1)`).**
This *looks* like the textbook `numpy.ma` use case (a real boolean mask,
unlike the `land_use_no_data` false alarm in `clue.py`), but the
`-np.inf` sentinel is already the standard, well-understood idiom for
"argmax over allowed choices only", and masked-array argmax has its own
sharp edge -- behavior on a fully-masked row (a cell with zero allowed
transitions) isn't obviously the same as `-np.inf`'s behavior (picks
index 0 deterministically) without checking. No test exercises a
transition matrix with a fully-blocked cell, so there's no way to
verify equivalence. Not worth the swap for a purely cosmetic gain over
already-correct, already-idiomatic code.

**Considered, rejected -- restructuring the `for n_iter in
range(self.max_iteration + 1): ... if n_iter >= self.max_iteration:
raise` convergence loop** into a cleaner `for/else`. Mechanically
sound, but touches the exact iteration count at which non-convergence
raises `RuntimeError`, and no test in this repository exercises that
failure path (Lab1/Lab15 always converge well within their configured
`max_iteration`). Changing loop bounds with zero test coverage of the
boundary condition it changes is exactly the kind of "looks safe,
unverifiable" edit this readability pass has been avoiding throughout
`potential/` and `allocation/`.

## `allocation/clue_s.py`: hoisting `pot`/`1+tau` out of the convergence loop -- an actual algorithmic improvement, not just readability

Different category from the three entries above: this one changes
*what the algorithm does* (fewer redundant recomputations per call),
not just how it's written, so it got measured, not just diffed.

`pot = np.stack([self.backend.get(lu + "_pot").ravel() for lu in
lu_types], axis=1)` was being recomputed **every iteration** of
`execute()`'s convergence loop, even though `<lu>_pot` is written once
by `Potential.execute()` before `Allocation.execute()` runs at all, and
nothing inside this loop ever writes it back -- only `iter_vec` changes
between iterations. Same for `1.0 + tau`. Instrumented Lab15 first
(before touching anything): `execute()` took between 1 and 68
iterations per time step across the 6 steps, so this was a real,
measurable amount of repeated work, not a one-off.

Hoisted both `pot` and `one_plus_tau = 1.0 + tau` above the loop.
Verified bit-for-bit identical Lab1/Lab15 metrics (this change only
touches `clue_s.py`, so Lab1 was never going to move, but checked
anyway per this session's own discipline). Measured wall-clock time
for `run_lab15_raster()` (8 repetitions each, sorted):

    before: median 0.4792s, min 0.4510s
    after:  median 0.4283s, min 0.4077s  (~10-11% faster end to end)

That end-to-end number includes shapefile loading (a fixed cost this
change doesn't touch), so the saving *inside* the allocation loop
itself is proportionally larger and should grow with raster size and
iteration count -- the avoided work scales with
`n_iterations * n_classes * n_cells` per step, while the I/O floor
stays constant. Not benchmarked at larger scale; if raster size grows
significantly in a future scenario, worth re-measuring rather than
assuming the same ~10% holds.

`pytest`/`mypy`/`ruff` all clean after the change.

## Ecosystem-wide review pass (PIBIC-focused): `RegressionSpec.newconst` footgun and an `api.md` inaccuracy

Broader pass across the whole package (not just `potential/`/`allocation/`
this time), specifically looking for anything that would confuse an
undergraduate reading this code for the first time. Two real findings,
both fixed.

**`schemas.RegressionSpec.newconst` was a silent-no-op constructor
trap.** It's a regular dataclass field (`newconst: float = 0.0`),
so `RegressionSpec(const=0.5, newconst=99)` was accepted -- but
`PotentialLinearRegression.setup()`/`execute()` always overwrite it
with `spec.newconst = spec.const` before ever reading it, on every
single step, not just the first. So any value passed at construction
time was silently discarded, immediately. Confirmed with `grep` that
nothing in `src/`/`examples/`/`tests/` ever constructs a
`RegressionSpec` with `newconst=...` -- this was a purely latent trap
for a future caller, not a bug that ever fired. Fixed with
`field(default=0.0, init=False, repr=False, compare=False)`:
`newconst` is internal runtime state the model manages, not something
a caller configures, so it's no longer part of `__init__`, doesn't
clutter `repr()`, and doesn't affect `==` between two specs that only
differ in runtime-mutated state. Verified: `RegressionSpec(const=0.5,
newconst=99)` now raises `TypeError` immediately instead of silently
accepting and discarding the value. Bit-for-bit identical Lab1/Lab15
metrics; `pytest`/`mypy`/`ruff` all clean.

**`docs/api.md` mischaracterized `land_use_no_data`.** It described the
parameter as "class to exclude from the calculation (e.g. water)" --
which is exactly the wrong mental model this session already
disproved by checking the real data (see the `potential/linear.py`
entry above): it's a real-valued `[0,1]` array that scales potential
down proportionally (`reg * (1 - value)`), not a binary
exclusion/no-data mask. This is the same misconception that produced
the dead `no_data` code in `allocation/clue.py`, now also fixed in the
one document a student would read *before* the source, making it more
likely to mislead, not less. Corrected the parameter comment in
`api.md` to describe the actual behavior.

## Reference data moved to LambdaGeo/terrame-docker; year-by-year goldens; `cell_correction`

**Where the references live.** `benchmark/reference/*.lua` and
`benchmark/data/*.zip` left this repository. The scripts (unchanged, byte for
byte, under their original names `lab1_*`/`lab6_*`) and the original TerraME
outputs now live in [LambdaGeo/terrame-docker](https://github.com/LambdaGeo/terrame-docker)
(`benchmark/references/`), next to the Docker image (TerraME 2.0.1 + LuccME
6244dd4) and the generator that produces year-by-year goldens. Here,
`benchmark/goldens/` keeps only the generated results, so tests run without
Docker. The two former zips are the last year of `lab01_md1643` and
`lab15_md10` (max difference 5e-13 and 0); every validation number in
`docs/validation.md` is unchanged (Lab1 MAE 0.0035832335619404 vs
0.0035832335619406 before).

terrame-docker (v0.1.0) has goldens for all 21 functional labs of the LuccME
package, with the package's numbering; this repository keeps only the four its
tests use and adds others together with the component and test that need them
(not every LuccME algorithm will be ported). In the package
labs the allocation is accepted at the first pass every year (0 iterations),
so only `lab01_md1643`/`lab15_md10` exercise the convergence loop.

**Discrete: convergence confirmed.** Year by year, `AllocationDClueSLike`
matches TerraME's iteration count (0, 67, 56, 56, 61, 61) and `d_out`/`d_pot`
exactly. This is the check the Lab15 discriminance warning asked for.

**Continuous: the Lab1 MAE has one cause, and it is a TerraME bug.** The drift
starts in 2009, a year with 0 iterations on both sides and identical `d_pot`.
LuccME's `correctCellChange` never runs: its guard reads
`if (cell.regionregionAloc == rNumber)` (`AllocationCClueLike.lua:503`, a typo
for `regionAloc`), always false (`CClueLikeSaturation` spells it correctly).
Decision: keep the intended algorithm. `AllocationClueLike` gains
`cell_correction: bool = True`; `False` skips `_correct_cell_change` and
reproduces TerraME year by year, iteration counts included (0, 0, 8, 26, 18,
17, 17; MAE < 1e-7). The tests against the continuous goldens use `False`;
`test_lab1_default_cell_correction_deviates_from_terrame` pins the default's
deviation. Both allocations also record `iterations_per_step`.

## Spatial-lag potential and saturation allocation, for LuccME-BR (2026-09-24, #6)

**What and why.** `PotentialSpatialLagRegression` and
`AllocationClueLikeSaturation` port LuccME's `PotentialCSpatialLagRegression`
and `AllocationCClueLikeSaturation` (LuccME `6244dd4`), the components LuccME-BR
(Bezerra et al. 2022, PLOS ONE e0256052) is built from. They were written and
validated first in [profsergiocosta/luccmebr-reconstruction](https://github.com/profsergiocosta/luccmebr-reconstruction),
with this package's interfaces, and moved here so that repository keeps only
the model. Nothing existing changed: Lab1/Lab15 numbers are the same.

**Faithful to the Lua, including what looks accidental** — each point is pinned
by a test that fails on the other reading:
- the potential's constant adaptation accumulates year to year (LuccME writes
  it back into `const`), unlike `PotentialLinearRegression`;
- `lab06`'s `updateYears` copies the new drivers into the cells by position
  (`forEachCellPair`), and `csAC_2009` is not in `csAC`'s order;
- `correctCellChange` runs here (the Saturation variant spells `regionAloc`
  right), as the Lua writes it — not `AllocationClueLike`'s own version —
  and its `BACKP`, declared outside the loop over cells, carries over from cell
  to cell: the cells' order matters, given by `order_attr`;
- the neighbourhood LuccME names "11x11" is `createNeighborhood{strategy="mxn"}`
  with no `m`/`n`: TerraME's default, 3 × 3 with the cell
  (`packages/base/lua/CellularSpace.lua`).

**Validation, and the Lua in `tests/lua/`.** The `lab03`/`lab06` goldens match
cell for cell, year by year, iterations and maximum error included
(`docs/validation.md`). But those labs never reach `correctCellChange`, the
saturation branch or an isolated cell. For those, `tests/test_lua_differential.py`
runs the original Lua functions with `lupa` on synthetic cases that reach every
branch. That brings Lua source back into this repository, after the reference
scripts left it for terrame-docker (entry above) — deliberately, and
**provisionally**: these are component sources needed to test branches, not
reference scripts, and `lupa` + stubs is not TerraME. The intended replacement
is component-level goldens generated in terrame-docker (the same synthetic
cases run in the real TerraME, inputs and outputs as CSV); when they exist,
`tests/lua/` and the `lupa` dependency go, and `benchmark/goldens/` holds
results only again.

**Left open.** `AllocationClueLike`'s `cell_correction=True` is an intended
version of the step LuccME skips there; the Saturation variant's
`correctCellChange` is LuccME's own. Whether the first should follow the second
is a separate question, not settled here.

## `LuccSaturationExecutor`, with raster input (2026-09-24, #6)

LuccME-BR is run from a model TOML, not a script: the same second entry point
the continuous and discrete executors are (entry "The Executor came back").
`LuccSaturationExecutor` builds the three components from `record.parameters`
and differs from `LuccContinuousExecutor` where that model needs it:

- **raster input.** A continental cellular space (≈ 260 k cells, 15+ drivers)
  is built once, as a raster, by the data pipeline (DisSCube in
  luccmebr-reconstruction); rasterizing a vector at every run, as the base's
  `load()` does, is the wrong way round there. So `load()` reads a GeoTIFF
  whose bands carry their names (`dissmodel.io.load_dataset(fmt="raster")`,
  the format `save()` already writes), and falls back to the base for vectors.
  `_read_geotiff` returns the georeference in `meta`, not in the backend, so
  `load()` copies it over — `save()` needs it.
- **regions** are named per entry (`lu`, `region`) instead of implied by list
  position, because LuccME-BR has three regions × six classes.
- **`save_steps`**: a model checked against maps of intermediate years
  (LuccME-BR: IBGE 2010, 2012, 2014) needs those states, not only the last.

Checked end to end through the CLI: `examples/dissmodel-configs/lucc_saturation.toml`
is lab03, and its run matches the lab03 golden in 2011 and 2014
(`tests/test_executor_saturation.py`).

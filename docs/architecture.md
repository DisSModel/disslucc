# Architecture — disslucc

## What this package is

**Raster-only**, **script-first** port of two real repositories from
the DisSModel ecosystem:

- [`disslucc-continuous`](https://github.com/DisSModel/disslucc-continuous)
  (`main` branch) — continuous CLUE (Verburg et al. 1999)
- [`disslucc-discrete`](https://github.com/DisSModel/disslucc-discrete) —
  discrete CLUE-S (Verburg et al. 2002)

unified into a single package, because real parts of what they do
(Demand, Validation) were already duplicated code between the two --
see ["Why unify continuous and discrete"](#why-unify-continuous-and-discrete)
below.

## Two decisions that define everything here, and a third that came back

**1. Raster only.** The two original repositories keep vector and
raster in parallel. For LUCC with large data, raster is the better
path, and keeping two substrates creates complication without
proportional payoff right now -- a deliberate decision, not a
technical limitation.

**2. Script-first as the default entry point, not the only one.** No
`ModelExecutor` required -- a Python script can build the components
directly:

```python
demand = DemandInline(values=..., land_use_types=...)
potential = PotentialLinearRegression(backend=..., demand=demand, ...)
allocation = AllocationClueLike(backend=..., demand=demand, potential=potential, ...)
env.run()
```

the way an original LuccME `.lua` script built
`P1 = PotentialCLinearRegression{...}; LuccMEModel{potential=P1, ...}`.
The whole script **is** the experiment -- reproducible, versionable in
Git, without depending on any platform on top.

**3. `executors/` — `ModelExecutor` came back, with a shared base.**
An earlier version of this package completely dropped
`ModelExecutor`/`ExperimentRecord` in favor of script-first only. That
contradicted `dissmodel`'s own central argument (automatic provenance
-- input checksum, parameters, timing, output paths -- is a
"first-class concern" in the paper's Statement of Need).
`executors/continuous.py` and `executors/discrete.py` bring that back
as a SECOND entry point, not as a replacement: the same direct scripts
keep working exactly as before.

After measuring with `diff` that the two had identical
`validate()`/`load()` and the same `save()` skeleton, I extracted
`executors/base.py` (`LuccExecutorBase`) with that shared behavior --
it's not dynamic dispatch by name, it's plain inheritance (method
template): `run()` stays abstract, each executor implements its own,
because that's where continuous and discrete genuinely diverge. Total
line count went up (237 → 286, `base.py`'s docstring is heavy), so the
gain isn't "less code" -- it's zero duplication of identical logic: a
bug in `validate()`/`load()` now only needs fixing in one place, not
two that could drift apart unnoticed (the same real problem we already
saw with `DemandPreComputedValues` duplicated between the original
repositories). Tested by running the same already-validated Lab1/Lab15
scenarios -- identical result, digit for digit. See
[`decisions.md`](decisions.md#the-executor-came-back) for the numbers.

## `validation/pontius.py`: a candidate for `dissmodel`, not just `disslucc`

`pontius_millones()`/`confusion_metrics()` have no code reference at
all to `land_use_types`, `backend`, `Demand`/`Potential`/`Allocation`
-- they take two arrays (`pred`, `ref`) and return the decomposition,
with no knowledge that land use is being compared. Same test that
separated `pipeline_core.py` (generic) from `disslucc/protocols.py`
(knows LUCC) in an earlier prototype -- by that criterion, it's a
`dissmodel` candidate, it doesn't belong stuck here.

Stronger evidence than any earlier candidate: the JOSS paper draft
already cites Pontius & Millones validating `brmangue-dissmodel`
(mangrove coastal dynamics -- a different domain from LUCC). A second
real consumer already exists, not a hypothetical one -- the criterion
`dissmodel`'s own issue #128 uses to decide on extraction is already
met.

Not migrated now: waiting for the JOSS verdict (decision already
made), `brmangue-dissmodel` isn't this team's (coordination between
people, not just refactoring), and the project's
one-repo-per-fellow structure makes "where the code lives" an
institutional decision, not just a technical one.

## `protocols.py`: a type hint with no enforcement, until now

`DemandProtocol`/`PotentialProtocol` are `@runtime_checkable`, but
nowhere in the code does anything `isinstance()` them -- the value was
just contract documentation until `mypy` entered the project (see
"What this package is" -- `[project.optional-dependencies].dev` +
`[tool.mypy]` in `pyproject.toml`). Running `mypy src/disslucc` for
the first time: **12 real errors across 4 files**, not noise --

- `load_demand_csv`: `reader.fieldnames` can be `None` (empty CSV),
  the original code didn't handle that -- an ugly `TypeError` instead
  of a clear error. Fixed.
- `RegressionSpec.newconst`: created dynamically at runtime
  (`spec.newconst = spec.const`), never declared on the dataclass --
  **the same problem exists in the real `disslucc-continuous`**
  (checked on `main`). Declared explicitly here, without changing
  behavior.
- Two `_mask()` methods (`allocation/clue.py`, `allocation/clue_s.py`)
  returning `Any` instead of `np.ndarray` -- `backend.arrays.get()`
  isn't typed. Explicit `cast()` in both.

After the fixes: `mypy src/disslucc` clean, retested all six example
scripts -- identical result (same checksum, same MAE, same F1).
`protocols.py` now has real enforcement, not just a promise.

## Fidelity, by module

| Module | Faithful to the original? | Source |
|---|---|---|
| `protocols.py` | Yes, byte for byte (main) | `disslucc-continuous/schemas/protocols.py` |
| `components/demand/precomputed.py` | Yes, byte for byte (main) | `disslucc-continuous/components/demand/precomputed.py` |
| `components/demand/inline.py` | **Doesn't exist in the original** | my own convenience (only exists on the `decoupling` branch, where the idea was taken from) |
| `components/potential/linear.py` | Yes, identical algorithm (main) | `disslucc-continuous/components/potential/raster/linear.py` |
| `components/allocation/clue.py` | Yes, identical algorithm (main) | `disslucc-continuous/components/allocation/raster/clue.py` |
| `components/potential/logistic.py` | Faithful algorithm, **raster is new** | ported from `disslucc-discrete/components/potential/vector/logistic_regression.py` (only vector existed) |
| `components/allocation/clue_s.py` | Faithful algorithm, **raster is new** | ported from `disslucc-discrete/components/allocation/vector/clue_s.py` (only vector existed) |
| `components/potential/spatial_lag.py` | Yes, the Lua itself (LuccME `6244dd4`), **raster is new** | `luccme/lua/PotentialCSpatialLagRegression.lua` — no earlier Python port |
| `components/allocation/saturation.py` | Yes, the Lua itself, quirks included (`BACKP` across cells), **raster is new** | `luccme/lua/AllocationCClueLikeSaturation.lua` — no earlier Python port |
| `validation/pontius.py` | New generalization | inspired by `disslucc-discrete/executors/lucc_validation_executor.py` (only had a binarized version) and matches the formula in `disslucc-continuous/executors/lucc_benchmark_executor.py::_metrics` (continuous, also not ported before) |

**Detail that only shows up when comparing `disslucc-continuous`
branches**: on the `decoupling` branch (experimental, not used here),
`AllocationClueLike` read the potential via
`self.potential.get_potential(lu)` -- an indirection through a
Protocol. On `main` -- and here -- it reads
`self.backend.get(lu + "_pot")` directly. More coupled, but it's what's
in production; that's why `PotentialProtocol` here only declares
`.modify()`, not `.get_potential()`.

## Why unify continuous and discrete

Comparing the two real repositories with `diff`:

- `DemandPreComputedValues` is **byte-for-byte identical** between the
  two -- only formatting differs. Duplicated, not intentional.
- `disslucc-discrete` has a validation metric
  (Pontius & Millones, `lucc_validation_executor.py::_discrete_metrics`)
  that `disslucc-continuous` doesn't have. Except that version
  binarizes at 0.5 before comparing -- loses information when the data
  is already a continuous fraction.
- `Potential` and `Allocation` are **genuinely different** between the
  two (logistic regression + cell-by-cell competition vs. linear
  regression + elasticity). That part of the two-repository split is
  justified -- it's not accidental duplication, it's a different
  technique.

Hence: `components/demand/` and `validation/` live in a single shared
place; `components/potential/` and `components/allocation/` stay
organized by strategy (one file per technique), but inside the same
package, distinguished by name (`linear.py`/`clue.py` = continuous,
`logistic.py`/`clue_s.py` = discrete) instead of by repository.

`validation/` sits OUTSIDE `components/` on purpose: there's no
"validation component" in the original repositories (Pontius &
Millones lived inside `executors/lucc_validation_executor.py`, not as
a reusable module) -- and we already identified `validation/pontius.py`
as a `dissmodel` candidate, not a LUCC "component" (see the section
above). Mixing the two inside `components/` would hide that
difference.

**This diverges from what chapter 26 of the *Geospatial Modeling with
Python* book (LambdaGeo, `docs/part5/ch26_lucc.ipynb`) describes
today** -- there, "DisSLUCC" is presented as two separate libraries,
with no mention of the Demand/Validation duplication. The chapter
itself is declared a draft, "written ahead of the DisSLUCC packages
settling... revise once that work stabilizes, not a final reference"
-- this repository (with real validation against TerraME in both
cases) is a natural candidate to feed that revision.

Chapter 26 does have, on the other hand, a cleaner decision criterion
than "look at the code" for choosing between continuous and discrete:
**look at the calibration/validation data type first**. If it's a
per-cell class label, discrete is the only one that can be checked
against it exactly. If it's per-cell area/percentage, continuous is
the only one that represents that without first forcing a lossy
discretization. It's a criterion based on the data, not the
architecture -- worth more than anything I derived just by comparing
the repositories.

## Why folder-per-role, file-per-strategy

`components/demand/`, `components/potential/`, `components/allocation/`
(and `validation/`, outside `components/` -- see above) are packages
(a folder, an `__init__.py` re-exporting), not a single file each --
same convention as the original repositories, with the same folder
name (`components/potential/raster/__init__.py` re-exporting from
`linear.py` there; here without the `raster/` level, which we already
dropped). Reason: the real LuccME has more than one strategy per role
(`PotentialCLinearRegression`, `PotentialCSpatialLagRegression`,
`PotentialCSampleBased`, ...) -- one file per strategy keeps this
extensible without reopening an already-large file every time a new
strategy comes in. Each `__init__.py` gains one line re-exporting the
new class; the rest of the package doesn't need to know the new
strategy exists.

> A `registry.py` (plain name→class dict) did exist here at one point,
> but was removed: nothing in the package did a lookup by name (not
> even `executors/`, which import the class directly in Python code)
> -- it was infrastructure with no real consumer, the same kind of
> problem that brought down the generic `StageRegistry` before it. It
> comes back if/when `executors/` starts resolving a strategy by name
> coming from `record.parameters` (a natural candidate, not
> implemented yet) -- see [`decisions.md`](decisions.md).

## What was considered and dropped

Before this version, there was a prototype with `Pipeline`/`Stage`
(generic Protocol)/`StageRegistry` (a class, `.register()` decorator) +
Pydantic schemas per strategy to auto-generate a UI. It was reverted:
for 3-6 known strategies per role, a plain literal dict solves the
same problem without the dynamic dispatch machinery -- which only pays
off at scale/runtime discovery, a problem that doesn't exist here.
Full history of that reversal, with line-count numbers comparing the
two versions, in [`decisions.md`](decisions.md).

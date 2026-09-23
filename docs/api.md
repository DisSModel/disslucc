# API — disslucc

Reference for all public classes and functions. Every parameter listed
was extracted from the real signature (`inspect.signature`), not from
memory.

```python
import disslucc as d
```

exposes everything below directly (`d.PotentialLinearRegression`, etc.)
-- no need to import from submodules.

---

## Demand

### `DemandPreComputedValues`

Land use demand precomputed per step. It's a `dissmodel.core.Model`
-- registers itself in the active `Environment` when constructed.

```python
DemandPreComputedValues(
    annual_demand: list[list[float]],  # [step][class], step 0 = env.now()==0
    land_use_types: list[str],          # class names, same order as the columns
)
```

Use `load_demand_csv()` to build `annual_demand` from a CSV instead of
writing the list by hand.

Implements `DemandProtocol`:

| Method | Returns |
|---|---|
| `get_current_lu_demand(i)` | demand for class `i` at the current step |
| `get_previous_lu_demand(i)` | demand for class `i` at the previous step |
| `get_current_lu_direction(i)` | `1` growing, `-1` shrinking, `0` stable |
| `change_lu_direction(i)` | flips and returns the direction (used by Allocation when elasticity saturates) |

### `DemandInline`

Same as `DemandPreComputedValues`, but takes the matrix directly as a
Python list (`values`) instead of `annual_demand` coming from a CSV.
**Doesn't exist in the original repository** -- convenience for
scripts, no external file needed.

```python
DemandInline(values: list[list[float]], land_use_types: list[str])
```

### `load_demand_csv(raw: str, land_use_types: list[str]) -> list[list[float]]`

Parses a CSV with one column per class, one row per step. Column order
in the CSV doesn't need to match `land_use_types` -- mapping is by
header name.

```python
from disslucc.components.demand import load_demand_csv
annual_demand = load_demand_csv(Path("demand.csv").read_text(), ["f", "d", "outros"])
```

---

## Potential

### `PotentialLinearRegression` (continuous)

Potential for change via linear regression (Verburg et al. 1999).
Writes `<lu>_pot` to the backend -- that's what `AllocationClueLike`
reads.

```python
PotentialLinearRegression(
    backend,
    potential_data: list[list[RegressionSpec]],  # [region][class]
    demand,                                        # object with DemandProtocol
    land_use_types: list[str],
    land_use_no_data: str | None = None,  # array in [0,1]: scales potential down by (1 - value); NOT a binary exclusion mask
    region_attr: str = "region",           # region array in the backend; created as 1 if absent
)
```

`potential_data` is an outer list per REGION (the same scenario can
have different coefficients per zone) -- for a single-region scenario,
use a list with one element: `[[class1_spec, class2_spec, ...]]`.

Each step, `_adapt_constants()` adjusts the regression constant
proportionally to the change in demand -- it's the implicit "learning"
that keeps the model close to the target without manual recalibration.

### `PotentialDLogisticRegression` (discrete, CLUE-S)

Transition potential via logistic regression (Verburg et al. 2002).
**No raster version exists in the original repository** -- this one
was written following the same pattern as `PotentialLinearRegression`,
it's not a literal translation.

```python
PotentialDLogisticRegression(
    backend,
    potential_data: list[list[LogisticRegressionSpec]],
    land_use_types: list[str],
    region_attr: str = "region",
)
```

Writes two arrays per class: `<lu>_reg` (raw logistic probability) and
`<lu>_pot` (`prob + elasticity`, used by Allocation -- elasticity
reinforces the class a cell already has, "locking" pixels into their
current class).

Doesn't implement `.modify()` -- CLUE-S doesn't use per-potential
feedback, it adjusts a global correction vector in
`AllocationDClueSLike` instead (same behavior as the original).

---

## Allocation

### `AllocationClueLike` (continuous)

CLUE allocation -- elasticity + iterative convergence + proportional
correction between classes + `complementar_lu`. Cell fraction in
`[0,1]`, not categorical.

```python
AllocationClueLike(
    backend,
    demand,                            # DemandProtocol
    potential,                         # PotentialProtocol (only uses .modify())
    land_use_types: list[str],
    static: dict[str, int],            # -1 follows demand | 0 free | 1 fixed, per class
    complementar_lu: str,               # class that absorbs the remainder (sum always = 1)
    cell_area: float,
    max_difference: float = 1643,       # convergence tolerance (scales with total area!)
    max_iteration: int = 1000,
    initial_elasticity: float = 0.1,
    min_elasticity: float = 0.001,
    max_elasticity: float = 1.5,
    allocation_data: list[AllocationSpec] | None = None,  # min/max per class, in land_use_types order
)
```

> `max_difference` has to be calibrated to the scenario's scale -- the
> default (1643) is the value used in the real Lab1 (~900k ha). In a
> synthetic scenario with 900 cells, using the default never triggers
> the iteration; lower it to something like `5.0`.

Reads `backend.get(lu + "_pot")` directly (doesn't call
`potential.get_potential()` -- that indirection only existed on an
experimental branch of the original repository, not on `main`).

### `AllocationDClueSLike` (discrete, CLUE-S)

Cell-by-cell competition allocation with a transition matrix. Each
cell belongs to exactly one class (binary 0/1 array).
**New raster version, no equivalent in the original** (same situation
as `PotentialDLogisticRegression`).

```python
AllocationDClueSLike(
    backend,
    demand,                                       # DemandProtocol
    land_use_types: list[str],
    transition_matrix: list[list[list[int]]],      # [region][from][to], 1=allowed
    cell_area: float = 1.0,
    max_difference: float = 10.0,
    max_iteration: int = 2000,
    factor_iteration: float = 0.0001,               # correction-vector adjustment rate
    region_attr: str = "region",
)
```

Optional `tau_<lu>` arrays in the backend act as per-cell/class
attraction/repulsion; if absent, `tau=0` (default behavior).

---

## Validation

### `pontius_millones(pred, ref) -> dict`

Pontius & Millones (2011) decomposition into quantity + allocation
disagreement. Accepts continuous `[0,1]` fraction OR `0/1` categorical
-- reduces exactly to the classic discrete formula in the binary case
(proof embedded in `validation/pontius.py`, run
`python3 src/disslucc/validation/pontius.py` to see the self-test).

```python
pontius_millones(pred: array-like, ref: array-like) -> {
    "n": int, "mae": float,
    "quantity_disagreement": float, "allocation_disagreement": float,
    "total_disagreement": float,  # == mae
}
```

`pred`/`ref` are the per-cell value of **one class** -- to compare
several classes, call once per class.

### `confusion_metrics(pred, ref, threshold=0.5) -> dict`

Accuracy/precision/recall/F1, binarizes at `threshold` before
comparing. Only makes sense for categorical comparison -- for
genuinely continuous maps, use `pontius_millones()` without binarizing
(binarizing throws away fractional information).

```python
confusion_metrics(pred, ref, threshold=0.5) -> {
    "n": int, "tp": int, "tn": int, "fp": int, "fn": int,
    "accuracy": float,  # in %
    "precision": float, "recall": float, "f1": float,
}
```

---

## Schemas (`disslucc.schemas`)

Plain dataclasses -- type validation, no logic.

```python
@dataclass
class RegressionSpec:
    const: float
    betas: dict[str, float] = {}
    is_log: bool = False          # if True, applies 10**reg before the clip

@dataclass
class LogisticRegressionSpec:
    const: float
    elasticity: float = 0.0
    betas: dict[str, float] = {}

@dataclass
class AllocationSpec:
    static: int = -1              # -1 follows demand | 0 free | 1 fixed
    min_value: float = 0.0
    max_value: float = 1.0
    min_change: float = 0.0
    max_change: float = 1.0
```

---

## Protocols (`disslucc.protocols`)

Contracts between roles -- `@runtime_checkable`, so
`isinstance(obj, DemandProtocol)` actually works at runtime.

```python
class DemandProtocol(Protocol):
    def get_current_lu_demand(self, lu_index: int) -> float: ...
    def get_previous_lu_demand(self, lu_index: int) -> float: ...
    def get_current_lu_direction(self, lu_index: int) -> int: ...
    def change_lu_direction(self, lu_index: int) -> int: ...

class PotentialProtocol(Protocol):
    def modify(self, r_number: int, lu_idx: int, direction: int) -> None: ...
```

---

## Executors (`disslucc.executors`)

Second entry point, with automatic provenance (`ExperimentRecord`) --
coexists with direct construction in a script, doesn't replace it.
Not imported by `import disslucc` (heavier import, pulls in
`geopandas`/rasterization) -- import it explicitly:

```python
from disslucc.executors import LuccContinuousExecutor, LuccDiscreteExecutor
```

### `LuccExecutorBase`

Base shared by `LuccContinuousExecutor`/`LuccDiscreteExecutor`,
extracted after measuring with `diff` that `validate()`/`load()` were
identical between the two and `save()` had the same skeleton -- not
premature abstraction. Provides:

- `validate()` -- checks `record.source.uri` and
  `self.required_parameters` (list of required keys, declared per
  subclass)
- `load()` -- loads the GeoDataFrame via `load_dataset`, applies
  `column_map`, **and already rasterizes** (`vector_to_raster_backend`)
  -- returns the `RasterBackend` ready to use, not the GeoDataFrame.
  Same convention as the real `LUCCRasterExecutor`, checked against the
  source: rasterizing is expensive, it runs once inside `load()`,
  never inside `run()`.
- `save()` -- a default that serves both cases: writes the land-use
  bands (+ `"mask"`, if present) as a GeoTIFF to `record.output_path`
  -- local path or `s3://` (MinIO), via `dissmodel.io.raster.save_geotiff`
  -- then `record.metrics.update(result["metrics"])`, output checksum
  (of the written file), status, final log. `crs`/`transform` come
  straight off the `RasterBackend` (`load()` already sets both via
  `vector_to_raster_backend`). Same mechanism as
  `brmangue-dissmodel`'s `RasterExecutor.save()`.

`run(data, record)` remains abstract -- `data` arrives as the
`RasterBackend` already built (not the GeoDataFrame); subclasses just
run the model on top of it and return
`{"backend", "land_use_types", "metrics", "final_log"}`.

### `LuccContinuousExecutor`

`name = "lucc_continuous"`. Expects in `record.parameters`:

| Key | Type | Required |
|---|---|---|
| `land_use_types` | `list[str]` | yes |
| `demand_csv` | `str` (path) | yes |
| `potential_data` | `list[dict]` (one per class: `const`, `betas`, `is_log`) | yes |
| `static` | `dict[str, int]` | yes |
| `complementar_lu` | `str` | yes |
| `allocation_data` | `list[dict]` (`AllocationSpec` fields) | yes |
| `cell_area`, `n_steps`, `resolution`, `max_difference`, `land_use_no_data` | -- | no (defaults) |

`record.source.uri` points to the input shapefile/GeoDataFrame
(rasterized via `vector_to_raster_backend`, `resolution` parameter).

### `LuccDiscreteExecutor`

`name = "lucc_discrete"`. Same shape, swapping `potential_data` for
`LogisticRegressionSpec` specs (`const`, `elasticity`, `betas`) and
`static`/`complementar_lu`/`allocation_data` for `transition_matrix`
(`list[list[list[int]]]`, `[region][from][to]`).

### Example

```python
from dissmodel.executor import ExperimentRecord
from dissmodel.executor.runner import execute_lifecycle
from disslucc.executors import LuccContinuousExecutor

record = ExperimentRecord(
    model_name=LuccContinuousExecutor.name,
    source={"uri": "my_shapefile.zip"},
    parameters={...},
)
record, timings = execute_lifecycle(LuccContinuousExecutor(), record)
print(record.metrics, record.artifacts, record.source.checksum)
```

See `examples/run_lab1_via_executor.py` and
`examples/run_lab15_via_executor.py` for a full example with real data.

### Registering with `dissmodel-configs` (TOML)

The Executors are also the entry point registered in
[`dissmodel-configs`](https://github.com/DisSModel/dissmodel-configs)
for running on `dissmodel-platform`, and (as of the `dissmodel` fix
below) runnable locally too, via `dissmodel.executor.cli.run_cli`
(`continuous.py`/`discrete.py` each have an `if __name__ == "__main__"`
block):

```bash
python -m disslucc.executors.continuous run \
  --toml examples/dissmodel-configs/lucc_continuous.toml \
  --input data/input/csAC.zip \
  --param demand_csv=data/input/examples_demand_lab1.csv
```

`examples/dissmodel-configs/` has one TOML per executor --
[`lucc_continuous.toml`](https://github.com/DisSModel/disslucc/blob/main/examples/dissmodel-configs/lucc_continuous.toml)
and
[`lucc_discrete.toml`](https://github.com/DisSModel/disslucc/blob/main/examples/dissmodel-configs/lucc_discrete.toml)
-- each encoding the exact same coefficients as its `*_via_executor.py`
sibling above (verified: same final metrics, same output checksum for
the continuous/Lab1 case). Everything under `[model]` besides
`[model.parameters]` (`land_use_types`, `[[model.potential_data]]`,
`[[model.allocation_data]]`, `static`, `transition_matrix`, ...) is
what gets merged into `record.parameters` before `run()` is called --
by the platform when registered in `dissmodel-configs`, and (as of the
fix below) by `dissmodel.executor.cli` for local `--toml` runs too.
Table names match this package's own `required_parameters`
(`potential_data`/`allocation_data`, not the shorter `potential`/
`allocation` used in some other `dissmodel-configs` entries) --
`disslucc`'s executors read those keys as-is, with no renaming layer
of its own.

> **Fixed in `dissmodel` 0.6.4.** The local-`--toml` merge above
> didn't exist in `dissmodel`'s CLI before this was found (only
> `[model.parameters]` was ever read into `record.parameters`,
> matching the docstring's promise but not the code). A fix was
> written and validated (full `dissmodel` test suite + new regression
> tests for the merge, `mypy` clean, and this exact
> `lucc_continuous.toml`/`lucc_discrete.toml` run end-to-end through
> the real CLI with matching output checksums) and shipped in
> `dissmodel` 0.6.4 -- `disslucc` pins `dissmodel>=0.6.4`, so both
> commands above work as written. See `docs/decisions.md`, "TOML
> config example added for the executors path", for the full history.

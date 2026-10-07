# Validation — disslucc vs TerraME

The agreement between disslucc and the original TerraME/LuccME is checked in a
separate repository,
**[LambdaGeo/disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark)**,
which keeps the reference results, the comparison code and the numbers. This
repository holds the package and examples only, so that learning the model
and checking it against TerraME are two separate things.

## Where things are

| What | Where |
|---|---|
| Per-lab results (iterations, MAE, max error, timings), reproducible with `make benchmark` | [disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark) |
| TerraME/LuccME reference results (goldens, all 21 LuccME labs) and the container that generated them | [LambdaGeo/luccme-goldens](https://github.com/LambdaGeo/luccme-goldens), [terrame-docker](https://github.com/profsergiocosta/terrame-docker) |
| What is checked here | `tests/`: demand components, and the TOML executors against hand-built experiments (same output file, same SHA-256) |

disslucc-benchmark pins the disslucc release it was run with; the numbers it
reports belong to that pair of versions.

## Two scenarios worth knowing

The package's two original scenarios are kept in the benchmark under these ids:

- **`lab01_md1643`** (continuous, Amazon deforestation, csAC region, 6,574 cells):
  iteration counts identical to TerraME in every year.
- **`lab15_md10`** (discrete, Moju region, 5,914 cells): iteration counts
  identical to TerraME in every year.

Their numbers are in the benchmark report; they are not copied here, so there
is one place to update when they change.

## One deliberate difference

LuccME's `correctCellChange` never runs: its guard reads `cell.regionregionAloc`,
a field name that no cell has (in `AllocationCClueLike.lua`). disslucc runs the
correction by default (`AllocationClueLike(cell_correction=True)`), the
algorithm as documented. With `cell_correction=False` disslucc follows the
behavior of the reference run. The benchmark reports both, and labels the
difference "by design".

## History

Before 0.5.0 this repository carried its own goldens, a Lua differential test
and a discriminance suite. They moved to (or were superseded by) the benchmark.
The full set is in the `v0.4.0` tag
([browse](https://github.com/DisSModel/disslucc/tree/v0.4.0)), including the
earlier version of this page with the Lab 1 and Lab 15 analysis.

# Changelog

All notable changes to `disslucc` are documented here.

## [0.3.0] -- unreleased

First version meant to be independently citable and reproducible
without `disslucc-continuous` or `disslucc-discrete` cloned alongside
it.

### Added
- `examples/dissmodel-configs/lucc_continuous.toml` and
  `lucc_discrete.toml` -- registration configs for
  `dissmodel-configs`/`dissmodel-platform`, matching the real
  production convention (`[model]` spec merged into
  `record.parameters`, `[model.parameters]` for run-specific
  overrides), corrected for this package's own `required_parameters`
  naming (`potential_data`/`allocation_data`).
- A working local CLI: `python -m disslucc.executors.continuous run
  --toml ... --input ... --output ...` and the `discrete` equivalent,
  via `if __name__ == "__main__": run_cli(...)` in each executor
  module. Requires `dissmodel>=0.6.4` (see Fixed, upstream).
- `--output` now writes a real georeferenced GeoTIFF (local path or
  `s3://`/MinIO), one band per land-use class plus a `mask` band --
  `LuccExecutorBase.save()` previously only hashed the backend's raw
  in-memory bytes and never wrote anything to disk despite accepting
  `--output`/`record.output_path`.
- `LICENSE` (MIT, same text/copyright as the two individual repos).
- `authors`, `readme` and `license` fields in `pyproject.toml`, and a
  `CITATION.cff` for GitHub/Zenodo citation metadata.
- Vendored the Lab1 and Lab15 validation datasets (`csAC.zip`,
  `examples_demand_lab1.csv`, `LUCCME_Lab1_2014.zip`, `cs_moju.zip`,
  `Lab15_2004.zip`, `demand_moju.csv`) so the repo no longer depends on
  `disslucc-continuous`/`disslucc-discrete` being cloned alongside it.
- `tests/` -- a pytest suite ported from both individual repos and
  adapted to the raster-only substrate:
  - `test_validation_lab1.py`, `test_validation_lab15.py` -- turn the
    published validation numbers into real assertions.
  - `test_benchmark_discriminance_lab1.py`,
    `test_benchmark_discriminance_lab15.py` -- does the benchmark
    itself distinguish a correct implementation from a wrong one?
    Includes the Lab15 `xfail`s documenting that a trivial static
    ranking already reproduces TerraME cell-for-cell there.
  - `test_demand.py` -- ported unchanged (substrate-agnostic).
- `src/disslucc/validation/naive_baseline.py` -- the static-ranking
  baseline the Lab15 discriminance test needs.
- `.github/workflows/tests.yml` -- runs the suite on every push and
  pull request.

### Fixed
- `python -m disslucc.executors.continuous ...` raised
  `RuntimeWarning: 'disslucc.executors.continuous' found in
  sys.modules after import of package 'disslucc.executors', but prior
  to execution` -- `disslucc/executors/__init__.py` eagerly imported
  `.continuous`/`.discrete`, colliding with `python -m`'s own
  import-then-execute-as-`__main__` sequence. Fixed with PEP 562 lazy
  `__getattr__` re-exports; `from disslucc.executors import
  LuccContinuousExecutor` still works identically.
- (Upstream) `dissmodel`'s local `--toml` CLI only ever merged
  `[model.parameters]` into `record.parameters`, silently dropping any
  `[model]`-level spec -- the convention this package's own
  `dissmodel-configs` examples (above) depend on. Found while wiring
  up the local CLI; reported as
  [dissmodel#176](https://github.com/DisSModel/dissmodel/issues/176),
  fixed in `dissmodel` 0.6.4.
- `examples/run_lab1_validation.py` and `run_lab15_validation.py` had
  absolute paths from a development session
  (`/home/claude/disslucc-continuous/...`, `/tmp/csAC`, `/tmp/moju`,
  `/tmp/lab15_ref`), so `git clone && pip install -e . && python3
  script.py` did not actually work standalone as the README claimed.
  Both now resolve data relative to the repo and read shapefiles
  directly from the vendored zips.
- README no longer claims Lab1 and Lab15 are both validated "cell by
  cell" -- Lab1 is within the official 0.01 MAE tolerance (MAE
  0.0036), only Lab15 is exact.

## [0.2.0] -- initial commit

Raster-only, script-first port of `disslucc-continuous` (`main`
branch) plus the discrete CLUE-S-like components from
`disslucc-discrete`, as new raster ports. `ModelExecutor` /
`ExperimentRecord` brought back as a second entry point alongside the
plain-script style. No tests, no CI, no LICENSE, no vendored data.

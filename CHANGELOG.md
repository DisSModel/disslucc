# Changelog

All notable changes to `disslucc` are documented here.

## [0.3.0] -- unreleased

First version meant to be independently citable and reproducible
without `disslucc-continuous` or `disslucc-discrete` cloned alongside
it.

### Added
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

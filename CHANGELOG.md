# Changelog

All notable changes to `disslucc` are documented here.

## [0.3.0] -- unreleased

First version meant to be independently citable and reproducible
without `disslucc-continuous` or `disslucc-discrete` cloned alongside
it.

### Added
- `docs/examples/notebooks/continuous_synthetic.ipynb` and
  `discrete_synthetic.ipynb` -- two small, fully synthetic (no
  shapefiles, no vendored data) teaching notebooks, one per allocation
  paradigm, meant to be read top to bottom and run cell by cell --
  same pedagogical shape as `dissmodel` core's own notebooks
  (concept explanation, an instantiation-order callout, a run, a
  quicklook, a "Try it yourself" section). Executed and committed with
  real output (`nbconvert --execute`); wired into `mkdocs.yml` via the
  `mkdocs-jupyter` plugin (added to `requirements-docs.txt`) and linked
  from `docs/index.md`/`docs/quickstart.md`. The discrete notebook's
  scenario (transition matrix, logistic potential coefficients,
  `max_difference`) is new -- no synthetic discrete example existed
  before -- and was validated to converge cleanly before being turned
  into a notebook.
- Published documentation site (`mkdocs.yml`, `docs/index.md`,
  `requirements-docs.txt`, `.github/workflows/docs_deploy.yml`) --
  mirrors `dissmodel` core's setup (Material theme, `mkdocs gh-deploy`
  on push to `main`) and wires the existing hand-written `docs/*.md`
  (quickstart, API reference, architecture, validation, decisions)
  into real navigation at
  [dissmodel.github.io/disslucc](https://dissmodel.github.io/disslucc/).
  Deploy only triggers on changes to `docs/`/`mkdocs.yml`/
  `requirements-docs.txt`, unlike core's unconditional trigger, so an
  unrelated code push doesn't redeploy docs that didn't change.
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
- CI `lint` job: `ruff check .` and `mypy src/disslucc` now run on
  every push/PR (previously only `pytest`, even though `mypy` was
  already a `dev` dependency with its own `[tool.mypy]` config -- it
  was just never wired into CI). `ruff` added as a `dev` dependency,
  pinned `>=0.16,<0.17` and configured in `[tool.ruff]`, same reasoning
  as `dissmodel` core: an unpinned `ruff` silently grows its default
  rule set across versions and would start failing CI with no code
  change on our side.
- `test` and `lint` jobs now run on a Python 3.11/3.12 matrix (was
  3.11-only for `test`, 3.11-only for the new `lint`; `requires-python`
  is `">=3.11"`, so no 3.10). `lint` needed the matrix too, not just
  `test`: running it caught `mypy` failing outright under Python 3.12
  (`pyproject.toml`'s `[tool.mypy]` pinned `python_version = "3.11"`,
  but numpy 2.5 -- what resolves under a 3.12 install, vs 2.4.x under
  3.11 -- ships a stub using PEP 695 `type` statement syntax that only
  parses when mypy targets 3.12+). Bumped `python_version` to `"3.12"`;
  same class of fix as the `zarr`/PEP-695 override already in
  `dissmodel` core's `[tool.mypy]`, different library.
- CI status badge in `README.md`.

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
- README.md, `docs/quickstart.md`, `docs/api.md`: all still said the
  fix above was unreleased and `disslucc` pinned the unfixed
  `dissmodel==0.6.3` exactly -- stale since `pyproject.toml`'s
  dependency was bumped to `dissmodel>=0.6.4`. Re-ran both `--toml`
  commands for real (continuous and discrete) to confirm they work as
  written before rewriting the callouts; `docs/decisions.md` (a dated
  decision log, not a live claim) keeps its original entry with a
  forward-pointing note instead of being rewritten.
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
- Fixed all 53 lint findings surfaced by turning `ruff` on (unsorted
  imports, unused imports in `disslucc/__init__.py`'s public re-exports
  -- now covered by an explicit `__all__`, an unsorted `__all__` in
  `validation/__init__.py`, three mutable class-attribute defaults
  (`required_parameters: list[str] = [...]`) -> `ClassVar`, a
  `dict(...)` call rewritten as a literal, an unused local variable in
  `AllocationDClueSLike.execute()`).
- Fixed 3 `mypy` errors in `validation/naive_baseline.py`
  (`no-any-return`: functions declared to return `np.ndarray` were
  returning values typed `Any`, since neither numpy's stubs nor
  geopandas -- which has none -- narrow them back; wrapped the returns
  in `np.asarray()`, a no-op at runtime).
- Removed run artifacts that had been accidentally committed
  (`outputs/*.tif`/`*.record.json`/`profiling_*.md`,
  root-level `profiling_*.md`, `experiment_record.json`) and added
  them to `.gitignore` so future local runs don't repeat this --
  distinct from `data/` and `benchmark/`, which are real vendored
  fixtures and stay tracked.

## [0.2.0] -- initial commit

Raster-only, script-first port of `disslucc-continuous` (`main`
branch) plus the discrete CLUE-S-like components from
`disslucc-discrete`, as new raster ports. `ModelExecutor` /
`ExperimentRecord` brought back as a second entry point alongside the
plain-script style. No tests, no CI, no LICENSE, no vendored data.

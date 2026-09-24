# TerraME/LuccME goldens

`goldens/` is a copy of goldens generated in
[LambdaGeo/terrame-docker](https://github.com/LambdaGeo/terrame-docker) **v0.1.1**
(`benchmark/goldens/`), with TerraME 2.0.1 + LuccME `6244dd4`. disslucc is validated
against them, one algorithm at a time.

The scripts, the original TerraME outputs and the generator live **only** in
terrame-docker; this repository keeps only the results, so the tests run without Docker.

## Contents of `goldens/<name>/`

| File | Contents |
|---|---|
| `<name>.csv.gz` | state of every cell at the end of every year: `year,id,col,row`, `<class>_out` and `<class>_pot`, 12 decimal places |
| `terrame.log` | TerraME output (demand, allocated area, iterations per year) |
| `manifest.json` | source script and SHA-256, versions, years, columns, iterations per year (`iterations_per_year`) and the cross-check |

`col`/`row` match `data/input/csAC.zip` (`col`, `row`) and `cs_moju.zip` (`col`, `lin`).

## Which ones

Only the goldens this repository's tests use. The others (the 21 labs of the LuccME
package) stay in terrame-docker and come here when the corresponding component is
implemented, together with the test that uses them.

| Golden | Components | Used in |
|---|---|---|
| `lab01` | PreComputedValues + CLinearRegression + CClueLike (`maxDifference` 5000) | `test_goldens_per_year.py` |
| `lab01_md1643` | same, `maxDifference` 1643: iterates up to 26 times per year | `test_goldens_per_year.py`, `test_validation_lab1.py`, discriminance |
| `lab15` | PreComputedValues + DLogisticRegression + DClueSLike (`maxDifference` 300) | `test_goldens_per_year.py` |
| `lab15_md10` | same, `maxDifference` 10: iterates 56–67 times per year | `test_goldens_per_year.py`, `test_validation_lab15.py`, discriminance |

The last year of `lab01_md1643` and of `lab15_md10` is this repository's former reference
(`benchmark/data/*.zip`).

## Before using them as evidence

- In the package labs the allocation is accepted at the first pass every year; only the
  `_md` variants test the convergence loop.
- In the labs with `CClueLike`, TerraME never runs `correctCellChange` (a
  `regionregionAloc` typo). disslucc runs it by default; compare with
  `cell_correction=False`. See `docs/validation.md`.
- Compare with a tolerance (1e-9 in the file; the tests use MAE < 1e-6), never by
  SHA-256: from one generation to the next, a few cells change in the 12th decimal place.

## Adding or updating

Copy the golden's folder from terrame-docker's `benchmark/goldens/<name>/`, at the same
version (`v0.1.1`), to `benchmark/goldens/<name>/` here, in the same commit as the test
that starts using it. Never edit a golden by hand; to regenerate one, run
`benchmark/generate.sh <name>` in terrame-docker.

# Reference LuccME scripts (provenance)

These four `.lua` files are the actual "LuccMe Model Configurator" output
scripts that generated the TerraME reference data vendored under
`benchmark/data/` (`LUCCME_Lab1_2014.zip`, `Lab15_2004.zip`). They are kept
here **unmodified** (content is byte-identical to the originals) so the
provenance of every validation number in this repository can be traced and
re-run independently of this project.

## File naming vs. internal model naming

The filenames here use this project's convention (`Lab1`, `Lab15`), but the
**internal model names inside the scripts are not "Lab15"** for the discrete
case:

| File in this folder | Internal `LuccMEModel.name` | `outputTheme` | Generates |
|---|---|---|---|
| `lab1_main.lua` + `lab1_submodel.lua` | `"Lab1"` | `"Lab1_"` | `Lab1_2014.shp` → `benchmark/data/LUCCME_Lab1_2014.zip` |
| `lab15_main.lua` + `lab15_submodel.lua` | `"Lab6"` | `"Lab6_"` | `Lab6_2004.shp` → `benchmark/data/Lab15_2004.zip` |

`lab15_main.lua`/`lab15_submodel.lua` are the *original* `lab6_main.lua`/
`lab6_submodel.lua` files (generated 2017-05-11, "Compatible with LuccME
3.0"), renamed here to match the `Lab15` label used throughout `disslucc`
(tests, docs, `benchmark/data/Lab15_2004.zip`). Nothing inside the files was
edited — the model still calls itself `Lab6`, uses `outputTheme = "Lab6_"`,
and produced a shapefile originally named `Lab6_2004.*` (renamed to
`Lab15_2004.*` inside the zip only for internal consistency in this repo).

## These are *not* the same scripts as `terrame/luccme` on GitHub

The public [`terrame/luccme`](https://github.com/terrame/luccme) repository's
own automated test suite (`tests/functional/`) contains scripts that share
identical calibrated regression coefficients and demand trajectories with the
ones here, and even similar names — but they are separate scripts, with a
different convergence parameter, and **did not generate the reference data
vendored in this repository**:

| Scenario | Script actually used here | `maxDifference` here | Look-alike on GitHub | `maxDifference` there |
|---|---|---|---|---|
| Lab1 (continuous) | `lab1_submodel.lua` | 1643 | `tests/functional/lab01.lua` | 5000 |
| Lab15 (discrete) | `lab15_submodel.lua` (= `lab6_submodel.lua`) | 10 | `tests/functional/lab15.lua` | 300 |

Everywhere in `disslucc`'s code and tests, the `max_difference` defaults
(1643 for the continuous CLUE-like allocation, 10 for the discrete
CLUE-S-like allocation) match the scripts in **this** folder, not the
GitHub look-alikes. Citing the GitHub scripts as the source of these
reference numbers would be inaccurate.

Source: local project files provided by the repository maintainer,
confirmed against `benchmark/data/*.zip` (matching coefficients, demand,
and — for Lab15 — the reference shapefile's original internal name
`Lab6_2004.*`).

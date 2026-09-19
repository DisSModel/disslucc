# Validation — disslucc vs TerraME

Two real scenarios, two numeric results against the original
TerraME/LuccME reference -- not just "runs without error".

## Lab1 (continuous) — Amazon deforestation, csAC region

Real data: `examples/data/input/csAC.zip` (shapefile, 6,574 cells) +
`examples/data/input/examples_demand_lab1.csv`, both from
`disslucc-continuous`. Real calibrated regression coefficients (not
synthetic). Reference: `benchmark/data/LUCCME_Lab1_2014.zip`
(`disslucc-continuous`).

Method: raster grid built via direct `row`/`col` mapping (each
shapefile polygon already knows its position in the original grid --
not spatial resampling by resolution, which would introduce alignment
error). Same method as
`lucc_benchmark_executor.py::_build_mock_raster`.

```
Pontius & Millones -- disslucc vs TerraME, class 'd' (deforestation):
  n:                        6574
  mae:                      0.003583
  quantity_disagreement:    0.003210
  allocation_disagreement:  0.000373
  total_disagreement:       0.003583
```

**MAE = 0.0036, within the 0.01 tolerance** that
`disslucc-continuous/tests/test_benchmark_validation.py` uses to
consider something "equivalent to TerraME". `quantity_disagreement`
dominates over `allocation_disagreement` by nearly 10x -- the spatial
pattern matches almost perfectly; the small difference is in total
allocated quantity, not position.

Reproduce: `examples/run_lab1_validation.py`.

Provenance: the original LuccME scripts that generated this reference
(`Lab1`, `maxDifference=1643`) are vendored at
`benchmark/reference/lab1_main.lua` + `lab1_submodel.lua`. These are
**not** the same scripts as `terrame/luccme`'s public
`tests/functional/lab01.lua`, which shares this scenario's coefficients
and demand but declares a different `maxDifference` (5000) and did not
generate this data -- see `benchmark/reference/README.md`.

## Lab15 (discrete) — deforestation, Moju region

Real data: `data/cs_moju.zip` (shapefile, 5,914 cells) from
`disslucc-discrete`. Real logistic regression coefficients, real
transition matrix (irreversible deforestation: forest can become
deforested, deforested doesn't go back to forest). Reference:
`benchmark/data/Lab15_2004.zip` (`disslucc-discrete`).

```
Pontius & Millones -- disslucc vs TerraME, class 'd':
  n:                        5914
  mae:                      0.0
  quantity_disagreement:    0.0
  allocation_disagreement:  0.0
  total_disagreement:       0.0

Accuracy: 100.0000%   F1: 1.0000   (TP=442 TN=5472 FP=0 FN=0)
```

**MAE = 0, 100% cell-by-cell agreement** -- matches exactly the result
documented in `disslucc-discrete` itself
(`benchmark/validate_lab15.py`: "100% cell-by-cell agreement with
TerraME d_out").

Reproduce: `examples/run_lab15_validation.py`.

Provenance: despite the "Lab15" label used throughout this project
(inherited from `disslucc-discrete`), the script that actually
generated this reference is named `Lab6` internally
(`outputTheme = "Lab6_"`, `maxDifference=10`), vendored unmodified at
`benchmark/reference/lab15_main.lua` + `lab15_submodel.lua` (renamed
from the originals' `lab6_main.lua`/`lab6_submodel.lua` to match this
project's "Lab15" naming). This is **not** the same script as
`terrame/luccme`'s public `tests/functional/lab15.lua`, which shares
this scenario's coefficients and demand but declares a different
`maxDifference` (300) and did not generate this data -- see
`benchmark/reference/README.md` for the full trace.

### Discriminance warning (inherited, not my own achievement)

The original `disslucc-discrete` already documents this caveat in
`benchmark/validate_lab15.py`, and it applies equally here: the Lab15
scenario is **nearly non-discriminative** -- a trivial static ranking
by `(prob_d - prob_f)`, with no CLUE-S, no iteration at all, no time
steps, already reproduces the same cell-by-cell output.

This means the result above confirms that **the logistic regression
coefficients were transcribed correctly** (the deterministic part,
easy to verify) -- **it is not proof that the allocation algorithm**
(CLUE-S with iteration/convergence via `factor_iteration`) **is
faithful** in scenarios where competition between classes really
matters. Proving that would require comparing the iteration count per
step against the TerraME log (`disslucc-discrete` documents 61-67
iterations per step) -- not done here.

## Summary

| Scenario | Type | MAE | Match | What it proves |
|---|---|---|---|---|
| Lab1 | continuous | 0.0036 | -- | full model (Demand+Potential+Allocation), within the official tolerance |
| Lab15 | discrete | 0.0 | 100% | correct regression coefficients; **does not** confirm CLUE-S convergence under real competition |

## What these numbers DON'T prove: engineering validation ≠ scientific validation

A distinction from chapter 26 of the *Geospatial Modeling with Python*
book (LambdaGeo), worth naming explicitly here: the two results above
are **engineering validation** -- they confirm this Python port matches
a TerraME reference run. That's a different question from **scientific
validation**: fitting the model to real observed data, splitting a
calibration period (used to fit parameters) from a held-out validation
period, checked only after fitting.

Neither scenario here does that calibration/validation split -- Lab1
and Lab15 run with already-calibrated coefficients (inherited from the
original repositories), comparing output against output, not against
an independent observation.

Also worth noting: cell-by-cell comparison is sometimes too strict a
standard even for scientific validation -- two reasonable runs of the
same model can disagree pixel by pixel and still be "equally good" at
the spatial-pattern level. The standard alternative is **multi-scale**
comparison (Costanza 1989) -- checking agreement over successively
larger windows (3×3, 5×5, 9×9, ...): two maps can disagree at the
finest resolution and agree well at a coarser one, real information a
strict pixel-by-pixel match would throw away. This metric is already
listed as implemented in the new LuccME specification spreadsheet
(`Multi-window (Costanza 86)`) but doesn't exist in this package yet.

## References

- Verburg, P. H. et al. (2002). "Modeling the spatial dynamics of
  regional land use: the CLUE-S model." *Environmental Management*,
  30(3), 391-405
- Verburg, P. H. et al. (2006). "Downscaling of land use change
  scenarios to assess the dynamics of European landscapes."
  *Agriculture, Ecosystems & Environment*, 114(1), 39-56
- Costanza, R. (1989). "Model goodness of fit: a multiple resolution
  procedure." *Ecological Modelling*, 47(3-4), 199-215 -- the
  multi-scale comparison method cited above
- Pontius Jr., R. G. & Millones, M. (2011). "Death to Kappa: birth of
  quantity disagreement and allocation disagreement for accuracy
  assessment." *International Journal of Remote Sensing*, 32(15),
  4407-4429 -- the decomposition used in `validation/pontius.py`

"""
disslucc.validation.naive_baseline
------------------------------------
Faithful port of disslucc-discrete/benchmark/naive_baseline.py.

Why this module exists
-----------------------
Reproducing a TerraME output is a **necessary** condition, not a
sufficient one, for claiming that an allocation algorithm (e.g.
CLUE-S) was faithfully translated. If a trivial procedure -- one that
does not implement the algorithm in question -- reaches the same
parity, the benchmark is not measuring the algorithm, but something
far simpler.

This module implements that trivial procedure: pure static ranking by
logistic-regression margin, with no iteration, no time steps and no
DisSModel component of any kind. See
``tests/test_benchmark_discriminance_lab15.py`` for the test that
exercises it against the full CLUE-S-like raster run.

Unlike the original, this version takes ``potential_data`` explicitly
-- no implicit fallback import from a scenario module, since disslucc
keeps scenario constants in tests/examples rather than in the package.
"""
from __future__ import annotations

import numpy as np


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # np.exp(-z) on an ndarray is typed Any (no stub narrows it back to
    # ndarray through the division), so mypy sees this as returning Any
    # against a declared ndarray return type; np.asarray is a no-op here
    # at runtime and just restores the static type.
    return np.asarray(1.0 / (1.0 + np.exp(-z)))


def logistic_probability(gdf, spec) -> np.ndarray:
    """Logistic probability of a ``LogisticRegressionSpec``, ignoring elasticity."""
    z = np.full(len(gdf), float(spec.const))
    for column, beta in (spec.betas or {}).items():
        z += float(beta) * gdf[column].values.astype(float)
    return _sigmoid(z)


def naive_allocation(gdf, n_target: int, potential_data) -> np.ndarray:
    """Allocate deforestation by pure static ranking.

    Parameters
    ----------
    gdf
        Input GeoDataFrame, with columns ``f``, ``d``, ``o`` and the covariates
        used by the regressions.
    n_target
        Total number of ``d`` cells wanted in the final state.
    potential_data
        The scenario's ``[[LogisticRegressionSpec, LogisticRegressionSpec, ...]]``
        structure -- index 0 is ``f``, index 1 is ``d``.

    Returns
    -------
    np.ndarray
        Binary deforestation vector for the final state, aligned to the rows
        of ``gdf``.
    """
    specs = potential_data[0]
    prob_f = logistic_probability(gdf, specs[0])
    prob_d = logistic_probability(gdf, specs[1])
    margin = prob_d - prob_f  # STATIC quantity -- does not change over time

    d0 = (gdf["d"].values >= 0.5).astype(int)
    o0 = (gdf["o"].values >= 0.5).astype(int)
    eligible = (d0 == 0) & (o0 == 0)

    n_new = int(n_target) - int(d0.sum())
    if n_new <= 0:
        # d0 comes from gdf["d"].values (geopandas has no type stubs, so
        # this is typed Any) -- np.asarray restores the ndarray type mypy
        # expects from the declared return type, with no runtime effect.
        return np.asarray(d0)

    order = np.argsort(-margin)
    order = order[eligible[order]]
    selected = order[:n_new]

    result = d0.copy()
    result[selected] = 1
    return np.asarray(result)

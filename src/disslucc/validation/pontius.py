"""
disslucc.validation.pontius
------------------------------
Pontius & Millones (2011) decomposition into quantity and allocation
disagreement -- generalized to CONTINUOUS maps (per-cell fraction in
[0,1], not just categorical 0/1).

Why this exists here, shared, and not in disslucc-continuous or
disslucc-discrete: the metric in disslucc-discrete
(executors/lucc_validation_executor.py::_discrete_metrics) only accepts
0/1 -- it binarizes before comparing (`(pred >= 0.5).astype(int)`).
That throws away real information when the data is already a fraction
(0.3 vs 0.7 becomes "both are 1"). The version below operates directly
on floats and REDUCES exactly to the discrete formula when the arrays
only contain 0 and 1 -- see the test at the end of the file.

Derivation
----------
For each cell i, let d_i = pred_i - ref_i (signed difference).

    mae        = mean(|d_i|)                    -- total error
    quantity   = |mean(d_i)|  =  |sum(d_i)| / n   -- part explained by
                                                    the overall wrong
                                                    quantity
    allocation = mae - quantity                   -- the rest: cell
                                                    right on quantity,
                                                    wrong on location

quantity + allocation = mae always (an identity, not an approximation),
because sum(|d_i|) >= |sum(d_i)| always holds.

Binary case (pred_i, ref_i in {0,1}): sum(d_i) = FP - FN,
sum(|d_i|) = FP + FN. Substituting:

    quantity   = |FP - FN| / n
    allocation = (FP + FN - |FP - FN|) / n = 2*min(FP, FN) / n

-- exactly the classic Pontius & Millones (2011) formulas used in
disslucc-discrete.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def pontius_millones(pred: Any, ref: Any) -> dict:
    """
    Pontius & Millones decomposition -- works on float ndarray/Series
    (0..1 fraction) or int (0/1 categorical); the result is identical
    to the classic formula in the binary case.

    Parameters
    ----------
    pred, ref : array-like, same shape
        Per-cell value of ONE class (e.g. predicted "urban" fraction vs
        reference fraction). To compare several classes, call once per
        class.

    Returns
    -------
    dict with n, mae, quantity_disagreement, allocation_disagreement,
    total_disagreement (== mae, kept under the name disslucc-discrete
    already uses).
    """
    pred = np.asarray(pred, dtype=np.float64).ravel()
    ref = np.asarray(ref, dtype=np.float64).ravel()
    if pred.shape != ref.shape:
        raise ValueError(f"pred and ref must have the same shape: {pred.shape} != {ref.shape}")

    diff = pred - ref
    n = diff.size
    mae = float(np.abs(diff).mean())
    quantity = float(abs(diff.sum()) / n)
    allocation = mae - quantity

    return {
        "n": n,
        "mae": mae,
        "quantity_disagreement": quantity,
        "allocation_disagreement": allocation,
        "total_disagreement": mae,
    }


def confusion_metrics(pred: Any, ref: Any, threshold: float = 0.5) -> dict:
    """
    Accuracy/precision/recall/F1 -- binarizes at `threshold` first.
    Only makes sense for categorical comparison (same use as
    disslucc-discrete); for genuinely continuous maps, use
    pontius_millones() without binarizing -- this function throws away
    fractional information.
    """
    pred_b = (np.asarray(pred, dtype=np.float64).ravel() >= threshold).astype(int)
    ref_b = (np.asarray(ref, dtype=np.float64).ravel() >= threshold).astype(int)
    n = len(pred_b)

    tp = int(((pred_b == 1) & (ref_b == 1)).sum())
    tn = int(((pred_b == 0) & (ref_b == 0)).sum())
    fp = int(((pred_b == 1) & (ref_b == 0)).sum())
    fn = int(((pred_b == 0) & (ref_b == 1)).sum())

    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else float("nan")

    return {
        "n": n, "tp": tp, "tn": tn, "fp": fp, "fn": fn, "accuracy": accuracy * 100,
        "precision": precision, "recall": recall, "f1": f1,
    }


if __name__ == "__main__":
    # self-test: the continuous version has to match the classic
    # discrete formula when the data is pure 0/1.
    rng = np.random.default_rng(0)
    pred = rng.integers(0, 2, size=1000).astype(float)
    ref = rng.integers(0, 2, size=1000).astype(float)

    fp = int(((pred == 1) & (ref == 0)).sum())
    fn = int(((pred == 0) & (ref == 1)).sum())
    n = len(pred)
    expected_quantity = abs(fp - fn) / n
    expected_allocation = 2 * min(fp, fn) / n

    m = pontius_millones(pred, ref)
    assert abs(m["quantity_disagreement"] - expected_quantity) < 1e-12
    assert abs(m["allocation_disagreement"] - expected_allocation) < 1e-12
    print("OK -- pontius_millones() reduces exactly to the classic discrete formula")
    print(m)

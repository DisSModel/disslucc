"""
disslucc -- raster-only, "script-first" port of disslucc-continuous
(main branch). See README for what was simplified and what wasn't
(the CLUE algorithm itself is faithful to the original).
"""
from .components.allocation import AllocationClueLike, AllocationDClueSLike
from .components.demand import DemandInline, DemandPreComputedValues, load_demand_csv
from .components.potential import (
    PotentialDLogisticRegression,
    PotentialLinearRegression,
)
from .protocols import DemandProtocol, PotentialProtocol
from .schemas import AllocationSpec, LogisticRegressionSpec, RegressionSpec
from .validation import confusion_metrics, pontius_millones

# Explicit public API: these are re-exports (nothing here is used within
# this module itself), so without __all__ ruff's default rule set flags
# every one of them as an unused import.
__all__ = [
    "AllocationClueLike",
    "AllocationDClueSLike",
    "AllocationSpec",
    "DemandInline",
    "DemandPreComputedValues",
    "DemandProtocol",
    "LogisticRegressionSpec",
    "PotentialDLogisticRegression",
    "PotentialLinearRegression",
    "PotentialProtocol",
    "RegressionSpec",
    "confusion_metrics",
    "load_demand_csv",
    "pontius_millones",
]

"""
disslucc -- raster-only, "script-first" port of disslucc-continuous
(main branch). See README for what was simplified and what wasn't
(the CLUE algorithm itself is faithful to the original).
"""
from .protocols import DemandProtocol, PotentialProtocol
from .schemas import RegressionSpec, AllocationSpec, LogisticRegressionSpec
from .components.demand import DemandPreComputedValues, DemandInline, load_demand_csv
from .components.potential import PotentialLinearRegression, PotentialDLogisticRegression
from .components.allocation import AllocationClueLike, AllocationDClueSLike
from .validation import pontius_millones, confusion_metrics

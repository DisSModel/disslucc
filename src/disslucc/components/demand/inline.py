"""
disslucc.demand.inline
------------------------
My own convenience addition, does NOT exist on the main branch (only on
decoupling, where the idea was ported from): takes the demand matrix
directly as a Python list instead of a CSV -- useful for scripts and
examples that don't need an external file.
"""
from __future__ import annotations

from .precomputed import DemandPreComputedValues


class DemandInline(DemandPreComputedValues):
    """
    Same as DemandPreComputedValues, but takes the demand matrix
    directly as a Python list (`values`) instead of a CSV -- useful for
    small scripts and examples that don't need an external file.
    """

    def setup(self, values: list[list[float]], land_use_types: list[str]) -> None:
        super().setup(annual_demand=values, land_use_types=land_use_types)

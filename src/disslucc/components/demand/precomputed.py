"""
disslucc.demand.precomputed
-----------------------------
Faithful port of disslucc_continuous.components.demand.precomputed,
main branch. Substrate-neutral -- no gdf/backend dependency -- which is
why there's no separate "raster" version: the same class works for
any substrate.
"""
from __future__ import annotations
import csv
import io

from dissmodel.core import Model


def load_demand_csv(raw: str, land_use_types: list[str]) -> list[list[float]]:
    """
    Parses a demand CSV shaped [step][land_use].

    Expected format -- one column per land use class, one row per
    step:

        forest,agriculture,urban
        899,0,1
        883,13,4
        ...

    Column order in the CSV doesn't need to match land_use_types;
    mapping is done by header name.
    """
    reader = csv.DictReader(io.StringIO(raw))
    fieldnames = reader.fieldnames
    if fieldnames is None:
        raise ValueError("Demand CSV is empty or has no header")
    missing = [lu for lu in land_use_types if lu not in fieldnames]
    if missing:
        raise ValueError(
            f"Missing columns in demand CSV: {missing}\n"
            f"Available columns: {list(fieldnames)}"
        )
    return [[float(row[lu]) for lu in land_use_types] for row in reader]


class DemandPreComputedValues(Model):
    """
    Land use demand precomputed per step.

    Parameters (setup)
    -------------------
    annual_demand : list[list[float]]
        [step][land_use] -- index 0 is the initial step (env.now() == 0).
        Use load_demand_csv() to build this from a CSV.
    land_use_types : list[str]
        Class names, in the same order as annual_demand's columns.
    """

    INCREASING, DECREASING, STATIC = 1, -1, 0

    def setup(self, annual_demand: list[list[float]], land_use_types: list[str]) -> None:
        self.annual_demand    = annual_demand
        self.land_use_types   = land_use_types
        self.num_lu           = len(land_use_types)
        self.current_demand   = annual_demand[0]
        self.previous_demand  = annual_demand[0]
        self.demand_direction = [self.STATIC] * self.num_lu

    def execute(self) -> None:
        step = int(self.env.now())
        self.current_demand  = self.annual_demand[step]
        self.previous_demand = self.annual_demand[step - 1] if step > 0 else self.annual_demand[0]
        for i in range(self.num_lu):
            prev, curr = self.previous_demand[i], self.current_demand[i]
            if step == 0 or prev == curr:
                self.demand_direction[i] = self.STATIC
            elif prev < curr:
                self.demand_direction[i] = self.INCREASING
            else:
                self.demand_direction[i] = self.DECREASING

    # ── DemandProtocol ────────────────────────────────────────────────────────

    def get_current_lu_demand(self, i: int) -> float:
        return self.current_demand[i]

    def get_previous_lu_demand(self, i: int) -> float:
        return self.previous_demand[i]

    def get_current_lu_direction(self, i: int) -> int:
        return self.demand_direction[i]

    def change_lu_direction(self, i: int) -> int:
        self.demand_direction[i] *= -1
        return self.demand_direction[i]

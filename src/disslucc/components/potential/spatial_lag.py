"""
disslucc.components.potential.spatial_lag
-----------------------------------------
Port of LuccME's ``PotentialCSpatialLagRegression`` (TerraME, LuccME 3.1,
commit 6244dd4 — ``luccme/lua/PotentialCSpatialLagRegression.lua``), raster
only. Used by LuccME-BR (Bezerra et al. 2022) for every class.

For each class, in every cell of a region::

    Y      = mean of the class share over the cell and its Moore neighbours,
             each share divided by (1 - no-data share); neighbours that are
             all no-data left out
    reg    = newconst + Σ beta·x + ro·Y            (log10 space if is_log)
    limit  = const    + Σ beta·x + ro·Y
    reg    = 1 if limit > max_reg, 0 if limit < min_reg
    reg    = reg · (1 - no-data share)
    pot    = reg - past share

Quirks of the original, kept on purpose:
- the clip tests ``limit`` (built with ``const``) but writes 1 or 0, not
  ``max_reg`` / ``min_reg`` — exercised by the goldens;
- ``adapt_constants`` writes the adapted constant back into ``const``, so the
  adaptation accumulates year after year — the goldens reject the other reading;
- a cell with no neighbour at all gets Y = 0, not its own share — no cell of
  csAC is isolated; checked against the Lua itself instead.

Validated against the LuccME goldens of lab03 and lab06 (2008–2014, every
cell, |Δ| < 1e-10: tests/test_spatial_lag_golden.py) and against the original
Lua function run with lupa, log-transformed classes, isolated and all-no-data
cells included (tests/test_lua_differential.py).
"""

from __future__ import annotations

import math

import numpy as np
from dissmodel.geo import SyncRasterModel

from ...protocols import DemandProtocol
from ...schemas import SpatialLagRegressionSpec

MOORE = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
LOG_OFFSET = 0.0001  # LuccME's "ANAP" offset for log-transformed classes
CONST_CHANGE = 0.1  # LuccME's constChange: the allocation's step on newconst


def _shifted(a: np.ndarray, dr: int, dc: int, fill) -> np.ndarray:
    """a[r + dr, c + dc] at (r, c); ``fill`` outside the grid."""
    out = np.full_like(a, fill)
    rows, cols = a.shape
    r0, r1 = max(0, -dr), min(rows, rows - dr)
    c0, c1 = max(0, -dc), min(cols, cols - dc)
    out[r0:r1, c0:c1] = a[r0 + dr : r1 + dr, c0 + dc : c1 + dc]
    return out


def spatial_lag_regression(
    spec: SpatialLagRegressionSpec,
    past: np.ndarray,
    drivers: dict[str, np.ndarray],
    valid: np.ndarray,
    no_data: np.ndarray | None = None,
    newconst: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """``(reg, pot)`` of one class, on every cell (callers apply the region mask).

    ``past``: share of the class at the start of the step; ``valid``: cells
    that exist (LuccME cells); ``no_data``: share of the no-data class, or
    None; ``newconst``: defaults to ``spec.const``.
    """
    past = np.asarray(past, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool)
    nd = np.zeros_like(past) if no_data is None else np.asarray(no_data, dtype=np.float64)
    newconst = spec.const if newconst is None else newconst

    with np.errstate(divide="ignore", invalid="ignore"):
        scaled = np.where(nd != 1, past / (1 - nd), past)
    eligible = valid & (nd < 1)

    neigh_sum = np.zeros_like(past)
    count = np.zeros(past.shape, dtype=np.int64)
    exists = np.zeros(past.shape, dtype=np.int64)
    for dr, dc in MOORE:
        e = _shifted(eligible, dr, dc, False)
        neigh_sum += np.where(e, _shifted(scaled, dr, dc, 0.0), 0.0)
        count += e
        exists += _shifted(valid, dr, dc, False)

    y = np.where(count > 0, (scaled + neigh_sum) / (count + 1), np.where(exists > 0, scaled, 0.0))
    if spec.is_log:
        y = np.log10(y + LOG_OFFSET)
    y = y * spec.ro

    x = np.zeros_like(past)
    for name, beta in spec.betas.items():
        x = x + beta * np.asarray(drivers[name], dtype=np.float64)

    reg = newconst + x + y
    limit = spec.const + x + y
    if spec.is_log:
        reg = 10.0**reg - LOG_OFFSET
        limit = 10.0**limit - LOG_OFFSET
    reg = np.where(limit > spec.max_reg, 1.0, reg)
    reg = np.where(limit < spec.min_reg, 0.0, reg)
    reg = reg * (1 - nd)
    return reg, reg - past


class PotentialSpatialLagRegression(SyncRasterModel):
    """Potential by spatial-lag regression — interface of ``PotentialLinearRegression``.

    Arrays in the backend: the land uses, their ``<lu>_past`` (kept by
    ``SyncRasterModel``), the drivers named in the betas, ``region_attr``
    (default: all cells in region 1) and ``mask`` (cells that exist).
    Writes ``<lu>_pot`` and ``<lu>_reg``.
    """

    def setup(
        self,
        backend,
        potential_data: list[list[SpatialLagRegressionSpec]],
        demand: DemandProtocol,
        land_use_types: list[str],
        land_use_no_data: str | None = None,
        region_attr: str = "region",
        mask_attr: str = "mask",
    ) -> None:
        super().setup(backend)
        self.potential_data = potential_data
        self.demand = demand
        self.land_use_types = land_use_types
        self.land_use_no_data = land_use_no_data
        self.region_attr = region_attr
        self.mask_attr = mask_attr

        if region_attr not in self.backend.arrays:
            self.backend.set(region_attr, np.ones(self.shape, dtype=np.int32))
        if mask_attr not in self.backend.arrays:
            self.backend.set(mask_attr, np.ones(self.shape, dtype=np.float32))
        for region in self.potential_data:
            for spec in region:
                spec.newconst = spec.const
        for lu in self.land_use_types:
            self.backend.set(lu + "_pot", np.zeros(self.shape, dtype=np.float64))
            self.backend.set(lu + "_reg", np.zeros(self.shape, dtype=np.float64))

    def execute(self) -> None:
        step = int(self.env.now())
        for r_idx, region in enumerate(self.potential_data):
            for spec in region:
                spec.newconst = spec.const
            if step > 0:
                self.adapt_constants(r_idx + 1)
            for lu_idx in range(len(self.land_use_types)):
                self.compute_potential(r_idx + 1, lu_idx)

    def adapt_constants(self, r_number: int) -> None:
        """LuccME ``adaptRegressionConstants``: const += 0.01 · relative change of demand."""
        for lu_idx, spec in enumerate(self.potential_data[r_number - 1]):
            curr = self.demand.get_current_lu_demand(lu_idx)
            prev = self.demand.get_previous_lu_demand(lu_idx)
            plus = 0.01 * ((curr - prev) / prev)
            spec.newconst = spec.const
            if spec.is_log:
                unlog = 10**spec.newconst + plus
                if unlog != 0:
                    spec.newconst = math.log10(unlog)
            else:
                spec.newconst = spec.newconst + plus
            spec.const = spec.newconst

    def compute_potential(self, r_number: int, lu_idx: int) -> None:
        lu = self.land_use_types[lu_idx]
        spec = self.potential_data[r_number - 1][lu_idx]
        in_region = self.backend.get(self.region_attr) == r_number
        drivers = {name: self.backend.get(name) for name in spec.betas}
        no_data = self.backend.get(self.land_use_no_data) if self.land_use_no_data else None
        reg, pot = spatial_lag_regression(
            spec,
            self.backend.get(lu + "_past"),
            drivers,
            self.backend.get(self.mask_attr) > 0,
            no_data,
            spec.newconst,
        )
        self.backend.arrays[lu + "_reg"] = np.where(in_region, reg, self.backend.get(lu + "_reg"))
        self.backend.arrays[lu + "_pot"] = np.where(in_region, pot, self.backend.get(lu + "_pot"))

    def modify_driver(self, attr_protection: str, rate: float) -> None:
        """LuccME ``modifyDriver``: scale the protection driver's beta in every regression.

        Called by the saturation allocation when it has not converged after half
        its iterations. As in the Lua, only the first class is recomputed: the loop
        meant to find the complementary class shadows its own variable and always
        stops at index 1. Not exercised by the lab03/lab06 goldens.
        """
        for r_idx, region in enumerate(self.potential_data):
            for spec in region:
                if attr_protection in spec.betas:
                    spec.betas[attr_protection] *= rate
            self.compute_potential(r_idx + 1, 0)

    def modify(self, r_number: int, lu_idx: int, direction: int) -> None:
        """LuccME ``modify``: the allocation moves newconst by ±constChange and recomputes."""
        spec = self.potential_data[r_number - 1][lu_idx]
        if spec.is_log:
            unlog = 10**spec.newconst + CONST_CHANGE * direction
            if unlog != 0:
                spec.newconst = math.log10(unlog)
        else:
            spec.newconst = spec.newconst + CONST_CHANGE * direction
        self.compute_potential(r_number, lu_idx)

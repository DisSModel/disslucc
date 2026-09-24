"""
disslucc.components.allocation.saturation
-----------------------------------------
Port of LuccME's ``AllocationCClueLikeSaturation`` (TerraME, LuccME 3.1, commit
6244dd4 — ``luccme/lua/AllocationCClueLikeSaturation.lua``), raster only. Used
by LuccME-BR (Bezerra et al. 2022).

CLUE-like continuous allocation (Verburg et al. 1999): each year, the change of a
class in a cell is ``potential × elasticity``, bounded per class and region; the
elasticity of each class is adapted until the allocated areas meet the demand.
What the Saturation variant adds to ``AllocationCClueLike``:

- a **saturation indicator** per cell, recomputed at the start of every year: the
  share of the "available" area (not no-data, not protected) that is no longer in
  the complementary class, averaged over the cell's 3 × 3 window. Where it
  exceeds ``change_limiar_value``, the change in the demand's direction is halved
  or capped at ``max_change_above_limiar``;
- ``correctCellChange`` **runs** (in ``AllocationCClueLike`` a typo in its region
  test — ``cell.regionregionAloc`` — skips it, which is why
  ``AllocationClueLike`` implements its own version, behind ``cell_correction``;
  this one is the Lua's own ``correctCellChange``);
- small differences in the bounds (no cap at 1, ``< min_value`` instead of
  ``<=``), a guard for a zero potential, areas counted over positive values only,
  and ``potential.modify_driver`` when half the iterations have gone by.

Faithful to the Lua, including what looks accidental:

- ``BACKP`` in ``correctCellChange`` is declared outside the loop over cells: a
  cell that lowers it lowers it for the cells visited after it, within the same
  call. The result depends on the order of the cells — ``order_attr`` gives it
  (TerraME visits the cells in the order of the layer);
- the neighbourhood LuccME names "11x11" is created with ``strategy = "mxn"`` and
  no ``m``/``n``: TerraME's default, 3 × 3 including the cell itself;
- ``compareAllocationToDemand`` adapts the elasticities once per potential region,
  and reads ``static`` from region 1.

Validation:
- tests/test_saturation_golden.py — the whole model (this allocation + the
  spatial-lag potential) run from 2008 against the TerraME goldens of lab03 and
  lab06: every cell's land use and potential, every year to 2014, within 1e-9,
  plus TerraME's logged iterations and maximum error per year. Those labs never
  need ``correctCellChange`` and never reach the saturation branch;
- tests/test_lua_differential.py — ``correct_cell_change``, ``compute_change``
  (saturation branch included) and ``saturation_indicator`` against the
  original Lua functions, run with lupa on synthetic cases that reach every
  branch, the running ``BACKP`` included (within 1e-12).
Not tested: ``potential.modify_driver`` (called only after 500 iterations).
"""

from __future__ import annotations

from typing import cast

import numpy as np
from dissmodel.geo import SyncRasterModel

from ...protocols import DemandProtocol, RegionalPotentialProtocol
from ...schemas import SaturationAllocationSpec

TOL_COVER = 0.005  # LuccME: a cell whose classes sum to 1 ± 0.005 is left alone
MAX_CORRECTIONS = 25  # LuccME: iterations of the per-cell correction
BACKP_START = 0.5


def compute_change(
    past: np.ndarray,
    pot: np.ndarray,
    elasticity: float,
    spec: SaturationAllocationSpec,
    direction: int,
    saturation: np.ndarray,
) -> np.ndarray:
    """New share of one class (LuccME ``computeChange``), elementwise."""
    change = pot * elasticity
    small = np.abs(change) < spec.min_change
    pot = np.where(small, 0.0, pot)
    change = np.where(small, 0.0, change)
    big = (np.abs(change) >= spec.max_change) & (pot != 0)
    change = np.where(big, spec.max_change * np.sign(pot), change)

    saturated = saturation > spec.change_limiar_value
    if spec.static < 1:
        cap = spec.max_change_above_limiar
        up = saturated & (pot >= 0) & (direction == 1) & (change >= cap)
        change = np.where(up, np.where(change / 2 < cap, change / 2, cap), change)
        down = saturated & (pot <= 0) & (direction == -1) & (np.abs(change) >= cap)
        change = np.where(down, np.where(np.abs(change / 2) < cap, change / 2, -cap), change)

    if spec.static == 1:
        new = past.copy()
    elif spec.static == 0:
        new = past + change
    else:
        follows = ((pot >= 0) & (direction == 1)) | ((pot <= 0) & (direction == -1))
        new = np.where(follows, past + change, past)

    new = np.where(new < 0, 0.0, new)
    new = np.where(new < spec.min_value, np.where(past >= spec.min_value, spec.min_value, past), new)
    new = np.where(new > spec.max_value, np.where(past <= spec.max_value, spec.max_value, past), new)
    return new


def correct_cell_change(
    values: np.ndarray,
    past: np.ndarray,
    specs: list[SaturationAllocationSpec],
    directions: list[int],
    stats: dict | None = None,
) -> np.ndarray:
    """LuccME ``correctCellChange``: bring each cell's classes back to a total of 1.

    ``values``, ``past``: (cells, classes), the cells **in visiting order** — the
    running ``BACKP`` depends on it. Returns the corrected values. ``stats``, if
    given, receives how many cells took each branch (for tests).
    """
    v = values.astype(np.float64).copy()
    p = past.astype(np.float64)
    static = np.array([s.static for s in specs])
    vmin = np.array([s.min_value for s in specs])
    vmax = np.array([s.max_value for s in specs])
    direction = np.array(directions)

    need = np.abs(v.sum(axis=1) - 1) > TOL_COVER
    dif = v - p
    totchange = np.abs(dif).sum(axis=1)
    biggest = np.abs(dif).max(axis=1)
    amin, amax = dif.min(axis=1), dif.max(axis=1)

    # BACKP carries over from cell to cell: a running minimum in visiting order
    with np.errstate(divide="ignore", invalid="ignore"):
        candidate = np.where(need & (totchange > 0), biggest / (2 * totchange), np.inf)
    backp = np.minimum(BACKP_START, np.minimum.accumulate(candidate))

    def free(x: np.ndarray) -> np.ndarray:
        return (static < 1) & ~((x <= vmin) | (x >= vmax))

    # all free classes moving the same way: shift them back
    f = free(v)
    step = (backp * totchange)[:, None]
    incr = (f & (dif > -step)).sum(axis=1)
    decr = (f & (dif < step)).sum(axis=1)
    n_free = f.sum(axis=1)
    all_incr = need & (incr == n_free)
    all_decr = need & (decr == n_free)
    shift = all_incr | all_decr
    if shift.any():
        s = v.copy()
        s = np.where(f & all_incr[:, None], s - (amin + backp * totchange)[:, None], s)
        s = np.where(f & all_decr[:, None], s + (backp * totchange - amax)[:, None], s)
        s = np.where(f & (s < 0), 0.0, s)
        follows = static == -1
        s = np.where(follows & (direction == 1) & (s < p), p, s)
        s = np.where(follows & (direction == -1) & (s > p), p, s)
        v = np.where(shift[:, None], s, v)

    # proportional correction, up to 25 times per cell
    active = need.copy()
    rounds = np.zeros(len(v), dtype=np.int64)
    for _ in range(MAX_CORRECTIONS):
        if not active.any():
            break
        rounds += active
        f = free(v)
        totcov = (v * f).sum(axis=1)
        totstatic = (v * ~f).sum(axis=1)
        totch = np.abs(v - p).sum(axis=1)
        off = active & (np.abs(totcov - (1 - totstatic)) > TOL_COVER)
        with np.errstate(divide="ignore", invalid="ignore"):
            rescale = np.where(f, v * ((1 - totstatic) / totcov)[:, None], v)
            reduce = v - np.abs(v - p) * ((totcov - (1 - totstatic)) / totch)[:, None]
        reduce = np.where(reduce < 0, 0.0, reduce)
        v = np.where((off & (totch == 0))[:, None], rescale, v)
        v = np.where((off & (totch != 0))[:, None], reduce, v)
        active = off  # the Lua stops a cell once its check passes at the start of a round

    last = need & (rounds == MAX_CORRECTIONS)
    if stats is not None:
        stats["need"] = stats.get("need", 0) + int(need.sum())
        stats["shift"] = stats.get("shift", 0) + int(shift.sum())
        stats["backp_lowered"] = stats.get("backp_lowered", 0) + int((need & (backp < BACKP_START)).sum())
        stats["several_rounds"] = stats.get("several_rounds", 0) + int((rounds > 1).sum())
        stats["last"] = stats.get("last", 0) + int(last.sum())
    if last.any():
        f = free(v)
        totcov = (v * f).sum(axis=1)
        totstatic = (v * ~f).sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            v = np.where(last[:, None] & f, v * ((1 - totstatic) / totcov)[:, None], v)
    return v


def saturation_indicator(
    complementar: np.ndarray,
    valid: np.ndarray,
    no_data: np.ndarray | None = None,
    protection: np.ndarray | None = None,
) -> np.ndarray:
    """LuccME ``updateAllocationParameters``: share of the available area no longer
    in the complementary class, averaged over the 3 × 3 window (cell included)."""
    original = np.ones_like(complementar) if no_data is None else 1 - no_data
    prot = np.zeros_like(complementar) if protection is None else protection
    available = original - prot
    with np.errstate(divide="ignore", invalid="ignore"):
        perc = np.minimum((1 - complementar) / available, 1.0)
    ok = valid & (available > 0)

    total = np.zeros_like(complementar, dtype=np.float64)
    count = np.zeros(complementar.shape, dtype=np.int64)
    rows, cols = complementar.shape
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            r0, r1 = max(0, -dr), min(rows, rows - dr)
            c0, c1 = max(0, -dc), min(cols, cols - dc)
            src_ok = ok[r0 + dr : r1 + dr, c0 + dc : c1 + dc]
            total[r0:r1, c0:c1] += np.where(src_ok, perc[r0 + dr : r1 + dr, c0 + dc : c1 + dc], 0.0)
            count[r0:r1, c0:c1] += src_ok
    with np.errstate(divide="ignore", invalid="ignore"):
        averaged = np.where(count > 0, total / count, perc)
    return np.where(available > 0, averaged, 1.0)


class AllocationClueLikeSaturation(SyncRasterModel):
    """Continuous CLUE allocation with saturation — interface of ``AllocationClueLike``.

    Arrays in the backend: the land uses (their ``<lu>_past`` kept by
    ``SyncRasterModel``), ``<lu>_pot`` written by the potential, ``mask`` (cells
    that exist), ``region_attr`` (default: all cells in region 1), and optionally
    ``order_attr`` (the order in which LuccME visits the cells; default: row-major)
    and ``attr_protection``. Writes the land uses, ``<lu>_out`` and the saturation
    indicator.
    """

    def setup(
        self,
        backend,
        demand: DemandProtocol,
        potential: RegionalPotentialProtocol,
        land_use_types: list[str],
        allocation_data: list[list[SaturationAllocationSpec]],
        complementar_lu: str,
        cell_area: float,
        land_use_no_data: str | None = None,
        attr_protection: str | None = None,
        saturation_indicator: str = "saturationLimiar",
        max_difference: float = 1643,
        max_iteration: int = 1000,
        initial_elasticity: float = 0.1,
        min_elasticity: float = 0.001,
        max_elasticity: float = 1.5,
        region_attr: str = "regionAloc",
        mask_attr: str = "mask",
        order_attr: str | None = None,
    ) -> None:
        super().setup(backend)
        self.demand = demand
        self.potential = potential
        self.land_use_types = land_use_types
        self.allocation_data = allocation_data
        self.complementar_lu = complementar_lu
        self.cell_area = cell_area
        self.land_use_no_data = land_use_no_data
        self.attr_protection = attr_protection
        self.saturation_attr = saturation_indicator
        self.max_difference = max_difference
        self.max_iteration = max_iteration
        self.initial_elasticity = initial_elasticity
        self.min_elasticity = min_elasticity
        self.max_elasticity = max_elasticity
        self.region_attr = region_attr
        self.mask_attr = mask_attr
        self.order_attr = order_attr
        # per step, as LuccME logs them: iterations of the convergence loop
        # (0 = first allocation accepted) and the maximum |area - demand| accepted
        self.iterations_per_step: list[int] = []
        self.max_error_per_step: list[float] = []

        if region_attr not in self.backend.arrays:
            self.backend.set(region_attr, np.ones(self.shape, dtype=np.int32))
        if mask_attr not in self.backend.arrays:
            self.backend.set(mask_attr, np.ones(self.shape, dtype=np.float32))

    # ── helpers ─────────────────────────────────────────────────────────────

    def _valid(self) -> np.ndarray:
        return cast(np.ndarray, self.backend.get(self.mask_attr) > 0)

    def _cells(self, r_number: int) -> tuple[np.ndarray, np.ndarray]:
        """(rows, cols) of the region's cells, in LuccME's visiting order."""
        sel = self._valid() & (self.backend.get(self.region_attr) == r_number)
        rows, cols = np.nonzero(sel)
        if self.order_attr is not None:
            key = self.backend.get(self.order_attr)[rows, cols]
            idx = np.argsort(key, kind="stable")
            rows, cols = rows[idx], cols[idx]
        return rows, cols

    def _areas(self) -> list[float]:
        valid = self._valid()
        return [
            float(np.where(self.backend.get(lu) > 0, self.backend.get(lu), 0.0)[valid].sum()) * self.cell_area
            for lu in self.land_use_types
        ]

    # ── the year ────────────────────────────────────────────────────────────

    def execute(self) -> None:
        step = int(self.env.now())
        self.elasticity = [self.initial_elasticity] * len(self.land_use_types)
        self.update_saturation()

        n_iter, max_adjust, flex = 0, self.max_difference, False
        while True:
            if step != 0:
                for r_number in range(1, len(self.allocation_data) + 1):
                    self.compute_change(r_number)
                    self.correct_cell_change(r_number)
            max_diff = self.compare_to_demand(step)
            if max_diff <= max_adjust:
                break
            n_iter += 1
            if n_iter > self.max_iteration * 0.5 and not flex:
                max_adjust *= 2
                flex = True
                if self.attr_protection is not None:
                    self.potential.modify_driver(self.attr_protection, 0.5)
            if n_iter >= self.max_iteration:
                raise RuntimeError(f"allocation did not converge at step {step} (error {max_diff:.1f})")
        self.iterations_per_step.append(n_iter)
        self.max_error_per_step.append(max_diff)

        self.apply_complementar()
        for lu in self.land_use_types:
            self.backend.set(lu + "_out", self.backend.get(lu).copy())

    def update_saturation(self) -> None:
        get = self.backend.get
        self.backend.set(
            self.saturation_attr,
            saturation_indicator(
                get(self.complementar_lu).astype(np.float64),
                self._valid(),
                get(self.land_use_no_data).astype(np.float64) if self.land_use_no_data else None,
                get(self.attr_protection).astype(np.float64) if self.attr_protection else None,
            ),
        )

    def compute_change(self, r_number: int) -> None:
        sel = self._valid() & (self.backend.get(self.region_attr) == r_number)
        saturation = self.backend.get(self.saturation_attr)
        for lu_idx, lu in enumerate(self.land_use_types):
            spec = self.allocation_data[r_number - 1][lu_idx]
            new = compute_change(
                self.backend.get(lu + "_past").astype(np.float64),
                self.backend.get(lu + "_pot").astype(np.float64),
                self.elasticity[lu_idx],
                spec,
                self.demand.get_current_lu_direction(lu_idx),
                saturation,
            )
            self.backend.set(lu, np.where(sel, new, self.backend.get(lu)))

    def correct_cell_change(self, r_number: int) -> None:
        rows, cols = self._cells(r_number)
        lus = self.land_use_types
        values = np.stack([self.backend.get(lu)[rows, cols] for lu in lus], axis=1)
        past = np.stack([self.backend.get(lu + "_past")[rows, cols] for lu in lus], axis=1)
        directions = [self.demand.get_current_lu_direction(i) for i in range(len(lus))]
        corrected = correct_cell_change(values, past, self.allocation_data[r_number - 1], directions)
        for i, lu in enumerate(lus):
            arr = self.backend.get(lu).astype(np.float64).copy()
            arr[rows, cols] = corrected[:, i]
            self.backend.set(lu, arr)

    def compare_to_demand(self, step: int) -> float:
        areas = self._areas()
        max_diff = 0.0
        for j in range(1, len(self.potential.potential_data) + 1):
            for i in range(len(self.land_use_types)):
                direction = self.demand.get_current_lu_direction(i)
                demand = self.demand.get_current_lu_demand(i)
                if direction == 0 and step == 0:
                    direction = 1 if demand >= areas[i] else -1
                if direction == 1:
                    self.elasticity[i] *= demand / areas[i]
                else:
                    self.elasticity[i] *= areas[i] / demand
                if self.elasticity[i] > self.max_elasticity:
                    self.elasticity[i] = self.max_elasticity
                    self.potential.modify(j, i, direction)
                if self.elasticity[i] < self.min_elasticity:
                    if self.allocation_data[0][i].static < 0:
                        self.elasticity[i] = self.min_elasticity
                        self.potential.modify(j, i, -direction)
                    else:
                        self.demand.change_lu_direction(i)
                max_diff = max(max_diff, abs(areas[i] - demand))
        return max_diff

    def apply_complementar(self) -> None:
        """complementar = 1 − the others; a deficit comes off the largest class
        (neither the complementary nor the no-data one)."""
        valid = self._valid()
        others = [lu for lu in self.land_use_types if lu != self.complementar_lu]
        total = sum(self.backend.get(lu).astype(np.float64) for lu in others)
        comp = 1 - total

        candidates = [lu for lu in others if lu != self.land_use_no_data]
        if candidates:
            stack = np.stack([self.backend.get(lu).astype(np.float64) for lu in candidates])
            biggest = np.argmax(stack, axis=0)  # first maximum, as LuccME's strict ">"
            has_bigger = stack.max(axis=0) > 0
            deficit = valid & (comp < 0) & has_bigger
            for k, lu in enumerate(candidates):
                hit = deficit & (biggest == k)
                self.backend.set(lu, np.where(hit, self.backend.get(lu) + comp, self.backend.get(lu)))
        comp = np.where(comp < 0, 0.0, comp)
        self.backend.set(self.complementar_lu, np.where(valid, comp, self.backend.get(self.complementar_lu)))

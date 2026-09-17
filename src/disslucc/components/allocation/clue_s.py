"""
disslucc.allocation.clue_s
-----------------------------
Discrete CLUE-S allocation (Verburg et al. 2002) -- cell-by-cell
competition. RASTER port of
disslucc_discrete.components.allocation.vector.clue_s (only vector
exists in the original -- new raster version, following the
mask/backend pattern already used in allocation/clue.py, algorithm
identical to the vector one).

Each cell belongs to exactly one class (binary 0/1 columns/arrays).
Each step, adjusts a global correction vector (iter_vec) per class
until the difference between demand and allocated area is within
max_difference.
"""
from __future__ import annotations
from typing import cast
import numpy as np

from dissmodel.geo import SyncRasterModel

from ...protocols import DemandProtocol


class AllocationDClueSLike(SyncRasterModel):
    """
    Algorithm (per step)
    -----------------------
    1. iter_vec[lu] = 0 for each lu (reset each step)
    2. For each cell: best_lu = argmax{(1+tau_lu)*pot_lu + iter_lu},
       restricted to transitions allowed by transition_matrix.
    3. diff[lu] = demand[lu] - allocated_area[lu]
    4. iter_vec[lu] += diff[lu] * factor_iteration
    5. Repeats 2-4 until max(|diff|) <= max_difference or max_iteration.

    tau_<lu> (optional): per-cell/class attraction/repulsion array --
    if absent, tau=0 (default behavior).
    """

    def setup(
        self,
        backend,
        demand: DemandProtocol,
        land_use_types: list[str],
        transition_matrix: list[list[list[int]]],
        cell_area: float = 1.0,
        max_difference: float = 10.0,
        max_iteration: int = 2000,
        factor_iteration: float = 0.0001,
        region_attr: str = "region",
    ) -> None:
        super().setup(backend)
        self.demand = demand
        self.land_use_types = land_use_types
        self.cell_area = cell_area
        self.max_difference = max_difference
        self.max_iteration = max_iteration
        self.factor_iteration = factor_iteration
        self.region_attr = region_attr

        # (n_regions, n_lu, n_lu) -- O(1) access in the inner loop
        self._tm = np.array(transition_matrix, dtype=np.int8)

        if region_attr not in self.backend.arrays:
            self.backend.set(region_attr, np.ones(self.shape, dtype=np.int32))

    def _mask(self) -> np.ndarray:
        arr = self.backend.arrays.get("mask", np.ones(self.shape, dtype=bool))
        return cast(np.ndarray, arr.astype(bool))

    def execute(self) -> None:
        lu_types = self.land_use_types
        n_lu = len(lu_types)
        mask = self._mask()
        flat_mask = mask.ravel()

        # 0-based regions for numpy indexing
        regions = (self.backend.get(self.region_attr).ravel().astype(int) - 1)
        regions = np.clip(regions, 0, self._tm.shape[0] - 1)

        # INITIAL STATE of the step -- the transition matrix uses each
        # cell's class at the START of the step, not whatever is being
        # tested during the equilibrium search (allows oscillating
        # between allowed classes until convergence).
        lu_matrix_start = np.stack([self.backend.get(lu).ravel() for lu in lu_types], axis=1)
        initial_lu_idx = np.argmax(lu_matrix_start, axis=1)
        allowed = self._tm[regions, initial_lu_idx, :]  # (n_cells, n_lu)

        n_cells = lu_matrix_start.shape[0]
        tau = np.zeros((n_cells, n_lu), dtype=np.float64)
        for j, lu in enumerate(lu_types):
            col = f"tau_{lu}"
            if col in self.backend.arrays:
                tau[:, j] = self.backend.get(col).ravel()

        iter_vec = np.zeros(n_lu, dtype=np.float64)

        for n_iter in range(self.max_iteration + 1):
            pot = np.stack([self.backend.get(lu + "_pot").ravel() for lu in lu_types], axis=1)
            scores = (1.0 + tau) * pot + iter_vec[np.newaxis, :]
            scores = np.where(allowed, scores, -np.inf)

            best_lu_idx = np.argmax(scores, axis=1)  # (n_cells,)

            for j, lu in enumerate(lu_types):
                new_arr = (best_lu_idx == j).astype(np.float32).reshape(self.shape)
                self.backend.arrays[lu] = np.where(mask, new_arr, self.backend.get(lu))

            diff = self._calc_diff(mask)
            max_diff = float(np.max(np.abs(list(diff.values()))))

            if max_diff <= self.max_difference:
                break
            if n_iter >= self.max_iteration:
                raise RuntimeError(
                    f"Allocation did not converge at step {int(self.env.now())} "
                    f"after {self.max_iteration} iterations (max error={max_diff:.2f})"
                )

            for j, lu in enumerate(lu_types):
                iter_vec[j] += diff[lu] * self.factor_iteration

    def _calc_diff(self, mask: np.ndarray) -> dict[str, float]:
        return {
            lu: (
                self.demand.get_current_lu_demand(i)
                - float((self.backend.get(lu)[mask] == 1).sum()) * self.cell_area
            )
            for i, lu in enumerate(self.land_use_types)
        }

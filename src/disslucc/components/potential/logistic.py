"""
disslucc.potential.logistic
------------------------------
Potential via logistic regression -- discrete CLUE-S. RASTER port of
disslucc_discrete.components.potential.vector.logistic_regression (only
vector exists in the original repository -- this raster version is
new, written following the same mask/backend pattern as
potential/linear.py, not a literal translation like the modules
"faithful to main").

Verburg et al. (2002). For each cell and each land use:

    z    = const + sum(beta_k * driver_k)
    prob = sigmoid(z)
    pot  = prob + elasticity * I(cell is already this class)

Elasticity reinforces the cell's current use -- the higher it is, the
more "locked in" the pixel stays in its current class (spatial
lock-in).
"""
from __future__ import annotations

import numpy as np
from dissmodel.geo import SyncRasterModel
from scipy.special import expit

from ...schemas import LogisticRegressionSpec


class PotentialDLogisticRegression(SyncRasterModel):
    """
    Arrays written
    ---------------
    <lu>_reg : raw logistic probability (no elasticity)
    <lu>_pot : prob + elasticity -- what Allocation reads

    Note: doesn't implement .modify() -- the discrete algorithm
    (CLUE-S) doesn't use per-potential elasticity feedback like
    continuous CLUE; it adjusts a global correction vector (iter_vec)
    in allocation/clue_s.py instead. PotentialProtocol.modify() goes
    unused here, same as in the original vector version.
    """

    def setup(
        self,
        backend,
        potential_data: list[list[LogisticRegressionSpec]],
        land_use_types: list[str],
        region_attr: str = "region",
    ) -> None:
        super().setup(backend)
        self.potential_data = potential_data
        self.land_use_types = land_use_types
        self.region_attr = region_attr

        if region_attr not in self.backend.arrays:
            self.backend.set(region_attr, np.ones(self.shape, dtype=np.int32))

        for lu in land_use_types:
            self.backend.set(lu + "_reg", np.zeros(self.shape, dtype=np.float32))
            self.backend.set(lu + "_pot", np.zeros(self.shape, dtype=np.float32))

    def execute(self) -> None:
        for r_idx, region_specs in enumerate(self.potential_data):
            r_number = r_idx + 1
            mask = self.backend.get(self.region_attr) == r_number
            for lu_idx, spec in enumerate(region_specs):
                self._compute_potential(mask, lu_idx, spec)

    def _compute_potential(self, mask: np.ndarray, lu_idx: int, spec: LogisticRegressionSpec) -> None:
        lu = self.land_use_types[lu_idx]

        z = np.full(self.shape, spec.const, dtype=np.float32)
        for col, beta in spec.betas.items():
            z = z + beta * self.backend.get(col).astype(np.float32)

        # scipy.special.expit is the standard, numerically stable sigmoid
        # (no manual overflow clipping needed -- it handles extreme z from
        # cells outside the mask, e.g. nodata=-1, without over/underflow).
        prob = expit(z)
        elas = np.where(self.backend.get(lu) == 1, spec.elasticity, 0.0).astype(np.float32)
        pot = prob + elas

        self.backend.arrays[lu + "_reg"] = np.where(mask, prob, self.backend.get(lu + "_reg"))
        self.backend.arrays[lu + "_pot"] = np.where(mask, pot, self.backend.get(lu + "_pot"))

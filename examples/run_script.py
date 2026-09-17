"""
Plain script, no Executor and no TOML -- "script usability": builds the
model with code, the way a LuccME .lua script built
`P1 = PotentialCLinearRegression{...}; LuccMEModel{potential=P1, ...}`.

    python3 examples/run_script.py

Demand -> Potential -> Allocation are each a real dissmodel.core.Model,
registered in the same Environment in the order they're built below --
exactly like the real disslucc-continuous does (no Pipeline, no Stage,
no StageRegistry).
"""
from __future__ import annotations

from dissmodel.core import Environment

from disslucc import DemandInline, PotentialLinearRegression, AllocationClueLike
from disslucc.schemas import RegressionSpec, AllocationSpec

from scenario import build_backend, build_demand, LAND_USE_TYPES, COMPLEMENTAR_LU

N_STEPS = 8
HEIGHT = WIDTH = 30

backend = build_backend(height=HEIGHT, width=WIDTH, seed=42)
demand_matrix = build_demand(N_STEPS, height=HEIGHT, width=WIDTH)

env = Environment(end_time=N_STEPS - 1)

demand = DemandInline(
    values=demand_matrix,
    land_use_types=LAND_USE_TYPES,
)

potential = PotentialLinearRegression(
    backend=backend,
    demand=demand,
    land_use_types=LAND_USE_TYPES,
    potential_data=[[
        RegressionSpec(const=-0.2, betas={"slope": 0.4}),                        # forest
        RegressionSpec(const=0.4, betas={"dist_road": -0.1, "slope": -0.5}),     # agriculture
        RegressionSpec(const=0.3, betas={"dist_road": -0.6, "slope": -0.3}),     # urban
    ]],
)

allocation = AllocationClueLike(
    backend=backend,
    demand=demand,
    potential=potential,
    land_use_types=LAND_USE_TYPES,
    static={"forest": 0, "agriculture": -1, "urban": -1},
    complementar_lu=COMPLEMENTAR_LU,
    cell_area=1.0,
    max_difference=5.0,
    allocation_data=[
        AllocationSpec(static=0),
        AllocationSpec(static=-1),
        AllocationSpec(static=-1),
    ],
)

env.run()

print("\nArea count evolution per class (sum of fractions * cell_area):")
for lu in LAND_USE_TYPES:
    area = float(backend.get(lu).sum())
    print(f"  {lu:>12}: {area:8.1f}")

print("\nLast-step demand target vs allocated area:")
for i, lu in enumerate(LAND_USE_TYPES):
    target = demand_matrix[-1][i]
    actual = float(backend.get(lu).sum())
    print(f"  {lu:>12}: target={target:8.1f}  allocated={actual:8.1f}  diff={abs(target - actual):6.2f}")

# ── quicklook -----------------------------------------------------------------
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(11, 4))
for ax, lu in zip(axes, LAND_USE_TYPES):
    im = ax.imshow(backend.get(lu), cmap="viridis", vmin=0, vmax=1)
    ax.set_title(lu)
    ax.axis("off")
fig.colorbar(im, ax=axes, shrink=0.7, label="cell fraction")
fig.suptitle(f"Land use after {N_STEPS - 1} steps")
out_path = "quicklook.png"
fig.savefig(out_path, dpi=120)
plt.close(fig)
print(f"\nquicklook saved to: {out_path}")

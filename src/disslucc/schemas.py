"""
disslucc.schemas
-----------------
Dataclasses defining the parameters of each component. Faithful port
of disslucc_continuous.schemas.schemas (decoupling branch).
Act as the contract between the user and the models -- validation
happens here, the models just consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegressionSpec:
    """Parameters of a linear regression for one land use class.

    `newconst` doesn't exist in the original schema (disslucc-continuous
    creates this attribute dynamically at runtime, without declaring it
    -- `spec.newconst = spec.const`, caught by mypy here). Declared
    explicitly: it's the `const` value already adjusted by
    `_adapt_constants()` each step -- mutable by design, not a typo
    for `const`.

    `init=False`: `PotentialLinearRegression.setup()`/`execute()`
    always overwrite it with `spec.newconst = spec.const` before ever
    reading it (every step, not just once), so a value passed to the
    constructor would be silently discarded on the first run -- this
    is internal runtime state the model manages, not something a
    caller configures. Excluded from `__init__`/`repr`/`==` so
    `RegressionSpec(const=0.5, newconst=99)` is a clear TypeError
    instead of a silent no-op, and two specs that only differ in
    runtime-mutated state still compare equal.
    """
    const:     float
    betas:     dict[str, float] = field(default_factory=dict)
    is_log:    bool = False
    newconst:  float = field(default=0.0, init=False, repr=False, compare=False)


@dataclass
class LogisticRegressionSpec:
    """
    Parameters of a logistic regression for one land use class.

    Faithful port of disslucc_discrete.schemas.schemas.LogisticRegressionSpec.
    Used by PotentialDLogisticRegression (discrete CLUE-S).
    """
    const:      float
    elasticity: float = 0.0
    betas:      dict[str, float] = field(default_factory=dict)


@dataclass
class AllocationSpec:
    """Allocation constraints for one land use class."""
    static:     int   = -1   # -1 = follows demand | 0 = free | 1 = fixed
    min_value:  float = 0.0
    max_value:  float = 1.0
    min_change: float = 0.0
    max_change: float = 1.0

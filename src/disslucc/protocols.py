"""
disslucc.protocols
-------------------
Contracts between Demand/Potential and Allocation. Faithful port of the
`main` branch of disslucc-continuous (not `decoupling` -- that one was
experimental).

On main, Allocation reads `<lu>_pot` directly from the shared backend
instead of going through a Potential method -- that's why
PotentialProtocol only declares `modify` (the elasticity feedback
hook), not `get_potential`. More coupled than the decoupling version,
but it's what's in production.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DemandProtocol(Protocol):
    def get_current_lu_demand(self, lu_index: int) -> float: ...
    def get_previous_lu_demand(self, lu_index: int) -> float: ...
    def get_current_lu_direction(self, lu_index: int) -> int: ...
    def change_lu_direction(self, lu_index: int) -> int: ...


@runtime_checkable
class PotentialProtocol(Protocol):
    def modify(self, r_number: int, lu_idx: int, direction: int) -> None: ...

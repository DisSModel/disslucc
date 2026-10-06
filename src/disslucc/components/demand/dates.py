"""
disslucc.demand.dates
----------------------
Port of LuccME's DemandComputeTwoDates and DemandComputeThreeDates.

Both build the annual demand from the land-use maps themselves instead of a
table: the initial demand is the area of each class in the layer at the start
year, the later demands (one or two reference years) are the areas read from
other columns of the layer (e.g. ``f2011``, ``f2014``), and the years in
between are interpolated linearly.

The result is handed to :class:`DemandPreComputedValues`, so both classes are
substrate-neutral from there on and implement the same ``DemandProtocol``.

Rounding follows LuccME exactly (and it matters): every year adds the step to
the **already rounded** demand of the previous year and rounds again with
``floor(x + 0.5)``; the reference years are set to their exact value, rounded.
That is why the demand is integer-valued and can differ by a few units from a
table computed with exact arithmetic.
"""
from __future__ import annotations

import math

import numpy as np

from .precomputed import DemandPreComputedValues

_DIRECTIONS = {"Increase": 1, "Decrease": -1}


def _round(x: float) -> int:
    """LuccME's `math.floor(x + 0.5)` (rounds half up, unlike Python's round())."""
    return math.floor(x + 0.5)


def _directions(
    direction: list[str] | None, start: list[float], end: list[float]
) -> list[int]:
    """+1 / -1 / 0 per class: the given `direction`, or the sign of end - start."""
    if direction is not None:
        # anything other than "Increase" / "Decrease" means stable, as in LuccME
        return [_DIRECTIONS.get(d, 0) for d in direction]
    return [(e > s) - (e < s) for s, e in zip(start, end)]


def interpolate_two_dates(
    initial: list[float],
    final: list[float],
    final_offset: int,
    n_years: int,
    direction: list[str] | None = None,
) -> list[list[int]]:
    """
    Annual demand from two dates (the algorithm of ``DemandComputeTwoDates``).

    initial, final : total area per class at the start year and at the final year.
    final_offset   : final year - start year (> 0).
    n_years        : number of rows to generate (end year - start year + 1).
                     Beyond the final year the same step keeps being applied.
    direction      : optional "Increase" / "Decrease" per class; default is the
                     sign of ``final - initial``.
    """
    if final_offset <= 0:
        raise ValueError("final_year must be after start_year")
    sign = _directions(direction, initial, final)
    step = [abs(f - i) / final_offset for i, f in zip(initial, final)]
    rows = [[_round(v) for v in initial]]
    for year in range(1, n_years):                      # year = offset from the start
        if year == final_offset:
            rows.append([_round(v) for v in final])
        else:
            prev = rows[-1]
            rows.append([_round(prev[j] + step[j] * sign[j]) for j in range(len(initial))])
    return rows[:n_years]


def interpolate_three_dates(
    initial: list[float],
    middle: list[float],
    final: list[float],
    middle_offset: int,
    final_offset: int,
    n_years: int,
    direction: list[str] | None = None,
) -> list[list[int]]:
    """
    Annual demand from three dates (``DemandComputeThreeDates``): linear from the
    start to the middle year, then linear from the middle to the final year, each
    segment with its own step and direction. The final year may lie after the end
    of the simulation (then only the first segment, or part of the second, is used).
    """
    if not 0 < middle_offset < final_offset:
        raise ValueError("start_year < middle_year < final_year is required")
    seg1, seg2 = middle_offset, final_offset - middle_offset
    sign1, sign2 = _directions(direction, initial, middle), _directions(direction, middle, final)
    step1 = [abs(m - i) / seg1 for i, m in zip(initial, middle)]
    step2 = [abs(f - m) / seg2 for m, f in zip(middle, final)]
    rows = [[_round(v) for v in initial]]
    for year in range(1, n_years):
        if year == middle_offset:
            rows.append([_round(v) for v in middle])
        elif year == final_offset:
            rows.append([_round(v) for v in final])
        else:
            step, sign = (step1, sign1) if year < middle_offset else (step2, sign2)
            prev = rows[-1]
            rows.append([_round(prev[j] + step[j] * sign[j]) for j in range(len(initial))])
    return rows[:n_years]


def _areas(backend, names: list[str], cell_area: float) -> list[float]:
    """Total area of each named layer over the valid cells (mask), cell by cell as LuccME does."""
    first = np.asarray(backend.get(names[0]))
    mask = np.asarray(backend.arrays.get("mask", np.ones(first.shape, dtype=bool))).astype(bool)
    return [float((np.asarray(backend.get(n), dtype=np.float64)[mask] * cell_area).sum()) for n in names]


class DemandComputeTwoDates(DemandPreComputedValues):
    """
    Demand interpolated between the start year and one final year.

    Parameters (setup)
    -------------------
    backend                  : substrate with the class layers and the final-year layers.
    land_use_types           : class layers at the start year, e.g. ["f", "d", "outros"].
    final_land_use_types     : layers with the same classes at the final year, in the
                               same order, e.g. ["f2014", "d2014", "outros"].
    start_year, end_year     : first and last simulated year (rows = end - start + 1).
    final_year               : year the ``final_land_use_types`` layers describe.
    cell_area                : area of one cell (the unit of the demand).
    direction_for_interpolation : optional "Increase" / "Decrease" per class.

    Create it before ``env.run()``: the start-year areas are read at construction.
    With float32 layers the areas carry float32 rounding; use float64 layers when
    the demand must match a reference to the unit.
    """

    def setup(
        self,
        backend,
        land_use_types: list[str],
        final_land_use_types: list[str],
        start_year: int,
        end_year: int,
        final_year: int,
        cell_area: float,
        direction_for_interpolation: list[str] | None = None,
    ) -> None:
        if len(final_land_use_types) != len(land_use_types):
            raise ValueError("final_land_use_types must have one layer per land use type")
        if direction_for_interpolation is not None and len(direction_for_interpolation) != len(land_use_types):
            raise ValueError("direction_for_interpolation must have one entry per land use type")
        rows = interpolate_two_dates(
            _areas(backend, land_use_types, cell_area),
            _areas(backend, final_land_use_types, cell_area),
            final_year - start_year,
            end_year - start_year + 1,
            direction_for_interpolation,
        )
        super().setup(annual_demand=rows, land_use_types=land_use_types)


class DemandComputeThreeDates(DemandPreComputedValues):
    """
    Demand interpolated through a middle year to a final year (see
    :class:`DemandComputeTwoDates` for the shared parameters).

    Extra parameters (setup)
    -------------------------
    middle_land_use_types : layers at the middle year, e.g. ["f2011", "d2011", "outros"].
    middle_year           : year they describe; start_year < middle_year < final_year.
    """

    def setup(
        self,
        backend,
        land_use_types: list[str],
        middle_land_use_types: list[str],
        final_land_use_types: list[str],
        start_year: int,
        end_year: int,
        middle_year: int,
        final_year: int,
        cell_area: float,
        direction_for_interpolation: list[str] | None = None,
    ) -> None:
        n = len(land_use_types)
        if len(middle_land_use_types) != n or len(final_land_use_types) != n:
            raise ValueError("middle and final land use types must have one layer per land use type")
        if direction_for_interpolation is not None and len(direction_for_interpolation) != n:
            raise ValueError("direction_for_interpolation must have one entry per land use type")
        rows = interpolate_three_dates(
            _areas(backend, land_use_types, cell_area),
            _areas(backend, middle_land_use_types, cell_area),
            _areas(backend, final_land_use_types, cell_area),
            middle_year - start_year,
            final_year - start_year,
            end_year - start_year + 1,
            direction_for_interpolation,
        )
        super().setup(annual_demand=rows, land_use_types=land_use_types)

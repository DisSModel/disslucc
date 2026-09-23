"""
tests/_golden_helpers.py
--------------------------
Per-year comparison against the LuccME goldens in benchmark/goldens/
(generated with LambdaGeo/terrame-docker; see benchmark/README.md).

A golden holds, for every cell and every simulated year, `<lu>_out` and
`<lu>_pot`, plus the TerraME iteration count per year in manifest.json.
`YearRecorder` snapshots the same arrays from the disslucc backend at the end
of each step, so both sides can be compared year by year.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from dissmodel.core import Model

ROOT = Path(__file__).resolve().parent.parent
GOLDENS = ROOT / "benchmark" / "goldens"


def golden_available(name: str) -> bool:
    return (GOLDENS / name / f"{name}.csv.gz").exists()


def load_golden(name: str) -> tuple[pd.DataFrame, dict]:
    """Golden table (year, id, col, row, <lu>_out, <lu>_pot) and its manifest."""
    df = pd.read_csv(GOLDENS / name / f"{name}.csv.gz")
    manifest = json.loads((GOLDENS / name / "manifest.json").read_text())
    return df, manifest


def golden_iterations(manifest: dict) -> list[int]:
    """TerraME iterations per year, in year order."""
    it = manifest["iterations_per_year"]
    return [it[y] for y in sorted(it)]


class YearRecorder(Model):
    """Snapshots `<lu>` and `<lu>_pot` at every step. Create it AFTER the
    allocation component so it runs after it in each step."""

    def setup(self, backend, rows: np.ndarray, cols: np.ndarray, land_use_types: list[str]) -> None:
        self.backend = backend
        self.rows, self.cols = rows, cols
        self.land_use_types = land_use_types
        self.snapshots: list[dict[str, np.ndarray]] = []

    def execute(self) -> None:
        snap = {}
        for lu in self.land_use_types:
            snap[f"{lu}_out"] = np.asarray(self.backend.get(lu), dtype=np.float64)[self.rows, self.cols].copy()
            if f"{lu}_pot" in self.backend.arrays:
                snap[f"{lu}_pot"] = np.asarray(
                    self.backend.get(f"{lu}_pot"), dtype=np.float64)[self.rows, self.cols].copy()
        self.snapshots.append(snap)


def per_year_frame(recorder: YearRecorder, years: list[int]) -> pd.DataFrame:
    """Recorder snapshots as a long table keyed by (year, row, col)."""
    frames = []
    for year, snap in zip(years, recorder.snapshots):
        f = pd.DataFrame(snap)
        f["year"], f["row"], f["col"] = year, recorder.rows, recorder.cols
        frames.append(f)
    return pd.concat(frames).set_index(["year", "row", "col"]).sort_index()


def per_year_mae(ours: pd.DataFrame, golden: pd.DataFrame, column: str) -> dict[int, float]:
    """MAE of `column` per year, cells aligned by (row, col)."""
    ref = golden.set_index(["year", "row", "col"])[column]
    joined = ours[[column]].join(ref.rename("ref"), how="inner")
    return {
        int(year): float(np.abs(g[column] - g["ref"]).mean())
        for year, g in joined.groupby(level="year")
    }

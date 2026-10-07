"""
The example TOML files (examples/dissmodel-configs/) through the local CLI.

What a modeler writes in TOML and what a script builds by hand are the same
experiment: the CLI run and the hand-built ExperimentRecord produce the same
output file (same SHA-256 in `record.artifacts["output"]`). Numerical agreement
with TerraME is not tested here; it lives in LambdaGeo/disslucc-benchmark.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from dissmodel.executor import ExperimentRecord
from dissmodel.executor.runner import execute_lifecycle
from dissmodel.geo.raster.backend import RasterBackend
from dissmodel.io.raster import save_geotiff
from rasterio.transform import from_origin

from disslucc.executors import LuccContinuousExecutor

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "examples" / "dissmodel-configs"
INPUT = ROOT / "data" / "input"


def run_cli(module: str, toml: str, source: Path, demand: Path, out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", f"disslucc.executors.{module}", "run",
         "--toml", str(CONFIGS / toml), "--input", str(source),
         "--param", f"demand_csv={demand}", "--output", str(out)],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    (record_path,) = out.parent.glob("*.record.json")
    return json.loads(record_path.read_text())


def test_continuous_toml_equals_hand_built_record(tmp_path):
    cli = run_cli("continuous", "lucc_continuous.toml", INPUT / "csAC.zip",
                  INPUT / "examples_demand_lab1.csv", tmp_path / "cli" / "result.tif")

    record = ExperimentRecord(
        model_name=LuccContinuousExecutor.name,
        source={"uri": str(INPUT / "csAC.zip")},
        parameters={
            "land_use_types": ["f", "d", "outros"],
            "complementar_lu": "f",
            "demand_csv": str(INPUT / "examples_demand_lab1.csv"),
            "land_use_no_data": "outros",
            "static": {"f": -1, "d": -1, "outros": 1},
            "cell_area": 25.0,
            "n_steps": 7,
            "resolution": 5000.0,
            "potential_data": [
                {"const": 0.7392, "betas": {
                    "assentamen": -0.2193, "uc_us": 0.1754, "uc_pi": 0.09708,
                    "ti": 0.1207, "dist_riobr": 0.0000002388, "fertilidad": -0.1313}},
                {"const": 0.267, "betas": {
                    "rodovias": -0.0000009922, "assentamen": 0.2294,
                    "uc_us": -0.09867, "dist_riobr": -0.0000003216, "fertilidad": 0.1281}},
                {"const": 0.0},
            ],
            "allocation_data": [
                {"static": -1, "min_value": 0, "max_value": 1, "min_change": 0, "max_change": 1},
                {"static": -1, "min_value": 0, "max_value": 1, "min_change": 0, "max_change": 1},
                {"static": 1, "min_value": 0, "max_value": 1, "min_change": 0, "max_change": 1},
            ],
        },
    )
    hand, _ = execute_lifecycle(LuccContinuousExecutor(), record)

    assert cli["status"] == hand.status == "completed"
    assert cli["source"]["checksum"] == hand.source.checksum
    assert cli["artifacts"]["output"] == hand.artifacts["output"]


def test_discrete_toml_runs_and_is_reproducible(tmp_path):
    runs = [run_cli("discrete", "lucc_discrete.toml", INPUT / "cs_moju.zip",
                    INPUT / "demand_moju.csv", tmp_path / f"run{i}" / "result.tif")
            for i in (1, 2)]
    assert all(r["status"] == "completed" for r in runs)
    assert runs[0]["artifacts"]["output"] == runs[1]["artifacts"]["output"]


def _saturation_input(path: Path) -> None:
    """csAC as a GeoTIFF with named bands: land uses, drivers, mask, cell order."""
    cells = gpd.read_file(INPUT / "csAC.zip")
    rows, cols = cells["row"].astype(int).values, cells["col"].astype(int).values
    shape = (rows.max() + 1, cols.max() + 1)

    def grid(values) -> np.ndarray:
        a = np.zeros(shape)
        a[rows, cols] = np.asarray(values, dtype=np.float64)
        return a

    bands = {c: grid(cells[c].astype(float).values) for c in
             ["f", "d", "outros", "uc_us", "uc_pi", "ti", "assentamen", "fertilidad", "dist_riobr"]}
    bands["mask"] = grid(np.ones(len(cells)))
    bands["order"] = grid(np.arange(len(cells)))
    backend = RasterBackend(shape=shape)
    for name, arr in bands.items():
        backend.set(name, arr)
    save_geotiff(
        (backend, {"crs": "EPSG:5880", "transform": from_origin(0, shape[0] * 5000.0, 5000.0, 5000.0)}),
        str(path), band_spec=[(n, "float64", -9999.0) for n in sorted(backend.arrays)],
    )


def test_saturation_toml_runs_and_is_reproducible(tmp_path):
    src = tmp_path / "csAC.tif"
    _saturation_input(src)
    runs = [run_cli("saturation", "lucc_saturation.toml", src,
                    INPUT / "examples_demand_lab1.csv", tmp_path / f"run{i}" / "result.tif")
            for i in (1, 2)]
    assert all(r["status"] == "completed" for r in runs)
    assert runs[0]["artifacts"]["output"] == runs[1]["artifacts"]["output"]

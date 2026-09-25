"""
LuccSaturationExecutor through the local CLI, with the example TOML
(examples/dissmodel-configs/lucc_saturation.toml = lab03), against the lab03
golden: the path a model like LuccME-BR is run by.

csAC goes in as a GeoTIFF with named bands (land uses, drivers, mask, the
cells' order), written with dissmodel's save_geotiff; the CLI writes the last
step and `save_steps`; both are compared with the golden.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from _lab03_helpers import LAND_USES, Lab
from dissmodel.geo.raster.backend import RasterBackend
from dissmodel.io import load_dataset
from dissmodel.io.raster import save_geotiff
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parent.parent
TOML = ROOT / "examples" / "dissmodel-configs" / "lucc_saturation.toml"
DEMAND_CSV = ROOT / "data" / "input" / "examples_demand_lab1.csv"  # lab03's demand table, same values
TOL = 1e-9


@pytest.fixture(scope="module")
def run_cli(tmp_path_factory):
    lab = Lab("lab03")
    tmp = tmp_path_factory.mktemp("saturation")
    backend = RasterBackend(shape=lab.shape)
    for lu in LAND_USES:
        backend.set(lu, lab.initial(lu))
    for name, arr in lab.drivers(2008).items():
        backend.set(name, arr)
    backend.set("mask", lab.valid.astype(np.float64))
    backend.set("order", lab.grid(np.arange(len(lab.cells))))
    names = sorted(backend.arrays)
    transform = from_origin(0, lab.shape[0] * 5000.0, 5000.0, 5000.0)  # any georeference: 5 km cells
    cellspace = tmp / "csAC.tif"
    save_geotiff(
        (backend, {"crs": "EPSG:5880", "transform": transform}),
        str(cellspace),
        band_spec=[(n, "float64", -9999.0) for n in names],
    )
    subprocess.run(
        [sys.executable, "-m", "disslucc.executors.saturation", "run", "--toml", str(TOML),
         "--input", str(cellspace), "--param", f"demand_csv={DEMAND_CSV}", "--output", str(tmp / "lab03.tif")],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    # the CLI adds the experiment id to the name: lab03_<id>.tif, lab03_<id>_step3.tif
    outputs = {p.name: p for p in tmp.glob("lab03_*.tif")}
    final = next(p for n, p in outputs.items() if "_step" not in n)
    return lab, {6: final, 3: final.with_name(f"{final.stem}_step3.tif")}


def read(path: Path) -> dict[str, np.ndarray]:
    (backend, _), _ = load_dataset(str(path), fmt="raster")
    return backend.arrays


@pytest.mark.parametrize("step", [3, 6])
def test_cli_run_matches_golden(run_cli, step):
    lab, paths = run_cli
    arrays = read(paths[step])
    ref = lab.golden_year(2008 + step)
    r = ref.index.get_level_values("row").values
    c = ref.index.get_level_values("col").values
    for lu in LAND_USES:
        err = np.abs(arrays[lu][r, c] - ref[f"{lu}_out"].values).max()
        assert err < TOL, f"{2008 + step} {lu}: {err:.3e}"


def test_demand_csv_is_lab03s():
    """The example reuses examples_demand_lab1.csv: it holds lab03's demand table."""
    from _lab03_helpers import DEMAND

    from disslucc.components.demand import load_demand_csv

    assert load_demand_csv(DEMAND_CSV.read_text(), LAND_USES) == DEMAND

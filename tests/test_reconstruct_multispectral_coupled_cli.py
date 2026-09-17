"""tests/test_reconstruct_multispectral_coupled_cli.py -- CLI-level test
for pipelines/reconstruct_multispectral_coupled.py, including its
--qc integration (agents/qc_agent.py) and, when QC recommends reporting,
its report_agent.py integration -- this project's three agents
(reconstruction orchestration, QC, report drafting) chained together in
one real pipeline invocation for the first time. Dry-run only (no real
API calls; see agents/*.py for why that costs real money and isn't done
in the regular test suite).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipelines"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ptyco_full_simulator import config, forward_model, led_array, optics  # noqa: E402
import reconstruct_multispectral_coupled as pipeline  # noqa: E402


def _write_fake_lab_data(tmp_path, grid_size=9, crop=16, background_rows=4):
    A_true, B_true = 1.34, 0.004
    setups = {ch: config.default_setup(channel=ch, grid_size=grid_size, objective="current",
                                        resolution_px=(crop, crop))
              for ch in config.CHANNEL_WAVELENGTH_NM}
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((xc - 0.1) ** 2 + (yc + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((xc + 0.15) ** 2 + (yc - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    ramp = np.clip((y - background_rows) / 4.0, 0, 1)
    t_true = 0.012 * np.sin(2 * np.pi * xc) * np.cos(2 * np.pi * yc) * ramp
    t_true -= t_true.min()

    for channel, setup in setups.items():
        wavelength_um = setup.wavelength_um
        opl = (A_true + B_true / wavelength_um**2) * t_true
        obj = amp * np.exp(1j * (2 * np.pi / wavelength_um * opl))
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            obj, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um,
        )
        subdir = tmp_path / channel / f"{grid_size}x{grid_size}_recortada_{crop}"
        subdir.mkdir(parents=True)
        for (row, col), intensity in lr_images.items():
            Image.fromarray(intensity.astype(np.float32), mode="F").save(
                subdir / f"fila{row}_columna{col}.tiff"
            )


def test_qc_and_report_agent_wiring_dry_run(tmp_path):
    _write_fake_lab_data(tmp_path)
    output_dir = tmp_path / "out"

    pipeline.main([
        "--data-root", str(tmp_path), "--grid-size", "9", "--crop", "16",
        "--iterations", "40", "--background-rows", "4", "--baseline-index", "1.34",
        "--qc", "--output-dir", str(output_dir),
    ])

    with open(output_dir / "qc_review.json") as fh:
        qc_out = json.load(fh)
    assert qc_out["decision"]["reasoning"] == "dry_run=True, no API call made"

    if qc_out["decision"]["recommendation"] == "report":
        with open(output_dir / "report_draft.json") as fh:
            draft = json.load(fh)
        assert draft["reasoning"] == "dry_run=True, no API call made"
    else:
        assert not (output_dir / "report_draft.json").exists()

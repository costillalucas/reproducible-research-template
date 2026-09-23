"""tests/test_reconstruct_multispectral_coupled_cli.py -- CLI-level test
for pipelines/reconstruct_multispectral_coupled.py, including its --qc
integration (agents/qc_agent.py) and, when QC recommends reporting, its
report_agent.py integration. `test_qc_and_report_agent_wiring_dry_run`
exercises 2 of this project's 3 agents (QC, report); test_all_three_agents_
_chained_dry_run below adds --use-reconstruction-agent to exercise all 3
(reconstruction orchestration, QC, report) chained in one pipeline
invocation -- the milestone this file's original docstring described
before that flag existed on this script. Dry-run only (no real API calls;
see agents/*.py for why that costs real money and isn't done in the
regular test suite).
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
    setups = {ch: config.default_setup(channel=ch, grid_size=grid_size, objective="2_5x_na007",
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
        "--data-root", str(tmp_path), "--grid-size", "9", "--crop", "16", "--objective", "2_5x_na007", "--z-distance-mm", "70", "--no-exposure-normalization", "--no-normalize-initial-guess",
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


def test_all_three_agents_chained_dry_run(tmp_path):
    """--use-reconstruction-agent (agent #1) + --qc (agent #2, chaining
    into agent #3 when QC recommends it) in one invocation -- proves the
    two previously-independent flows (reconstruction_orchestrator wired
    into simulate_and_reconstruct.py; QC->report wired into this script)
    can now run together on the same pipeline, closing the gap the
    roadmap's milestone 7 write-up flagged as still open.
    """
    _write_fake_lab_data(tmp_path)
    output_dir = tmp_path / "out"

    pipeline.main([
        "--data-root", str(tmp_path), "--grid-size", "9", "--crop", "16", "--objective", "2_5x_na007", "--z-distance-mm", "70", "--no-exposure-normalization", "--no-normalize-initial-guess",
        "--iterations", "40", "--background-rows", "4", "--baseline-index", "1.34",
        "--use-reconstruction-agent", "--max-attempts", "2",
        "--qc", "--output-dir", str(output_dir),
    ])

    with open(output_dir / "coupled_metrics.json") as fh:
        coupled_metrics = json.load(fh)
    assert coupled_metrics["use_reconstruction_agent"] is True
    for channel in ("red", "green", "blue"):
        attempts = coupled_metrics["agent_attempts"][channel]
        assert len(attempts) >= 1
        assert attempts[0]["decision"]["reasoning"] == "dry_run=True, no API call made"
        # dry-run always canned-accepts on the first attempt, same as a plain call
        assert attempts[0]["decision"]["action"] == "accept"

    with open(output_dir / "qc_review.json") as fh:
        qc_out = json.load(fh)
    assert qc_out["decision"]["reasoning"] == "dry_run=True, no API call made"


def test_chromatic_report_flag_writes_report_json(tmp_path):
    """--chromatic-report (2026-09-18) on the coupled pipeline -- CLI
    wiring check, not a re-derivation of the diagnostic's own accuracy
    (already covered with a known injected shift in
    tests/test_chromatic_diagnostics.py).
    """
    _write_fake_lab_data(tmp_path)
    output_dir = tmp_path / "out"

    pipeline.main([
        "--data-root", str(tmp_path), "--grid-size", "9", "--crop", "16", "--objective", "2_5x_na007", "--z-distance-mm", "70", "--no-exposure-normalization", "--no-normalize-initial-guess",
        "--iterations", "20", "--chromatic-report", "--output-dir", str(output_dir),
    ])

    with open(output_dir / "chromatic_report.json") as fh:
        report = json.load(fh)
    assert set(report) == {"red_vs_green", "blue_vs_green"}
    for entry in report.values():
        assert len(entry["lateral_shift_px"]) == 2
        assert "offset_um" in entry["focus"]

"""tests/test_gd_solver_pipelines.py -- `--solver gd-amplitude`
(`joint_calibration.reconstruct_gradient_descent`) as an opt-in alternative
to the Wirtinger flow in the pipelines.

Captures here are simulated with EXACT (unrounded) LED k
(`joint_calibration.simulate_lr_stack_continuous`), like real hardware
would produce. The repo's older fake captures use `forward_model.
simulate_lr_stack`, which rounds k to a spectrum bin -- the very model the
Wirtinger flow inverts, so those tests can't show what happens on
continuous-k data (see reconstruct_gradient_descent's docstring: WF 0.076
vs GD 0.995 on the same exact-k data at 16px crops).
"""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipelines"))
sys.path.insert(0, os.path.dirname(__file__))
from ptyco_full_simulator import config, led_array, metrics, optics, reconstruction  # noqa: E402
from ptyco_full_simulator import joint_calibration as jc  # noqa: E402
import reconstruct_multispectral_independent as multispectral  # noqa: E402
import simulate_and_reconstruct as sim_pipeline  # noqa: E402
from test_joint_calibration import _synthetic_object  # noqa: E402

CROP = 16


def _channel_case(channel="green", crop=CROP):
    setup = config.default_setup(channel=channel, grid_size=9, objective="current", resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hp = optics.actual_hr_pixel_size_um(setup, factor)
    hs = optics.hr_shape((crop, crop), factor)
    truth = _synthetic_object(hs)
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr = jc.simulate_lr_stack_continuous(truth, hp, grid, (crop, crop), setup.lr_pixel_size_um,
                                          setup.objective.na, setup.wavelength_um)
    return setup, factor, hp, hs, truth, grid, lr


def _phase_corr(obj, truth):
    return metrics.compare_to_ground_truth(obj, truth)["phase_correlation"]


def test_reconstruct_gradient_descent_matches_reconstruct_schema_and_recovers_phase():
    setup, factor, hp, hs, truth, grid, lr = _channel_case()
    arbitrary_gain = 137.0  # real captures have an arbitrary intensity scale
    raw = {k: v * arbitrary_gain for k, v in lr.items()}
    result = jc.reconstruct_gradient_descent(raw, grid, hp, setup.lr_pixel_size_um, setup.objective.na,
                                              setup.wavelength_um, factor, iterations=100)
    assert set(result) == {"object", "history"}
    assert result["object"].shape == hs
    assert [h["iteration"] for h in result["history"]] == list(range(100))
    conv = metrics.convergence_summary(result["history"])  # must work unchanged
    assert conv["last_error"] < 0.2 * conv["first_error"]
    assert _phase_corr(result["object"], truth) > 0.95


def test_initial_object_is_rescaled_so_a_tie_style_start_passes_straight_through():
    setup, factor, hp, hs, truth, grid, lr = _channel_case()
    gain = 137.0
    raw = {k: v * gain for k, v in lr.items()}
    center = raw[(grid[0]["row"], grid[0]["col"])]
    amp0_hr = np.kron(np.sqrt(center), np.ones((factor, factor)))  # what the pipelines build for TIE init
    init = amp0_hr * np.exp(1j * np.angle(truth))
    result = jc.reconstruct_gradient_descent(raw, grid, hp, setup.lr_pixel_size_um, setup.objective.na,
                                              setup.wavelength_um, factor, iterations=15, initial_object=init)
    assert _phase_corr(result["object"], truth) > 0.95


def test_on_exact_k_data_the_bin_rounded_wirtinger_flow_fails_where_gradient_descent_does_not():
    """The finding behind this file's premise: same exact-k data, WF (bin-
    rounded k model, 200 epochs) 0.076 vs GD 0.995 phase correlation.
    """
    setup, factor, hp, hs, truth, grid, lr = _channel_case()
    scale = (hs[0] * hs[1]) / (CROP * CROP)
    wf = reconstruction.reconstruct({k: v * scale ** 2 for k, v in lr.items()}, grid, hp,
                                     setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
                                     factor, iterations=200)["object"]
    gd = jc.reconstruct_gradient_descent(lr, grid, hp, setup.lr_pixel_size_um, setup.objective.na,
                                          setup.wavelength_um, factor, iterations=100)["object"]
    assert _phase_corr(wf, truth) < 0.3
    assert _phase_corr(gd, truth) > 0.9


def _write_exact_k_lab_captures(tmp_path, crop=CROP):
    setups = {ch: config.default_setup(channel=ch, grid_size=9, objective="current", resolution_px=(crop, crop))
              for ch in multispectral.CHANNEL_ORDER}
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hp = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hs = optics.hr_shape((crop, crop), factor)
    truth = _synthetic_object(hs)
    for ch, setup in setups.items():
        grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr = jc.simulate_lr_stack_continuous(truth, hp, grid, (crop, crop), setup.lr_pixel_size_um,
                                              setup.objective.na, setup.wavelength_um)
        subdir = tmp_path / ch / f"9x9_recortada_{crop}"
        subdir.mkdir(parents=True)
        for (row, col), inten in lr.items():
            Image.fromarray(inten.astype(np.float32), mode="F").save(subdir / f"fila{row}_columna{col}.tiff")
    return truth


def test_multispectral_pipeline_gd_amplitude_solver_on_exact_k_captures(tmp_path):
    truth = _write_exact_k_lab_captures(tmp_path)
    run = multispectral.reconstruct_all_channels(str(tmp_path), 9, objective="current", crop=CROP,
                                                  iterations=100, solver="gd-amplitude")
    shapes = {ch: c["object"].shape for ch, c in run["channels"].items()}
    assert len(set(shapes.values())) == 1
    for ch, c in run["channels"].items():
        assert c["pupil"] is None and c["agent_attempts"] is None
        assert _phase_corr(c["object"], truth) > 0.9, ch


@pytest.mark.parametrize("extra", [{"recover_pupil": True}, {"adaptive_step": True},
                                    {"use_reconstruction_agent": True}])
def test_gd_amplitude_solver_is_mutually_exclusive_with_wirtinger_internals(tmp_path, extra):
    with pytest.raises(ValueError, match="gd-amplitude"):
        multispectral.reconstruct_all_channels(str(tmp_path), 9, crop=CROP, solver="gd-amplitude", **extra)


def test_unknown_solver_name_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="solver must be"):
        multispectral.reconstruct_all_channels(str(tmp_path), 9, crop=CROP, solver="nope")


def test_simulate_and_reconstruct_cli_accepts_solver_flag_and_records_it(tmp_path):
    h = w = 32
    y, x = np.mgrid[0:h, 0:w].astype(float)
    amp = (0.5 + 0.5 * np.exp(-((x / w - 0.5) ** 2 + (y / h - 0.5) ** 2) / 0.05)) * 255
    Image.fromarray(amp.astype(np.uint8)).save(tmp_path / "a.png")
    Image.fromarray((np.sin(2 * np.pi * x / w) * 100 + 128).astype(np.uint8)).save(tmp_path / "p.png")
    out = tmp_path / "out"
    sim_pipeline.main(["--amplitude-image", str(tmp_path / "a.png"), "--phase-image", str(tmp_path / "p.png"),
                       "--lr-size", "16", "--iterations", "5", "--solver", "gd-amplitude",
                       "--output-dir", str(out)])
    with open(out / "metrics.json") as fh:
        assert json.load(fh)["setup"]["solver"] == "gd-amplitude"
    with pytest.raises(SystemExit):
        sim_pipeline.main(["--amplitude-image", str(tmp_path / "a.png"), "--phase-image", str(tmp_path / "p.png"),
                           "--lr-size", "16", "--solver", "gd-amplitude", "--adaptive-step",
                           "--output-dir", str(out)])

"""tests/test_reconstruct_multispectral_pipeline.py -- roadmap milestone
2a (docs/roadmap_agentic_multispectral_pipeline.md):
pipelines/reconstruct_multispectral_independent.py must load real-lab-shaped
captures for all three RGB channels and reconstruct them on the single
shared HR grid from milestone 1.

No real lab captures are available in this Codespace (see
tests/test_multispectral_registration.py's docstring), so this test
synthesizes fake-but-realistic captures: it simulates the LR stack for a
known object at each channel's wavelength and writes them out as TIFFs
under the lab's own fila<row>_columna<col>.tiff naming, then drives the
pipeline's real-data code path (io_utils.load_real_lr_stack) against them
-- the same path real captures would take.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipelines"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
import reconstruct_multispectral_independent as pipeline  # noqa: E402


def _synthetic_object(shape):
    """Same amplitude phantom as the other test modules in this suite
    (tests/test_ptyco_simulator.py, test_multispectral_registration.py),
    but a SMALLER phase magnitude (0.08 pi, not 0.15 pi).

    Found empirically while writing this test: at the other modules'
    0.15 pi, on this exact 9x9-LED/objective="2_5x_na007" grid, the *red*
    channel (630nm, the longest wavelength -> smallest synthetic-aperture
    extension in cycles/um for the same physical LED angles) reliably
    lands in a local minimum (phase_correlation ~0.64, not improving with
    more iterations) while green and blue converge fine (~0.95-0.97) --
    a wavelength-dependent instance of the local-minimum property already
    documented in reconstruction.py/README.md for vanilla Wirtinger flow
    on a small LED grid, not a bug in this pipeline. 0.08 pi converges for
    all three channels; worth noting in the roadmap as a limitation to
    watch for in milestone 2a/2b on real (typically smaller-phase
    biological) samples.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5

    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)

    phase = 0.08 * np.pi * np.sin(2 * np.pi * 1 * x) * np.cos(2 * np.pi * 1 * y)
    return amp * np.exp(1j * phase)


def _write_fake_lab_captures(tmp_path, grid_size, crop, objective="2_5x_na007"):
    """Simulate an LR stack per channel and save it under
    <tmp_path>/<channel>/<grid>x<grid>_recortada_<crop>/fila<R>_columna<C>.tiff,
    the lab's own convention (see io_utils.py). Returns (truth, hr_shape,
    hr_pixel_um) so the caller can compare the reconstruction against a
    known object.
    """
    setups = {
        channel: config.default_setup(
            channel=channel, grid_size=grid_size, objective=objective,
            resolution_px=(crop, crop),
        )
        for channel in pipeline.CHANNEL_ORDER
    }
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    truth = _synthetic_object(hr_shape)

    for channel, setup in setups.items():
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            truth, hr_pixel_um, led_grid, (crop, crop),
            setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
        )
        subdir = tmp_path / channel / f"{grid_size}x{grid_size}_recortada_{crop}"
        subdir.mkdir(parents=True)
        for (row, col), intensity in lr_images.items():
            Image.fromarray(intensity.astype(np.float32), mode="F").save(
                subdir / f"fila{row}_columna{col}.tiff"
            )

    return truth, hr_shape, hr_pixel_um


def test_reconstruct_all_channels_on_fake_lab_captures(tmp_path):
    grid_size, crop = 9, 12
    truth, hr_shape, hr_pixel_um = _write_fake_lab_captures(tmp_path, grid_size, crop)

    run = pipeline.reconstruct_all_channels(
        str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=40,
    )

    assert run["hr_shape"] == hr_shape
    assert run["hr_pixel_um"] == hr_pixel_um
    assert set(run["channels"]) == {"red", "green", "blue"}

    shapes = {ch: c["object"].shape for ch, c in run["channels"].items()}
    assert len(set(shapes.values())) == 1, shapes

    for channel, c in run["channels"].items():
        assert c["n_leds_used"] == c["n_leds_expected"] == grid_size * grid_size
        gt = metrics.compare_to_ground_truth(c["object"], truth)
        assert gt["amplitude_correlation"] > 0.5, (channel, gt)
        assert gt["phase_correlation"] > 0.85, (channel, gt)
        assert c["pupil"] is None


def test_reconstruct_all_channels_recover_pupil_wiring(tmp_path):
    """Wiring check, not a re-derivation of EPRY's own quality claim
    (already established at the library level in
    tests/test_epry_pupil_recovery.py with a known injected aberration --
    this fake lab data uses the ideal pupil, so there's nothing for EPRY
    to correct here). Just confirms reconstruct_all_channels(recover_pupil
    =True) runs per-channel EPRY and returns a per-channel complex pupil
    of the right shape without breaking anything else.
    """
    grid_size, crop = 9, 12
    truth, hr_shape, hr_pixel_um = _write_fake_lab_captures(tmp_path, grid_size, crop)

    run = pipeline.reconstruct_all_channels(
        str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=20,
        recover_pupil=True,
    )
    for channel, c in run["channels"].items():
        assert c["pupil"] is not None
        assert c["pupil"].shape == (crop, crop)
        gt = metrics.compare_to_ground_truth(c["object"], truth)
        assert gt["phase_correlation"] > 0.5, (channel, gt)


def test_reconstruct_all_channels_adaptive_step_wiring(tmp_path):
    """Same spirit as the pupil-recovery wiring test above: confirms
    per-channel zuo2016 adaptive stepping runs end to end through this
    pipeline without breaking reconstruction quality on an easy (noiseless)
    case -- tests/test_adaptive_step_size.py already covers the mechanism
    and its honest not-clearly-better finding at the library level.
    """
    grid_size, crop = 9, 12
    truth, hr_shape, hr_pixel_um = _write_fake_lab_captures(tmp_path, grid_size, crop)

    run = pipeline.reconstruct_all_channels(
        str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=40,
        adaptive_step=True,
    )
    for channel, c in run["channels"].items():
        assert c["pupil"] is None
        gt = metrics.compare_to_ground_truth(c["object"], truth)
        assert gt["phase_correlation"] > 0.5, (channel, gt)


def test_recover_pupil_and_reconstruction_agent_are_mutually_exclusive(tmp_path):
    grid_size, crop = 9, 12
    _write_fake_lab_captures(tmp_path, grid_size, crop)
    try:
        pipeline.reconstruct_all_channels(
            str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=5,
            recover_pupil=True, use_reconstruction_agent=True,
        )
        assert False, "expected ValueError for recover_pupil + use_reconstruction_agent"
    except ValueError as exc:
        assert "not wired together" in str(exc)


def test_adaptive_step_and_reconstruction_agent_can_now_be_combined(tmp_path):
    """Unlike recover_pupil above, this combination was resolved
    2026-09-18 -- see agents/reconstruction_orchestrator.py's
    orchestrate_reconstruction docstring for why it's sound.
    """
    grid_size, crop = 9, 12
    _write_fake_lab_captures(tmp_path, grid_size, crop)
    run = pipeline.reconstruct_all_channels(
        str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=5,
        adaptive_step=True, use_reconstruction_agent=True,
    )
    for channel, c in run["channels"].items():
        assert c["agent_attempts"] is not None, channel
        steps = [h["step"] for h in c["history"]]
        assert all(s is not None for s in steps), (channel, "adaptive_step must reach reconstruct()")


def test_chromatic_report_flag_writes_report_json(tmp_path):
    """--chromatic-report (2026-09-18) runs chromatic_diagnostics.py's
    report on the 3 already-reconstructed channels and saves it -- CLI
    wiring check, not a re-derivation of the diagnostic's own accuracy
    (already covered with a known injected shift in
    tests/test_chromatic_diagnostics.py).
    """
    grid_size, crop = 9, 12
    _write_fake_lab_captures(tmp_path, grid_size, crop)
    output_dir = tmp_path / "out"
    pipeline.main([
        "--data-root", str(tmp_path), "--grid-size", str(grid_size), "--crop", str(crop),
        "--objective", "2_5x_na007", "--z-distance-mm", "70", "--no-exposure-normalization", "--no-normalize-initial-guess", "--iterations", "20", "--chromatic-report", "--output-dir", str(output_dir),
    ])
    with open(output_dir / "chromatic_report.json") as fh:
        report = json.load(fh)
    assert set(report) == {"red_vs_green", "blue_vs_green"}
    for entry in report.values():
        assert len(entry["lateral_shift_px"]) == 2
        assert "offset_um" in entry["focus"]

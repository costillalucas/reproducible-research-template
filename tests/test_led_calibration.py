"""tests/test_led_calibration.py -- roadmap milestone 4, "Agente #2"
(docs/roadmap_agentic_multispectral_pipeline.md):
src/ptyco_full_simulator/led_calibration.py's spectral-correlation LED
position correction, adapted from `eckert2018` (see that module's
docstring for exactly what was/wasn't implemented from the paper).

Three tests, three different jobs:
- `test_similarity_transform_fit_recovers_exact_transform_noiseless` is a
  pure-math sanity check of the closed-form fit itself, no FPM involved.
- `test_spectral_correlation_recovers_known_misalignment_given_good_object_estimate`
  proves the SC search + rigid-fit correctly identifies an injected LED
  misalignment WHEN GIVEN A GOOD OBJECT SPECTRUM -- the algorithm's core
  contribution, isolated from the reconstruction solver's own problems.
- `test_sc_only_calibration_without_bf_bootstrap_does_not_reliably_fix_reconstruction`
  is a NEGATIVE result, found while building this integration, not
  originally expected: bootstrapping calibration purely from a rough
  reconstruction under the WRONG (nominal) LED grid does not reliably
  work with only SC calibration -- see this test's docstring and
  docs/roadmap_agentic_multispectral_pipeline.md for why this matters
  (it's exactly why the paper's own brightfield pre-calibration stage
  exists, and why skipping it here -- a scope decision, not an oversight
  -- is a real, load-bearing limitation, not just a nice-to-have gap).
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, led_calibration as cal  # noqa: E402
from ptyco_full_simulator import metrics, optics, reconstruction  # noqa: E402


def _synthetic_object(shape):
    """Same phantom as tests/test_ptyco_simulator.py -- reused deliberately
    so any reconstruction-quality numbers here are comparable to that
    file's already-established baseline.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.15 * np.pi * np.sin(2 * np.pi * x) * np.cos(2 * np.pi * y)
    return amp * np.exp(1j * phase)


def test_similarity_transform_fit_recovers_exact_transform_noiseless():
    rng = np.random.default_rng(0)
    nominal = rng.uniform(-0.5, 0.5, (20, 2))

    scale, rotation_rad, shift = 1.03, 0.05, (0.02, -0.01)
    a = scale * np.exp(1j * rotation_rad)
    b = shift[0] + 1j * shift[1]
    z = nominal[:, 0] + 1j * nominal[:, 1]
    corrected = np.stack([(a * z + b).real, (a * z + b).imag], axis=1)

    fit = cal.fit_similarity_transform(nominal, corrected)
    assert fit["scale"] == pytest.approx(scale, abs=1e-9)
    assert fit["rotation_rad"] == pytest.approx(rotation_rad, abs=1e-9)
    assert fit["shift"][0] == pytest.approx(shift[0], abs=1e-9)
    assert fit["shift"][1] == pytest.approx(shift[1], abs=1e-9)

    round_trip = cal.apply_similarity_transform(nominal, fit)
    assert np.allclose(round_trip, corrected, atol=1e-9)


def _setup_and_grids(grid_size=9, crop=16):
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    delta_k = 1.0 / (hr_shape[1] * hr_pixel_um)
    nominal_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    return setup, factor, hr_pixel_um, hr_shape, delta_k, nominal_grid


def test_spectral_correlation_recovers_known_misalignment_given_good_object_estimate():
    crop = 16
    setup, factor, hr_pixel_um, hr_shape, delta_k, nominal_grid = _setup_and_grids(crop=crop)
    truth = _synthetic_object(hr_shape)

    true_shift, true_rotation, true_scale = (0.03, -0.02), 0.03, 1.02
    true_grid = cal.perturb_led_grid_rigid(nominal_grid, shift_fx=true_shift[0], shift_fy=true_shift[1],
                                            rotation_rad=true_rotation, scale=true_scale)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, true_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )

    # The object estimate a WORKING reconstruction (correct LED grid) would already have --
    # isolates the calibration math from the solver's own convergence problems, deliberately.
    obj_spectrum_true = np.fft.fftshift(np.fft.fft2(truth))

    calib = cal.calibrate_led_grid(nominal_grid, obj_spectrum_true, hr_pixel_um, lr_images,
                                    setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um, delta_k)
    fit = calib["transform"]

    assert fit["scale"] == pytest.approx(true_scale, abs=0.01)
    assert fit["rotation_rad"] == pytest.approx(true_rotation, abs=0.015)
    assert fit["shift"][0] == pytest.approx(true_shift[0], abs=0.01)
    assert fit["shift"][1] == pytest.approx(true_shift[1], abs=0.01)


def test_sc_only_calibration_without_bf_bootstrap_does_not_reliably_fix_reconstruction():
    """Found while building this integration, not expected going in: a
    SMALL misalignment (well within what real LED arrays plausibly have)
    already makes the nominal-grid reconstruction fail badly
    (phase_correlation goes negative -- worse than a random guess). SC
    calibration bootstrapped from THAT already-broken reconstruction
    cannot rescue it -- the object spectrum it's given to correlate
    against is too corrupted to identify the true LED positions from.

    This is not a bug in `spectral_correlation_correction` itself (see the
    test above, which proves the math works given a decent object
    estimate) -- it's a real limitation of skipping the paper's
    brightfield pre-calibration bootstrap stage (see this module's
    docstring). Documented here so a future BF-calibration implementation
    has a concrete before/after case to improve on, and so this limitation
    doesn't quietly regress into "calibration works fine" folklore.
    """
    crop = 16
    setup, factor, hr_pixel_um, hr_shape, delta_k, nominal_grid = _setup_and_grids(crop=crop)
    truth = _synthetic_object(hr_shape)

    small_shift, small_rotation, small_scale = (0.01, -0.005), 0.005, 1.005
    true_grid = cal.perturb_led_grid_rigid(nominal_grid, shift_fx=small_shift[0], shift_fy=small_shift[1],
                                            rotation_rad=small_rotation, scale=small_scale)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, true_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )

    rough = reconstruction.reconstruct(
        lr_images, nominal_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
    )
    gt_rough = metrics.compare_to_ground_truth(rough["object"], truth)
    assert gt_rough["phase_correlation"] < 0.3, (
        "this test's premise is that the nominal (miscalibrated) grid already reconstructs badly -- "
        f"got phase_correlation={gt_rough['phase_correlation']}, premise no longer holds, re-tune the "
        "injected misalignment magnitude"
    )

    obj_spectrum = np.fft.fftshift(np.fft.fft2(rough["object"]))
    calib = cal.calibrate_led_grid(nominal_grid, obj_spectrum, hr_pixel_um, lr_images,
                                    setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um, delta_k)

    corrected = reconstruction.reconstruct(
        lr_images, calib["led_grid"], hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
    )
    gt_corrected = metrics.compare_to_ground_truth(corrected["object"], truth)

    assert gt_corrected["phase_correlation"] < 0.3, (
        f"SC-only calibration unexpectedly rescued a badly-corrupted reconstruction "
        f"(phase_correlation={gt_corrected['phase_correlation']}) -- if this now reliably works, "
        "the limitation documented in this test and the roadmap may be stale, update both"
    )

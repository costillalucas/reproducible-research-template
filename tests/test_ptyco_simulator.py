import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, reconstruction  # noqa: E402


def _synthetic_object(shape):
    """Deterministic amplitude+phase phantom, no external image files
    needed -- a smooth blob (amplitude) crossed with an independent, low
    spatial-frequency grating (phase), so the two carry genuinely
    different information. Phase magnitude/frequency are kept modest
    (0.15 pi, 1 cycle) deliberately: vanilla incremental Wirtinger flow
    (no pupil/LED-position refinement yet, see references/bibliography.yaml
    `priority_focus`) is sensitive to non-convex local minima on a
    small (9x9 LED) synthetic aperture -- a much larger phase excursion or
    higher frequency reliably gets stuck short of the true object, which
    is a real property of this baseline algorithm, not a test bug.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5

    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)

    phase = 0.15 * np.pi * np.sin(2 * np.pi * 1 * x) * np.cos(2 * np.pi * 1 * y)
    return amp * np.exp(1j * phase)


def _small_setup(grid_size):
    return config.default_setup(
        channel="green", grid_size=grid_size, objective="2_5x_na007",
        resolution_px=(12, 12),
    )


def _simulate_and_reconstruct(grid_size, iterations=25, lr_size=12):
    setup = _small_setup(grid_size)
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((lr_size, lr_size), factor)

    truth = _synthetic_object(hr_shape)
    full_led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, full_led_grid, (lr_size, lr_size),
        setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
    )
    return setup, factor, hr_pixel_um, truth, full_led_grid, lr_images


def test_led_grid_center_is_on_axis():
    setup = _small_setup(grid_size=5)
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    center = grid[0]
    assert center["radial_mm"] == 0.0
    assert abs(center["fx"]) < 1e-12 and abs(center["fy"]) < 1e-12


def test_multi_led_reconstruction_recovers_amplitude_and_phase():
    setup, factor, hr_pixel_um, truth, led_grid, lr_images = _simulate_and_reconstruct(grid_size=9)

    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
    )

    conv = metrics.convergence_summary(result["history"])
    assert conv["relative_improvement"] > 0.9, conv

    gt = metrics.compare_to_ground_truth(result["object"], truth)
    assert gt["amplitude_correlation"] > 0.5, gt
    assert gt["phase_correlation"] > 0.85, gt


def test_single_led_negative_control_cannot_recover_phase():
    """A single on-axis LED gives one intensity image with no angular
    diversity -- classic phase retrieval is impossible from that alone.
    Reconstructing with only that LED, through the *identical* pipeline
    and metric as the passing multi-LED test above, must fail to recover
    phase -- proving the metric is capable of catching a bad reconstruction,
    not just praising a good one.
    """
    setup, factor, hr_pixel_um, truth, led_grid, lr_images = _simulate_and_reconstruct(grid_size=9)

    single_led = [led_grid[0]]  # the on-axis, zero-frequency-shift LED
    single_lr_images = {(single_led[0]["row"], single_led[0]["col"]):
                         lr_images[(single_led[0]["row"], single_led[0]["col"])]}

    result = reconstruction.reconstruct(
        single_lr_images, single_led, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
    )

    gt = metrics.compare_to_ground_truth(result["object"], truth)
    assert gt["phase_correlation"] < 0.3, (
        f"single-LED reconstruction should NOT recover phase, got correlation {gt['phase_correlation']}"
    )

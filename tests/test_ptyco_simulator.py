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
        channel="green", grid_size=grid_size, objective="current",
        resolution_px=(12, 12),
    )


def _aberrated_pupil(shape, pixel_size_um, na, wavelength_um, amplitude):
    """A circular NA support with a smooth low-order (defocus-like) phase
    aberration added on top, in radians at the pupil edge -- a stand-in
    for the un-modeled aberration EPRY (ou2014) is meant to recover.
    """
    support = optics.circular_pupil(shape, pixel_size_um, na, wavelength_um)
    h, w = shape
    fy = np.fft.fftshift(np.fft.fftfreq(h, d=pixel_size_um))
    fx = np.fft.fftshift(np.fft.fftfreq(w, d=pixel_size_um))
    FX, FY = np.meshgrid(fx, fy)
    cutoff = na / wavelength_um
    rho2 = (FX ** 2 + FY ** 2) / cutoff ** 2
    return support * np.exp(1j * amplitude * rho2)


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


def test_epry_pupil_update_improves_reconstruction_with_aberrated_pupil():
    """EPRY (Ou et al. 2014, references/bibliography.yaml id `ou2014`,
    `priority_focus` rank 1): when the *true* pupil carries an aberration
    the reconstruction's static circular pupil doesn't model, updating
    the pupil in-loop (reconstruction.reconstruct's `update_pupil=True`,
    the default) must recover the object at least as well as leaving the
    pupil static -- and, for an aberration strong enough that the static
    pupil visibly suffers, strictly better on both amplitude and phase.
    """
    grid_size = 9
    lr_size = 12
    setup = _small_setup(grid_size)
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((lr_size, lr_size), factor)

    truth = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    true_pupil = _aberrated_pupil((lr_size, lr_size), setup.lr_pixel_size_um,
                                   setup.objective.na, setup.wavelength_um,
                                   amplitude=1.5)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, led_grid, (lr_size, lr_size),
        setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
        pupil=true_pupil,
    )

    common = dict(
        lr_images=lr_images, led_grid=led_grid, hr_pixel_um=hr_pixel_um,
        lr_pixel_um=setup.lr_pixel_size_um, na=setup.objective.na,
        wavelength_um=setup.wavelength_um, factor=factor, iterations=40,
    )
    static = reconstruction.reconstruct(update_pupil=False, **common)
    epry = reconstruction.reconstruct(update_pupil=True, **common)

    gt_static = metrics.compare_to_ground_truth(static["object"], truth)
    gt_epry = metrics.compare_to_ground_truth(epry["object"], truth)

    assert gt_epry["amplitude_correlation"] >= gt_static["amplitude_correlation"], (
        gt_static, gt_epry)
    assert gt_epry["phase_correlation"] >= gt_static["phase_correlation"], (
        gt_static, gt_epry)
    assert gt_epry["amplitude_correlation"] > gt_static["amplitude_correlation"] + 0.02, (
        "EPRY pupil update should measurably beat a static pupil under a "
        f"real aberration, got static={gt_static} epry={gt_epry}"
    )
    assert gt_epry["phase_correlation"] > gt_static["phase_correlation"] + 0.02, (
        "EPRY pupil update should measurably beat a static pupil under a "
        f"real aberration, got static={gt_static} epry={gt_epry}"
    )


def test_epry_disabled_matches_static_pupil_baseline():
    """`update_pupil=False` must reproduce the original static-pupil
    Wirtinger flow exactly (this is the pre-EPRY behavior other tests
    and pipelines already rely on) -- adding EPRY must not change
    reconstruct()'s output when it's turned off.
    """
    setup, factor, hr_pixel_um, truth, led_grid, lr_images = _simulate_and_reconstruct(grid_size=9)

    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
        update_pupil=False,
    )

    gt = metrics.compare_to_ground_truth(result["object"], truth)
    assert gt["amplitude_correlation"] > 0.5, gt
    assert gt["phase_correlation"] > 0.85, gt
    np.testing.assert_array_equal(
        result["pupil"],
        optics.circular_pupil((12, 12), setup.lr_pixel_size_um,
                               setup.objective.na, setup.wavelength_um),
    )

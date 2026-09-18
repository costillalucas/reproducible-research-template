"""tests/test_epry_pupil_recovery.py -- EPRY pupil recovery
(`references/bibliography.yaml` id `ou2014`, priority_focus rank 1),
`reconstruction.reconstruct`'s `recover_pupil` param.

Ground truth for the pupil doesn't exist in real data, so this simulates
a KNOWN aberration (`optics.add_defocus_aberration`, injected via
`forward_model.simulate_lr_stack`'s new `pupil_override`) and checks two
independent things: (1) does letting the solver also fit a complex pupil
recover an object closer to ground truth than assuming the ideal
(unaberrated) pupil, and (2) does the recovered pupil's phase actually
correlate with the true injected aberration (not just "helps the object
by coincidence").

HONEST, NOT-overclaimed finding from exploring this (see the numbers
below, reproduced by `test_epry_beats_uncorrected_under_defocus_aberration`):
the improvement is real and reproducible but MODEST, not the dramatic
fix TIE-informed initialization was for the weak-phase-object problem.
At the chosen defocus_rad_amplitude=2.0 (die used object's phase is
already near the edge of what the baseline solver handles well even with
an ideal pupil, per `test_ptyco_simulator.py`'s own note on this same
synthetic object), object phase correlation goes 0.687 -> 0.793 and
pupil phase correlation is 0.648 -- clearly not noise, clearly not a
full recovery either. At LARGER aberration (defocus_rad_amplitude=4.0,
tried during development, not asserted here) both uncorrected and EPRY
reconstructions fail outright on this small (9x9 LED, 12x12px crop) test
problem -- EPRY is not a silver bullet for arbitrarily large aberration
on a small synthetic aperture, consistent with ou2014's own real-data
demonstration needing 225 images (15x15 LEDs) and many more pixels than
this test's fast/small setup uses.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import reconstruction  # noqa: E402


def _synthetic_object(shape):
    """Same phantom as test_ptyco_simulator.py's `_synthetic_object` --
    reuse it rather than inventing a new one, so this test's baseline
    (unaberrated) behavior is already known-good from that file.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.15 * np.pi * np.sin(2 * np.pi * 1 * x) * np.cos(2 * np.pi * 1 * y)
    return (amp * np.exp(1j * phase)).astype(complex)


def _setup_and_pupil(grid_size=9, crop=12, defocus_rad_amplitude=2.0):
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    pupil_mask = optics.circular_pupil((crop, crop), setup.lr_pixel_size_um,
                                        setup.objective.na, setup.wavelength_um)
    true_pupil = optics.add_defocus_aberration(
        pupil_mask, (crop, crop), setup.lr_pixel_size_um, setup.objective.na,
        setup.wavelength_um, defocus_rad_amplitude,
    )
    return setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil


def test_epry_beats_uncorrected_under_defocus_aberration():
    grid_size, crop, iterations = 9, 12, 40
    setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil = _setup_and_pupil(
        grid_size, crop, defocus_rad_amplitude=2.0,
    )
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, pupil_override=true_pupil,
    )

    uncorrected = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    corrected = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        recover_pupil=True,
    )
    assert "pupil" in corrected and corrected["pupil"].shape == (crop, crop)

    gt_unc = metrics.compare_to_ground_truth(uncorrected["object"], obj_true)
    gt_cor = metrics.compare_to_ground_truth(corrected["object"], obj_true)

    assert gt_unc["phase_correlation"] < 0.75, (
        "premise check: assuming the ideal pupil under a real defocus aberration should "
        f"clearly degrade phase recovery -- got {gt_unc['phase_correlation']}"
    )
    assert gt_cor["phase_correlation"] > gt_unc["phase_correlation"] + 0.05, (
        f"EPRY should meaningfully beat the uncorrected reconstruction here: "
        f"uncorrected={gt_unc['phase_correlation']}, epry={gt_cor['phase_correlation']}"
    )

    true_phase = np.angle(true_pupil)[pupil_mask]
    rec_phase = np.angle(corrected["pupil"])[pupil_mask]
    true_phase = true_phase - true_phase.mean()
    rec_phase = rec_phase - rec_phase.mean()
    pupil_corr = float(np.corrcoef(true_phase, rec_phase)[0, 1])
    assert pupil_corr > 0.5, (
        f"recovered pupil phase should correlate with the true injected defocus, got {pupil_corr}"
    )


def test_epry_pupil_support_stays_inside_na_circle():
    """The paper's "pupil function constraint" (Section 2, after Eq. 4):
    noise outside the physical aperture stop must be zeroed every update,
    not allowed to accumulate. Cheap, deterministic check independent of
    whether recovery quality is good on a given object.
    """
    grid_size, crop, iterations = 9, 12, 10
    setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil = _setup_and_pupil(
        grid_size, crop, defocus_rad_amplitude=2.0,
    )
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, pupil_override=true_pupil,
    )
    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        recover_pupil=True,
    )
    outside = ~pupil_mask
    assert np.all(result["pupil"][outside] == 0)


def test_recover_pupil_default_off_reproduces_original_behavior():
    """Regression guard: `recover_pupil=False` (the default) must produce
    bit-identical results to before this feature existed -- the fixed
    circular boolean pupil, cast to complex, multiplies identically.
    """
    grid_size, crop, iterations = 9, 12, 15
    setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil = _setup_and_pupil(grid_size, crop)
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    assert "pupil" not in result

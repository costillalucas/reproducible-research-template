"""tests/test_brightfield_calibration.py -- roadmap milestone 4:
brightfield (BF) pre-calibration bootstrap
(src/ptyco_full_simulator/led_calibration.py's `find_circle_center` /
`brightfield_calibration`), added after `calibrate_led_grid` (SC-only
calibration) was found unable to bootstrap from a badly-miscalibrated
reconstruction (see tests/test_led_calibration.py's documented negative
result) -- BF calibration works directly on raw LR images, with no object
estimate needed, so it doesn't have that chicken-and-egg problem.

Two findings, two different confidence levels -- read both, don't just
skim the first:

- `test_mean_spectrum_normalization_is_necessary_for_correct_circle_detection`
  is a SOLID, reproducible finding: without dividing out the mean
  spectrum (Eckert et al. 2018 Algorithm 1 line 1), circle detection is
  reliably biased toward the edge of the search box, dominated by the
  generic 1/f-like falloff of natural image spectra rather than the
  actual pupil-edge circle -- normalizing fixes this specific failure
  mode.
- `test_brightfield_calibration_precision_with_sparse_leds_is_a_real_open_problem`
  is an HONEST NEGATIVE finding, not a solved problem: with this lab's
  actual optics (see `references/bibliography.yaml`'s note on
  `eckert2018`'s own Fig. 4d -- a low-NA objective gives few brightfield
  LEDs), only ~5 brightfield LEDs are available even with the "future"
  objective (1 with "current"), and the similarity-transform fit from so
  few, geometrically clustered points is NOT reliable enough in this
  project's simplified implementation to consistently improve
  reconstruction quality -- sometimes it makes things WORSE than doing
  nothing. This is NOT claimed as fixed; see
  docs/roadmap_agentic_multispectral_pipeline.md for the honest status.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, led_calibration as cal  # noqa: E402
from ptyco_full_simulator import metrics, optics, reconstruction  # noqa: E402


def _amplitude_blob(shape):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    return np.clip(amp, 0, 1)


def _future_setup_with_misalignment(grid_size=9, crop=32, shift=(0.02, -0.015),
                                     rotation_rad=0.02, scale=1.01):
    """objective="2x_na010" (NA=0.10) is used deliberately, not "current"
    (NA=0.07): with this lab's geometry (LEDArrayConfig pitch=6mm,
    z_distance=70mm), "current" has only ONE brightfield LED (the on-axis
    one alone) -- not enough points to fit a transform at all. "future"
    has 5, still sparse but usable.
    """
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="2x_na010",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    truth = _amplitude_blob(hr_shape) * np.exp(
        1j * 0.15 * np.pi * np.sin(2 * np.pi * np.linspace(-0.5, 0.5, hr_shape[1]))[None, :]
        * np.cos(2 * np.pi * np.linspace(-0.5, 0.5, hr_shape[0]))[:, None]
    )
    nominal_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    true_grid = cal.perturb_led_grid_rigid(nominal_grid, shift_fx=shift[0], shift_fy=shift[1],
                                            rotation_rad=rotation_rad, scale=scale)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, true_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    return setup, factor, hr_pixel_um, hr_shape, nominal_grid, lr_images, truth


def test_mean_spectrum_normalization_is_necessary_for_correct_circle_detection():
    setup, factor, hr_pixel_um, hr_shape, nominal_grid, lr_images, truth = \
        _future_setup_with_misalignment(shift=(0.0, 0.0), rotation_rad=0.0, scale=1.0)  # no misalignment here

    bf_entries = [e for e in nominal_grid if (e["row"], e["col"]) in lr_images
                  and np.hypot(e["fx"], e["fy"]) * setup.wavelength_um < setup.objective.na]
    assert len(bf_entries) >= 3, "test needs at least 3 brightfield LEDs to be meaningful"
    center = bf_entries[0]
    key = (center["row"], center["col"])

    # WITHOUT normalization: biased toward the edge of the search box (large offset).
    unnormalized = cal.find_circle_center(lr_images[key], setup.lr_pixel_size_um, setup.objective.na,
                                           setup.wavelength_um, center["fx"], center["fy"],
                                           search_radius_px=3.0, search_step_px=0.5)
    unnorm_offset_px = abs(unnormalized["fx"] - center["fx"]) + abs(unnormalized["fy"] - center["fy"])

    # WITH normalization: much closer to the (here, correct/unperturbed) nominal position,
    # since there's no injected misalignment in this test -- the true answer IS the nominal one.
    mean_spectrum = cal.mean_spectrum_magnitude(lr_images, [(e["row"], e["col"]) for e in bf_entries])
    normalized = cal.find_circle_center(lr_images[key], setup.lr_pixel_size_um, setup.objective.na,
                                         setup.wavelength_um, center["fx"], center["fy"],
                                         search_radius_px=3.0, search_step_px=0.5,
                                         normalize_by=mean_spectrum)
    norm_offset_px = abs(normalized["fx"] - center["fx"]) + abs(normalized["fy"] - center["fy"])

    assert norm_offset_px < unnorm_offset_px, (
        f"normalization should land closer to the (here, known-correct) center -- "
        f"got normalized_offset={norm_offset_px}, unnormalized_offset={unnorm_offset_px}"
    )


def test_brightfield_calibration_precision_with_sparse_leds_is_a_real_open_problem():
    """Honest negative result, NOT a regression test for a fixed bug:
    with only 5 sparse brightfield LEDs (this project's actual optics,
    see module docstring), running BF calibration on a small, realistic
    misalignment does NOT reliably improve reconstruction quality over
    doing nothing -- documented here so a future session doesn't assume
    `brightfield_calibration` is production-ready and skip checking.
    """
    grid_size, crop, iterations = 9, 16, 40
    setup, factor, hr_pixel_um, hr_shape, nominal_grid, lr_images, truth = \
        _future_setup_with_misalignment(grid_size=grid_size, crop=crop,
                                         shift=(0.01, -0.005), rotation_rad=0.005, scale=1.005)

    result_nominal = reconstruction.reconstruct(
        lr_images, nominal_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    gt_nominal = metrics.compare_to_ground_truth(result_nominal["object"], truth)

    bf = cal.brightfield_calibration(lr_images, nominal_grid, setup.lr_pixel_size_um,
                                      setup.objective.na, setup.wavelength_um)
    result_bf = reconstruction.reconstruct(
        lr_images, bf["led_grid"], hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    gt_bf = metrics.compare_to_ground_truth(result_bf["object"], truth)

    # Deliberately NOT asserting gt_bf > gt_nominal -- see this test's docstring, that is NOT
    # reliably true with this few brightfield LEDs. Only sanity-check the plumbing: finite
    # output of the right shape, so a real crash/NaN regression still gets caught.
    print(f"nominal phase_correlation={gt_nominal['phase_correlation']:.3f}  "
          f"BF-calibrated phase_correlation={gt_bf['phase_correlation']:.3f}")
    assert result_bf["object"].shape == result_nominal["object"].shape
    assert np.all(np.isfinite(result_bf["object"]))
    assert np.isfinite(gt_bf["phase_correlation"])

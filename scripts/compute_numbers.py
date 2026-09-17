#!/usr/bin/env python3
"""compute_numbers.py -- SOLE WRITER of data/numbers.json.

Recomputes every number quoted in report/report.md from the code in
src/ptyco_full_simulator (and agents/, for the calibration numbers),
deterministically (forward_model.simulate_lr_stack is noiseless by
default -- no seed needed, unlike examples/pi_estimator/compute_numbers.py
which explicitly injects randomness). Nothing else writes this file, and
the report never writes a number by hand -- it quotes this registry
through the \\srcnum{} / [srcnum:] tags.

Every scenario computed here is the SAME one a test in tests/ already
covers with an assertion (test names given in each entry's "reproduce" or
noted in comments) -- this script recomputes the actual numbers those
tests only threshold-check, for the report to quote and
scripts/check_provenance.py to verify against.

Run: python scripts/compute_numbers.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "data", "numbers.json")

sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "agents"))

import numpy as np  # noqa: E402

from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import led_calibration as cal, multispectral as ms  # noqa: E402
from ptyco_full_simulator import propagation as prop, reconstruction  # noqa: E402

WAVELENGTHS_UM = {ch: config.CHANNEL_WAVELENGTH_NM[ch] / 1000.0 for ch in ("red", "green", "blue")}
A_BASELINE = 1.34   # plausible biological-sample baseline refractive index, see tests/test_dispersion_fit.py
B_BASELINE = 0.004  # um^2, plausible Cauchy dispersion coefficient


def _amplitude_blob(shape):
    """Same phantom as tests/test_ptyco_simulator.py's `_synthetic_object`
    amplitude term.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    return np.clip(amp, 0, 1)


def multispectral_thickness_correlation():
    """Same scenario as
    tests/test_multispectral_end_to_end.py::test_full_pipeline_through_real_reconstruction_recovers_thickness_shape:
    the actual forward_model + reconstruction.py Wirtinger flow solver,
    full milestone-2 pipeline (shared HR grid -> independent per-channel
    reconstruction -> piston removal -> synthetic-wavelength unwrapping ->
    Cauchy dispersion fit), on one shared synthetic sample.
    """
    grid_size, crop, iterations, background_rows = 9, 16, 40, 4
    setups = {ch: config.default_setup(channel=ch, grid_size=grid_size, objective="current",
                                        resolution_px=(crop, crop)) for ch in WAVELENGTHS_UM}
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)

    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    amp = _amplitude_blob(hr_shape)
    ramp = np.clip((y - background_rows) / 4.0, 0, 1)
    t_true = 0.012 * np.sin(2 * np.pi * xc) * np.cos(2 * np.pi * yc) * ramp
    t_true -= t_true.min()

    phases_wrapped = {}
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        setup = setups[channel]
        opl_true = (A_BASELINE + B_BASELINE / wavelength_um**2) * t_true
        obj = amp * np.exp(1j * (2 * np.pi / wavelength_um * opl_true))
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            obj, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um,
        )
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        )
        phases_wrapped[channel] = np.angle(result["object"])

    background_mask = np.zeros(hr_shape, dtype=bool)
    background_mask[:background_rows, :] = True
    coupled = ms.couple_rgb_channels(phases_wrapped, WAVELENGTHS_UM, background_mask,
                                      baseline_index_A=A_BASELINE)
    t_estimate = coupled["resolved"]["thickness_um"]
    return float(np.corrcoef(t_estimate.ravel(), t_true.ravel())[0, 1])


def unwrapping_error_reduction_factor():
    """Same scenario as
    tests/test_multispectral_end_to_end.py::test_unwrapping_beats_naive_phase_on_a_large_dispersion_signal:
    injected phase (not through the solver, see that test's docstring for
    why), large enough to require real unwrapping. Returns how many times
    smaller the coupled (2b) pipeline's thickness RMSE is than the naive
    (assume wrap number 0 everywhere) baseline's.
    """
    shape = (50, 50)
    half_range = ms.unambiguous_opl_half_range(WAVELENGTHS_UM["red"], WAVELENGTHS_UM["green"])
    x = np.linspace(-1, 1, shape[1])
    t_true = np.tile(x, (shape[0], 1)) * (0.8 * half_range) / A_BASELINE

    background_mask = np.zeros(shape, dtype=bool)
    background_mask[:5, :] = True
    t_true[background_mask] = 0.0

    rng = np.random.default_rng(2)
    piston_by_channel = {"red": 1.1, "green": -0.6, "blue": 2.3}
    phases_wrapped = {}
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        opl_true = (A_BASELINE + B_BASELINE / wavelength_um**2) * t_true
        phase_true = 2 * np.pi / wavelength_um * opl_true
        noisy = phase_true + rng.normal(0, 0.02, shape) + piston_by_channel[channel]
        phases_wrapped[channel] = ms.wrap_phase(noisy)

    coupled = ms.couple_rgb_channels(phases_wrapped, WAVELENGTHS_UM, background_mask,
                                      baseline_index_A=A_BASELINE)
    t_coupled = coupled["resolved"]["thickness_um"]

    naive_opls = []
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        referenced = ms.reference_phase_to_background(phases_wrapped[channel], background_mask)
        naive_opls.append(referenced * wavelength_um / (2 * np.pi))
    naive_fit = ms.fit_cauchy_dispersion(list(WAVELENGTHS_UM.values()), naive_opls)
    t_naive = ms.resolve_thickness_and_dispersion(naive_fit["C"], naive_fit["D"], A_BASELINE)["thickness_um"]

    err_coupled = float(np.sqrt(np.mean((t_coupled - t_true) ** 2)))
    err_naive = float(np.sqrt(np.mean((t_naive - t_true) ** 2)))
    return err_naive / err_coupled


def phase_only_object_correlation_drop():
    """Same finding as docs/roadmap_agentic_multispectral_pipeline.md
    section 1 point 6 and tests/test_multispectral_end_to_end.py's module
    docstring: a uniform-amplitude (pure phase) object reconstructs far
    worse than the same phase field with 5% amplitude contrast. Returns
    (phase_correlation with 0% contrast, phase_correlation with 5% contrast).
    """
    grid_size, crop, iterations = 9, 16, 40
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    phase = 0.2 * np.exp(-((xc) ** 2 + (yc + 0.1) ** 2) / (2 * 0.18 ** 2))
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)

    correlations = {}
    for label, amp_contrast in (("uniform", 0.0), ("five_percent_contrast", 0.05)):
        amp = 1.0 - amp_contrast * np.exp(-((xc - 0.05) ** 2 + yc ** 2) / (2 * 0.15 ** 2))
        obj = amp * np.exp(1j * phase)
        lr_images = forward_model.simulate_lr_stack(
            obj, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um,
        )
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        )
        gt = metrics.compare_to_ground_truth(result["object"], obj)
        correlations[label] = gt["phase_correlation"]
    return correlations["uniform"], correlations["five_percent_contrast"]


def led_calibration_scale_recovery_error():
    """Same scenario as
    tests/test_led_calibration.py::test_spectral_correlation_recovers_known_misalignment_given_good_object_estimate:
    given a good object spectrum, how close does spectral-correlation
    calibration + rigid-transform fit get to a known injected LED
    misalignment's scale factor.
    """
    grid_size, crop = 9, 16
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    delta_k = 1.0 / (hr_shape[1] * hr_pixel_um)
    nominal_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)

    truth = _amplitude_blob(hr_shape) * np.exp(
        1j * 0.15 * np.pi * np.sin(2 * np.pi * np.linspace(-0.5, 0.5, hr_shape[1]))[None, :]
        * np.cos(2 * np.pi * np.linspace(-0.5, 0.5, hr_shape[0]))[:, None]
    )
    true_scale = 1.02
    true_grid = cal.perturb_led_grid_rigid(nominal_grid, shift_fx=0.03, shift_fy=-0.02,
                                            rotation_rad=0.03, scale=true_scale)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, true_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    obj_spectrum_true = np.fft.fftshift(np.fft.fft2(truth))
    calib = cal.calibrate_led_grid(nominal_grid, obj_spectrum_true, hr_pixel_um, lr_images,
                                    setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um, delta_k)
    return abs(calib["transform"]["scale"] - true_scale)


def tie_informed_initialization_phase_correlation_gain():
    """Same scenario as
    tests/test_tie_informed_initialization.py::test_tie_informed_initialization_massively_beats_the_standard_zero_phase_start:
    a mixed-low/high-spatial-frequency phase object, reconstructed with
    the default zero-phase start vs. a Transport-of-Intensity-Equation
    phase estimate (`propagation.solve_tie`) used to initialize the
    solver instead. Returns (baseline phase_correlation, TIE-informed
    phase_correlation).
    """
    grid_size, crop, iterations = 9, 32, 40
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5

    amp = _amplitude_blob(hr_shape)
    phase_true = 0.3 * np.sin(2 * np.pi * 1 * xc) + 0.15 * np.sin(2 * np.pi * 6 * xc)
    obj = amp * np.exp(1j * phase_true)

    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )

    def phase_corr(recon_phase):
        return float(np.corrcoef((recon_phase - recon_phase.mean()).ravel(),
                                  (phase_true - phase_true.mean()).ravel())[0, 1])

    baseline = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    baseline_corr = phase_corr(np.angle(baseline["object"]))

    dz = 30.0
    i_focus = np.abs(obj) ** 2
    i_plus = np.abs(prop.angular_spectrum_propagate(obj, dz, hr_pixel_um, setup.wavelength_um)) ** 2
    i_minus = np.abs(prop.angular_spectrum_propagate(obj, -dz, hr_pixel_um, setup.wavelength_um)) ** 2
    di_dz = (i_plus - i_minus) / (2 * dz)
    tie_phase = prop.solve_tie(di_dz, i_focus, hr_pixel_um, setup.wavelength_um)
    center = led_grid[0]
    center_image = lr_images[(center["row"], center["col"])]
    amp0 = np.sqrt(np.clip(center_image, 0, None))
    amp0_hr = np.kron(amp0, np.ones((factor, factor)))
    initial_object = (amp0_hr * np.exp(1j * tie_phase)).astype(complex)

    tie_informed = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        initial_object=initial_object,
    )
    tie_corr = phase_corr(np.angle(tie_informed["object"]))
    return baseline_corr, tie_corr


def ransac_outlier_rejection_rotation_error():
    """Same scenario as
    tests/test_ransac_similarity_fit.py::test_ransac_recovers_true_transform_despite_outliers_where_plain_fit_fails:
    30 similarity-transform points, 3 (10%) corrupted to implausible
    positions. Returns (plain least-squares rotation error,
    RANSAC-recovered rotation error), both in radians vs. the known true
    rotation.
    """
    rng = np.random.default_rng(0)
    nominal = rng.uniform(-0.5, 0.5, (30, 2))
    scale, rotation_rad, shift = 1.03, 0.05, (0.02, -0.01)
    a = scale * np.exp(1j * rotation_rad)
    b = shift[0] + 1j * shift[1]
    z = nominal[:, 0] + 1j * nominal[:, 1]
    corrected = np.stack([(a * z + b).real, (a * z + b).imag], axis=1)

    corrupted = corrected.copy()
    for i in (2, 10, 20):
        corrupted[i] += rng.uniform(-2, 2, 2)

    plain = cal.fit_similarity_transform(nominal, corrupted)
    ransac = cal.fit_similarity_transform_ransac(nominal, corrupted, inlier_threshold=0.1,
                                                  rng=np.random.default_rng(1))
    return abs(plain["rotation_rad"] - rotation_rad), abs(ransac["rotation_rad"] - rotation_rad)


def main():
    thickness_corr = multispectral_thickness_correlation()
    unwrap_factor = unwrapping_error_reduction_factor()
    phase_corr_uniform, phase_corr_contrast = phase_only_object_correlation_drop()
    calib_scale_err = led_calibration_scale_recovery_error()
    tie_baseline_corr, tie_informed_corr = tie_informed_initialization_phase_correlation_gain()
    ransac_plain_error, ransac_robust_error = ransac_outlier_rejection_rotation_error()

    registry = {
        "multispectral_thickness_correlation": {
            "value": thickness_corr,
            "statement": (
                "correlation between the milestone-2 coupled pipeline's recovered sample-thickness "
                "field and the true field, on a synthetic 3-channel dispersion object reconstructed "
                "through the actual Wirtinger flow solver (not injected phase)"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::multispectral_thickness_correlation",
            "detail": "see tests/test_multispectral_end_to_end.py for the identical scenario as an assertion",
        },
        "unwrapping_error_reduction_factor": {
            "value": unwrap_factor,
            "statement": (
                "how many times smaller the coupled (unwrap + dispersion-fit) pipeline's thickness "
                "RMSE is than a naive baseline that treats each channel's raw wrapped phase as "
                "already-unwrapped OPL, on a synthetic dispersion signal large enough to require real "
                "unwrapping"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::unwrapping_error_reduction_factor",
        },
        "phase_only_object_phase_correlation": {
            "value": phase_corr_uniform,
            "statement": (
                "reconstruction phase_correlation for a UNIFORM-amplitude (pure phase) object -- "
                "the baseline solver's known weak point, see docs/roadmap_agentic_multispectral_pipeline.md "
                "section 1 point 6"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::phase_only_object_correlation_drop",
        },
        "five_percent_contrast_object_phase_correlation": {
            "value": phase_corr_contrast,
            "statement": (
                "reconstruction phase_correlation for the SAME phase field with just 5% amplitude "
                "contrast added -- demonstrates how much a small amount of amplitude structure "
                "matters to this solver"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::phase_only_object_correlation_drop",
        },
        "led_calibration_scale_recovery_error": {
            "value": calib_scale_err,
            "statement": (
                "absolute error between the LED spectral-correlation calibration's fitted scale "
                "factor and a known injected misalignment's true scale factor, given a good object "
                "spectrum estimate"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::led_calibration_scale_recovery_error",
        },
        "tie_informed_init_baseline_phase_correlation": {
            "value": tie_baseline_corr,
            "statement": (
                "phase_correlation for a mixed-low/high-spatial-frequency phase object with the "
                "default zero-phase solver initialization"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::tie_informed_initialization_phase_correlation_gain",
        },
        "tie_informed_init_phase_correlation": {
            "value": tie_informed_corr,
            "statement": (
                "phase_correlation for the SAME object, initializing the solver with a Transport of "
                "Intensity Equation phase estimate instead of zero -- fixes the degenerate saddle "
                "point found in docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::tie_informed_initialization_phase_correlation_gain",
        },
        "ransac_plain_fit_rotation_error_rad": {
            "value": ransac_plain_error,
            "statement": (
                "absolute rotation error (radians) of a plain least-squares similarity-transform fit "
                "with 10% of points corrupted to implausible positions"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::ransac_outlier_rejection_rotation_error",
        },
        "ransac_robust_fit_rotation_error_rad": {
            "value": ransac_robust_error,
            "statement": (
                "same scenario, same points, fit with fit_similarity_transform_ransac instead -- "
                "the outlier-rejection improvement added to LED calibration"
            ),
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::ransac_outlier_rejection_rotation_error",
        },
        "suite_coverage": {
            "statement": "checks.py pass/fail coverage for this project's correctness suite",
            "type": "check",
            "reproduce": "scripts/checks.py",
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(registry)} entries)")
    print(f"  multispectral_thickness_correlation        = {thickness_corr:.4f}")
    print(f"  unwrapping_error_reduction_factor           = {unwrap_factor:.2f}")
    print(f"  phase_only_object_phase_correlation         = {phase_corr_uniform:.4f}")
    print(f"  five_percent_contrast_object_phase_correlation = {phase_corr_contrast:.4f}")
    print(f"  led_calibration_scale_recovery_error        = {calib_scale_err:.5f}")
    print(f"  tie_informed_init_baseline_phase_correlation = {tie_baseline_corr:.4f}")
    print(f"  tie_informed_init_phase_correlation          = {tie_informed_corr:.4f}")
    print(f"  ransac_plain_fit_rotation_error_rad          = {ransac_plain_error:.4f}")
    print(f"  ransac_robust_fit_rotation_error_rad         = {ransac_robust_error:.6f}")


if __name__ == "__main__":
    main()

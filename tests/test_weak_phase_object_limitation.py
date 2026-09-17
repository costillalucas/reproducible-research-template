"""tests/test_weak_phase_object_limitation.py -- root-cause characterization
of the weak/low-spatial-frequency phase object limitation flagged in
docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6.

Found through direct experimentation (not from a paper first -- confirmed
against one afterward, see below): the standard reconstruction
initialization (`reconstruction.initial_hr_guess`: the on-axis LED's own
amplitude, zero phase) places the solver at or near a DEGENERATE SADDLE
POINT of the loss landscape for a weak/low-spatial-frequency phase
object -- not a "too little information" problem in general, a specific,
literature-confirmed FPM blind spot:

    Rogalski et al. 2025, "FPM aided with Transport of Intensity Equation"
    (references/bibliography.yaml id `rogalski2025`, already in the
    curated bibliography, previously not flagged as applicable):
    "FPM remains fundamentally limited in retrieving low spatial frequency
    phase information due to the absence of phase encoding in all on-axis
    and slightly-off-axis (brightfield) illumination angles."

This project's own empirical finding matches that exactly and adds
something the paper's abstract doesn't spell out: near the TRUE solution,
the loss landscape is well-behaved (small perturbations converge back
toward truth, see the passing test below) -- the problem is specifically
that the standard initialization starts AT the degenerate point, not that
the whole optimization is hopeless. This rules out one tempting cheap
fix, tested here: since `reconstruction.reconstruct`'s own internal
`recovery_error` (data-fit residual) does NOT correlate with true
reconstruction accuracy for a weak-phase object (a genuinely surprising,
important negative result -- the amplitude/intensity measurements are
nearly phase-insensitive here, so a low residual does not mean a correct
phase), a "multi-restart, keep the lowest recovery_error" strategy
(the kind of thing `agents/reconstruction_orchestrator.py`'s agent could
naturally do) WOULD NOT WORK for this specific failure mode. A real fix
needs new information the current forward model doesn't have -- e.g.
Rogalski et al.'s extra defocused on-axis image + Transport of Intensity
Equation, not implemented here (a good next-session candidate).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import reconstruction  # noqa: E402
from ptyco_full_simulator.optics import circular_pupil  # noqa: E402
from ptyco_full_simulator.spectral_ops import led_crop_window  # noqa: E402


def _weak_phase_setup(grid_size=9, crop=16):
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    phase = 0.2 * np.exp(-(xc ** 2 + (yc + 0.1) ** 2) / (2 * 0.18 ** 2))  # low spatial frequency, weak
    obj = np.ones(hr_shape) * np.exp(1j * phase)  # uniform amplitude -- pure phase object
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    return setup, factor, hr_pixel_um, hr_shape, led_grid, lr_images, obj


def _reconstruct_from(obj0, setup, factor, hr_pixel_um, led_grid, lr_images,
                       iterations=40, step_max=20.0, step_alpha=0.3):
    """A copy of reconstruction.reconstruct's inner loop that accepts an
    arbitrary starting complex field `obj0`, for testing initialization
    sensitivity -- the public `reconstruct()` always starts from
    `initial_hr_guess`, which is exactly the thing under test here.
    """
    lr_shape = next(iter(lr_images.values())).shape
    used_leds = [e for e in led_grid if (e["row"], e["col"]) in lr_images]
    pupil = circular_pupil(lr_shape, setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um)
    obj_spectrum = np.fft.fftshift(np.fft.fft2(obj0))
    lr_n_px = lr_shape[0] * lr_shape[1]

    for it in range(iterations):
        step = step_max * (1.0 - np.exp(-step_alpha * it))
        sq_err_sum = 0.0
        for entry in used_leds:
            key = (entry["row"], entry["col"])
            ys, xs = led_crop_window(obj0.shape, hr_pixel_um, lr_shape, entry["fx"], entry["fy"])
            patch = obj_spectrum[ys, xs] * pupil
            est_field = np.fft.ifft2(np.fft.ifftshift(patch))
            est_amp = np.abs(est_field)
            meas_amp = np.sqrt(np.clip(lr_images[key], 0, None))
            residual = est_amp - meas_amp
            sq_err_sum += float(np.sum(residual ** 2))
            safe_amp = np.where(est_amp > 1e-12, est_amp, 1e-12)
            grad_field = residual * est_field / safe_amp
            grad_spectrum = np.fft.fftshift(np.fft.fft2(grad_field)) * pupil / lr_n_px
            obj_spectrum[ys, xs] -= step * grad_spectrum

    recovery_error = float(np.sqrt(sq_err_sum / (lr_n_px * len(used_leds))))
    return np.fft.ifft2(np.fft.ifftshift(obj_spectrum)), recovery_error


def test_standard_zero_phase_initialization_diverges_deterministically():
    """The exact `initial_hr_guess`-style start (true/flat amplitude,
    EXACTLY zero phase, no randomness at all) is a degenerate point: this
    reconstruction gets steadily WORSE with more iterations, not better --
    the opposite of normal convergence behavior, and fully deterministic
    (no seed dependence -- run it twice, same result).
    """
    setup, factor, hr_pixel_um, hr_shape, led_grid, lr_images, obj = _weak_phase_setup()
    obj0 = np.ones(hr_shape).astype(complex)

    recon_early, _ = _reconstruct_from(obj0.copy(), setup, factor, hr_pixel_um, led_grid, lr_images,
                                        iterations=10)
    recon_late, _ = _reconstruct_from(obj0.copy(), setup, factor, hr_pixel_um, led_grid, lr_images,
                                       iterations=35)
    err_early = np.abs(np.angle(recon_early) - np.angle(obj)).mean()
    err_late = np.abs(np.angle(recon_late) - np.angle(obj)).mean()
    assert err_late > err_early, (
        f"expected the zero-phase init to drift FURTHER from truth with more iterations "
        f"(err_early={err_early}, err_late={err_late}) -- if this now improves, the saddle-point "
        "finding documented in this file and the roadmap may be stale"
    )


def test_small_perturbations_around_the_true_solution_converge_reliably():
    """Contrast case, same object: starting CLOSE to the true answer (not
    at the degenerate zero point) is a well-behaved, reliable local basin
    -- proving the loss landscape itself is fine near the true solution;
    the problem is specifically that the standard initialization starts at
    a degenerate point, not that this object is unrecoverable in principle.
    """
    setup, factor, hr_pixel_um, hr_shape, led_grid, lr_images, obj = _weak_phase_setup()

    correlations = []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        near_truth = obj * np.exp(1j * rng.normal(0, 0.01, hr_shape))
        recon, _ = _reconstruct_from(near_truth.astype(complex), setup, factor, hr_pixel_um,
                                      led_grid, lr_images)
        gt = metrics.compare_to_ground_truth(recon, obj)
        correlations.append(gt["phase_correlation"])

    assert min(correlations) > 0.9, correlations


def test_recovery_error_does_not_predict_true_accuracy_for_weak_phase_objects():
    """The important negative result: across different random-phase-noise
    initializations (the "uninformed restart" case, not the near-truth
    case above), `reconstruct()`'s own internal `recovery_error` metric is
    essentially UNCORRELATED with true phase_correlation -- sometimes the
    run with the LOWEST (best-looking) recovery_error has WORSE true
    accuracy than a run with higher recovery_error. This means a
    "multi-restart, keep the lowest recovery_error" strategy would NOT
    reliably fix this failure mode -- worth knowing before anyone (a future
    session, an orchestration agent) tries exactly that as a cheap fix.
    """
    setup, factor, hr_pixel_um, hr_shape, led_grid, lr_images, obj = _weak_phase_setup()

    recovery_errors, correlations = [], []
    for seed in range(10):
        rng = np.random.default_rng(seed)
        obj0 = (np.ones(hr_shape) * np.exp(1j * rng.normal(0, 0.05, hr_shape))).astype(complex)
        recon, recovery_error = _reconstruct_from(obj0, setup, factor, hr_pixel_um, led_grid, lr_images)
        gt = metrics.compare_to_ground_truth(recon, obj)
        recovery_errors.append(recovery_error)
        correlations.append(gt["phase_correlation"])

    rank_correlation = float(np.corrcoef(recovery_errors, correlations)[0, 1])
    assert abs(rank_correlation) < 0.5, (
        f"expected recovery_error to be a poor predictor of true accuracy here (|corr| < 0.5), "
        f"got {rank_correlation} -- if this is now a reliable predictor, the multi-restart-by-"
        "recovery_error fix ruled out by this finding might actually be viable, worth revisiting"
    )

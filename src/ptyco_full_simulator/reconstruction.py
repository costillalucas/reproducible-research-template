"""reconstruction.py -- ptychographic Wirtinger flow FPM reconstruction.

Base algorithm: Bian et al. 2015 (references/bibliography.yaml id
`bian2015`) -- incremental (ePIE-style) gradient descent on
L_k(O) = (|A_k(O)| - sqrt(I_k))^2 per LED k, where A_k(O) is the predicted
LR complex field: crop O's spectrum to LED k's illumination window,
multiply by the pupil, inverse transform. The Wirtinger gradient of L_k
with respect to A_k* is (|A_k| - sqrt(I_k)) * A_k / |A_k|; propagating it
back through the (self-adjoint) pupil and the crop's adjoint (zero-pad)
gives the update to the HR spectrum.

Step size: by default the fixed ramp mu = step_max * (1 - exp(-alpha*n)),
the same shape as the ramp notebook.md found already in use, adapted to
this module's Fourier-domain-normalized gradient (grad_field is divided
by lr_n_px -- see the adjoint-of-ifft2 comment below -- so step_max isn't
bounded to [0, 1] the way the original real-space-domain ramp was).

Two of references/bibliography.yaml's `priority_focus` gaps are now
implemented as opt-in params on `reconstruct` (2026-09-18, see that
function's docstring for details and honest caveats on each):
`recover_pupil` (rank 1, EPRY / `ou2014`) and `adaptive_step` (rank 3,
`zuo2016`). LED self-calibration (rank 2, `eckert2018`) is implemented
separately in `led_calibration.py`, not here.
"""
from __future__ import annotations

import numpy as np

from .optics import circular_pupil
from .spectral_ops import led_crop_window


def initial_hr_guess(lr_images: dict[tuple[int, int], np.ndarray],
                      led_grid: list[dict], factor: int) -> np.ndarray:
    """Nearest-neighbor upsample of the center (on-axis) LED's image,
    amplitude only, zero phase -- the standard FPM starting point.
    `led_grid` must be sorted center-first (build_led_grid already does).
    """
    center = led_grid[0]
    center_img = lr_images[(center["row"], center["col"])]
    amp = np.sqrt(np.clip(center_img, 0, None))
    amp_hr = np.kron(amp, np.ones((factor, factor)))
    return amp_hr.astype(complex)


def _next_adaptive_step(history: list[dict], step: float, step_max: float,
                         shrink_factor: float = 0.7, patience: int = 3,
                         min_step: float = 1e-3) -> float:
    """zuo2016 (Adaptive Step-Size Strategy for Noise-Robust FPM, Zuo/
    Sun/Chen 2016, `references/papers/2016/oe-24-18-20724.pdf`): the
    paper's core idea is to stop growing (or actively shrink) the step
    size once `recovery_error` stops improving, instead of a step that
    grows on a fixed schedule regardless of whether it's still helping --
    a plateaued/increasing error under a fixed-growing step is exactly
    the noise-amplification failure mode the paper targets (their
    section 2/3, using a per-iteration residual-based criterion in the
    same spirit as `recovery_error` here).

    Simplified rule actually implemented here (their full method
    additionally reasons per-LED about individual image noise levels,
    which this project's `history` does not track -- only the pooled
    per-epoch `recovery_error` is available, see `reconstruct`'s
    docstring): grow toward `step_max` on the same ramp as the fixed
    schedule while error keeps improving; once `recovery_error` fails to
    improve for `patience` consecutive epochs, multiply the step by
    `shrink_factor` (floored at `min_step`) instead of continuing to grow
    -- and keep shrinking on every further non-improving epoch, so a
    genuinely stuck run doesn't hover at a step that's still too large.
    """
    if len(history) < patience + 1:
        return step
    recent = [h["recovery_error"] for h in history[-(patience + 1):]]
    improved = any(recent[i + 1] < recent[i] - 1e-12 for i in range(len(recent) - 1))
    if improved:
        return min(step * 1.05, step_max)
    return max(step * shrink_factor, min_step)


def reconstruct(lr_images: dict[tuple[int, int], np.ndarray],
                 led_grid: list[dict], hr_pixel_um: float, lr_pixel_um: float,
                 na: float, wavelength_um: float, factor: int,
                 iterations: int = 40, step_max: float = 20.0,
                 step_alpha: float = 0.3, initial_object: np.ndarray | None = None,
                 recover_pupil: bool = False, epry_alpha: float = 1.0,
                 epry_beta: float = 1.0, adaptive_step: bool = False) -> dict:
    """Returns {"object": complex HR array, "history": [{"iteration",
    "recovery_error"} per epoch]}. `recovery_error` is the RMS amplitude
    residual across all LEDs used that epoch -- the same quantity
    scripts/checks.py-style correctness checks should track for
    convergence (it must go down; a negative control must show it does
    NOT go down, see tests/test_reconstruction.py).

    `initial_object`, if given, overrides the default `initial_hr_guess`
    (on-axis LED amplitude, zero phase) starting point -- added
    specifically so a Transport-of-Intensity-Equation phase estimate
    (`propagation.solve_tie`) can be used to initialize the phase instead
    of zero, which reliably escapes the degenerate saddle point the
    default initialization sits at for weak/low-spatial-frequency phase
    objects (see tests/test_weak_phase_object_limitation.py and
    tests/test_tie_informed_initialization.py). Must already be shaped
    like the target HR canvas (`optics.hr_shape`).

    `recover_pupil` (EPRY, `ou2014`): if True, alternately updates the
    object spectrum patch AND a complex pupil estimate each LED, using
    Eq. 3/4 of the paper (read in full from
    `references/papers/2014/oe-22-5-4960.pdf`) instead of this module's
    own fixed-ramp Wirtinger-flow step for that patch --
    `step_max`/`step_alpha`/`adaptive_step` are ignored when this is set
    (EPRY's per-pixel normalization by max(|P|^2)/max(|S|^2) is its own
    self-scaling step, the paper uses alpha=beta=1 and so does this
    default). Returned dict gains a `"pupil"` key (complex HR-pupil-sized
    array, shape == lr_shape) with the final recovered pupil when this is
    on. The recovered pupil is masked back to the ideal NA-limited
    circular support every update (paper: "a pupil function constraint is
    imposed... the area in the pupil function that corresponds to the
    stop should always be zero" -- this project's aperture stop is a
    hard circular cutoff, not something EPRY needs to also infer).

    `adaptive_step` (`zuo2016`): if True (and `recover_pupil` is False),
    replaces the fixed exponential-ramp step schedule with
    `_next_adaptive_step` -- see that function's docstring for the
    (simplified) rule and honest caveat about what it does and doesn't
    capture from the paper.
    """
    lr_shape = next(iter(lr_images.values())).shape
    pupil_mask = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    pupil = pupil_mask.astype(complex)
    used_leds = [e for e in led_grid if (e["row"], e["col"]) in lr_images]
    if not used_leds:
        raise ValueError("none of led_grid's (row, col) keys are present in lr_images")

    obj0 = initial_object if initial_object is not None else initial_hr_guess(lr_images, used_leds, factor)
    hr_shape = obj0.shape
    obj_spectrum = np.fft.fftshift(np.fft.fft2(obj0))
    lr_n_px = lr_shape[0] * lr_shape[1]

    history = []
    step = step_max * (1.0 - np.exp(-step_alpha * 0))
    for it in range(iterations):
        if recover_pupil:
            pass  # EPRY's per-pixel normalization is its own step; see docstring.
        elif adaptive_step:
            step = _next_adaptive_step(history, step, step_max)
        else:
            step = step_max * (1.0 - np.exp(-step_alpha * it))
        sq_err_sum = 0.0
        for entry in used_leds:
            key = (entry["row"], entry["col"])
            ys, xs = led_crop_window(hr_shape, hr_pixel_um, lr_shape,
                                      entry["fx"], entry["fy"])
            patch_s = obj_spectrum[ys, xs]
            patch = patch_s * pupil
            est_field = np.fft.ifft2(np.fft.ifftshift(patch))
            est_amp = np.abs(est_field)
            meas_amp = np.sqrt(np.clip(lr_images[key], 0, None))
            residual = est_amp - meas_amp
            sq_err_sum += float(np.sum(residual ** 2))

            safe_amp = np.where(est_amp > 1e-12, est_amp, 1e-12)
            if recover_pupil:
                # EPRY (ou2014 Eq. 2-4): impose the intensity constraint,
                # propagate the resulting exit-wave correction back to
                # the pupil plane, and use it to update S and P in turn
                # (P with the *previous* S, S with the *previous* P --
                # same simultaneous-update convention as the paper's
                # flowchart, Fig. 1).
                corrected_field = meas_amp * est_field / safe_amp
                diff_freq = np.fft.fftshift(np.fft.fft2(corrected_field - est_field)) / lr_n_px
                p_max_sq = max(float(np.max(np.abs(pupil) ** 2)), 1e-12)
                s_max_sq = max(float(np.max(np.abs(patch_s) ** 2)), 1e-12)
                obj_spectrum[ys, xs] = patch_s + epry_alpha * np.conj(pupil) / p_max_sq * diff_freq
                pupil = (pupil + epry_beta * np.conj(patch_s) / s_max_sq * diff_freq) * pupil_mask
            else:
                grad_field = residual * est_field / safe_amp
                # Adjoint of ifft2 is (1/lr_n_px) * fft2, not fft2 -- numpy's
                # ifft2 carries the 1/N normalization that fft2 doesn't, so
                # this factor is required or the effective step size scales
                # with LR image size (verified: omitting it diverges as
                # lr_size grows).
                grad_spectrum = np.fft.fftshift(np.fft.fft2(grad_field)) * pupil / lr_n_px
                obj_spectrum[ys, xs] -= step * grad_spectrum

        n_px = lr_shape[0] * lr_shape[1] * len(used_leds)
        history.append({
            "iteration": it,
            "recovery_error": float(np.sqrt(sq_err_sum / n_px)),
        })

    obj = np.fft.ifft2(np.fft.ifftshift(obj_spectrum))
    result = {"object": obj, "history": history}
    if recover_pupil:
        result["pupil"] = pupil
    return result

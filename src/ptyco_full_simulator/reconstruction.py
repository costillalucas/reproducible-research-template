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

CAVEAT (2026-09-23, roadmap 6.8 / fork F): because the gradient carries
that 1/lr_n_px, the classic ePIE/Gerchberg-Saxton unit step corresponds
to step_max == lr_n_px, so a FIXED step_max is a step that shrinks as
1/(crop^2). The default 20 was tuned on this project's tiny synthetic
crops (~12-16 px, where 20 is ~0.1 of the unit step); at crop 400 it is
~1/8000 of it and the solver barely moves (noiseless synthetic control,
20 it: relative improvement 0.62/0.20/0.05 at crop 16/64/128 with the
default, ~0.90 at every crop with 0.3 of the unit step). `step_relative`
expresses the step as that crop-independent fraction instead. The
default is left unchanged so recorded synthetic results reproduce.

Initial-guess scale: `forward_model.simulate_lr_stack` and this module's
own model use un-normalized fft2 (HR) / ifft2 (LR), so an HR object of
amplitude a predicts an LR field of amplitude a * n_hr/n_lr = a*factor^2.
`initial_hr_guess`'s plain upsample of sqrt(I) therefore starts
factor^2 too bright (real 2025-12-12 data: initial bright-field per-LED
residual 24.3 -> 0.24 once divided). `match_forward_model_scale=True`
divides it out; off by default for the same reproducibility reason.

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
                      led_grid: list[dict], factor: int,
                      match_forward_model_scale: bool = False) -> np.ndarray:
    """Nearest-neighbor upsample of the center (on-axis) LED's image,
    amplitude only, zero phase -- the standard FPM starting point.
    `led_grid` must be sorted center-first (build_led_grid already does).

    `match_forward_model_scale=True` divides by factor^2 so the guess,
    pushed through the un-normalized forward model, predicts the measured
    intensities instead of factor^4 times them (see the module docstring).
    Off by default: recorded synthetic results used the unscaled guess.
    """
    center = led_grid[0]
    center_img = lr_images[(center["row"], center["col"])]
    amp = np.sqrt(np.clip(center_img, 0, None))
    amp_hr = np.kron(amp, np.ones((factor, factor)))
    if match_forward_model_scale:
        amp_hr = amp_hr / factor**2
    return amp_hr.astype(complex)


def _next_adaptive_step(history: list[dict], step: float, eta: float = 0.01,
                         min_step: float = 1e-3) -> float:
    """zuo2016 (Adaptive Step-Size Strategy for Noise-Robust FPM, Zuo/
    Sun/Chen 2016, `references/papers/2016/oe-24-18-20724.pdf`) Eq. 16,
    implemented as written, not approximated: given the global error
    metric epsilon(O^k) each full cycle (`recovery_error` in `history`
    already plays this role, see `reconstruct`'s docstring), keep the
    step-size unchanged while the previous cycle's relative improvement
    exceeds `eta`, otherwise HALVE it:
        alpha^k = alpha^(k-1)     if (eps(O^k)-eps(O^(k-1)))/eps(O^(k-1)) > eta
                = alpha^(k-1)/2   otherwise
    The paper starts alpha^0=1 (no ramp-up, same convention this
    project's `reconstruct` follows for `adaptive_step=True`: step starts
    at `step_max` on iteration 0, see below) and only ever shrinks --
    Eq. 16 has no branch that grows the step back up, unlike this
    module's own default fixed-ramp schedule. `min_step` is an
    engineering floor NOT in the paper's equation, added only so a
    long-stuck run's step can't underflow to exactly 0 and stall the
    optimizer entirely; `eta=0.01` matches the paper's own stated
    default ("a reasonably good result can always be obtained by fixing
    eta=0.01").
    """
    if len(history) < 2:
        return step
    prev_error, curr_error = history[-2]["recovery_error"], history[-1]["recovery_error"]
    if prev_error <= 0:
        return step
    relative_improvement = (prev_error - curr_error) / prev_error
    if relative_improvement > eta:
        return step
    return max(step / 2.0, min_step)


def reconstruct(lr_images: dict[tuple[int, int], np.ndarray],
                 led_grid: list[dict], hr_pixel_um: float, lr_pixel_um: float,
                 na: float, wavelength_um: float, factor: int,
                 iterations: int = 40, step_max: float = 20.0,
                 step_alpha: float = 0.3, initial_object: np.ndarray | None = None,
                 recover_pupil: bool = False, epry_alpha: float = 1.0,
                 epry_beta: float = 1.0, adaptive_step: bool = False,
                 step_relative: float | None = None,
                 normalize_initial_guess: bool = False) -> dict:
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

    CAVEAT (2026-09-18, tests/test_epry_pupil_recovery.py): NOT a safe
    default to always turn on for the small, fast synthetic problems this
    project's test suite uses (crop~12px, 81-441 LEDs). Under a real
    injected aberration it helps (modestly, see that test's docstring);
    with NO aberration present it can instead REGRESS an already-well-
    converging reconstruction at that scale (seen reproducibly for the
    blue/470nm channel) -- the object update's own normalization can
    overfit even though the recovered pupil itself stays nearly flat, and
    `recovery_error` keeps improving throughout while true accuracy gets
    worse (the metric doesn't catch this, same as elsewhere in this
    project). Confirmed this is a SMALL-TESTBED/LOW-DATA-REDUNDANCY
    artifact, not a general EPRY failure or an implementation bug: the
    same regression does NOT reproduce at a scale closer to ou2014's own
    real demo (225 LEDs, 64x64px, see
    `test_recover_pupil_regression_is_a_small_testbed_artifact_not_reproduced_at_paper_scale`),
    and the literature's standard fix for over-aggressive PIE-family
    normalization (rPIE-style regularization) barely changes the small-
    scale numbers, ruling out "just needs a better-regularized update
    rule". No per-channel diagnostic exists yet to predict in advance
    whether a given run is in the safe or unsafe regime, and real data
    from this project's actual lab grids (81-441 LEDs) sits closer to the
    small/risky end than the paper's own 225-image demo.

    `adaptive_step` (`zuo2016`): if True (and `recover_pupil` is False),
    replaces the fixed exponential-ramp step schedule with the paper's
    Eq. 16 rule (`_next_adaptive_step` -- read in full from
    `references/papers/2016/oe-24-18-20724.pdf`, see that function's
    docstring for the exact equation and an honest note on its one
    non-paper addition, a numerical-safety floor). Step starts at
    `step_max` on iteration 0 (the paper's alpha^0=1 convention -- this
    module's step is already gradient-normalized, see the module
    docstring, so `step_max` plays the role of "no extra scaling", same
    as the fixed-ramp schedule's step approaches `step_max` from below)
    and only ever shrinks, per Eq. 16.

    CAVEAT (2026-09-18, tests/test_adaptive_step_size.py): the advantage
    over the fixed ramp is real but regime-dependent, NOT unconditional
    like TIE-informed initialization. At light-to-moderate Poisson noise
    (`peak_photon_count` >= 20) and modest iteration counts (<=60),
    quality was within a few percent either way -- no clean win. At
    heavier noise (`peak_photon_count`=3) and more iterations (400,
    letting the paper's described noise-driven oscillation actually
    manifest -- their Section 4, Property A), adaptive_step reproducibly
    beat the fixed ramp across 8 random seeds (8/8 wins, paired mean gain
    0.06 phase_correlation). If reconstructing under light noise or few
    iterations, don't expect adaptive_step to help much; it's the heavy-
    noise/many-cycle regime where it earns its keep.

    `step_relative` (2026-09-23): if set, overrides `step_max` with
    `step_relative * lr_n_px`, i.e. the step as a fraction of the classic
    ePIE unit step, independent of crop size (see the module docstring's
    CAVEAT on why a fixed `step_max` freezes the solver at large crops).
    The ramp / adaptive schedule then applies on top as usual. 0.3 was
    what fork F used (results/led_geometry_2025-12-12/). NOT the default
    and NOT validated on real data: unfrozen on the 2025-12-12 capture it
    fits dark-field LEDs but the phase comes out noise-like (roadmap 6.8).
    Under `recover_pupil` it instead scales EPRY's alpha/beta: the
    effective values are `epry_alpha * step_relative * lr_n_px` and
    `epry_beta * step_relative * lr_n_px`. The EPRY branch divides its
    exit-wave correction by lr_n_px (same adjoint-of-ifft2 convention as
    the WF gradient), which makes alpha=beta=1 a step 1/lr_n_px of the
    paper's -- frozen at large crops exactly like the WF default (forks
    H/K, roadmap 6.10). With `step_relative=1.0` and the default
    alpha=beta=1 this reproduces ou2014 Eq. 3/4 exactly. Without
    `step_relative` the EPRY branch is unchanged.

    `normalize_initial_guess` (2026-09-23): when no `initial_object` is
    given, build the default guess with `initial_hr_guess(...,
    match_forward_model_scale=True)` (divide by factor^2, module docstring).
    """
    lr_shape = next(iter(lr_images.values())).shape
    pupil_mask = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    pupil = pupil_mask.astype(complex)
    used_leds = [e for e in led_grid if (e["row"], e["col"]) in lr_images]
    if not used_leds:
        raise ValueError("none of led_grid's (row, col) keys are present in lr_images")

    obj0 = initial_object if initial_object is not None else initial_hr_guess(
        lr_images, used_leds, factor, match_forward_model_scale=normalize_initial_guess)
    hr_shape = obj0.shape
    obj_spectrum = np.fft.fftshift(np.fft.fft2(obj0))
    lr_n_px = lr_shape[0] * lr_shape[1]
    if step_relative is not None:
        if step_relative <= 0:
            raise ValueError(f"step_relative must be > 0, got {step_relative}")
        step_max = step_relative * lr_n_px
        if recover_pupil:
            epry_alpha = epry_alpha * step_relative * lr_n_px
            epry_beta = epry_beta * step_relative * lr_n_px

    history = []
    step = step_max  # zuo2016 Eq. 16 convention: alpha^0 = 1 (see reconstruct's docstring)
    for it in range(iterations):
        if recover_pupil:
            pass  # EPRY's per-pixel normalization is its own step; see docstring.
        elif adaptive_step:
            step = _next_adaptive_step(history, step)
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
                # this is the exact gradient w.r.t. the spectrum. But the
                # spectrum's own scale is ~lr_n_px times the field's, so the
                # natural (ePIE unit) step for this gradient is step ==
                # lr_n_px: a FIXED step_max therefore shrinks as 1/lr_n_px
                # (the old note here, "omitting it diverges as lr_size
                # grows", was the same fact seen from the other side). Use
                # `step_relative` for a crop-independent step; see the
                # module docstring's CAVEAT.
                grad_spectrum = np.fft.fftshift(np.fft.fft2(grad_field)) * pupil / lr_n_px
                obj_spectrum[ys, xs] -= step * grad_spectrum

        n_px = lr_shape[0] * lr_shape[1] * len(used_leds)
        history.append({
            "iteration": it,
            "recovery_error": float(np.sqrt(sq_err_sum / n_px)),
            "step": None if recover_pupil else float(step),
        })

    obj = np.fft.ifft2(np.fft.ifftshift(obj_spectrum))
    result = {"object": obj, "history": history}
    if recover_pupil:
        result["pupil"] = pupil
    return result

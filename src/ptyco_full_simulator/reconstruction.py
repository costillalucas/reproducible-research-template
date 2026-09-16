"""reconstruction.py -- ptychographic Wirtinger flow FPM reconstruction.

Base algorithm: Bian et al. 2015 (references/bibliography.yaml id
`bian2015`) -- incremental (ePIE-style) gradient descent on
L_k(O) = (|A_k(O)| - sqrt(I_k))^2 per LED k, where A_k(O) is the predicted
LR complex field: crop O's spectrum to LED k's illumination window,
multiply by the pupil, inverse transform. The Wirtinger gradient of L_k
with respect to A_k* is (|A_k| - sqrt(I_k)) * A_k / |A_k|; propagating it
back through the (self-adjoint) pupil and the crop's adjoint (zero-pad)
gives the update to the HR spectrum.

Step size: the fixed ramp mu = step_max * (1 - exp(-alpha*n)), the same
shape as the ramp notebook.md found already in use, adapted to this
module's Fourier-domain-normalized gradient (grad_field is divided by
lr_n_px -- see the adjoint-of-ifft2 comment below -- so step_max isn't
bounded to [0, 1] the way the original real-space-domain ramp was).

Pupil recovery (EPRY, Ou et al. 2014, references/bibliography.yaml id
`ou2014`, `priority_focus` rank 1): patch = obj_window * pupil is an
elementwise product of two complex Fourier-domain arrays, so the same
Wirtinger adjoint used to correct obj_window (dL/d(patch)* times conj of
the *other* factor) applies symmetrically to pupil -- swap obj_window and
pupil in that product rule and reuse the identical per-LED gradient
(`adjoint_field` below). The pupil update is normalized by
max(|obj_window|^2) (the standard ePIE/EPRY probe-update normalization --
without it, pupil's O(1) magnitude vs. obj_window's much larger spectrum
values would blow up) and re-masked to the static NA support each step,
since the physical pupil is exactly zero outside the objective's cutoff.
Remaining gaps ranked in references/bibliography.yaml's `priority_focus`
(LED self-calibration, adaptive step size, ...) are NOT implemented yet.
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


def reconstruct(lr_images: dict[tuple[int, int], np.ndarray],
                 led_grid: list[dict], hr_pixel_um: float, lr_pixel_um: float,
                 na: float, wavelength_um: float, factor: int,
                 iterations: int = 40, step_max: float = 20.0,
                 step_alpha: float = 0.3, update_pupil: bool = True,
                 pupil_step_max: float = 50.0,
                 pupil_update_start: int = 3) -> dict:
    """Returns {"object": complex HR array, "pupil": complex LR-shaped
    array, "history": [{"iteration", "recovery_error"} per epoch]}.
    `recovery_error` is the RMS amplitude residual across all LEDs used
    that epoch -- the same quantity scripts/checks.py-style correctness
    checks should track for convergence (it must go down; a negative
    control must show it does NOT go down, see tests/test_reconstruction.py).

    `update_pupil` turns on the EPRY pupil-recovery step (see module
    docstring); disable it to fall back to the original static-pupil
    Wirtinger flow. `pupil_update_start` delays the first pupil update by
    a few epochs so the object has a chance to leave its crude initial
    guess first -- updating an aberration estimate against a still-wrong
    object is the classic EPRY failure mode.
    """
    lr_shape = next(iter(lr_images.values())).shape
    pupil_support = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    pupil = pupil_support.astype(complex)
    used_leds = [e for e in led_grid if (e["row"], e["col"]) in lr_images]
    if not used_leds:
        raise ValueError("none of led_grid's (row, col) keys are present in lr_images")

    obj0 = initial_hr_guess(lr_images, used_leds, factor)
    hr_shape = obj0.shape
    obj_spectrum = np.fft.fftshift(np.fft.fft2(obj0))
    lr_n_px = lr_shape[0] * lr_shape[1]

    history = []
    for it in range(iterations):
        step = step_max * (1.0 - np.exp(-step_alpha * it))
        pupil_step = pupil_step_max * (1.0 - np.exp(-step_alpha * it))
        do_pupil = update_pupil and it >= pupil_update_start
        sq_err_sum = 0.0
        for entry in used_leds:
            key = (entry["row"], entry["col"])
            ys, xs = led_crop_window(hr_shape, hr_pixel_um, lr_shape,
                                      entry["fx"], entry["fy"])
            obj_window = obj_spectrum[ys, xs]
            patch = obj_window * pupil
            est_field = np.fft.ifft2(np.fft.ifftshift(patch))
            est_amp = np.abs(est_field)
            meas_amp = np.sqrt(np.clip(lr_images[key], 0, None))
            residual = est_amp - meas_amp
            sq_err_sum += float(np.sum(residual ** 2))

            safe_amp = np.where(est_amp > 1e-12, est_amp, 1e-12)
            grad_field = residual * est_field / safe_amp
            # Adjoint of ifft2 is (1/lr_n_px) * fft2, not fft2 -- numpy's
            # ifft2 carries the 1/N normalization that fft2 doesn't, so
            # this factor is required or the effective step size scales
            # with LR image size (verified: omitting it diverges as
            # lr_size grows). This is dL/d(patch)*, shared by both the
            # object and pupil updates below (see module docstring).
            adjoint_field = np.fft.fftshift(np.fft.fft2(grad_field)) / lr_n_px

            obj_spectrum[ys, xs] = obj_window - step * adjoint_field * np.conj(pupil)

            if do_pupil:
                # ePIE/EPRY probe-update normalization: divide by the
                # object window's peak intensity so the update magnitude
                # doesn't depend on the (much larger) HR spectrum scale.
                denom = max(float(np.max(np.abs(obj_window) ** 2)), 1e-12)
                pupil = pupil - pupil_step * adjoint_field * np.conj(obj_window) / denom
                pupil = pupil * pupil_support

        n_px = lr_shape[0] * lr_shape[1] * len(used_leds)
        history.append({
            "iteration": it,
            "recovery_error": float(np.sqrt(sq_err_sum / n_px)),
        })

    obj = np.fft.ifft2(np.fft.ifftshift(obj_spectrum))
    return {"object": obj, "pupil": pupil, "history": history}

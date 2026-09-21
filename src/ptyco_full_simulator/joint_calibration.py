"""joint_calibration.py -- self-calibrating FPM reconstruction: recover the
complex object AND every LED's illumination spatial frequency together by
gradient descent on the intensity mismatch, following You & Liang, "Self-
calibrating Fourier ptychographic microscopy using automatic
differentiation" (Optics Letters 50(2), 2025; AD-SC, Eq. 1-4, Fig. 2).

Difference from the paper: no PyTorch here (the project is numpy-only), so
instead of autodiff the gradient of the loss is derived by hand and
checked against finite differences (tests/test_joint_calibration.py). It
is the same computational graph as the paper's Fig. 2, backpropagated
manually. The optimizer is Adam, as in the paper.

Forward model differs from `forward_model.simulate_lr_stack` in one way
that matters: illumination k is CONTINUOUS. The existing model rounds k
to the nearest HR spectrum bin (`spectral_ops.led_crop_window`), which
has no gradient. Here the tilt is applied in real space instead --
u = o * exp(-2*pi*i*(kx*x + ky*y)), then the CENTER lr_shape window of
U = FFT(u) is taken -- which for a bin-aligned k gives exactly the same
image as the crop model (tested) and is differentiable in k in between.

Not implemented from the paper: the pupil (Zernike) is held fixed at the
ideal NA disk, and the paper's z-height parametrization of LED position
is replaced by optimizing (fx, fy) per LED directly.
"""
from __future__ import annotations

import numpy as np

from .optics import circular_pupil


_LOSSES = ("intensity", "amplitude", "poisson")


def _coords(hr_shape: tuple[int, int], hr_pixel_um: float) -> tuple[np.ndarray, np.ndarray]:
    h, w = hr_shape
    y = (np.arange(h) - h // 2) * hr_pixel_um
    x = (np.arange(w) - w // 2) * hr_pixel_um
    return np.meshgrid(x, y)


def _center_slices(hr_shape: tuple[int, int], lr_shape: tuple[int, int]) -> tuple[slice, slice]:
    y0 = hr_shape[0] // 2 - lr_shape[0] // 2
    x0 = hr_shape[1] // 2 - lr_shape[1] // 2
    return slice(y0, y0 + lr_shape[0]), slice(x0, x0 + lr_shape[1])


def _field_scale(hr_shape: tuple[int, int], lr_shape: tuple[int, int]) -> float:
    """Unnormalized fft2 (HR) followed by ifft2 (LR) scales the field by
    n_hr/n_lr; undo it so a flat object of amplitude 1 gives intensity 1
    -- measured images must be in these units (object-amplitude^2).
    """
    return (lr_shape[0] * lr_shape[1]) / (hr_shape[0] * hr_shape[1])


def initial_object_from_center_led(center_image: np.ndarray, hr_shape: tuple[int, int]) -> np.ndarray:
    """Amplitude-only, zero-phase starting object: nearest-neighbor
    upsample of sqrt(on-axis LR image) to `hr_shape`. Units match this
    module's forward model (no extra scale factor, unlike
    `reconstruction.initial_hr_guess` used with the un-normalized model).
    """
    amp = np.sqrt(np.clip(center_image, 0, None))
    fy, fx = hr_shape[0] // amp.shape[0], hr_shape[1] // amp.shape[1]
    return np.kron(amp, np.ones((fy, fx))).astype(complex)


def simulate_lr_stack_continuous(hr_object: np.ndarray, hr_pixel_um: float,
                                  led_grid: list[dict], lr_shape: tuple[int, int],
                                  lr_pixel_um: float, na: float, wavelength_um: float,
                                  ) -> dict[tuple[int, int], np.ndarray]:
    """Noiseless {(row, col): intensity} using the continuous-k forward
    model of this module (no rounding of k to a spectrum bin).
    """
    pupil = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    X, Y = _coords(hr_object.shape, hr_pixel_um)
    ys, xs = _center_slices(hr_object.shape, lr_shape)
    out = {}
    for e in led_grid:
        tilt = np.exp(-2j * np.pi * (e["fx"] * X + e["fy"] * Y))
        U = np.fft.fftshift(np.fft.fft2(hr_object * tilt))
        field = _field_scale(hr_object.shape, lr_shape) * np.fft.ifft2(np.fft.ifftshift(U[ys, xs] * pupil))
        out[(e["row"], e["col"])] = np.abs(field) ** 2
    return out


def loss_and_gradients(hr_object: np.ndarray, hr_pixel_um: float, led_grid: list[dict],
                        lr_images: dict, lr_shape: tuple[int, int], lr_pixel_um: float,
                        na: float, wavelength_um: float, loss: str = "intensity") -> dict:
    """Loss, summed over LEDs and pixels and normalized so step sizes don't
    depend on image brightness, plus its exact gradients. `loss`:
      - "intensity": sum (I - M)^2 / sum M^2 (paper Eq. 4);
      - "amplitude": sum (|f| - sqrt(M))^2 / sum M -- Gaussian noise on the
        amplitude, the choice Yeh et al. 2015 found most robust to noise;
      - "poisson": sum (I - M*ln(I + eps)) / sum M -- the Poisson negative
        log-likelihood (up to a constant), the actual noise model of a
        photon-counting camera.
    Gradients:
      - `grad_object`: dL/d(conj(o)), complex (real/imag partials are
        2*Re/2*Im of it);
      - `grad_k`: (n_leds, 2) array of dL/d(fx, fy).
    """
    pupil = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    X, Y = _coords(hr_object.shape, hr_pixel_um)
    ys, xs = _center_slices(hr_object.shape, lr_shape)
    n_lr = lr_shape[0] * lr_shape[1]
    scale = _field_scale(hr_object.shape, lr_shape)
    n_hr = hr_object.shape[0] * hr_object.shape[1]
    if loss not in _LOSSES:
        raise ValueError(f"loss must be one of {_LOSSES}, got {loss!r}")
    power = 2 if loss == "intensity" else 1
    norm = sum(float(np.sum(lr_images[(e["row"], e["col"])] ** power)) for e in led_grid)

    total = 0.0
    grad_obj = np.zeros_like(hr_object, dtype=complex)
    grad_k = np.zeros((len(led_grid), 2))
    for i, e in enumerate(led_grid):
        meas = lr_images[(e["row"], e["col"])]
        tilt = np.exp(-2j * np.pi * (e["fx"] * X + e["fy"] * Y))
        u = hr_object * tilt
        U = np.fft.fftshift(np.fft.fft2(u))
        field = scale * np.fft.ifft2(np.fft.ifftshift(U[ys, xs] * pupil))
        inten = np.abs(field) ** 2
        if loss == "intensity":
            resid = inten - meas
            total += float(np.sum(resid ** 2))
            g_field = 2.0 * resid * field  # dL/d conj(field)
        elif loss == "amplitude":
            amp = np.sqrt(inten)
            resid = amp - np.sqrt(np.clip(meas, 0, None))
            total += float(np.sum(resid ** 2))
            g_field = resid * field / np.maximum(amp, 1e-12)
        else:
            eps = 1e-6 * max(float(meas.max()), 1e-12)
            total += float(np.sum(inten - meas * np.log(inten + eps)))
            g_field = (1.0 - meas / (inten + eps)) * field

        # backprop: dL/d conj(field) -> through ifft2 -> pupil -> zero-pad -> fft2
        g_crop = scale * np.fft.fftshift(np.fft.fft2(g_field)) / n_lr * np.conj(pupil)
        g_full = np.zeros(hr_object.shape, dtype=complex)
        g_full[ys, xs] = g_crop
        g_u = np.fft.ifft2(np.fft.ifftshift(g_full)) * n_hr  # dL/d conj(u)

        grad_obj += np.conj(tilt) * g_u
        d_conj_u = 2j * np.pi * np.conj(u)
        grad_k[i, 0] = 2.0 * np.real(np.sum(g_u * X * d_conj_u))
        grad_k[i, 1] = 2.0 * np.real(np.sum(g_u * Y * d_conj_u))
    return {"loss": total / norm, "grad_object": grad_obj / norm, "grad_k": grad_k / norm}


class _Adam:
    def __init__(self, shape, lr, b1=0.9, b2=0.999, eps=1e-8):
        self.m = np.zeros(shape)
        self.v = np.zeros(shape)
        self.lr, self.b1, self.b2, self.eps, self.t = lr, b1, b2, eps, 0

    def step(self, grad: np.ndarray) -> np.ndarray:
        self.t += 1
        self.m = self.b1 * self.m + (1 - self.b1) * grad
        self.v = self.b2 * self.v + (1 - self.b2) * grad ** 2
        m_hat = self.m / (1 - self.b1 ** self.t)
        v_hat = self.v / (1 - self.b2 ** self.t)
        return self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


def reconstruct_and_calibrate(lr_images: dict, led_grid_nominal: list[dict],
                               hr_shape: tuple[int, int], hr_pixel_um: float,
                               lr_shape: tuple[int, int], lr_pixel_um: float,
                               na: float, wavelength_um: float,
                               initial_object: np.ndarray, n_iterations: int = 200,
                               calibrate_leds: bool = True, led_model: str = "rigid",
                               warmup_iterations: int = 0, object_lr: float = 0.02,
                               k_lr_bins: float = 0.02, loss: str = "intensity") -> dict:
    """Joint object + LED-position recovery (AD-SC). With
    `calibrate_leds=False` this is plain gradient-descent FPM with the
    given LED positions held fixed (the paper's "direct AD" baseline).

    `led_model`: "per_led" frees (fx, fy) of every LED independently, as
    in the paper; "rigid" instead fits ONE similarity transform
    z' = a*z + b (z = fx + i*fy nominal, a, b complex: rotation + scale +
    translation of the whole array, 4 real parameters) -- the same
    regularization `led_calibration.fit_similarity_transform` uses, here
    optimized jointly with the object. Far fewer parameters than data, so
    it can't overfit per-LED the way "per_led" can on small crops.

    `loss`: see `loss_and_gradients` ("intensity", "amplitude", "poisson").

    `warmup_iterations`: the first N iterations update only the object
    (positions held at nominal), so the position gradient isn't computed
    against a still-garbage object.

    `k_lr_bins` is the Adam step size for translation / per-LED positions,
    in units of one HR spectrum bin (1 / (hr_shape * hr_pixel_um)) so it
    doesn't depend on the sampling; for the rigid model the a-step is that
    same bin fraction divided by the array's RMS radius, so a change in a
    moves the typical LED by about `k_lr_bins` bins.

    Returns {"object", "led_grid" (calibrated copy), "history"}.
    """
    if led_model not in ("per_led", "rigid"):
        raise ValueError(f"led_model must be 'per_led' or 'rigid', got {led_model!r}")
    obj = initial_object.astype(complex).copy()
    nominal_z = np.array([e["fx"] + 1j * e["fy"] for e in led_grid_nominal])
    grid = [dict(e) for e in led_grid_nominal]
    delta_k = 1.0 / (hr_shape[1] * hr_pixel_um)
    opt_re, opt_im = _Adam(obj.shape, object_lr), _Adam(obj.shape, object_lr)
    opt_pos = _Adam((len(grid), 2), k_lr_bins * delta_k)
    opt_a = _Adam((2,), k_lr_bins * delta_k / float(np.sqrt(np.mean(np.abs(nominal_z) ** 2))))
    opt_b = _Adam((2,), k_lr_bins * delta_k)
    a, b = 1.0 + 0j, 0.0 + 0j

    history = []
    for it in range(n_iterations):
        out = loss_and_gradients(obj, hr_pixel_um, grid, lr_images, lr_shape,
                                  lr_pixel_um, na, wavelength_um, loss)
        history.append({"iteration": it, "loss": out["loss"]})
        g = out["grad_object"]
        obj = obj - opt_re.step(2 * g.real) - 1j * opt_im.step(2 * g.imag)
        if not calibrate_leds or it < warmup_iterations:
            continue
        gk = out["grad_k"]
        if led_model == "per_led":
            dk = opt_pos.step(gk)
            for e, (dfx, dfy) in zip(grid, dk):
                e["fx"] -= float(dfx)
                e["fy"] -= float(dfy)
        else:
            gz = gk[:, 0] + 1j * gk[:, 1]
            # z' = a*z + b is linear in (a_re, a_im, b_re, b_im): d z'/d a_re = z,
            # d z'/d a_im = i*z, d z'/d b_re = 1, d z'/d b_im = i
            ga = np.array([np.real(np.sum(np.conj(gz) * nominal_z)),
                           np.real(np.sum(np.conj(gz) * 1j * nominal_z))])
            gb = np.array([np.real(np.sum(gz)), np.imag(np.sum(gz))])
            da, db = opt_a.step(ga), opt_b.step(gb)
            a, b = a - (da[0] + 1j * da[1]), b - (db[0] + 1j * db[1])
            z = a * nominal_z + b
            for e, zi in zip(grid, z):
                e["fx"], e["fy"] = float(zi.real), float(zi.imag)
    return {"object": obj, "led_grid": grid, "history": history,
            "similarity": {"scale": float(abs(a)), "rotation_rad": float(np.angle(a)),
                           "shift": (float(b.real), float(b.imag))}}

"""spectral_ops.py -- the one piece of index arithmetic shared by the
forward model and the reconstruction: which block of the HR spectrum a
given LED's illumination angle corresponds to.

By construction (HR pixel size = LR pixel size / integer factor, HR shape
= LR shape * factor), the HR spectrum's frequency spacing exactly matches
a standalone LR-sized FFT grid's -- so "crop a lr_shape-sized window out
of the HR spectrum" and "this LED's own LR-sized FFT" are the same grid,
just offset. That's what makes the FPM forward model just crop + pupil +
ifft, and its adjoint just fft + pupil + zero-pad-back.
"""
from __future__ import annotations

import numpy as np


def hr_freq_axes(hr_shape: tuple[int, int], hr_pixel_um: float) -> tuple[np.ndarray, np.ndarray]:
    h, w = hr_shape
    fy = np.fft.fftshift(np.fft.fftfreq(h, d=hr_pixel_um))
    fx = np.fft.fftshift(np.fft.fftfreq(w, d=hr_pixel_um))
    return fx, fy


def led_crop_window(hr_shape: tuple[int, int], hr_pixel_um: float,
                     lr_shape: tuple[int, int], fx_led: float, fy_led: float
                     ) -> tuple[slice, slice]:
    """The (row_slice, col_slice) into the fftshift-ed HR spectrum that
    this LED's illumination selects, sized lr_shape and centered on the
    HR frequency bin closest to (fx_led, fy_led).
    """
    fx_axis, fy_axis = hr_freq_axes(hr_shape, hr_pixel_um)
    df_x = fx_axis[1] - fx_axis[0]
    df_y = fy_axis[1] - fy_axis[0]
    cx = int(round((fx_led - fx_axis[0]) / df_x))
    cy = int(round((fy_led - fy_axis[0]) / df_y))
    n_lr_y, n_lr_x = lr_shape
    y0 = cy - n_lr_y // 2
    x0 = cx - n_lr_x // 2
    y1, x1 = y0 + n_lr_y, x0 + n_lr_x
    if y0 < 0 or x0 < 0 or y1 > hr_shape[0] or x1 > hr_shape[1]:
        raise ValueError(
            f"LED at (fx={fx_led:.4f}, fy={fy_led:.4f}) 1/um needs HR window "
            f"rows[{y0}:{y1}] cols[{x0}:{x1}] which falls outside the HR "
            f"array {hr_shape} -- increase the HR canvas (a larger "
            "safety_factor in optics.hr_pixel_size_um, or a smaller LED grid)."
        )
    return slice(y0, y1), slice(x0, x1)

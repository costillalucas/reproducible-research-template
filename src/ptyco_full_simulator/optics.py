"""optics.py -- pupil function and HR/LR sampling geometry.

The pupil is a static circular low-pass mask (NA-limited coherent
transfer function), no aberration term. Updating it in place from data
is EPRY (Ou 2014) -- references/bibliography.yaml id `ou2014`, the
current #1 priority gap -- not implemented yet.
"""
from __future__ import annotations

import numpy as np

from .config import SetupConfig
from .led_array import max_axis_illumination_na, max_illumination_na


def circular_pupil(shape: tuple[int, int], pixel_size_um: float,
                    na: float, wavelength_um: float) -> np.ndarray:
    """Boolean circular support in the (fftshift-ed) Fourier domain of an
    array with this shape and real-space pixel size, cut off at the
    objective's NA.
    """
    h, w = shape
    fy = np.fft.fftshift(np.fft.fftfreq(h, d=pixel_size_um))
    fx = np.fft.fftshift(np.fft.fftfreq(w, d=pixel_size_um))
    FX, FY = np.meshgrid(fx, fy)
    cutoff = na / wavelength_um
    return (FX**2 + FY**2) <= cutoff**2


def add_defocus_aberration(pupil_mask: np.ndarray, shape: tuple[int, int],
                            pixel_size_um: float, na: float, wavelength_um: float,
                            defocus_rad_amplitude: float) -> np.ndarray:
    """Complex pupil = `pupil_mask` (boolean support) with a defocus phase
    term added inside it -- a synthetic, known aberration for testing EPRY
    pupil recovery (`ou2014`) against ground truth. This is Zernike mode 4
    (defocus): phase(fx, fy) = defocus_rad_amplitude * (rho/rho_max)^2,
    where rho is radial spatial frequency and rho_max = na/wavelength_um
    is the pupil edge -- the same low-order aberration ou2014 Fig. 3(d)
    found dominant in a real microscope (see the paper's Zernike
    decomposition discussion, mode 4).
    """
    h, w = shape
    fy = np.fft.fftshift(np.fft.fftfreq(h, d=pixel_size_um))
    fx = np.fft.fftshift(np.fft.fftfreq(w, d=pixel_size_um))
    FX, FY = np.meshgrid(fx, fy)
    rho_max = na / wavelength_um
    rho_sq_norm = (FX**2 + FY**2) / (rho_max**2)
    phase = defocus_rad_amplitude * rho_sq_norm
    return (pupil_mask.astype(complex)) * np.exp(1j * phase)


def hr_pixel_size_um(setup: SetupConfig, safety_factor: float = 2.0) -> float:
    """Nyquist-adequate HR pixel size for the synthetic aperture this LED
    grid + objective can achieve: NA_synthetic = NA_objective + NA_illum_max.
    `safety_factor` >= 2 keeps some margin over the bare Nyquist limit.
    """
    na_illum_max = max_illumination_na(setup.led_array)
    na_synthetic = setup.objective.na + na_illum_max
    return setup.wavelength_um / (safety_factor * na_synthetic)


def _odd_ceil(ratio: float) -> int:
    factor = int(np.ceil(ratio))
    return factor + 1 if factor % 2 == 0 else factor


def nyquist_upsampling_factor(setup: SetupConfig, safety_factor: float = 2.0) -> int:
    """The resolution-driven factor: enough HR pixels per LR pixel to
    Nyquist-sample the synthetic aperture NA_obj + NA_illum_max
    (`hr_pixel_size_um`), rounded up to odd.
    """
    return _odd_ceil(setup.lr_pixel_size_um / hr_pixel_size_um(setup, safety_factor))


def canvas_upsampling_factor(setup: SetupConfig) -> int:
    """The *canvas*-driven factor: enough HR pixels per LR pixel that the
    farthest LED's crop window still lies inside the HR array.

    `spectral_ops.led_crop_window` cuts an `lr_shape`-sized rectangle out
    of the HR spectrum, centered on the LED's frequency bin. The HR
    spectrum spans f/(2*lr_pixel_um) each way (f = this factor) and the
    crop itself is 1/(2*lr_pixel_um) wide each way -- independent of
    `lr_shape`, because HR and LR share one frequency spacing -- so the
    LED at |f_led| = max_axis_illumination_na/lam fits iff

        f >= 1 + 2 * lr_pixel_um * max_axis_illumination_na / lam .

    `nyquist_upsampling_factor` alone does NOT imply this: it gives
    f = 2*lr_pixel_um*(NA_obj + NA_illum_max)/lam, which meets the bound
    above only when 2*lr_pixel_um*NA_obj/lam >= 1, i.e. only when the
    camera pixel already Nyquist-samples the objective's own passband. The
    lab's 2.5x/NA 0.07 setup is far from that (1.28 um pixel, 530 nm:
    2*1.28*0.07/0.53 = 0.34), so the canvas came out ~0.66 factors short
    and `led_crop_window` raised "falls outside the HR array" for the
    outermost LEDs once the integer rounding stopped hiding the deficit
    (green 13x13, offset (0, 3) mm, z = 85 mm: 3 of 169 LEDs).

    Note this is a property of the sampling, not of `center_offset_mm`:
    the deficit is the same with a perfectly centered array; the offset
    only pushes the requirement over the next odd integer.
    """
    na_axis = max_axis_illumination_na(setup.led_array)
    return _odd_ceil(1.0 + 2.0 * setup.lr_pixel_size_um * na_axis / setup.wavelength_um)


def upsampling_factor(setup: SetupConfig, safety_factor: float = 2.0) -> int:
    """How many HR pixels span one LR (camera) pixel, rounded up to an
    odd integer so the LR patch cropped from the HR spectrum is centered
    on a single Fourier bin.

    The max of two independent requirements -- resolution
    (`nyquist_upsampling_factor`) and canvas size
    (`canvas_upsampling_factor`). Taking the max is deliberately monotone:
    any setup whose Nyquist factor was already big enough to hold every
    LED's crop window keeps exactly the factor it had before the canvas
    term existed, so its numbers are unchanged.
    """
    return max(nyquist_upsampling_factor(setup, safety_factor),
               canvas_upsampling_factor(setup))


def hr_shape(lr_shape: tuple[int, int], factor: int) -> tuple[int, int]:
    return (lr_shape[0] * factor, lr_shape[1] * factor)


def actual_hr_pixel_size_um(setup: SetupConfig, factor: int) -> float:
    """The HR pixel size actually implied by an integer upsampling
    `factor`, as opposed to `hr_pixel_size_um`'s continuous Nyquist
    target (which `factor` only approximates by rounding up to an odd
    integer). Everything downstream (forward model, reconstruction) must
    use this value, not the target, or the two won't share a Fourier grid.
    """
    return setup.lr_pixel_size_um / factor


def shared_upsampling_factor(setups: list[SetupConfig], safety_factor: float = 2.0) -> int:
    """A single odd integer upsampling factor safe for every setup in
    `setups` -- e.g. one SetupConfig per RGB channel, same LED grid /
    objective / sensor, only `channel` (and so `wavelength_um`) differing.

    Calling `upsampling_factor` per channel independently gives a
    *different* factor per wavelength: `hr_pixel_size_um`'s Nyquist target
    scales with `wavelength_um` in its numerator while `na_synthetic` (the
    denominator) is purely geometric and wavelength-independent, so the
    shortest wavelength always demands the finest (largest) factor. Since
    `actual_hr_pixel_size_um` = `lr_pixel_size_um / factor` and
    `lr_pixel_size_um` doesn't depend on wavelength at all, three channels
    reconstructed with three different per-channel factors end up on three
    different HR grids (different pixel size, different `hr_shape` for the
    same `lr_shape`) -- not comparable pixel-for-pixel, let alone fusable.

    Using the max factor across channels puts every channel on the *same*
    HR grid: the shortest wavelength's requirement (typically blue) drives
    the shared factor, and longer wavelengths end up slightly oversampled
    relative to their own bare Nyquist need, which only costs a bit of
    unnecessary resolution -- harmless, unlike under-sampling.
    """
    if not setups:
        raise ValueError("setups must be non-empty")
    return max(upsampling_factor(s, safety_factor) for s in setups)

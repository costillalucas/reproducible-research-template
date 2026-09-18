"""optics.py -- pupil function and HR/LR sampling geometry.

The pupil is a static circular low-pass mask (NA-limited coherent
transfer function), no aberration term. Updating it in place from data
is EPRY (Ou 2014) -- references/bibliography.yaml id `ou2014`, the
current #1 priority gap -- not implemented yet.
"""
from __future__ import annotations

import numpy as np

from .config import SetupConfig
from .led_array import max_illumination_na


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


def upsampling_factor(setup: SetupConfig, safety_factor: float = 2.0) -> int:
    """How many HR pixels span one LR (camera) pixel, rounded up to an
    odd integer so the LR patch cropped from the HR spectrum is centered
    on a single Fourier bin.
    """
    ratio = setup.lr_pixel_size_um / hr_pixel_size_um(setup, safety_factor)
    factor = int(np.ceil(ratio))
    return factor + 1 if factor % 2 == 0 else factor


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

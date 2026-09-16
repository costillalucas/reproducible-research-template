"""forward_model.py -- simulate the low-resolution image stack an FPM
microscope would capture of a known complex object, one image per LED.

Physical model per LED: shift the object's spectrum into the pupil by
cropping the HR Fourier transform around that LED's illumination spatial
frequency, apply the NA-limited circular pupil, inverse transform, and
record intensity (the camera only sees |field|^2). Optional Poisson shot
noise makes the simulated images behave like real captures.
"""
from __future__ import annotations

import numpy as np

from .optics import circular_pupil
from .spectral_ops import led_crop_window


def simulate_lr_stack(hr_object: np.ndarray, hr_pixel_um: float,
                       led_grid: list[dict], lr_shape: tuple[int, int],
                       lr_pixel_um: float, na: float, wavelength_um: float,
                       peak_photon_count: float | None = None,
                       rng: np.random.Generator | None = None,
                       pupil: np.ndarray | None = None
                       ) -> dict[tuple[int, int], np.ndarray]:
    """Returns {(row, col): intensity_image} for every entry in led_grid.

    `peak_photon_count`, if set, adds Poisson shot noise scaled so the
    brightest pixel across the whole stack has that many expected counts
    -- pass None for a noiseless simulation.

    `pupil`, if given, overrides the default NA-limited circular pupil --
    used by tests to simulate an aberrated pupil (e.g. for exercising
    EPRY pupil recovery in reconstruction.reconstruct).
    """
    if pupil is None:
        pupil = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    hr_spectrum = np.fft.fftshift(np.fft.fft2(hr_object))

    raw = {}
    peak = 0.0
    for entry in led_grid:
        ys, xs = led_crop_window(hr_object.shape, hr_pixel_um, lr_shape,
                                  entry["fx"], entry["fy"])
        patch = hr_spectrum[ys, xs] * pupil
        field = np.fft.ifft2(np.fft.ifftshift(patch))
        intensity = np.abs(field) ** 2
        raw[(entry["row"], entry["col"])] = intensity
        peak = max(peak, float(intensity.max()))

    if peak_photon_count is None or peak <= 0:
        return raw

    if rng is None:
        rng = np.random.default_rng()
    scale = peak_photon_count / peak
    noisy = {}
    for key, intensity in raw.items():
        counts = rng.poisson(intensity * scale).astype(float)
        noisy[key] = counts / scale
    return noisy

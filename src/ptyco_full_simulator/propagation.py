"""propagation.py -- free-space (defocus) wave propagation and Transport
of Intensity Equation (TIE) phase retrieval, groundwork for closing the
gap `tests/test_weak_phase_object_limitation.py` and
docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6 found:
this project's baseline FPM solver cannot recover low-spatial-frequency
phase (on-axis/near-axis illumination carries essentially no phase-to-
amplitude conversion for a weak/low-frequency phase object). Rogalski et
al. 2025 (references/bibliography.yaml id `rogalski2025`, local PDF read
directly) fix exactly this with one extra defocused on-axis capture +
TIE, recovering the low-frequency phase FPM can't see, then merging it
with FPM's own (accurate at high frequency) result.

This module implements the two pieces TIE needs on their own, tested
independently of the FPM solver:
  - `angular_spectrum_propagate`: simulate what a defocused capture would
    look like (or, run backwards, back-propagate one).
  - `solve_tie`: recover phase from a measured axial intensity derivative
    (the classical Poisson-equation-in-Fourier-space TIE solution).

NOT implemented here (left for a future session): actually merging a
TIE-recovered low-frequency phase with an FPM-recovered high-frequency
phase, or wiring this into `pipelines/`. This module is deliberately
scoped to the two physics building blocks alone, each independently
tested against known analytic/simulated ground truth.
"""
from __future__ import annotations

import numpy as np


def angular_spectrum_propagate(field: np.ndarray, distance_um: float,
                                pixel_um: float, wavelength_um: float) -> np.ndarray:
    """Propagate a complex field a `distance_um` further along the optical
    axis (free-space/defocus, no lens) via the angular spectrum method:
    multiply the field's Fourier transform by the exact propagation
    transfer function exp(i*kz*d), inverse transform back. Evanescent
    (kx^2+ky^2 > k^2) components are zeroed, not blown up -- this is what
    makes the angular spectrum method exact and stable, unlike the
    paraxial Fresnel approximation.

    `distance_um` > 0 propagates forward (away from the source, i.e. what
    a camera moved further from the sample would see); negative
    back-propagates. Round-trip (propagate by +d then -d) recovers the
    original field to numerical precision -- see
    tests/test_propagation.py.
    """
    h, w = field.shape
    k0 = 2 * np.pi / wavelength_um
    fy = np.fft.fftfreq(h, d=pixel_um)
    fx = np.fft.fftfreq(w, d=pixel_um)
    FX, FY = np.meshgrid(fx, fy)
    kz_sq = k0**2 - (2 * np.pi * FX) ** 2 - (2 * np.pi * FY) ** 2
    kz = np.sqrt(np.clip(kz_sq, 0, None))  # evanescent (kz_sq < 0) components -> kz=0, phase factor 1
    propagator = np.exp(1j * kz * distance_um) * (kz_sq >= 0)

    spectrum = np.fft.fft2(field)
    return np.fft.ifft2(spectrum * propagator)


def solve_tie(intensity_derivative_dz: np.ndarray, intensity_infocus: np.ndarray,
              pixel_um: float, wavelength_um: float, regularization: float = 1e-3) -> np.ndarray:
    """The classical Transport of Intensity Equation solution: given the
    measured axial derivative of intensity dI/dz (e.g. from a finite
    difference between a slightly-defocused and an in-focus capture) and
    the in-focus intensity itself, recover phase via

        dI/dz = -(lambda / 2*pi) * div(I * grad(phi))

    solved in two nested Poisson-equation-in-Fourier-space steps (Teague
    1983's standard approach): first solve for an auxiliary potential
    psi with laplacian(psi) = -(2*pi/lambda) * dI/dz, then phi from
    div((1/I) * grad(psi)) ... simplified here to the common
    WEAK-ABSORPTION approximation (I roughly constant, e.g. for a phase
    object with mild amplitude variation -- exactly the regime this
    module exists for): laplacian(phi) = -(2*pi / (lambda * I0)) * dI/dz,
    solved directly by a single FFT-domain division by -(fx^2+fy^2),
    with `regularization` added to the zero-frequency singularity (an
    unrecoverable global piston -- same ambiguity phase retrieval always
    has, see multispectral.py's piston-removal note for the analogous
    issue there).

    `intensity_infocus` may be an array (spatially varying I0) or a
    scalar; only its mean is used under this approximation.
    """
    h, w = intensity_derivative_dz.shape
    fy = np.fft.fftfreq(h, d=pixel_um)
    fx = np.fft.fftfreq(w, d=pixel_um)
    FX, FY = np.meshgrid(fx, fy)
    freq_sq = (2 * np.pi * FX) ** 2 + (2 * np.pi * FY) ** 2

    i0_mean = float(np.mean(intensity_infocus))
    rhs_spectrum = np.fft.fft2(-(2 * np.pi / wavelength_um / i0_mean) * intensity_derivative_dz)
    phase_spectrum = rhs_spectrum / (-freq_sq - regularization)
    phase_spectrum[0, 0] = 0.0  # global piston is unrecoverable, pin it to 0

    return np.real(np.fft.ifft2(phase_spectrum))


def _gaussian_lowpass(field: np.ndarray, cutoff_cycles_per_um: float, pixel_um: float) -> np.ndarray:
    h, w = field.shape
    fy = np.fft.fftfreq(h, d=pixel_um)
    fx = np.fft.fftfreq(w, d=pixel_um)
    FX, FY = np.meshgrid(fx, fy)
    mask = np.exp(-(FX**2 + FY**2) / cutoff_cycles_per_um**2)
    return np.real(np.fft.ifft2(np.fft.fft2(field) * mask))


def merge_low_and_high_frequency_phase(phase_tie: np.ndarray, phase_fpm: np.ndarray,
                                        cutoff_cycles_per_um: float, pixel_um: float) -> np.ndarray:
    """Rogalski et al. 2025's actual fix for this project's own found gap
    (docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6,
    tests/test_weak_phase_object_limitation.py): FPM (`reconstruction.py`)
    cannot recover low-spatial-frequency phase at all (on/near-axis
    illumination carries essentially no phase-to-amplitude conversion),
    but DOES recover high-frequency phase well once there's enough
    amplitude/spatial structure to bootstrap from. TIE (`solve_tie`) is
    the physical complement: its transfer function is strong at low
    spatial frequency and weak at high frequency (defocus barely converts
    fine phase detail into detectable intensity contrast over a short
    propagation distance).

    Spectral merge (a smooth Gaussian low-pass split, not a hard cutoff,
    to avoid ringing): take TIE's own low-frequency content, and FPM's
    own HIGH-frequency content (its full spectrum minus its own
    low-frequency content -- this is what actually discards FPM's wrong,
    noise-dominated low-frequency estimate, not just adds TIE on top of
    it). `cutoff_cycles_per_um` should sit between the two techniques'
    respective validity ranges -- there's no universal number, it depends
    on the defocus distance used for TIE and the LED array's synthetic
    aperture for FPM; pick it by inspecting where each technique's own
    accuracy (compared to a known object) actually falls off, the way
    tests/test_propagation.py's merge test does.

    CAVEAT found interactively while testing this (2026-09-17, see
    docs/roadmap_agentic_multispectral_pipeline.md): this post-hoc
    spectral splice does NOT reliably outperform just using TIE's own
    result alone across the mixed-frequency test objects tried -- FPM's
    high-frequency recovery itself degrades when a poorly-handled
    low-frequency component is also present in the same object (the
    reconstruction couples frequencies nonlinearly through the shared
    amplitude estimate; they aren't independently recoverable channels).
    Kept here as a general-purpose spectral utility and because it's
    still a large improvement over FPM alone, but
    `reconstruction.reconstruct`'s `initial_object` parameter -- seeding
    FPM's OWN iterative solver with TIE's phase instead of splicing two
    already-finished results together -- tested much more consistently
    well; see tests/test_tie_informed_initialization.py and prefer that
    approach.
    """
    tie_low = _gaussian_lowpass(phase_tie, cutoff_cycles_per_um, pixel_um)
    fpm_low = _gaussian_lowpass(phase_fpm, cutoff_cycles_per_um, pixel_um)
    fpm_high = phase_fpm - fpm_low
    return tie_low + fpm_high

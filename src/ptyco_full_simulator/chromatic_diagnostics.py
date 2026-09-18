"""chromatic_diagnostics.py -- roadmap open question #2
(docs/roadmap_agentic_multispectral_pipeline.md, "Preguntas abiertas /
riesgos"): does this project's real objective (`ObjectiveConfig` in
config.py) have chromatic aberration between the 3 RGB channels, or is it
already achromatic? The agreed plan was "diagnostico gratis con los datos
reales ya existentes en data/<channel>/... -- comparar registro/foco entre
los 3 canales de un mismo target; si hay corrimiento lateral o de foco
entre red/green/blue, ahi esta medida la aberracion cromatica
directamente." There is NO real lab data in this Codespace (data/ has no
TIFF captures, only the provenance registry files) -- this module is
built and validated against a KNOWN synthetic shift/defocus so it's ready
to run the moment real captures exist, same "build now, validate
synthetically" pattern as io_utils.load_defocus_pair.

Two independent measurements, both taking the 3 channels' already-
registered (same hr_pixel_um/hr_shape, see optics.shared_upsampling_factor)
reconstructed complex fields as input:
  - `measure_lateral_shift_px`: sub-pixel (dy, dx) registration offset
    between two channels' amplitude images, via normalized cross-power
    spectrum (phase correlation) with a parabolic sub-pixel peak fit.
  - `measure_focus_offset_um`: relative focus offset between two
    channels, by searching over candidate defocus distances
    (`propagation.angular_spectrum_propagate`) for the one that makes one
    channel's field best match the other's amplitude.

`chromatic_registration_report` runs both, pairwise, across red-green and
green-blue (green is the natural reference: middle wavelength, and this
project's `led_calibration.py`/`reconstruction.py` already default to it
as the reference channel in several tests).

HONEST LIMITS (found while validating against synthetic ground truth, see
tests/test_chromatic_diagnostics.py): both measurements are validated
against ideal (ground-truth) complex fields, where they are accurate to
a fraction of a pixel / a few um. Run through this project's own
imperfect Wirtinger flow reconstruction instead, measurement noise grows
with reconstruction error -- this diagnostic can only be as good as the
reconstruction it's measuring, so a run that itself has a weak-phase-
object or local-minimum problem (see reconstruction.py's own documented
limitations) will report a noisier, less trustworthy chromatic-shift
estimate, not a wrong one silently taken as gospel. Always sanity-check
against the run's own `metrics.convergence_summary`/`compare_to_ground_truth`
(when ground truth exists) before trusting this diagnostic's output on a
poorly-converged reconstruction.
"""
from __future__ import annotations

import numpy as np

from . import propagation as prop


def measure_lateral_shift_px(amp_reference: np.ndarray, amp_target: np.ndarray) -> tuple[float, float]:
    """Sub-pixel (dy, dx) shift that best aligns `amp_target` onto
    `amp_reference`, via the normalized cross-power spectrum (phase
    correlation, Kuglin & Hutson 1975) plus a parabolic 3-point fit
    around the integer-pixel peak in each axis for sub-pixel precision.
    Positive dy/dx means `amp_target` is shifted toward +row/+col
    relative to `amp_reference` (i.e. shifting amp_target by (-dy, -dx)
    would register it onto amp_reference).

    Both inputs must be the same shape (already on the shared HR grid,
    see optics.shared_upsampling_factor -- this function does NOT resize
    anything).
    """
    if amp_reference.shape != amp_target.shape:
        raise ValueError(f"shape mismatch: {amp_reference.shape} vs {amp_target.shape}")
    h, w = amp_reference.shape
    fa = np.fft.fft2(amp_reference - amp_reference.mean())
    fb = np.fft.fft2(amp_target - amp_target.mean())
    # fb * conj(fa) (not fa * conj(fb)) so the correlation peak lands at
    # +shift-of-target-relative-to-reference -- verified against a known
    # injected shift in tests/test_chromatic_diagnostics.py (the other
    # order gives the exact negation).
    cross = fb * np.conj(fa)
    cross /= np.maximum(np.abs(cross), 1e-12)
    corr = np.fft.ifft2(cross).real

    py, px = np.unravel_index(np.argmax(corr), corr.shape)

    def _subpixel_offset(c_minus, c_zero, c_plus):
        denom = c_minus - 2 * c_zero + c_plus
        if abs(denom) < 1e-12:
            return 0.0
        return 0.5 * (c_minus - c_plus) / denom

    dy_sub = _subpixel_offset(corr[(py - 1) % h, px], corr[py, px], corr[(py + 1) % h, px])
    dx_sub = _subpixel_offset(corr[py, (px - 1) % w], corr[py, px], corr[py, (px + 1) % w])

    dy = (py + dy_sub + h // 2) % h - h // 2
    dx = (px + dx_sub + w // 2) % w - w // 2
    return float(dy), float(dx)


def measure_focus_offset_um(field_reference: np.ndarray, field_target: np.ndarray,
                             hr_pixel_um: float, wavelength_target_um: float,
                             search_range_um: float = 50.0, n_search: int = 41) -> dict:
    """Relative focus offset of `field_target` vs. `field_reference`:
    searches candidate defocus distances in
    [-search_range_um, +search_range_um], propagates `field_target` by
    each (`propagation.angular_spectrum_propagate`), and picks the
    distance whose propagated amplitude correlates best with
    `field_reference`'s amplitude. `offset_um` is the CORRECTION applied
    to `field_target` (not the raw defocus): if `field_target`'s own
    focal plane sits some distance `+d` further along the optical axis
    than `field_reference`'s (as if `field_reference` had been forward-
    propagated by `+d` to produce it), this returns `offset_um` close to
    `-d` -- the propagation that undoes it. See
    tests/test_chromatic_diagnostics.py for the sign convention verified
    against a known injected defocus.

    Both fields must already be laterally registered (see
    `measure_lateral_shift_px` -- run that first and shift/roll
    field_target if there is a meaningful lateral offset, otherwise a
    lateral chromatic shift can masquerade as a spurious focus offset
    here, since neither measurement disentangles the other).

    Returns {"offset_um": float, "correlation_at_offset": float,
             "correlation_at_zero": float} -- the last two let the caller
    judge whether the fit is actually informative (a flat, low-contrast
    correlation curve means the search found nothing meaningful, not a
    confident zero offset).
    """
    ref_amp = np.abs(field_reference)
    candidates = np.linspace(-search_range_um, search_range_um, n_search)
    correlations = []
    for dz in candidates:
        propagated = prop.angular_spectrum_propagate(field_target, float(dz), hr_pixel_um, wavelength_target_um)
        target_amp = np.abs(propagated)
        c = float(np.corrcoef(ref_amp.ravel(), target_amp.ravel())[0, 1])
        correlations.append(c)
    correlations = np.array(correlations)
    best_idx = int(np.argmax(correlations))
    zero_idx = int(np.argmin(np.abs(candidates)))
    return {
        "offset_um": float(candidates[best_idx]),
        "correlation_at_offset": float(correlations[best_idx]),
        "correlation_at_zero": float(correlations[zero_idx]),
    }


def chromatic_registration_report(fields: dict, hr_pixel_um: float, wavelengths_um: dict,
                                   focus_search_range_um: float = 50.0) -> dict:
    """Pairwise chromatic registration/focus report across red-green and
    green-blue (green as the shared reference channel). `fields` and
    `wavelengths_um` must both be keyed by "red"/"green"/"blue", with
    `fields[channel]` the channel's reconstructed complex object on the
    shared HR grid (e.g. `reconstruct_all_channels(...)["channels"][ch]["object"]`).

    Returns {"red_vs_green": {"lateral_shift_px": (dy, dx), "focus": {...}},
             "blue_vs_green": {same shape}}.
    """
    report = {}
    for label, other in (("red_vs_green", "red"), ("blue_vs_green", "blue")):
        ref_amp = np.abs(fields["green"])
        other_amp = np.abs(fields[other])
        dy, dx = measure_lateral_shift_px(ref_amp, other_amp)
        focus = measure_focus_offset_um(
            fields["green"], fields[other], hr_pixel_um, wavelengths_um[other],
            search_range_um=focus_search_range_um,
        )
        report[label] = {"lateral_shift_px": (dy, dx), "focus": focus}
    return report

"""multispectral.py -- roadmap milestones 2b.i and 2b.ii
(docs/roadmap_agentic_multispectral_pipeline.md).

2b.i: multi-wavelength phase unwrapping via a synthetic ("beat")
wavelength, adapted from Shen/Tian et al. 2025 "Dual-wavelength Fourier
Ptychographic Topography" (references/bibliography.yaml id `shen2025`,
arXiv:2512.08883).

Adaptation from their setting to ours: they measure REFLECTIVE surface
height h, where round-trip path gives phi = (4*pi/lambda) * h (light
travels to the surface and back). We measure a TRANSMISSIVE phase object,
where phi = (2*pi/lambda) * OPL (single pass, OPL = optical path length =
integral of refractive index contrast along the path -- see
docs/roadmap_agentic_multispectral_pipeline.md point 1.5 for how OPL feeds
into the milestone 2b.ii dispersion fit). Everything below is written in
terms of a general `path_factor` (2*pi for transmission, 4*pi for
reflection) so both conventions share one implementation; `unwrap_two_channel`
defaults to the transmissive 2*pi convention this project actually needs.

This is an ADAPTATION, not a byte-for-byte reimplementation: the wrap-number
search (the part with the clearest, checkable equations from the paper) is
implemented faithfully; the refinement stage (circular TV + soft bounds,
solved by convex optimization in the paper) is approximated here with a
simple smoothed-TV + soft-bound gradient descent, since the paper's exact
solver details weren't available beyond its abstract/equations. See
docs/roadmap_agentic_multispectral_pipeline.md for that caveat in context.

2b.ii: fit the sample's dispersion from the unwrapped multi-channel OPL
maps 2b.i produces -- `fit_cauchy_dispersion` and
`resolve_thickness_and_dispersion` at the bottom of this file. No paper
found for this part in the literature check
(docs/literature_check_multispectral_dispersion.md) -- this is this
project's own design, and working through it surfaced a real degeneracy
the original roadmap wording missed: see `fit_cauchy_dispersion`'s
docstring.
"""
from __future__ import annotations

import numpy as np


def synthetic_wavelength(wavelength1_um: float, wavelength2_um: float) -> float:
    """The beat/synthetic wavelength of two illumination wavelengths:
    lambda_s = lambda1 * lambda2 / |lambda1 - lambda2|. Always larger than
    either input -- that's the whole point: it extends the unambiguous
    range past what either wavelength alone can resolve.
    """
    if wavelength1_um == wavelength2_um:
        raise ValueError("wavelength1 and wavelength2 must differ to form a synthetic wavelength")
    return wavelength1_um * wavelength2_um / abs(wavelength1_um - wavelength2_um)


def unambiguous_opl_half_range(wavelength1_um: float, wavelength2_um: float,
                                path_factor: float = 2 * np.pi) -> float:
    """Half-width of the OPL range the synthetic-wavelength method can
    resolve without ambiguity, centered on 0: derived from the combined
    phase difference phi1 - phi2 = path_factor*OPL/lambda_s staying within
    (-pi, pi] as OPL varies continuously from 0. An OPL outside
    +/- this value can, even with a correct search, be resolved to the
    wrong (k1, k2) pair -- a real limit of the two-wavelength technique
    itself (see `unwrap_two_channel`'s docstring), not a bug.
    """
    lambda_s = synthetic_wavelength(wavelength1_um, wavelength2_um)
    return np.pi * lambda_s / path_factor


def wrap_phase(phase: np.ndarray) -> np.ndarray:
    """Wrap to (-pi, pi], the convention a phase-retrieval solver's raw
    output already respects (np.angle does this too) -- exposed here so
    callers building synthetic test phases don't need to reach into numpy
    directly.
    """
    return np.angle(np.exp(1j * np.asarray(phase)))


def opl_from_wrapped_phase(phase_wrapped: np.ndarray, k: np.ndarray | int,
                            wavelength_um: float, path_factor: float = 2 * np.pi) -> np.ndarray:
    """The optical path length (same units as `wavelength_um`) implied by
    wrapped phase `phase_wrapped` if its true (unwrapped) 2*pi multiple is
    `k`: OPL = (phase_wrapped + 2*pi*k) * wavelength_um / path_factor.
    """
    return (np.asarray(phase_wrapped) + 2 * np.pi * np.asarray(k)) * wavelength_um / path_factor


def search_wrap_numbers(phase1_wrapped: np.ndarray, phase2_wrapped: np.ndarray,
                         wavelength1_um: float, wavelength2_um: float,
                         path_factor: float = 2 * np.pi,
                         k_range: range = range(-4, 5)) -> dict:
    """Per-pixel search over integer wrap-number pairs (k1, k2), picking
    the pair whose implied OPLs agree best across the two channels:

        (K1, K2) = argmin_{k1,k2 in k_range} |OPL1(k1) - OPL2(k2)|

    This is the core of the synthetic-wavelength method (Shen et al.
    2025, adapted -- see module docstring): it enforces cross-wavelength
    consistency directly on physical OPL rather than on the raw phase
    difference, which is what makes it robust to noise near a wrap
    boundary (a small phase perturbation can flip which single integer k
    "looks closest", but it rarely flips which (k1, k2) PAIR gives the
    best cross-wavelength agreement).

    Returns {"K1", "K2": integer arrays (same shape as the inputs),
             "opl1", "opl2": each channel's candidate OPL at the winning
                 k, "opl_estimate": their average, "opl_min", "opl_max":
                 elementwise min/max of opl1, opl2 (the two channels'
                 disagreement band, used as soft bounds in
                 `refine_opl_tv`), "disagreement": |opl1 - opl2| at the
                 winning pair -- large values flag pixels where even the
                 best (k1, k2) pair disagrees a lot, a useful per-pixel
                 confidence signal for a future Confidence/QC agent
                 (docs/roadmap_agentic_multispectral_pipeline.md section 2)}.
    """
    phase1_wrapped = np.asarray(phase1_wrapped, dtype=float)
    phase2_wrapped = np.asarray(phase2_wrapped, dtype=float)
    if phase1_wrapped.shape != phase2_wrapped.shape:
        raise ValueError(f"shape mismatch: {phase1_wrapped.shape} vs {phase2_wrapped.shape}")

    best_disagreement = np.full(phase1_wrapped.shape, np.inf)
    best_K1 = np.zeros(phase1_wrapped.shape, dtype=int)
    best_K2 = np.zeros(phase1_wrapped.shape, dtype=int)
    best_opl1 = np.zeros(phase1_wrapped.shape)
    best_opl2 = np.zeros(phase1_wrapped.shape)

    for k1 in k_range:
        opl1 = opl_from_wrapped_phase(phase1_wrapped, k1, wavelength1_um, path_factor)
        for k2 in k_range:
            opl2 = opl_from_wrapped_phase(phase2_wrapped, k2, wavelength2_um, path_factor)
            disagreement = np.abs(opl1 - opl2)
            better = disagreement < best_disagreement
            best_disagreement = np.where(better, disagreement, best_disagreement)
            best_K1 = np.where(better, k1, best_K1)
            best_K2 = np.where(better, k2, best_K2)
            best_opl1 = np.where(better, opl1, best_opl1)
            best_opl2 = np.where(better, opl2, best_opl2)

    return {
        "K1": best_K1, "K2": best_K2,
        "opl1": best_opl1, "opl2": best_opl2,
        "opl_estimate": 0.5 * (best_opl1 + best_opl2),
        "opl_min": np.minimum(best_opl1, best_opl2),
        "opl_max": np.maximum(best_opl1, best_opl2),
        "disagreement": best_disagreement,
    }


def refine_opl_tv(opl_estimate: np.ndarray, opl_min: np.ndarray, opl_max: np.ndarray,
                   tv_weight: float = 0.05, bound_weight: float = 1.0,
                   iterations: int = 200, step_size: float = 0.05,
                   eps: float = 1e-6) -> np.ndarray:
    """Global refinement of the per-pixel OPL estimate: smooths it (total
    variation) while softly penalizing excursions outside each pixel's own
    [opl_min, opl_max] disagreement band from `search_wrap_numbers`, via
    plain gradient descent on

        0.5*||H - opl_estimate||^2 + tv_weight*TV(H) + bound_weight*soft_bound(H)

    Simplified relative to Shen et al. 2025's convex solver (see module
    docstring) -- a smoothed isotropic TV (sqrt(gx^2 + gy^2 + eps), so it's
    differentiable everywhere) rather than their circular-TV formulation,
    solved by gradient descent rather than ADMM/proximal splitting.
    "Soft bounds" (not hard clipping) means a pixel CAN end up outside
    [opl_min, opl_max] if neighboring pixels pull it there through the TV
    term -- that's deliberate, it's what lets this preserve a genuine
    discontinuity instead of clamping it away.

    Caution on `step_size`: the bound-penalty subgradient has constant
    magnitude (+/-1) regardless of distance from the bound, so
    `step_size * bound_weight` too large makes pixels near a bound
    oscillate across it every iteration and INCREASE total variation
    instead of reducing it (found empirically while testing this function
    -- the default 0.2 from a first pass did exactly that). Keep
    `step_size` small (this default, 0.05, was picked because it's stable
    across `bound_weight` from 0.02 to 1.0 on this project's test cases).
    """
    H = opl_estimate.copy().astype(float)
    for _ in range(iterations):
        data_grad = H - opl_estimate

        gy = np.zeros_like(H)
        gx = np.zeros_like(H)
        gy[:-1, :] = H[1:, :] - H[:-1, :]
        gx[:, :-1] = H[:, 1:] - H[:, :-1]
        grad_mag = np.sqrt(gx**2 + gy**2 + eps)
        ny, nx = gy / grad_mag, gx / grad_mag
        # Divergence of the normalized gradient field = TV gradient (finite-difference adjoint).
        div = np.zeros_like(H)
        div[:-1, :] += ny[:-1, :]
        div[1:, :] -= ny[:-1, :]
        div[:, :-1] += nx[:, :-1]
        div[:, 1:] -= nx[:, :-1]
        tv_grad = -div

        below = H < opl_min
        above = H > opl_max
        bound_grad = np.where(below, -1.0, np.where(above, 1.0, 0.0))

        H -= step_size * (data_grad + tv_weight * tv_grad + bound_weight * bound_grad)

    return H


def unwrap_two_channel(phase1_wrapped: np.ndarray, phase2_wrapped: np.ndarray,
                        wavelength1_um: float, wavelength2_um: float,
                        path_factor: float = 2 * np.pi, k_range: range = range(-4, 5),
                        refine: bool = True, **refine_kwargs) -> dict:
    """The full milestone 2b.i step for one channel pair: wrap-number
    search, then (by default) the TV+soft-bound refinement. See
    `search_wrap_numbers` and `refine_opl_tv` for what each stage does and
    what's returned in the dict beyond `opl` (the final estimate: refined
    if `refine=True`, else the raw per-pixel `opl_estimate`).

    Unambiguous OPL range: see `unambiguous_opl_half_range` -- an OPL
    outside +/- that value can be recovered wrong even with a correct
    search, a real limit of the two-wavelength method itself, not a bug
    (see tests/test_multispectral_unwrapping.py).
    """
    search = search_wrap_numbers(phase1_wrapped, phase2_wrapped, wavelength1_um,
                                  wavelength2_um, path_factor, k_range)
    opl = (refine_opl_tv(search["opl_estimate"], search["opl_min"], search["opl_max"], **refine_kwargs)
           if refine else search["opl_estimate"])
    return {**search, "opl": opl}


def fit_cauchy_dispersion(wavelengths_um: list[float], opls: list[np.ndarray]) -> dict:
    """Fit a 2-parameter Cauchy-shaped model OPL(lambda) = C + D/lambda^2
    to 2+ channels' unwrapped OPL maps (2b.i's output), per pixel.

    C and D are what unwrapped multi-wavelength OPL can actually identify
    about the sample -- NOT the sample's baseline refractive index A,
    dispersion coefficient B, and thickness t individually. Physically,
    n(lambda) = A + B/lambda^2 and OPL(lambda) = n(lambda) * t, so

        OPL(lambda) = A*t + (B*t)/lambda^2 = C + D/lambda^2,  C := A*t,  D := B*t

    Any other (A', B', t') with A'*t' = C and B'*t' = D produces the exact
    same OPL at every wavelength -- a thicker sample with weaker dispersion
    is indistinguishable from a thinner one with stronger dispersion, from
    phase-only multi-wavelength measurements alone. This is a real
    degeneracy, not a limitation of this fit's method: no amount of
    additional wavelengths breaks it, since the model only ever has 2
    identifiable degrees of freedom. Recovering A, B, t individually needs
    one more piece of external information -- see
    `resolve_thickness_and_dispersion`. (The original roadmap milestone
    2b.ii wording assumed A, B, t were "3 unknowns, 3 equations, exactly
    determined" from 3 channels; that undercounts the degeneracy -- see
    docs/roadmap_agentic_multispectral_pipeline.md's note where this is
    corrected.)

    With exactly 2 channels this is an exact 2x2 solve (0 residual by
    construction, C and D fit any 2 points on a line in 1/lambda^2 space
    exactly). With 3+ channels it's an ordinary least-squares fit,
    over-determined by (n_channels - 2) equations -- the noise-averaging
    benefit of using all 3 RGB channels together instead of picking any 2.

    Returns {"C", "D": arrays shaped like one input `opls` entry,
             "residuals": array shaped (n_channels, *pixel_shape) -- large
                 residuals mean the Cauchy model itself doesn't fit this
                 pixel well (e.g. absorption/resonance near the sample's
                 wavelengths, where the 2-parameter Cauchy approximation
                 breaks down), a useful per-pixel diagnostic independent
                 of measurement noise}.
    """
    if len(wavelengths_um) < 2:
        raise ValueError("need at least 2 channels to fit a 2-parameter model")
    if len(wavelengths_um) != len(opls):
        raise ValueError(f"got {len(wavelengths_um)} wavelengths but {len(opls)} OPL maps")

    design = np.stack([np.ones(len(wavelengths_um)), 1.0 / np.asarray(wavelengths_um) ** 2], axis=1)
    stacked = np.stack([np.asarray(o, dtype=float) for o in opls], axis=0)
    pixel_shape = stacked.shape[1:]
    flat = stacked.reshape(len(wavelengths_um), -1)

    coeffs, *_ = np.linalg.lstsq(design, flat, rcond=None)
    C = coeffs[0].reshape(pixel_shape)
    D = coeffs[1].reshape(pixel_shape)

    pred_flat = design @ coeffs
    residuals = (flat - pred_flat).reshape((len(wavelengths_um),) + pixel_shape)

    return {"C": C, "D": D, "residuals": residuals}


def resolve_thickness_and_dispersion(C: np.ndarray, D: np.ndarray, baseline_index_A: float) -> dict:
    """Break `fit_cauchy_dispersion`'s A/B/t degeneracy using an
    EXTERNALLY known baseline refractive index `baseline_index_A` (e.g. a
    literature value for the sample material/medium) -- this cannot come
    from the OPL data itself, see `fit_cauchy_dispersion`.

    t = C / baseline_index_A ; B = D / t (undefined, returned as NaN,
    where |t| is ~0 -- no measurable optical path implies no thickness to
    divide by, and B is meaningless there regardless of A).

    A WRONG `baseline_index_A` silently returns a self-consistent but
    wrong (t, B) -- the returned OPL(lambda) = (A + B/lambda^2)*t still
    matches the data exactly either way, because C and D (the only
    quantities the data constrains) are unchanged. There is no way to
    detect a wrong baseline index from this data alone; it must come from
    independent knowledge of the sample.
    """
    t = C / baseline_index_A
    with np.errstate(divide="ignore", invalid="ignore"):
        B = np.where(np.abs(t) > 1e-12, D / t, np.nan)
    return {"thickness_um": t, "dispersion_B": B, "baseline_index_A": baseline_index_A}


def reference_phase_to_background(phase_wrapped: np.ndarray, background_mask: np.ndarray) -> np.ndarray:
    """Remove a reconstruction's arbitrary global phase piston using a
    region of the field of view known to have zero OPL (bare medium, no
    sample) -- found while building the 2a->2b.i->2b.ii integration test,
    not anticipated when 2b.i was first written.

    Phase retrieval (Wirtinger flow / ePIE-style, `reconstruction.py`)
    recovers the object's complex field only up to an arbitrary global
    phase factor exp(i*theta): |field|^2 (what the camera measures) is
    invariant to ANY real theta, not just multiples of 2*pi, and each
    channel is reconstructed independently in `reconstruct_all_channels`
    (milestone 2a) -- so red, green, blue each carry their OWN unknown
    theta. `search_wrap_numbers`'s cross-wavelength consistency argument
    assumes phase is already referenced to a true OPL=0 point; with an
    unremoved per-channel theta it isn't, and the search has no way to
    tell a real wrap number apart from an arbitrary offset -- IT WILL
    SILENTLY PRODUCE A WRONG (K1, K2) instead of failing loudly, since a
    wrong global offset just looks like a different (but still
    self-consistent) height, exactly the kind of failure
    `docs/roadmap_agentic_multispectral_pipeline.md`'s Confidence/QC agent
    (section 2) is meant to catch downstream.

    Fix used here: subtract each channel's own mean phase over a region
    known a priori to have zero OPL (e.g. bare substrate/medium visible in
    the field of view) BEFORE calling `search_wrap_numbers` -- this only
    removes the constant piston, not any real spatial structure. If no
    such region exists in a given field of view, the piston is NOT
    recoverable from a single reconstruction alone; that's a real limit of
    this approach, not a bug in this function.
    """
    if not np.any(background_mask):
        raise ValueError("background_mask has no True pixels -- nothing to reference against")
    piston = np.mean(phase_wrapped[background_mask])
    return wrap_phase(phase_wrapped - piston)


def couple_rgb_channels(phases_wrapped: dict, wavelengths_um: dict, background_mask: np.ndarray,
                         baseline_index_A: float | None = None,
                         k_range: range = range(-4, 5), **unwrap_kwargs) -> dict:
    """The full milestone 2b step, wiring together everything above:
    given each RGB channel's raw (piston-ambiguous) wrapped phase from an
    independent per-channel reconstruction (milestone 2a,
    `pipelines/reconstruct_multispectral_independent.py`) plus a region of
    the field of view known to be bare medium, resolve each channel's
    piston, unwrap via the red-green and green-blue synthetic-wavelength
    pairs, and fit the sample's Cauchy dispersion.

    `phases_wrapped`, `wavelengths_um`: dicts keyed "red", "green", "blue".

    Per-channel OPL for the dispersion fit comes from each pair's own
    per-channel candidate (`search_wrap_numbers`'s "opl1"/"opl2"), NOT the
    pair's refined/averaged estimate -- averaging red and green together
    before fitting would erase exactly the small cross-channel difference
    that IS the dispersion signal `fit_cauchy_dispersion` needs to see.
    Green is estimated twice (once per pair it's in) and averaged, a small
    extra consistency check.

    Returns {"opl": {"red", "green", "blue": array}, "fit":
    fit_cauchy_dispersion's return dict, "resolved":
    resolve_thickness_and_dispersion's return dict (or None if
    `baseline_index_A` is None), "pair_disagreement": {"red_green",
    "green_blue": array} -- each pair's cross-channel OPL disagreement, a
    per-pixel confidence diagnostic (large values flag pixels where even
    the best wrap-number pair didn't agree well)}.
    """
    channels = ("red", "green", "blue")
    referenced = {ch: reference_phase_to_background(phases_wrapped[ch], background_mask)
                  for ch in channels}

    rg = unwrap_two_channel(referenced["red"], referenced["green"],
                             wavelengths_um["red"], wavelengths_um["green"],
                             k_range=k_range, **unwrap_kwargs)
    gb = unwrap_two_channel(referenced["green"], referenced["blue"],
                             wavelengths_um["green"], wavelengths_um["blue"],
                             k_range=k_range, **unwrap_kwargs)

    opl = {
        "red": rg["opl1"],
        "green": 0.5 * (rg["opl2"] + gb["opl1"]),
        "blue": gb["opl2"],
    }

    fit = fit_cauchy_dispersion([wavelengths_um[ch] for ch in channels], [opl[ch] for ch in channels])
    resolved = (resolve_thickness_and_dispersion(fit["C"], fit["D"], baseline_index_A)
                if baseline_index_A is not None else None)

    return {
        "opl": opl, "fit": fit, "resolved": resolved,
        "pair_disagreement": {"red_green": rg["disagreement"], "green_blue": gb["disagreement"]},
    }

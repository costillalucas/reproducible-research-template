"""led_calibration.py -- roadmap milestone 4, "Agente #2"
(docs/roadmap_agentic_multispectral_pipeline.md): LED illumination-angle
self-calibration, adapted from Eckert/Phillips/Waller 2018 "Efficient
Illumination Angle Self-Calibration in Fourier Ptychography"
(references/bibliography.yaml id `eckert2018`,
references/papers/2018/SelfCalibration_Eckert_1804.03299.pdf -- read
directly from the local PDF, not just the abstract, for this one).

Gap this closes: `led_array.build_led_grid` computes illumination angles
purely from `LEDArrayConfig`'s assumed geometry (pitch, z-distance,
centering) -- a real LED array is never perfectly aligned to that
assumption (bumped, rotated slightly, mismeasured pitch/distance), and
`reconstruct_real_images.py`/`reconstruct_multispectral_independent.py`
had no way to correct for that.

ADAPTATION, not a full reimplementation (scoped down given time budget --
see docs/roadmap_agentic_multispectral_pipeline.md for the explicit
comparison against the paper's full method):

- Implemented: their **spectral correlation (SC) calibration** (paper
  Eq. 7) -- a small local integer grid search per LED, in k-space, that
  finds the position shift best explaining the measured LR amplitude
  given a current object-spectrum estimate. Implemented as
  `spectral_correlation_correction`.
- Implemented: their **rigid source projection** regularization (paper
  Fig. 3a's "Rigid Source Projection" step, and Algorithm 1 lines 9-12's
  RANSAC-based transform) -- fit ONE similarity transform (rotation +
  uniform scale + translation) from the nominal LED geometry to the
  per-LED SC-corrected estimates, then project every LED (not just the
  ones SC corrected well) through that single transform. Implemented as
  `fit_similarity_transform` / `apply_similarity_transform`. Simplified
  to plain least squares (closed-form, exact for a 2D similarity
  transform posed as one complex-linear regression) rather than their
  RANSAC (robust to gross outliers, which plain least squares is not --
  a real limitation if some LEDs are badly miscalibrated by SC, not
  just noisy).
- NOT implemented: their **brightfield (BF) calibration** pre-processing
  stage (Algorithm 1's circular-edge-detection on each brightfield
  image's own Fourier spectrum, used to bootstrap a good initial
  estimate before SC calibration even starts). Skipped for scope --
  this module instead bootstraps SC calibration directly from a rough
  reconstruction using the (possibly wrong) NOMINAL LED grid, which the
  paper's own Fig. 3d shows converges slower/less robustly than with BF
  pre-processing, especially for larger misalignments. A real BF stage
  would be the natural next increment here.
- Simplification of coordinate space: both the SC search and the
  similarity-transform fit operate directly in illumination spatial
  frequency (fx, fy) [cycles/um] space -- what `led_crop_window` actually
  consumes -- rather than the paper's LED-array mm-space geometry. For
  small misalignments this is physically equivalent (fx, fy is a smooth,
  locally near-linear function of LED position); it would break down for
  large `z_distance_mm` errors, which change the nonlinear sin(theta)
  relationship enough that a linear fit in (fx, fy) space and one in
  mm-space would disagree. Not tested here.
"""
from __future__ import annotations

import numpy as np

from .spectral_ops import led_crop_window
from .optics import circular_pupil


def perturb_led_grid_rigid(led_grid: list[dict], shift_fx: float = 0.0, shift_fy: float = 0.0,
                            rotation_rad: float = 0.0, scale: float = 1.0) -> list[dict]:
    """TEST/SIMULATION helper: apply a known rigid misalignment (rotation +
    uniform scale + translation, directly in (fx, fy) space -- see module
    docstring's coordinate-space caveat) to every LED's illumination
    spatial frequency. Stands in for a real LED array's actual physical
    misalignment from its assumed design geometry: `forward_model.
    simulate_lr_stack` should be given the PERTURBED ("true") grid to
    simulate what a misaligned real array would actually capture, while
    reconstruction/calibration starts from the ORIGINAL ("assumed")
    `led_array.build_led_grid` output, exactly like a real experiment.
    """
    a = scale * np.exp(1j * rotation_rad)
    b = shift_fx + 1j * shift_fy
    perturbed = []
    for entry in led_grid:
        z = entry["fx"] + 1j * entry["fy"]
        w = a * z + b
        perturbed.append({**entry, "fx": float(w.real), "fy": float(w.imag)})
    return perturbed


def spectral_correlation_correction(obj_spectrum: np.ndarray, hr_pixel_um: float,
                                     led_grid: list[dict], lr_images: dict,
                                     lr_pixel_um: float, na: float, wavelength_um: float,
                                     delta_k: float, search_range: tuple = (-1, 0, 1)) -> dict:
    """Eckert et al. 2018 Eq. 7, adapted: for each LED with a captured
    image, search integer perturbations n in `search_range` x
    `search_range` of the assumed illumination frequency (fx, fy) by
    n*delta_k, and keep whichever perturbation makes the CURRENT object
    spectrum estimate's predicted LR amplitude best match the measured
    amplitude. `obj_spectrum` should come from a reconstruction run with
    at least a few iterations under the (possibly wrong) nominal LED
    grid -- SC calibration refines an already-reasonable object estimate,
    it doesn't bootstrap one from nothing (that's what the paper's BF
    calibration stage is for, not implemented here -- see module
    docstring).

    `delta_k`: the k-space grid step to search over, in cycles/um -- the
    paper uses the Nyquist-limited angular resolution set by the
    reconstructed field of view (2/FoV); a reasonable default here is
    `1 / (hr_shape[axis] * hr_pixel_um)` for whichever axis, exposed as a
    parameter rather than derived internally so callers can tune search
    granularity independently of `obj_spectrum`'s actual shape.

    Returns {(row, col): (corrected_fx, corrected_fy)} for every LED with
    a captured image in `lr_images`.
    """
    hr_shape = obj_spectrum.shape
    lr_shape = next(iter(lr_images.values())).shape
    pupil = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)

    corrected = {}
    for entry in led_grid:
        key = (entry["row"], entry["col"])
        if key not in lr_images:
            continue
        meas_amp = np.sqrt(np.clip(lr_images[key], 0, None))

        best_cost = np.inf
        best_fx, best_fy = entry["fx"], entry["fy"]
        for nx in search_range:
            for ny in search_range:
                fx = entry["fx"] + nx * delta_k
                fy = entry["fy"] + ny * delta_k
                ys, xs = led_crop_window(hr_shape, hr_pixel_um, lr_shape, fx, fy)
                patch = obj_spectrum[ys, xs] * pupil
                field = np.fft.ifft2(np.fft.ifftshift(patch))
                cost = float(np.sum((np.abs(field) - meas_amp) ** 2))
                if cost < best_cost:
                    best_cost, best_fx, best_fy = cost, fx, fy
        corrected[key] = (best_fx, best_fy)
    return corrected


def fit_similarity_transform(nominal_fxfy: np.ndarray, corrected_fxfy: np.ndarray) -> dict:
    """Closed-form least-squares fit of a 2D similarity transform
    (uniform scale `s`, rotation `theta`, translation `t`) mapping
    `nominal_fxfy` points onto `corrected_fxfy` points: w = a*z + b, with
    z, w the points as complex numbers and a = s*exp(i*theta). This is
    LINEAR in the complex unknowns (a, b), so it's an exact closed-form
    least squares (`np.linalg.lstsq` on complex arrays), not an iterative
    fit -- the paper's "Rigid Source Projection" (Fig. 3a) plays the same
    regularizing role: don't trust each LED's own noisy SC correction in
    isolation, trust the single rigid transform that best explains all of
    them together (this project's simplification: no RANSAC outlier
    rejection, see module docstring).

    Returns {"scale", "rotation_rad", "shift": (dx, dy)} plus the raw
    complex coefficients "a", "b" (what `apply_similarity_transform`
    actually uses).
    """
    z = nominal_fxfy[:, 0] + 1j * nominal_fxfy[:, 1]
    w = corrected_fxfy[:, 0] + 1j * corrected_fxfy[:, 1]
    design = np.stack([z, np.ones_like(z)], axis=1)
    coeffs, *_ = np.linalg.lstsq(design, w, rcond=None)
    a, b = coeffs[0], coeffs[1]
    return {
        "scale": float(np.abs(a)), "rotation_rad": float(np.angle(a)),
        "shift": (float(b.real), float(b.imag)), "a": a, "b": b,
    }


def apply_similarity_transform(fxfy: np.ndarray, transform: dict) -> np.ndarray:
    """Apply a `fit_similarity_transform` result to a set of (fx, fy)
    points -- used to project EVERY LED's nominal position through the
    single fitted transform, not just the ones a per-LED search happened
    to correct well.
    """
    z = fxfy[:, 0] + 1j * fxfy[:, 1]
    w = transform["a"] * z + transform["b"]
    return np.stack([w.real, w.imag], axis=1)


def fit_similarity_transform_ransac(nominal_fxfy: np.ndarray, corrected_fxfy: np.ndarray,
                                     inlier_threshold: float, n_iterations: int = 200,
                                     min_inliers: int = 2, rng: np.random.Generator | None = None) -> dict:
    """`fit_similarity_transform`, but robust to a minority of grossly
    wrong (row, col) corrections -- e.g. a genuinely noisy/darkfield LED
    that `spectral_correlation_correction`/`find_circle_center` corrected
    to an implausible position. Plain least squares has NO resistance to
    this (previously documented as a known simplification/limitation of
    `calibrate_led_grid`/`brightfield_calibration` -- see their
    docstrings and docs/roadmap_agentic_multispectral_pipeline.md
    milestone 4): a single bad point can pull scale/rotation/shift far
    from the true transform, confirmed with an injected-outlier test
    while adding this function (a 10%-outlier scenario flipped the
    fitted rotation's sign entirely under plain least squares).

    Standard RANSAC: repeatedly fit the exact 2-point solution from a
    random minimal sample, count how many of ALL the points that
    candidate transform predicts within `inlier_threshold` (same units as
    the input points, i.e. cycles/um for LED calibration), keep the
    candidate with the most inliers, then refit
    `fit_similarity_transform` using only ITS inlier set for the final,
    refined answer (the standard "refit on the winning consensus set"
    step -- more accurate than the minimal 2-point sample alone).

    Returns `fit_similarity_transform`'s own dict, plus "inlier_mask" (a
    boolean array over the input points) and "n_inliers" -- a natural
    per-point confidence signal an agent could use, same role as
    `search_wrap_numbers`'s "disagreement" in multispectral.py.
    """
    n = len(nominal_fxfy)
    if n < 2:
        raise ValueError("need at least 2 points to fit a similarity transform")
    rng = rng if rng is not None else np.random.default_rng()

    best_inliers, best_mask = 0, np.zeros(n, dtype=bool)
    for _ in range(n_iterations):
        sample = rng.choice(n, size=2, replace=False)
        if nominal_fxfy[sample[0]].tolist() == nominal_fxfy[sample[1]].tolist():
            continue  # degenerate sample, two identical points can't fix a similarity transform
        candidate = fit_similarity_transform(nominal_fxfy[sample], corrected_fxfy[sample])
        predicted = apply_similarity_transform(nominal_fxfy, candidate)
        errors = np.hypot(*(predicted - corrected_fxfy).T)
        mask = errors < inlier_threshold
        if mask.sum() > best_inliers:
            best_inliers, best_mask = int(mask.sum()), mask

    if best_inliers < min_inliers:
        raise ValueError(
            f"RANSAC found only {best_inliers} inliers (need >= {min_inliers}) after "
            f"{n_iterations} iterations -- either inlier_threshold is too tight, or the data "
            "genuinely has no consistent rigid transform"
        )

    refined = fit_similarity_transform(nominal_fxfy[best_mask], corrected_fxfy[best_mask])
    return {**refined, "inlier_mask": best_mask, "n_inliers": best_inliers}


def calibrate_led_grid(led_grid_nominal: list[dict], obj_spectrum: np.ndarray, hr_pixel_um: float,
                        lr_images: dict, lr_pixel_um: float, na: float, wavelength_um: float,
                        delta_k: float, search_range: tuple = (-1, 0, 1),
                        ransac_inlier_threshold: float | None = None) -> dict:
    """The full milestone 4 pipeline step: SC-correct every imaged LED's
    position, fit one similarity transform from nominal to corrected
    positions, and project ALL nominal LED positions (imaged or not)
    through it -- giving a corrected LED grid usable for a second,
    better-calibrated reconstruction pass.

    `ransac_inlier_threshold`, if given (in cycles/um, same units as
    `delta_k`), uses `fit_similarity_transform_ransac` instead of the
    plain least-squares `fit_similarity_transform` -- robust to a
    minority of LEDs the per-LED search corrected to an implausible
    position (a genuinely noisy/darkfield image gives `search_wrap_numbers`-
    style search nothing reliable to lock onto). A reasonable starting
    point is a small multiple of `delta_k` itself, since that's already
    this pipeline's own notion of "how far a single correction step
    moves a point". Omit for the original plain-least-squares behavior
    (no outlier resistance).

    Returns {"led_grid": corrected grid (same entries as
    `led_grid_nominal`, "fx"/"fy" replaced), "transform": the fitted
    transform result -- its magnitude is the natural per-pixel diagnostic
    for a Calibration agent (docs/roadmap... section 2) deciding whether
    real misalignment was found (large, consistent shift/rotation/scale)
    or this looks like noise (transform close to identity: scale~1,
    rotation~0, shift~0); with RANSAC, also carries "inlier_mask" and
    "n_inliers"}.
    """
    corrected_by_key = spectral_correlation_correction(
        obj_spectrum, hr_pixel_um, led_grid_nominal, lr_images,
        lr_pixel_um, na, wavelength_um, delta_k, search_range,
    )
    imaged_entries = [e for e in led_grid_nominal if (e["row"], e["col"]) in corrected_by_key]
    nominal_fxfy = np.array([[e["fx"], e["fy"]] for e in imaged_entries])
    corrected_fxfy = np.array([corrected_by_key[(e["row"], e["col"])] for e in imaged_entries])

    transform = (
        fit_similarity_transform_ransac(nominal_fxfy, corrected_fxfy, ransac_inlier_threshold)
        if ransac_inlier_threshold is not None
        else fit_similarity_transform(nominal_fxfy, corrected_fxfy)
    )

    all_fxfy = np.array([[e["fx"], e["fy"]] for e in led_grid_nominal])
    projected_fxfy = apply_similarity_transform(all_fxfy, transform)
    corrected_grid = [
        {**entry, "fx": float(projected_fxfy[i, 0]), "fy": float(projected_fxfy[i, 1])}
        for i, entry in enumerate(led_grid_nominal)
    ]
    return {"led_grid": corrected_grid, "transform": transform}


# ---------------------------------------------------------------------------
# Brightfield (BF) calibration -- Eckert et al. 2018 Algorithm 1, added
# 2026-09-17 after `calibrate_led_grid` above (SC-only) was found NOT to
# reliably bootstrap from a badly-miscalibrated reconstruction (see
# docs/roadmap_agentic_multispectral_pipeline.md milestone 4's documented
# negative result, and tests/test_led_calibration.py). This closes that
# gap: BF calibration works directly on each raw LR image's own Fourier
# spectrum, with NO object-spectrum estimate needed at all -- so it has
# nothing to bootstrap FROM, unlike SC calibration.
#
# Simplified relative to the paper (Algorithm 1): a single combined
# "radial edge strength" metric (see `_circle_edge_strength`) stands in
# for their two-stage E1 (first-derivative) / E2 (second-derivative)
# metrics and the Gaussian-smoothed radial profile machinery behind them
# (Eqs 3-5) -- both are ultimately looking for the same thing, a sharp
# step in spectrum magnitude at radius R from the true center, and this
# metric detects that directly without needing the intermediate
# derivative formalism. RANSAC outlier rejection (2026-09-17,
# `fit_similarity_transform_ransac`) is now available via
# `ransac_inlier_threshold` on both `calibrate_led_grid` and
# `brightfield_calibration` -- opt-in, not the default, since it needs a
# threshold tuned to the data's own units. No darkfield extrapolation
# beyond applying the fitted transform to every LED (which IS what the
# paper does too, per its Fig. 1c / Algorithm 1 lines 9-12 -- this part
# is faithful).
# ---------------------------------------------------------------------------


def _led_illumination_pixel_center(lr_shape: tuple[int, int], lr_pixel_um: float,
                                    fx: float, fy: float) -> tuple[float, float]:
    """Where (fx, fy) [cycles/um] lands in the LR image's own
    fftshift-ed FFT pixel grid -- same index arithmetic as
    `spectral_ops.led_crop_window`, but returning a (possibly
    sub-pixel-rounded here to the nearest bin, since this is only used to
    center a *search box*) row/col pair for a standalone lr_shape-sized
    FFT, not a crop window into a larger HR spectrum.
    """
    h, w = lr_shape
    fy_axis = np.fft.fftshift(np.fft.fftfreq(h, d=lr_pixel_um))
    fx_axis = np.fft.fftshift(np.fft.fftfreq(w, d=lr_pixel_um))
    df_y, df_x = fy_axis[1] - fy_axis[0], fx_axis[1] - fx_axis[0]
    row = (fy - fy_axis[0]) / df_y
    col = (fx - fx_axis[0]) / df_x
    return row, col


def _bilinear_sample(image: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    """Sample `image` at (possibly sub-pixel, possibly out-of-bounds --
    clamped) (row, col) points via bilinear interpolation. Vectorized over
    arrays of points.
    """
    h, w = image.shape
    rows = np.clip(rows, 0, h - 1.001)
    cols = np.clip(cols, 0, w - 1.001)
    r0, c0 = np.floor(rows).astype(int), np.floor(cols).astype(int)
    r1, c1 = r0 + 1, c0 + 1
    fr, fc = rows - r0, cols - c0
    return (
        image[r0, c0] * (1 - fr) * (1 - fc) + image[r0, c1] * (1 - fr) * fc
        + image[r1, c0] * fr * (1 - fc) + image[r1, c1] * fr * fc
    )


def _circle_edge_strength(spectrum_mag: np.ndarray, center_row: float, center_col: float,
                           radius_px: float, n_angles: int = 36, band_px: float = 1.0) -> float:
    """Sum, over `n_angles` points around a circle of `radius_px` centered
    at (center_row, center_col), of |spectrum just inside the circle -
    spectrum just outside| -- large when the candidate center sits on a
    real circular step edge in the spectrum (Fig. 2 in `eckert2018`),
    small/noisy when it doesn't. See this section's docstring for how
    this stands in for the paper's E1/E2 metrics.
    """
    angles = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
    cos_a, sin_a = np.cos(angles), np.sin(angles)
    inside_r = center_row + (radius_px - band_px) * sin_a
    inside_c = center_col + (radius_px - band_px) * cos_a
    outside_r = center_row + (radius_px + band_px) * sin_a
    outside_c = center_col + (radius_px + band_px) * cos_a
    inside_vals = _bilinear_sample(spectrum_mag, inside_r, inside_c)
    outside_vals = _bilinear_sample(spectrum_mag, outside_r, outside_c)
    return float(np.sum(np.abs(inside_vals - outside_vals)))


def mean_spectrum_magnitude(lr_images: dict, keys: list) -> np.ndarray:
    """Algorithm 1 line 1 (`eckert2018`): the mean |FFT| spectrum across
    several images. Dividing each individual spectrum by this (see
    `find_circle_center`'s `normalize_by`) removes the generic 1/f-like
    falloff shape common to essentially all natural-ish image spectra,
    which otherwise completely swamps the LED-specific circular pupil
    edge this function is actually looking for -- found necessary
    empirically (the un-normalized version reliably found the WRONG
    center, biased outward along the generic spectral gradient, every
    time) while implementing this module.
    """
    spectra = [np.abs(np.fft.fftshift(np.fft.fft2(lr_images[k]))) for k in keys]
    return np.mean(spectra, axis=0)


def find_circle_center(lr_image: np.ndarray, lr_pixel_um: float, na: float, wavelength_um: float,
                        expected_fx: float, expected_fy: float,
                        search_radius_px: float = 3.0, search_step_px: float = 0.5,
                        n_angles: int = 36, normalize_by: np.ndarray | None = None) -> dict:
    """Brightfield circular edge detection for ONE LED's image (paper
    Algorithm 1 lines 4-8, simplified per this section's docstring): grid
    search over candidate circle centers within `search_radius_px` of the
    NOMINAL expected center (from `led_array`'s assumed geometry),
    scoring each with `_circle_edge_strength` at the objective's own
    NA-cutoff radius, keeping the best.

    `normalize_by`, if given (see `mean_spectrum_magnitude`), divides the
    image's own spectrum by it before scoring -- NOT optional in
    practice, see that function's docstring for why skipping this gives
    reliably wrong results, dominated by generic spectral falloff rather
    than the actual pupil-edge circle. Kept as an optional parameter only
    so a single-image caller/test can still probe the raw, un-normalized
    metric if it wants to.

    Returns {"fx", "fy": the calibrated illumination frequency at the
    winning center, "edge_strength": its score -- low relative to other
    LEDs' scores is this function's own confidence signal (a genuinely
    flat/low-contrast image, e.g. a darkfield LED or -- per this
    project's own finding, see tests/test_weak_phase_object_limitation.py
    -- a weak-phase-object brightfield image, has no real circle to find,
    and this function will return a effectively arbitrary "best" candidate
    from noise)}.
    """
    lr_shape = lr_image.shape
    spectrum_mag = np.abs(np.fft.fftshift(np.fft.fft2(lr_image)))
    if normalize_by is not None:
        spectrum_mag = spectrum_mag / np.clip(normalize_by, 1e-9, None)
    expected_row, expected_col = _led_illumination_pixel_center(lr_shape, lr_pixel_um,
                                                                  expected_fx, expected_fy)
    radius_px = na / wavelength_um * lr_shape[1] * lr_pixel_um  # same cutoff as optics.circular_pupil

    offsets = np.arange(-search_radius_px, search_radius_px + 1e-9, search_step_px)
    best_score, best_row, best_col = -np.inf, expected_row, expected_col
    for d_row in offsets:
        for d_col in offsets:
            row, col = expected_row + d_row, expected_col + d_col
            score = _circle_edge_strength(spectrum_mag, row, col, radius_px, n_angles)
            if score > best_score:
                best_score, best_row, best_col = score, row, col

    fy_axis = np.fft.fftshift(np.fft.fftfreq(lr_shape[0], d=lr_pixel_um))
    fx_axis = np.fft.fftshift(np.fft.fftfreq(lr_shape[1], d=lr_pixel_um))
    fy = fy_axis[0] + best_row * (fy_axis[1] - fy_axis[0])
    fx = fx_axis[0] + best_col * (fx_axis[1] - fx_axis[0])
    return {"fx": fx, "fy": fy, "edge_strength": best_score}


def brightfield_calibration(lr_images: dict, led_grid_nominal: list[dict], lr_pixel_um: float,
                             na: float, wavelength_um: float,
                             search_radius_px: float = 3.0,
                             ransac_inlier_threshold: float | None = None) -> dict:
    """The full milestone-4 bootstrap step: run `find_circle_center` on
    every BRIGHTFIELD LED (illumination NA < objective NA -- the only ones
    with a clean circle edge, per the paper's own Fig. 1b: darkfield
    images "do not" show one), fit one similarity transform from nominal
    to found positions, and project every LED (brightfield AND darkfield)
    through it -- usable as-is for a first reconstruction pass, or as the
    starting `led_grid_nominal` for `calibrate_led_grid` (SC calibration)
    to refine further.

    Unlike `calibrate_led_grid`, this needs NO object-spectrum estimate --
    it only reads `lr_images` directly, which is what makes it a real
    bootstrap (see this section's docstring for why SC-only calibration
    can't play that role on its own).

    `ransac_inlier_threshold`: see `calibrate_led_grid`'s parameter of
    the same name -- same robust-fit option, same units (cycles/um).
    Especially relevant here given how few brightfield LEDs this
    project's own lab geometry has (docs/roadmap_agentic_multispectral_pipeline.md
    milestone 4 -- as few as 1, or 5 with the "future" objective): with a
    minimal point count, a single bad `find_circle_center` result is an
    even larger fraction of the data than in `calibrate_led_grid`'s case.

    Returns {"led_grid": corrected grid, "transform": the fitted
    transform result, "edge_strengths": {(row,col): score} for every
    brightfield LED used -- a confidence diagnostic, same role as
    `calibrate_led_grid`'s "transform" magnitude}.
    """
    brightfield_entries = [
        e for e in led_grid_nominal
        if (e["row"], e["col"]) in lr_images and np.hypot(e["fx"], e["fy"]) * wavelength_um < na
    ]
    if not brightfield_entries:
        raise ValueError("no brightfield LEDs (illumination NA < na) found in led_grid_nominal/lr_images")

    bf_keys = [(e["row"], e["col"]) for e in brightfield_entries]
    mean_spectrum = mean_spectrum_magnitude(lr_images, bf_keys)

    found_fxfy, nominal_fxfy, edge_strengths = [], [], {}
    for entry in brightfield_entries:
        key = (entry["row"], entry["col"])
        found = find_circle_center(lr_images[key], lr_pixel_um, na, wavelength_um,
                                    entry["fx"], entry["fy"], search_radius_px,
                                    normalize_by=mean_spectrum)
        found_fxfy.append([found["fx"], found["fy"]])
        nominal_fxfy.append([entry["fx"], entry["fy"]])
        edge_strengths[key] = found["edge_strength"]

    nominal_fxfy_arr, found_fxfy_arr = np.array(nominal_fxfy), np.array(found_fxfy)
    transform = (
        fit_similarity_transform_ransac(nominal_fxfy_arr, found_fxfy_arr, ransac_inlier_threshold)
        if ransac_inlier_threshold is not None
        else fit_similarity_transform(nominal_fxfy_arr, found_fxfy_arr)
    )

    all_fxfy = np.array([[e["fx"], e["fy"]] for e in led_grid_nominal])
    projected_fxfy = apply_similarity_transform(all_fxfy, transform)
    corrected_grid = [
        {**entry, "fx": float(projected_fxfy[i, 0]), "fy": float(projected_fxfy[i, 1])}
        for i, entry in enumerate(led_grid_nominal)
    ]
    return {"led_grid": corrected_grid, "transform": transform, "edge_strengths": edge_strengths}

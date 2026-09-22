"""metrics.py -- compare a reconstruction against ground truth (script 1,
simulation) or just report internal self-consistency (script 2, real
data, where there is no ground truth to compare against).
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def _normalize_phase(phase: np.ndarray) -> np.ndarray:
    """Wrap to (-pi, pi] and remove the global piston (mean) -- FPM
    recovers phase only up to an arbitrary additive constant.
    """
    wrapped = np.angle(np.exp(1j * phase))
    return wrapped - np.mean(wrapped)


def compare_to_ground_truth(recon: np.ndarray, truth: np.ndarray) -> dict:
    """`recon` and `truth` must be the same shape complex arrays. Phase is
    compared after removing each array's own global piston, since FPM
    can't recover an absolute phase reference.
    """
    if recon.shape != truth.shape:
        raise ValueError(f"shape mismatch: recon {recon.shape} vs truth {truth.shape}")

    recon_amp, truth_amp = np.abs(recon), np.abs(truth)
    amp_rmse = float(np.sqrt(np.mean((recon_amp - truth_amp) ** 2)))
    amp_corr = float(np.corrcoef(recon_amp.ravel(), truth_amp.ravel())[0, 1])

    recon_phase = _normalize_phase(np.angle(recon))
    truth_phase = _normalize_phase(np.angle(truth))
    phase_rmse = float(np.sqrt(np.mean((recon_phase - truth_phase) ** 2)))
    phase_corr = float(np.corrcoef(recon_phase.ravel(), truth_phase.ravel())[0, 1])

    return {
        "amplitude_rmse": amp_rmse,
        "amplitude_correlation": amp_corr,
        "phase_rmse_rad": phase_rmse,
        "phase_correlation": phase_corr,
    }


def correlate_against_hr_reference(recon_amplitude: np.ndarray, reference: np.ndarray) -> dict:
    """Pearson correlation between a reconstruction's amplitude and a real
    HR intensity reference image (e.g. a separately captured, well-focused
    image of the actual sample) -- for validating a REAL-data reconstruction
    against an actual ground truth, as opposed to `compare_to_ground_truth`
    (synthetic phantom, exact same array shape and a complex-valued truth
    with a known phase).

    `reference` may be a different resolution than `recon_amplitude`; it is
    resized (Lanczos) to match. Both are z-scored (mean 0, unit std) before
    correlating, since a real reference's absolute intensity scale/offset
    has no reason to match a reconstruction's arbitrary amplitude scale.

    Tries all 4 combinations of vertical/horizontal flip on
    `recon_amplitude` and returns the best by |correlation| -- real-camera
    vs. this project's forward-model axis convention (row/col vs x/y,
    sign of the illumination-angle-to-shift mapping) is a real risk this
    project had no way to check until an actual real HR reference existed
    (2026-09-22); this is not a hedge against a bug we expect, it's the
    first time this convention could be checked against real data at all.

    Returns {"correlation": float, "flipud": bool, "fliplr": bool,
    "all_orientations": {(flipud, fliplr): float, ...}} -- the last field
    is there so a caller/test can confirm the winning orientation wasn't
    a coin flip against its nearest competitor.
    """
    if reference.ndim != 2 or recon_amplitude.ndim != 2:
        raise ValueError("both images must be 2D (amplitude/intensity, no complex/color axis)")

    # PIL's "F" mode is specifically 32-bit float -- float64 input to
    # fromarray(..., mode="F") silently reinterprets bytes wrong (NaNs),
    # it does not convert
    ref_img = Image.fromarray(np.ascontiguousarray(reference, dtype=np.float32), mode="F")
    ref_resized = np.asarray(
        ref_img.resize((recon_amplitude.shape[1], recon_amplitude.shape[0]), Image.LANCZOS),
        dtype=np.float64,
    )
    ref_z = (ref_resized - ref_resized.mean()) / ref_resized.std()

    all_orientations = {}
    best = None
    for flipud in (False, True):
        for fliplr in (False, True):
            a = np.asarray(recon_amplitude, dtype=np.float64)
            if flipud:
                a = a[::-1]
            if fliplr:
                a = a[:, ::-1]
            a_z = (a - a.mean()) / a.std()
            corr = float(np.mean(a_z * ref_z))
            all_orientations[(flipud, fliplr)] = corr
            if best is None or abs(corr) > abs(best["correlation"]):
                best = {"correlation": corr, "flipud": flipud, "fliplr": fliplr}
    best["all_orientations"] = all_orientations
    return best


def convergence_summary(history: list[dict]) -> dict:
    """Did the reconstruction actually converge? First vs. last epoch's
    recovery error, and whether it monotonically-ish improved.
    """
    errors = [h["recovery_error"] for h in history]
    n = len(errors)
    if n == 0:  # e.g. --iterations 0: nothing ran, so there is nothing to summarize
        return {"first_error": None, "last_error": None, "relative_improvement": 0.0,
                "fraction_of_epochs_that_improved": 1.0}
    improved = sum(1 for i in range(1, n) if errors[i] <= errors[i - 1])
    return {
        "first_error": errors[0],
        "last_error": errors[-1],
        "relative_improvement": (errors[0] - errors[-1]) / errors[0] if errors[0] else 0.0,
        "fraction_of_epochs_that_improved": improved / (n - 1) if n > 1 else 1.0,
    }

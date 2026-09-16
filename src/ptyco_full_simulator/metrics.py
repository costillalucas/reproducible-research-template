"""metrics.py -- compare a reconstruction against ground truth (script 1,
simulation) or just report internal self-consistency (script 2, real
data, where there is no ground truth to compare against).
"""
from __future__ import annotations

import numpy as np


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


def convergence_summary(history: list[dict]) -> dict:
    """Did the reconstruction actually converge? First vs. last epoch's
    recovery error, and whether it monotonically-ish improved.
    """
    errors = [h["recovery_error"] for h in history]
    n = len(errors)
    improved = sum(1 for i in range(1, n) if errors[i] <= errors[i - 1])
    return {
        "first_error": errors[0],
        "last_error": errors[-1],
        "relative_improvement": (errors[0] - errors[-1]) / errors[0] if errors[0] else 0.0,
        "fraction_of_epochs_that_improved": improved / (n - 1) if n > 1 else 1.0,
    }

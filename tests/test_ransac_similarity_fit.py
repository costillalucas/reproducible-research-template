"""tests/test_ransac_similarity_fit.py --
led_calibration.fit_similarity_transform_ransac, added to close a
previously-documented simplification in milestone 4 (both
`calibrate_led_grid` and `brightfield_calibration` used plain least
squares with no outlier rejection, unlike `eckert2018`'s own RANSAC step
-- see those functions' docstrings and
docs/roadmap_agentic_multispectral_pipeline.md).

Pure math, no FPM/reconstruction involved -- isolates the fitting
algorithm itself from everything else in this project's LED calibration
pipeline that could also go wrong.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import led_calibration as cal  # noqa: E402


def _similarity_points(n, scale, rotation_rad, shift, rng):
    nominal = rng.uniform(-0.5, 0.5, (n, 2))
    a = scale * np.exp(1j * rotation_rad)
    b = shift[0] + 1j * shift[1]
    z = nominal[:, 0] + 1j * nominal[:, 1]
    w = a * z + b
    corrected = np.stack([w.real, w.imag], axis=1)
    return nominal, corrected


def test_ransac_recovers_true_transform_despite_outliers_where_plain_fit_fails():
    rng = np.random.default_rng(0)
    scale, rotation_rad, shift = 1.03, 0.05, (0.02, -0.01)
    nominal, corrected = _similarity_points(30, scale, rotation_rad, shift, rng)

    corrupted = corrected.copy()
    outlier_idx = [2, 10, 20]
    for i in outlier_idx:
        corrupted[i] += rng.uniform(-2, 2, 2)

    plain = cal.fit_similarity_transform(nominal, corrupted)
    assert abs(plain["rotation_rad"] - rotation_rad) > 0.05, (
        "premise check: plain least squares should actually be thrown off by these outliers"
    )

    ransac = cal.fit_similarity_transform_ransac(nominal, corrupted, inlier_threshold=0.1,
                                                  rng=np.random.default_rng(1))
    assert ransac["scale"] == pytest.approx(scale)
    assert ransac["rotation_rad"] == pytest.approx(rotation_rad)
    assert ransac["n_inliers"] == 27
    assert not np.any(ransac["inlier_mask"][outlier_idx]), "the 3 injected outliers should be excluded"
    inlier_idx = [i for i in range(30) if i not in outlier_idx]
    assert np.all(ransac["inlier_mask"][inlier_idx]), "every genuine (non-outlier) point should be kept"


def test_ransac_matches_plain_fit_when_there_are_no_outliers():
    rng = np.random.default_rng(2)
    scale, rotation_rad, shift = 0.98, -0.03, (-0.01, 0.02)
    nominal, corrected = _similarity_points(20, scale, rotation_rad, shift, rng)

    ransac = cal.fit_similarity_transform_ransac(nominal, corrected, inlier_threshold=0.05,
                                                  rng=np.random.default_rng(3))
    assert ransac["n_inliers"] == 20
    assert ransac["scale"] == pytest.approx(scale)
    assert ransac["rotation_rad"] == pytest.approx(rotation_rad)


def test_ransac_raises_when_too_few_inliers_are_found():
    rng = np.random.default_rng(4)
    # pure noise, no real underlying similarity transform to find
    nominal = rng.uniform(-0.5, 0.5, (10, 2))
    corrected = rng.uniform(-0.5, 0.5, (10, 2))
    try:
        cal.fit_similarity_transform_ransac(nominal, corrected, inlier_threshold=1e-6,
                                             min_inliers=5, rng=np.random.default_rng(5))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError when no consistent transform explains enough points")

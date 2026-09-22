"""tests/test_metrics.py -- src/ptyco_full_simulator/metrics.py's
`correlate_against_hr_reference`: Pearson correlation between a
reconstruction's amplitude and a real HR intensity reference image,
added 2026-09-22 alongside this project's first real HR reference
capture ("elefante", a real lab sample -- see
docs/roadmap_agentic_multispectral_pipeline.md's real-data-validation
section). Structured-but-synthetic arrays only here; the actual real
reference lives outside the repo.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import metrics  # noqa: E402


def _structured_image(shape=(60, 80), seed=0):
    """A smooth, non-symmetric field -- structured enough that
    correlation against a flipped/rotated copy of itself is clearly
    lower than against the identity orientation, unlike e.g. a
    checkerboard or anything else with accidental symmetry.
    """
    rng = np.random.default_rng(seed)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    field = (
        np.sin(xx / 7.0) * np.cos(yy / 11.0)
        + 0.6 * np.exp(-((xx - w * 0.7) ** 2 + (yy - h * 0.2) ** 2) / (2 * 15.0 ** 2))
        + 0.3 * rng.standard_normal(shape)
    )
    return field


def test_identical_image_gives_correlation_near_one_with_no_flip():
    img = _structured_image()
    result = metrics.correlate_against_hr_reference(img, img)
    assert result["correlation"] > 0.999
    assert result["flipud"] is False
    assert result["fliplr"] is False


def test_uncorrelated_random_noise_gives_near_zero_correlation():
    rng = np.random.default_rng(1)
    a = rng.standard_normal((50, 50))
    b = rng.standard_normal((50, 50))
    result = metrics.correlate_against_hr_reference(a, b)
    assert abs(result["correlation"]) < 0.3


def test_recovers_known_flip_orientation():
    img = _structured_image()
    flipped_reference = img[::-1, ::-1]  # flipud AND fliplr relative to img
    result = metrics.correlate_against_hr_reference(img, flipped_reference)
    # correlating img (unflipped) against a reference that is img flipped both ways
    # is maximized by flipping img the same way before comparing
    assert result["flipud"] is True
    assert result["fliplr"] is True
    assert result["correlation"] > 0.999


def test_all_orientations_reported_and_winner_is_the_max_abs():
    img = _structured_image()
    result = metrics.correlate_against_hr_reference(img, img[:, ::-1])
    assert set(result["all_orientations"].keys()) == {
        (False, False), (False, True), (True, False), (True, True),
    }
    winner_key = (result["flipud"], result["fliplr"])
    assert result["all_orientations"][winner_key] == result["correlation"]
    assert all(abs(result["correlation"]) >= abs(v) for v in result["all_orientations"].values())


def test_different_resolution_reference_is_resized_to_match():
    img = _structured_image(shape=(90, 120))
    # downsample crudely (strided, no anti-aliasing) to build a lower-resolution
    # "reference" of the same content -- some correlation loss from aliasing/the
    # noise term is expected, this just checks resizing makes the shapes
    # comparable at all and the structure that survives is still recognized
    low_res = img[::3, ::3]
    result = metrics.correlate_against_hr_reference(img, low_res)
    assert result["correlation"] > 0.6
    assert set(result["all_orientations"]) == {
        (False, False), (False, True), (True, False), (True, True),
    }


def test_rejects_non_2d_input():
    img = _structured_image()
    color = np.stack([img, img, img], axis=-1)
    try:
        metrics.correlate_against_hr_reference(color, img)
        assert False, "expected ValueError for non-2D input"
    except ValueError:
        pass

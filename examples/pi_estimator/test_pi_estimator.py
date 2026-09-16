import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pi_estimator import constant_estimator, estimate_pi


def test_estimate_pi_is_seed_reproducible():
    a = estimate_pi(5_000, seed=7)
    b = estimate_pi(5_000, seed=7)
    assert a == b


def test_estimate_pi_different_seeds_differ():
    a = estimate_pi(5_000, seed=1)
    b = estimate_pi(5_000, seed=2)
    assert a["pi_hat"] != b["pi_hat"]


def test_estimate_pi_converges_in_the_right_direction():
    small = abs(estimate_pi(500, seed=42)["pi_hat"] - math.pi)
    large = abs(estimate_pi(500_000, seed=42)["pi_hat"] - math.pi)
    # not a strict guarantee for any single seed/n pair in general, but this
    # seed/n pair is fixed and checked once here -- see scripts/checks.py
    # for the statistically honest version (a slope fit over many N).
    assert large < small


def test_constant_estimator_ignores_its_inputs():
    a = constant_estimator(10, seed=1)
    b = constant_estimator(10_000_000, seed=99)
    assert a["pi_hat"] == b["pi_hat"] == 3.0

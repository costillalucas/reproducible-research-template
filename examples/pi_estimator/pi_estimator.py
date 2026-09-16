"""The worked example under test: a Monte Carlo estimator of pi.

This module exists only to give the template something real to compute and
check -- swap it for your own analysis code when you fork the template. Keep
the shape: a pure function that takes a seed and returns a dict, so every
number downstream is reproducible from (function, seed) alone.
"""
from __future__ import annotations

import numpy as np


def estimate_pi(n: int, seed: int) -> dict:
    """Estimate pi from the fraction of n uniform points in [-1,1]^2 that
    land inside the unit circle.

    Returns pi_hat and its predicted 1-sigma standard error, propagated
    from the binomial variance of the inside/outside fraction p:
    Var(p) = p(1-p)/n, and pi_hat = 4p, so SE(pi_hat) = 4 * sqrt(Var(p)).
    """
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-1.0, 1.0, size=(n, 2))
    inside = int(np.sum(xy[:, 0] ** 2 + xy[:, 1] ** 2 <= 1.0))
    p = inside / n
    pi_hat = 4.0 * p
    se = 4.0 * np.sqrt(p * (1.0 - p) / n)
    return {"n": n, "seed": seed, "inside": inside, "pi_hat": float(pi_hat), "se": float(se)}


def constant_estimator(n: int, seed: int) -> dict:
    """A deliberately WRONG 'estimator': it ignores n, seed and the data
    entirely and always returns 3.0.

    This is the negative control. Run through the exact same convergence
    check as estimate_pi, its error must NOT shrink with n -- proving the
    check can tell a real estimator from a fake one, not just recompute a
    number that was going to agree anyway.
    """
    return {"n": n, "seed": seed, "pi_hat": 3.0}

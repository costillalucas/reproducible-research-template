#!/usr/bin/env python3
"""compute_numbers.py -- frozen reference copy, see examples/pi_estimator/README.md.

This is the original template worked example, kept standalone here so it
stays runnable for reference after the live scripts/ and structure/ were
reset for a real project. It is NOT wired into scripts/reproduce.sh or
scripts/check_provenance.py's default paths -- run it directly, as shown
below, if you want to see the mechanism work end to end again.

Run: python examples/pi_estimator/compute_numbers.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pi_estimator import estimate_pi  # noqa: E402

OUT = os.path.join(HERE, "numbers.json")

SEED = 42
N = 200_000


def main():
    est = estimate_pi(N, SEED)

    registry = {
        "pi_true": {
            "value": math.pi,
            "statement": "the analytic value of pi",
            "type": "derivation",
            "reproduce": "math.pi",
        },
        "pi_estimate_n200000": {
            "value": est["pi_hat"],
            "statement": (
                f"Monte Carlo estimate of pi from n={N} uniform points in "
                "[-1,1]^2, 4 * (fraction landing inside the unit circle)"
            ),
            "type": "script",
            "reproduce": "examples/pi_estimator/compute_numbers.py::main",
            "detail": f"seed={SEED}, n={N}",
        },
        "pi_estimate_se_n200000": {
            "value": est["se"],
            "statement": (
                "predicted 1-sigma standard error of that estimate, from the "
                "binomial variance of the inside/outside fraction"
            ),
            "type": "derivation",
            "reproduce": "examples/pi_estimator/pi_estimator.py::estimate_pi",
        },
        "pi_abs_error_n200000": {
            "value": abs(est["pi_hat"] - math.pi),
            "statement": "absolute error of the n=200000 estimate against the analytic value",
            "type": "script",
            "reproduce": "examples/pi_estimator/compute_numbers.py::main",
        },
        "suite_coverage": {
            "statement": "checks.py pass/fail coverage for this example (positive checks + the negative control)",
            "type": "check",
            "reproduce": "examples/pi_estimator/checks.py",
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"wrote {os.path.relpath(OUT, HERE)} ({len(registry)} entries)")
    print(f"  pi_estimate_n200000  = {est['pi_hat']:.6f}")
    print(f"  pi_estimate_se       = {est['se']:.6f}")
    print(f"  pi_abs_error         = {abs(est['pi_hat'] - math.pi):.6f}")


if __name__ == "__main__":
    main()

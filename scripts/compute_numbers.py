#!/usr/bin/env python3
"""compute_numbers.py -- SOLE WRITER of data/numbers.json.

Recomputes every number quoted in report/report.md from the code in
src/example_pkg, with a fixed seed, and writes them to the single registry
file that scripts/check_provenance.py checks the report against. Nothing
else writes this file, and the report never writes a number by hand -- it
quotes this registry through the \\srcnum{} / [srcnum:] tags.

Run: python scripts/compute_numbers.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from example_pkg.pi_estimator import estimate_pi  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "data", "numbers.json")

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
            "reproduce": "scripts/compute_numbers.py::main",
            "detail": f"seed={SEED}, n={N}",
        },
        "pi_estimate_se_n200000": {
            "value": est["se"],
            "statement": (
                "predicted 1-sigma standard error of that estimate, from the "
                "binomial variance of the inside/outside fraction"
            ),
            "type": "derivation",
            "reproduce": "src/example_pkg/pi_estimator.py::estimate_pi",
        },
        "pi_abs_error_n200000": {
            "value": abs(est["pi_hat"] - math.pi),
            "statement": "absolute error of the n=200000 estimate against the analytic value",
            "type": "script",
            "reproduce": "scripts/compute_numbers.py::main",
        },
        "suite_coverage": {
            "statement": "checks.py pass/fail coverage for this example (positive checks + the negative control)",
            "type": "check",
            "reproduce": "scripts/checks.py",
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(registry)} entries)")
    print(f"  pi_estimate_n200000  = {est['pi_hat']:.6f}")
    print(f"  pi_estimate_se       = {est['se']:.6f}")
    print(f"  pi_abs_error         = {abs(est['pi_hat'] - math.pi):.6f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""checks.py -- frozen reference copy, see examples/pi_estimator/README.md.

Two kinds of check, same discipline as a real deliverable's suite:
  - positive checks: things that MUST agree with the derivation.
  - a negative control: a WRONG estimator run through the identical check,
    which MUST be caught disagreeing -- proving the check is capable of
    failing, not just capable of passing. A suite with no negative control
    cannot be trusted when it passes.

Run: python examples/pi_estimator/checks.py
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pi_estimator import constant_estimator, estimate_pi  # noqa: E402

results = []


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if detail:
        print(f"       {detail}")


Ns = [1_000, 4_000, 16_000, 64_000, 256_000]
log_n = np.log(Ns)

# ---- P1: MC error shrinks as N^-1/2 ---------------------------------------
errs = [abs(estimate_pi(n, seed=42)["pi_hat"] - math.pi) for n in Ns]
slope, _ = np.polyfit(log_n, np.log(errs), 1)
check(
    "P1  MC error of pi_hat shrinks as N^-1/2",
    abs(slope - (-0.5)) < 0.15,
    f"fitted slope d(ln err)/d(ln N) = {slope:.3f} (predicted -0.500, tol 0.15)",
)

# ---- P2: the n=200000 point estimate lands within its predicted SE band --
est = estimate_pi(200_000, seed=42)
err = abs(est["pi_hat"] - math.pi)
check(
    "P2  pi_hat at n=200000 lands within 4 predicted standard errors",
    err < 4 * est["se"],
    f"pi_hat={est['pi_hat']:.6f}, error={err:.6f}, predicted SE={est['se']:.6f}",
)

# ---- D1: NEGATIVE CONTROL -- an estimator that ignores the data ----------
wrong_errs = [abs(constant_estimator(n, seed=42)["pi_hat"] - math.pi) for n in Ns]
wrong_slope, _ = np.polyfit(log_n, np.log(wrong_errs), 1)
check(
    "D1  NEGATIVE CONTROL: an estimator that ignores its input must NOT shrink",
    abs(wrong_slope) < 0.05,
    f"fitted slope = {wrong_slope:.4f} (must be ~flat, not ~-0.5 -- and it is not)",
)

passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 60)
print(f"COVERAGE: {passed}/{total} passed")
print("=" * 60)

with open(os.path.join(HERE, "checks_results.json"), "w") as fh:
    json.dump(
        {"results": [{"name": n, "passed": ok} for n, ok in results],
         "passed": passed, "total": total},
        fh, indent=2,
    )
    fh.write("\n")

sys.exit(0 if passed == total else 1)

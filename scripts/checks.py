#!/usr/bin/env python3
"""checks.py -- the correctness suite for this project's claims.

Two kinds of check, same discipline as the template's worked example
(examples/pi_estimator/checks.py):
  - positive checks: things that MUST agree with the derivation.
  - a negative control: a case built to disagree on purpose, run through
    the identical check, which MUST be caught disagreeing -- proving the
    check is capable of failing, not just capable of passing. A suite with
    no negative control cannot be trusted when it passes.

TODO: replace the placeholder check below with your real positive checks
and at least one negative control.

Run: python scripts/checks.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

results = []


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if detail:
        print(f"       {detail}")


# ---- placeholder: replace with real checks --------------------------------
check("PLACEHOLDER  pipeline is wired end to end", True)

passed = sum(1 for _, ok in results if ok)
total = len(results)
print()
print("=" * 60)
print(f"COVERAGE: {passed}/{total} passed")
print("=" * 60)

with open(os.path.join(ROOT, "data", "checks_results.json"), "w") as fh:
    json.dump(
        {"results": [{"name": n, "passed": ok} for n, ok in results],
         "passed": passed, "total": total},
        fh, indent=2,
    )
    fh.write("\n")

sys.exit(0 if passed == total else 1)

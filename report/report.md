# Example deliverable: does a Monte Carlo estimate of pi actually converge?

This is the worked example that ships with the template. It exists to prove
the mechanism end to end, not to say anything interesting about pi: every
number below is read from `data/numbers.json`, which is written *only* by
`scripts/compute_numbers.py`, and `scripts/check_provenance.py` refuses to
pass if any tag below stops resolving or any literal stops matching the
registry. Fork this file — and `structure/claims.yaml` alongside it — for
your own deliverable.

## Claim

Estimate pi as `4 * (points inside the unit circle) / (points drawn)`, for
`N` points drawn uniformly in `[-1, 1]^2`. The analytic value is
`pi = [srcnum:pi_true:3.14159]` [src:pi_true].

At `N = 200,000` (seed 42), the estimate is
`pi_hat = [srcnum:pi_estimate_n200000:3.14106]`, with predicted standard
error `[srcnum:pi_estimate_se_n200000:0.00367]`
[src:pi_estimate_n200000]. The realized absolute error is
`[srcnum:pi_abs_error_n200000:0.00053]` [src:pi_abs_error_n200000] — well
inside 4 standard errors, which is exactly what check P2 below verifies
explicitly rather than eyeballing.

## What was actually checked

`scripts/checks.py` [src:suite_coverage] — output pasted verbatim, not
retyped:

```
[PASS] P1  MC error of pi_hat shrinks as N^-1/2
       fitted slope d(ln err)/d(ln N) = -0.545 (predicted -0.500, tol 0.15)
[PASS] P2  pi_hat at n=200000 lands within 4 predicted standard errors
       pi_hat=3.141060, error=0.000533, predicted SE=0.003673
[PASS] D1  NEGATIVE CONTROL: an estimator that ignores its input must NOT shrink
       fitted slope = 0.0000 (must be ~flat, not ~-0.5 -- and it is not)

============================================================
COVERAGE: 3/3 passed
============================================================
```

- **P1** — the error shrinks as `N^-1/2` (fit slope vs. the predicted
  `-0.5`, over five values of `N` from `1e3` to `2.56e5`).
- **P2** — the single `N = 200,000` estimate lands inside 4 predicted
  standard errors.
- **D1 — negative control** — a deliberately wrong "estimator" that
  ignores its input (`constant_estimator`, always returns `3.0`) is run
  through the *identical* slope check as P1. Its error must **not** shrink
  with `N`, and it does not. This is what proves the check is capable of
  failing, not just capable of passing — a suite that never fails on
  anything cannot be trusted when it passes on the real thing.

Re-run it yourself: `python scripts/checks.py`.

## What this does NOT check

- Whether `N = 200,000` is "enough" samples for any purpose beyond
  demonstrating the `N^-1/2` scaling — it is not tuned for precision, only
  for making the exponent measurable quickly.
- Any estimator other than the two implemented in
  `src/example_pkg/pi_estimator.py`.
- Anything about the argument-graph layer's own correctness beyond
  structural resolution — `check_provenance.py` proves every reference
  *resolves*, not that the underlying claim is *true*. Truth is what
  `checks.py` is for.

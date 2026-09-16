# pi_estimator — frozen reference example

This is the original worked example that shipped with the
reproducible-research template, before `ptyco-full-simulator` was scaffolded
in its place. It is kept here, self-contained, purely as a reference for the
provenance-tag mechanism (`[src:key]` / `[srcnum:key:value]`) and the
`structure/` argument-graph pattern — read it while writing your own
`report/report.md` and `structure/claims.yaml`.

## What's here

- `pi_estimator.py` — the estimator under test and its negative control.
- `compute_numbers.py`, `checks.py` — self-contained copies of the
  original pipeline scripts, with paths rewritten to read/write inside this
  folder instead of the repo-root `data/`.
- `report.md` — the original tagged deliverable.
- `claims.yaml`, `scripts.yaml`, `outputs.yaml` — the original
  `structure/` files, paths rewritten to point here.
- `numbers.json`, `checks_results.json` — the last generated outputs.
- `test_pi_estimator.py` — unit tests for the estimator.

## Running it standalone

```bash
python examples/pi_estimator/compute_numbers.py
python examples/pi_estimator/checks.py
pytest examples/pi_estimator/test_pi_estimator.py -v
```

**Caveat:** `scripts/check_provenance.py` (the shared gate) hardcodes its
registry and structure paths to the repo root (`data/numbers.json`,
`structure/*.yaml`), so it cannot be pointed at this folder's copies
directly. This example is for reading the pattern, not for re-running the
full gate in place. The live, gate-checked deliverable is
`report/report.md` at the repo root.

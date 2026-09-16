# ptyco-full-simulator

A minimal, **runnable** skeleton for a deliverable where every number
carries a provenance tag that traces back to the code that computed it, and
a gate script refuses to pass if any tag stops resolving.

The pattern is lifted from
[`matiaszaldarriaga/pta-gwb-anisotropy`](https://github.com/matiaszaldarriaga/pta-gwb-anisotropy)
(companion code for a real physics paper) and simplified into something you
can fork for anything: a paper, a report, a blog post, a decision memo —
anywhere a reader needs to trust that a number wasn't just typed by hand.

This project started from that template's own worked example — a Monte
Carlo estimate of pi with a deliberate negative control — which is kept as
a frozen, runnable reference at `examples/pi_estimator/`. Read it while
building the real thing out below.

## Quick start

```bash
git clone <this-repo-url> && cd ptyco-full-simulator
conda env create -f environment.yml -n ptyco-full-simulator   # or: pip install -r requirements.txt
conda activate ptyco-full-simulator

bash scripts/reproduce.sh   # compute -> check -> provenance gate, in order
pytest tests/ -v             # unit tests, plus an automated negative control on the gate itself
```

`report/report.md` currently carries just one placeholder tag
(`template_wired`) proving the pipeline is wired end to end. Try breaking
it: change `[srcnum:template_wired:1]` to `[srcnum:template_wired:2]`, and
rerun `python scripts/check_provenance.py report/report.md`. It refuses to
pass, and tells you exactly which tag disagrees with the registry and by
how much. `tests/test_check_provenance.py` does this automatically so the
gate stays honest as the project evolves.

## The mechanism

**One registry, one writer.** `data/numbers.json` holds every number the
deliverable quotes. It is written *only* by `scripts/compute_numbers.py` —
nothing else touches it, and the deliverable never writes a number by hand.

**Two tags in the deliverable**, working in Markdown/HTML or LaTeX:

| Tag | Markdown/HTML | LaTeX | Checks |
|---|---|---|---|
| existence | `[src:key]` | `\src{key}` | the registry entry is well-formed and its `reproduce` path exists |
| literal value | `[srcnum:key:value]` | `\srcnum{key}{value}` | the above, **and** the displayed `value` agrees with the registry at the literal's own displayed precision |

`[srcnum:pi_true:3.14159]` means: this literal, `3.14159`, *is* registry
key `pi_true`, checked to half a unit in its last displayed digit (so
`3.14159` tolerates registry values from `3.141585` to `3.141595` — write
more digits to demand more precision). Getting this precision rule right
matters: with plain equality, any harmless rounding in how you chose to
*display* a number would fail the gate; with no precision check at all, a
wildly wrong digit would pass silently. This is the same rule
`pta-gwb-anisotropy`'s `\dataref` macro uses.

**An argument graph in `structure/`**, also modeled on
`pta-gwb-anisotropy`:

- `claims.yaml` — one record per load-bearing claim: its `statement`, the
  `numbers` keys it rests on, the `evidence.data_refs` (scripts) that
  produce them, and `depends_on` other claims — a graph, not a flat list.
- `scripts.yaml` — every script on the critical path; nothing the
  deliverable depends on may be missing from this list.
- `outputs.yaml` — every output artifact (figure, table, results file —
  generalized beyond LaTeX figures specifically), the script that produced
  it, and the claims it supports.

**One gate**, `scripts/check_provenance.py`, that cross-checks all of the
above and exits nonzero the moment anything doesn't resolve.

## Directory layout

```
.
|-- README.md
|-- LICENSE
|-- environment.yml            # pinned conda environment
|-- requirements.txt           # pip alternative
|
|-- structure/                 # the argument graph
|   |-- claims.yaml
|   |-- scripts.yaml
|   `-- outputs.yaml
|
|-- src/ptyco_full_simulator/  # the real analysis code -- currently just a placeholder
|
|-- scripts/
|   |-- compute_numbers.py     # SOLE WRITER of data/numbers.json
|   |-- checks.py              # correctness suite: positive checks + at least one negative control
|   |-- check_provenance.py    # the gate
|   `-- reproduce.sh           # compute -> check -> gate, in that order
|
|-- report/
|   `-- report.md              # the deliverable itself, tagged
|
|-- data/
|   |-- numbers.json           # the registry (generated; committed here so a fresh
|   |                          #   clone can run check_provenance.py immediately)
|   `-- checks_results.json    # machine-readable checks.py output
|
|-- tests/
|   `-- test_check_provenance.py   # PROVES the gate can fail: corrupts a copy of
|                                   #   the report and asserts it's rejected
|
`-- examples/pi_estimator/     # frozen reference: the template's original worked
                                #   example (Monte Carlo pi), fully self-contained --
                                #   see examples/pi_estimator/README.md
```

## Adapting this to a real project

This project already went through steps 1 and 4-6 below in placeholder
form (see `src/ptyco_full_simulator/`, `report/report.md`'s
`template_wired` tag, and `structure/claims.yaml`'s `template_wired`
claim) so the pipeline is runnable from the first commit. Fill it in:

1. Write your actual analysis code into `src/ptyco_full_simulator/`.
2. Rewrite `scripts/compute_numbers.py` to compute your real numbers, keep
   it the sole writer of `data/numbers.json`.
3. Rewrite `scripts/checks.py` with your real positive checks, and **keep
   at least one negative control** — a case built to disagree on purpose,
   so a passing suite means something. Pick negative controls that would
   expose a real error in your method, not ones chosen to flatter it.
4. Rewrite `report/report.md` (or swap it for LaTeX + `paperclaims.sty`-
   style macros, if you're writing a paper) with `[src:]` / `[srcnum:]`
   tags for every number.
5. Rewrite `structure/claims.yaml` as the actual argument of your
   deliverable — this is usually the most useful file to write *first*,
   before the code, because it forces you to state what you're going to
   need evidence for.
6. `bash scripts/reproduce.sh` end to end before you call anything done.

`examples/pi_estimator/` is the original template worked example, kept as
a running reference for the tag/registry/structure mechanism — it is not
wired into the live scripts above.

## What this template deliberately leaves out

`pta-gwb-anisotropy`'s `check_provenance.py` runs ten checks; this one runs
five (the tag layer, plus the three `structure/` cross-reference checks). Worth
adding if your project grows into a real release:

- **a repo-wide dangling-local-path scan** — every path-like token in every
  shipped file (not just the report) must resolve, so a stale reference in
  a comment or a doc can't rot silently;
- **`CITATION.cff` validation** — if you ship one, check it's valid YAML
  and carries the fields the Citation File Format requires;
- **deposited-data provenance** — if any input array is too large to
  commit and lives on Zenodo/similar, verify each file's recorded producer
  and schema against a manifest, the way `data/ZENODO.md` does there.

Also worth adding once you have a LaTeX report: a `[draft]`/`[final]`
package option (see `paperclaims.sty` in the reference repo) that renders
provenance annotations inline for review and hides them completely in the
version you ship.

## Reference

The full pattern, applied to a real 15,000-word paper with ~15 GB of
Monte Carlo data behind it, is at
[`matiaszaldarriaga/pta-gwb-anisotropy`](https://github.com/matiaszaldarriaga/pta-gwb-anisotropy).
Read its README's "Number provenance" and "Reproducibility" sections for
the fuller discipline this template only samples — in particular its
honest breakdown of what's bit-for-bit reproducible, what's reproducible
within a measured tolerance, and what isn't claimed at all.

## License

MIT — see `LICENSE`.

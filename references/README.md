# references/

Papers this project draws on — for theoretical grounding and/or as
comparison targets for computed results. Currently 37 Fourier
Ptychographic Microscopy (FPM) papers (2013-2026), 35 with a local PDF
(the other 2 — `pan2020`, `xiao2021` — are cited by DOI only: no
open-access copy).

- `bibliography.yaml` — one record per paper: metadata, `local_file` (when
  a PDF was actually downloaded), `role` (theory / comparison), and
  `applicable_to_gap` (flagged in the source reading notes as addressing a
  concrete gap in the current simulator code). Also carries
  `priority_focus`: the six highest-value gaps to tackle first, each
  pointing at one paper.
- `papers/` — the actual PDF files, organized by year, plus the original
  human-written reading notes `bibliography.yaml` was compiled from:
  `notebook.md` (full reading pass with the code-gap analysis),
  `foundational_papers.md`, and one `<year>_papers.md` per year. Keep
  reading `notebook.md` for the prose version/reasoning; `bibliography.yaml`
  is the structured, gate-compatible distillation of it.

## How to use a paper in the provenance chain

- **Theoretical grounding** — cite the PDF directly as a `data_ref` in the
  relevant claim in `structure/claims.yaml`, e.g.
  `references/papers/smith2020.pdf`. `scripts/check_provenance.py` checks
  that path exists on disk, same as any other evidence file.
- **Comparison target** — add the published value to `data/numbers.json`
  (via `scripts/compute_numbers.py`, its sole writer) as an entry with
  `"type": "source"` and `"reproduce"` set to a citation string (e.g.
  `"smith2020, Table 3"`). Quote it in `report/report.md` with
  `[srcnum:key:value]` like any other number — the gate then checks your
  reported literal against what you recorded from the paper.

#!/usr/bin/env python3
"""reconstruct_multispectral_coupled.py -- roadmap milestone 2b
(docs/roadmap_agentic_multispectral_pipeline.md): builds on milestone 2a
(reconstruct_multispectral_independent.py) by additionally unwrapping the
three RGB phases via the red-green/green-blue synthetic-wavelength pairs
and fitting the sample's Cauchy dispersion -- see
src/ptyco_full_simulator/multispectral.py's `couple_rgb_channels`.

IMPORTANT CAVEAT (found while building the integration test for this
script, see docs/roadmap_agentic_multispectral_pipeline.md): the current
baseline Wirtinger flow reconstruction (reconstruction.py) only converges
reliably for SMALL phase objects (roughly <0.1*pi rad on a 9x9 LED grid --
see the milestone 2a note on red's local-minimum sensitivity). Multi-
wavelength unwrapping only matters for objects with phase excursion beyond
pi (otherwise every channel's own wrap number is already 0, and this
script's unwrapping step is a no-op that still runs correctly, just
without anything to prove). On a REAL sample large enough to need
unwrapping, today's baseline solver likely cannot reconstruct it well
enough for this script's phase input to be trustworthy -- gap #1 (pupil
recovery, `ou2014`) and gap #3 (adaptive step size, `zuo2016`) from
references/bibliography.yaml's `priority_focus` are effectively
PREREQUISITES for this script to be useful on real large-phase samples,
not independent nice-to-haves. Both are now available per-channel via
--recover-pupil/--adaptive-step (2026-09-18), but see
tests/test_epry_pupil_recovery.py/test_adaptive_step_size.py for their
honest, measured effect -- EPRY's benefit was real but modest, and
adaptive_step showed no clean win on this project's small synthetic test
problems; neither is a proven fix for this caveat yet on a real sample.

With --use-reconstruction-agent and --qc both passed, this is the one
pipeline that chains all 3 of this project's agents in a single run:
agents/reconstruction_orchestrator.py per channel (milestone 3), then
agents/qc_agent.py on the coupled result (milestone 5), then -- if QC
recommends it -- agents/report_agent.py drafts a claim/report paragraph
(milestone 7). All three default to dry-run (no billed API calls); pass
--agent-live/--qc-live for real calls.

Usage:
    python pipelines/reconstruct_multispectral_coupled.py \\
        --data-root /path/to/data --grid-size 9 --objective current \\
        --crop 400 --background-rows 40 \\
        --baseline-index 1.34 --use-reconstruction-agent --qc \\
        --output-dir results/coupled_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import config, metrics, multispectral as ms  # noqa: E402
from reconstruct_multispectral_independent import CHANNEL_ORDER, reconstruct_all_channels  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
import qc_agent  # noqa: E402
import report_agent  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", required=True,
                    help="folder containing <channel>/<grid>x<grid>_recortada_<crop>/fila*_columna*.tiff")
    p.add_argument("--grid-size", type=int, default=9, help="LED grid is grid_size x grid_size (must be odd)")
    p.add_argument("--objective", choices=sorted(config.OBJECTIVES), default="current")
    p.add_argument("--crop", type=int, default=400,
                    help="the crop size named in the lab's own folder naming (...recortada_<crop>)")
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--background-rows", type=int, default=None,
                    help="use the top N rows of the reconstructed HR image as the bare-medium "
                         "background region for piston removal (see io_utils.py if your real field "
                         "of view puts the background somewhere else -- pass a custom mask via Python "
                         "instead of this CLI for that case)")
    p.add_argument("--baseline-index", type=float, default=None,
                    help="known refractive index of the sample/medium, to resolve thickness and B "
                         "from the fitted C, D (see multispectral.py's degeneracy note) -- omit to "
                         "only report C, D")
    p.add_argument("--use-reconstruction-agent", action="store_true",
                    help="use agents/reconstruction_orchestrator.py's milestone-3 agent per channel "
                         "instead of a single direct reconstruction call -- combine with --qc to "
                         "exercise all 3 of this project's agents (reconstruction, QC, report) in "
                         "one pipeline run. Defaults to a canned dry-run decision; pass --agent-live "
                         "for a real (billed) claude -p call per channel.")
    p.add_argument("--agent-live", action="store_true",
                    help="make --use-reconstruction-agent call the real agent instead of a dry-run "
                         "stub -- COSTS MONEY per channel, see agents/reconstruction_orchestrator.py")
    p.add_argument("--max-attempts", type=int, default=3,
                    help="only used with --use-reconstruction-agent")
    p.add_argument("--recover-pupil", action="store_true",
                    help="use reconstruction.reconstruct's EPRY pupil-recovery mode (ou2014) per "
                         "channel instead of assuming the ideal NA-limited pupil -- see that "
                         "function's docstring and tests/test_epry_pupil_recovery.py for its honest, "
                         "modest measured benefit (and its real risk of REGRESSING an already-good "
                         "channel at this project's small testbed scale). Mutually exclusive with "
                         "--use-reconstruction-agent (a real information deficit, not just "
                         "unimplemented -- see agents/reconstruction_orchestrator.py's docstring) "
                         "and with --adaptive-step (EPRY has its own self-scaling step).")
    p.add_argument("--adaptive-step", action="store_true",
                    help="use reconstruction.reconstruct's zuo2016 adaptive step-size mode per "
                         "channel instead of the fixed ramp -- see that function's docstring and "
                         "tests/test_adaptive_step_size.py: no clean win at light noise/few "
                         "iterations, but a real gain at heavy noise (peak_photon_count<=3) and "
                         "many iterations (>=400). CAN be combined with --use-reconstruction-agent "
                         "(2026-09-18: resolved, see orchestrate_reconstruction's docstring). "
                         "Mutually exclusive with --recover-pupil.")
    p.add_argument("--qc", action="store_true",
                    help="run the milestone-5 QC/confidence agent (agents/qc_agent.py) on this run's "
                         "diagnostics -- defaults to a canned dry-run decision, pass --qc-live for a "
                         "real (billed) claude -p call, see that module's docstring for measured cost")
    p.add_argument("--qc-live", action="store_true",
                    help="make --qc call the real agent instead of a dry-run stub -- COSTS MONEY "
                         "per run, see agents/reconstruction_orchestrator.py's docstring for the "
                         "measured cost/latency of this call pattern")
    p.add_argument("--output-dir", default="results/reconstruct_multispectral_coupled")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.output_dir, exist_ok=True)

    run = reconstruct_all_channels(
        args.data_root, args.grid_size, objective=args.objective,
        crop=args.crop, iterations=args.iterations,
        use_reconstruction_agent=args.use_reconstruction_agent,
        agent_live=args.agent_live, max_attempts=args.max_attempts,
        recover_pupil=args.recover_pupil, adaptive_step=args.adaptive_step,
    )
    for channel in CHANNEL_ORDER:
        attempts = run["channels"][channel]["agent_attempts"]
        if attempts is not None:
            for i, attempt in enumerate(attempts):
                print(f"  {channel} agent attempt {i + 1}/{len(attempts)}: "
                      f"step_max={attempt['step_max']}  decision={attempt['decision']['action']}  "
                      f"reasoning={attempt['decision']['reasoning']!r}")
        pupil = run["channels"][channel]["pupil"]
        if pupil is not None:
            print(f"  {channel} recovered pupil phase range: "
                  f"[{np.angle(pupil).min():.3f}, {np.angle(pupil).max():.3f}] rad")
    hr_shape = run["hr_shape"]
    background_rows = args.background_rows or max(1, hr_shape[0] // 8)
    background_mask = np.zeros(hr_shape, dtype=bool)
    background_mask[:background_rows, :] = True

    phases_wrapped = {ch: np.angle(run["channels"][ch]["object"]) for ch in CHANNEL_ORDER}
    wavelengths_um = {ch: config.CHANNEL_WAVELENGTH_NM[ch] / 1000.0 for ch in CHANNEL_ORDER}

    coupled = ms.couple_rgb_channels(phases_wrapped, wavelengths_um, background_mask,
                                      baseline_index_A=args.baseline_index)

    print(f"grid={args.grid_size}x{args.grid_size}  objective={args.objective}  "
          f"background_rows={background_rows}  baseline_index={args.baseline_index}")
    for pair, disagreement in coupled["pair_disagreement"].items():
        print(f"  {pair} disagreement: mean={float(np.mean(disagreement)):.5f}um  "
              f"max={float(np.max(disagreement)):.5f}um")
    if coupled["resolved"] is not None:
        t = coupled["resolved"]["thickness_um"]
        print(f"  thickness: mean={float(np.mean(t)):.4f}um  range=[{float(np.min(t)):.4f}, {float(np.max(t)):.4f}]um")

    if args.qc:
        channel_convergence = {ch: metrics.convergence_summary(run["channels"][ch]["history"])
                                for ch in CHANNEL_ORDER}
        qc_out = qc_agent.qc_review(channel_convergence, coupled["pair_disagreement"],
                                     background_rows, hr_shape, dry_run=not args.qc_live)
        print(f"  QC verdict: confidence={qc_out['decision']['confidence']}  "
              f"recommendation={qc_out['decision']['recommendation']}")
        if qc_out["decision"]["flagged_issues"]:
            print(f"  QC flagged: {qc_out['decision']['flagged_issues']}")
        with open(os.path.join(args.output_dir, "qc_review.json"), "w") as fh:
            json.dump(qc_out, fh, indent=2)

        if qc_out["decision"]["recommendation"] == "report":
            report_numbers = {
                k: {"value": v} for k, v in qc_out["diagnostics"]["pairs"].items()
            }
            if coupled["resolved"] is not None:
                report_numbers["thickness_um_mean"] = {"value": float(np.mean(coupled["resolved"]["thickness_um"]))}
            draft = report_agent.draft_claim_and_report(
                report_numbers,
                f"A milestone-2b coupled multispectral run on real data (grid={args.grid_size}, "
                f"objective={args.objective}) passed QC review with confidence="
                f"{qc_out['decision']['confidence']}.",
                existing_claim_ids=[],  # unknown here -- draft is for a human to reconcile against
                # structure/claims.yaml themselves, this pipeline doesn't read that file
                dry_run=not args.qc_live,
            )
            print(f"  report draft: worth_reporting={draft['worth_reporting']}  "
                  f"claim_id={draft.get('claim_id')}")
            with open(os.path.join(args.output_dir, "report_draft.json"), "w") as fh:
                json.dump(draft, fh, indent=2)
            print("  NOTE: report_draft.json's numbers are NOT yet in data/numbers.json -- "
                  "this is a draft for a human to formalize into scripts/compute_numbers.py and "
                  "structure/claims.yaml, not something applied automatically.")

    np.savez(
        os.path.join(args.output_dir, "coupled_opl.npz"),
        **{f"opl_{ch}": coupled["opl"][ch] for ch in CHANNEL_ORDER},
        C=coupled["fit"]["C"], D=coupled["fit"]["D"],
    )
    metrics_out = {
        "background_rows": background_rows, "baseline_index": args.baseline_index,
        "use_reconstruction_agent": args.use_reconstruction_agent,
        "recover_pupil": args.recover_pupil, "adaptive_step": args.adaptive_step,
        "agent_attempts": {ch: run["channels"][ch]["agent_attempts"] for ch in CHANNEL_ORDER},
        "pair_disagreement_mean": {k: float(np.mean(v)) for k, v in coupled["pair_disagreement"].items()},
        "pair_disagreement_max": {k: float(np.max(v)) for k, v in coupled["pair_disagreement"].items()},
    }
    if coupled["resolved"] is not None:
        metrics_out["thickness_um_mean"] = float(np.mean(coupled["resolved"]["thickness_um"]))
    with open(os.path.join(args.output_dir, "coupled_metrics.json"), "w") as fh:
        json.dump(metrics_out, fh, indent=2)
    print(f"wrote results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

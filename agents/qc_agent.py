#!/usr/bin/env python3
"""qc_agent.py -- roadmap milestone 5, "Agente #3": Cross-channel
consistency + Confidence/QC agent (docs/roadmap_agentic_multispectral_pipeline.md
section 2/milestone 5), merged into one agent since both decisions are
answered by the same underlying diagnostics this project already computes
and neither has real data to reconstruct-and-compare against in this
Codespace (no ground truth for real captures, and no real lab data here
at all -- see every other multispectral test file's docstring).

What this agent decides, given a completed milestone-2 coupled run
(`pipelines/reconstruct_multispectral_coupled.py` /
`multispectral.couple_rgb_channels`) and no ground truth to compare
against (the real-data case; simulation has `metrics.compare_to_ground_truth`
for that, this agent is for when that's not available):

- **Cross-channel consistency**: are the red-green and green-blue OPL
  disagreements (`couple_rgb_channels`'s "pair_disagreement", already
  computed, not new math here) small and uniform, or does one region/
  channel look like it diverged?
- **Confidence**: given per-channel convergence health
  (`metrics.convergence_summary`, from milestone 2a's `reconstruct_all_channels`)
  and the phase-only/low-amplitude-contrast risk this project's own
  milestone-2 integration found (docs/roadmap...  section 1 point 6),
  should this run's dispersion result be reported, flagged for review, or
  discarded?

Same architecture as `agents/reconstruction_orchestrator.py` (Claude Code
itself via `claude -p --restricted --json-schema`, not a standalone
framework -- see that module's docstring for the measured cost/latency
this implies, which applies here too) and the same testing discipline:
`tests/test_qc_agent.py` stubs `agent_fn`, no real (billed) API call runs
in the regular test suite.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "recommendation": {"type": "string", "enum": ["report", "flag_for_review", "discard"]},
        "flagged_issues": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["confidence", "recommendation", "flagged_issues", "reasoning"],
}


def summarize_run_diagnostics(channel_convergence: dict, pair_disagreement: dict,
                               background_rows: int, hr_shape: tuple) -> dict:
    """Reduce a milestone-2 coupled run's raw per-pixel/per-channel outputs
    to the small set of numbers actually worth putting in an agent prompt
    -- deterministic, no LLM involved, so it's directly unit-testable
    (tests/test_qc_agent.py) independent of any API call.

    `channel_convergence`: {"red"/"green"/"blue":
    metrics.convergence_summary(...) return value}.
    `pair_disagreement`: `couple_rgb_channels`'s "pair_disagreement" dict
    ({"red_green", "green_blue": array}).
    """
    summary = {"channels": {}, "pairs": {}}
    for channel, conv in channel_convergence.items():
        summary["channels"][channel] = {
            "relative_improvement": round(float(conv["relative_improvement"]), 4),
            "fraction_of_epochs_that_improved": round(float(conv["fraction_of_epochs_that_improved"]), 4),
        }
    for pair, disagreement in pair_disagreement.items():
        flat = np.asarray(disagreement).ravel()
        summary["pairs"][pair] = {
            "mean_um": round(float(np.mean(flat)), 6),
            "p95_um": round(float(np.percentile(flat, 95)), 6),
            "max_um": round(float(np.max(flat)), 6),
        }
    summary["background_rows"] = background_rows
    summary["hr_shape"] = list(hr_shape)
    return summary


def build_qc_prompt(diagnostics: dict) -> str:
    return (
        "You are a QC/confidence agent for a multispectral (RGB) Fourier Ptychographic Microscopy "
        "reconstruction pipeline (pipelines/reconstruct_multispectral_coupled.py). There is NO ground "
        "truth available (real lab data) -- you must judge trustworthiness from internal diagnostics "
        "alone.\n\n"
        f"Per-channel reconstruction convergence: {json.dumps(diagnostics['channels'])}\n"
        f"Cross-channel OPL disagreement after unwrapping (red-green, green-blue pairs, in "
        f"micrometers -- small and uniform is good, large or spatially concentrated suggests one "
        f"channel diverged or the wrap-number search picked the wrong pair somewhere): "
        f"{json.dumps(diagnostics['pairs'])}\n"
        f"HR image shape: {diagnostics['hr_shape']}, background reference rows used for piston "
        f"removal: {diagnostics['background_rows']}.\n\n"
        "Known failure modes of this pipeline (from its own development, "
        "docs/roadmap_agentic_multispectral_pipeline.md): (1) a channel with "
        "relative_improvement well below the others, or fraction_of_epochs_that_improved "
        "noticeably less than 1.0, may be stuck in a local minimum -- this baseline solver is known "
        "to be sensitive to phase magnitude, spatial frequency content, and especially LOW AMPLITUDE "
        "CONTRAST objects (near phase-only samples reconstruct much worse). (2) Large pair "
        "disagreement (especially p95/max much bigger than mean) suggests the two-wavelength "
        "unwrapping picked a wrong wrap-number pair for some pixels, not real cross-channel physics.\n\n"
        "Decide: confidence (high/medium/low), recommendation (report the dispersion result as-is / "
        "flag_for_review by a human / discard this run and re-acquire+re-reconstruct), and list any "
        "specific issues you flagged."
    )


def call_agent_decision(prompt: str, model: str = "claude-haiku-4-5-20251001",
                         timeout_s: float = 120.0, dry_run: bool = False) -> dict:
    """See agents/reconstruction_orchestrator.py's `call_agent_decision`
    for the measured cost/latency this implies -- identical pattern,
    reused here rather than duplicated logic with different numbers.
    """
    if dry_run:
        return {
            "confidence": "high", "recommendation": "report",
            "flagged_issues": [], "reasoning": "dry_run=True, no API call made",
        }

    result = subprocess.run(
        ["claude", "-p", "--restricted", "--model", model,
         "--output-format", "json", "--json-schema", json.dumps(DECISION_SCHEMA), prompt],
        capture_output=True, text=True, timeout=timeout_s, check=True,
    )
    payload = json.loads(result.stdout)
    if payload.get("is_error"):
        raise RuntimeError(f"claude -p returned an error: {payload}")
    return payload["structured_output"]


def qc_review(channel_convergence: dict, pair_disagreement: dict, background_rows: int,
              hr_shape: tuple, dry_run: bool = False, agent_fn=call_agent_decision) -> dict:
    """The milestone 5 deliverable: reduce a coupled run's diagnostics
    (`summarize_run_diagnostics`) and ask the agent for a confidence
    verdict. `agent_fn` is injected for testing, same pattern as
    `agents/reconstruction_orchestrator.orchestrate_reconstruction`.

    Returns {"diagnostics": summarize_run_diagnostics's output, "decision":
    the agent's structured decision}.
    """
    diagnostics = summarize_run_diagnostics(channel_convergence, pair_disagreement,
                                             background_rows, hr_shape)
    prompt = build_qc_prompt(diagnostics)
    decision = agent_fn(prompt, dry_run=dry_run)
    return {"diagnostics": diagnostics, "decision": decision}

#!/usr/bin/env python3
"""reconstruction_orchestrator.py -- roadmap milestone 3, "Agente #1"
(docs/roadmap_agentic_multispectral_pipeline.md section 2/3): a
Reconstruction-orchestration agent that decides, given a completed run's
`metrics.convergence_summary`, whether to accept the result, retry with a
different `step_max`, or declare the run stuck in the known local-minimum
failure mode (reconstruction.py's own documented limitation) -- instead of
a human reading `history` by hand, which is what this project's own
milestone 2a/2 sections did by hand throughout their development.

Architecture decision this follows (confirmed with the user 2026-09-17,
see docs/roadmap_agentic_multispectral_pipeline.md's resolved question
#3): the agent IS Claude Code itself, invoked as a subprocess (`claude -p`
with `--output-format json` and `--json-schema` for a structured decision)
-- not a standalone framework (LangGraph/AutoGen). Every call to
`call_agent_decision` below makes a REAL, BILLED API call when
`dry_run=False` -- see the cost/latency note in that function's docstring
before running this against a live budget.

Two entry points:
- `orchestrate_reconstruction`: runs reconstruction.reconstruct, asks the
  agent whether to retry with an adjusted step_max, and repeats up to
  `max_attempts` -- the actual milestone 3 deliverable.
- `call_agent_decision` / `build_decision_prompt`: split out so
  tests/test_reconstruction_orchestrator.py can test the orchestration
  LOGIC (prompt content, retry bookkeeping, decision handling) via a
  stub, without making a real (billed) API call on every test run --
  standard practice for code that wraps a paid external API, and
  necessary here specifically: a live smoke test during development of
  this file cost $0.03-0.13 and took 9-11 seconds PER CALL (see that
  finding in the roadmap) -- unaffordable to run on every test suite
  invocation.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import metrics, reconstruction  # noqa: E402

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["accept", "retry", "give_up"]},
        "new_step_max": {"type": ["number", "null"]},
        "reasoning": {"type": "string"},
    },
    "required": ["action", "new_step_max", "reasoning"],
}


def build_decision_prompt(history: list[dict], step_max: float, attempt: int, max_attempts: int) -> str:
    """The context the agent needs to decide -- deliberately just the
    convergence history and current parameters, nothing about the object
    or image data (the agent reasons about optimization dynamics, not
    image content -- keeps the prompt small and the decision fast/cheap).
    """
    conv = metrics.convergence_summary(history)
    return (
        "You are deciding whether an FPM (Fourier Ptychographic Microscopy) phase-retrieval "
        "reconstruction (incremental Wirtinger flow, reconstruction.py) has converged, or is "
        "stuck in a local minimum and should be retried with a different step_max.\n\n"
        f"Attempt {attempt + 1} of {max_attempts} (max). Current step_max={step_max}.\n"
        f"recovery_error per iteration: {[round(h['recovery_error'], 6) for h in history]}\n"
        f"Summary: first_error={conv['first_error']:.6g}, last_error={conv['last_error']:.6g}, "
        f"relative_improvement={conv['relative_improvement']:.4f}, "
        f"fraction_of_epochs_that_improved={conv['fraction_of_epochs_that_improved']:.4f}\n\n"
        "Known properties of this algorithm (references/bibliography.yaml priority_focus, "
        "docs/roadmap_agentic_multispectral_pipeline.md): a large/high-frequency phase object, "
        "or one with low amplitude contrast, on a small LED grid can converge to the wrong local "
        "minimum -- recovery_error can keep decreasing (fitting the noisy data better) while "
        "actual reconstruction quality stops improving or gets worse; this is a real property of "
        "vanilla Wirtinger flow, not always fixable by just running longer.\n\n"
        "Decide one of: \"accept\" (converged well, use this result), \"retry\" (try again with a "
        "different step_max -- set new_step_max to your suggested value), or \"give_up\" (this "
        "object is likely stuck in a local minimum that changing step_max won't fix -- e.g. if this "
        "is already the last allowed attempt, or error improvement has plateaued across attempts). "
        "If action is not \"retry\", set new_step_max to null."
    )


def call_agent_decision(prompt: str, model: str = "claude-haiku-4-5-20251001",
                         timeout_s: float = 120.0, dry_run: bool = False) -> dict:
    """Invoke `claude -p` for a single structured decision.

    COST/LATENCY, measured live during development of this file
    (2026-09-17, see docs/roadmap_agentic_multispectral_pipeline.md):
    ~$0.03-0.04 and ~10-11 seconds per call with `--restricted` and this
    module's default (cheap/fast) model pinned -- an UNRESTRICTED call
    with no model pinned cost ~$0.13 and took ~9s with unexpected extra
    tool-use turns. `--restricted` (no Bash/file tools) is passed below
    specifically to keep this a pure text-in/JSON-out decision, not an
    open-ended agentic session.

    `dry_run=True` returns a canned "accept" decision without calling the
    API at all -- used by this module's own tests, and a reasonable
    default for anyone exploring this script who doesn't want to spend
    money by accident.
    """
    if dry_run:
        return {"action": "accept", "new_step_max": None, "reasoning": "dry_run=True, no API call made"}

    result = subprocess.run(
        ["claude", "-p", "--restricted", "--model", model,
         "--output-format", "json", "--json-schema", json.dumps(DECISION_SCHEMA), prompt],
        capture_output=True, text=True, timeout=timeout_s, check=True,
    )
    payload = json.loads(result.stdout)
    if payload.get("is_error"):
        raise RuntimeError(f"claude -p returned an error: {payload}")
    return payload["structured_output"]


def orchestrate_reconstruction(lr_images, led_grid, hr_pixel_um, lr_pixel_um, na, wavelength_um,
                                factor, initial_step_max: float = 20.0, iterations: int = 40,
                                max_attempts: int = 3, dry_run: bool = False,
                                agent_fn=call_agent_decision, initial_object=None) -> dict:
    """The milestone 3 deliverable: run `reconstruction.reconstruct`, ask
    the agent whether to retry with a different `step_max`, and repeat up
    to `max_attempts`. Each attempt restarts from scratch (reconstruct()
    has no resume/warm-start support -- adding one is out of scope here;
    a retry costs a full `iterations` pass, not a cheap continuation).

    `agent_fn` is injected (defaults to the real `call_agent_decision`) so
    tests can pass a stub instead -- see this module's docstring for why.

    `initial_object`, if given, is passed through to every attempt's
    `reconstruction.reconstruct` call unchanged (e.g. a Transport-of-
    Intensity-Equation phase estimate from `propagation.solve_tie` --
    see `pipelines/simulate_and_reconstruct.py`'s `--tie-defocus-um` for
    where that comes from). Combining the two is exactly the open
    question docs/roadmap_agentic_multispectral_pipeline.md flags under
    milestone 3/section 1 point 6: whether continuing iteration after a
    TIE-informed start helps or hurts is inconsistent, and no internal
    diagnostic tried so far (recovery_error, held-out residual, low-freq
    drift from TIE) can tell the agent which -- so `build_decision_prompt`
    is NOT currently told whether `initial_object` was used, and the
    agent's retry/step_max decisions here are no more informed about that
    open question than before. Wiring `initial_object` through is a
    prerequisite for eventually closing that gap, not a claim that it's
    closed.

    Returns {"result": the winning attempt's reconstruction.reconstruct()
    return value, "attempts": [{"step_max", "history", "decision"} per
    attempt tried] -- a full audit trail of what the agent decided and
    why, at every attempt}.
    """
    step_max = initial_step_max
    attempts_log = []
    result = None

    for attempt in range(max_attempts):
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, lr_pixel_um, na, wavelength_um, factor,
            iterations=iterations, step_max=step_max, initial_object=initial_object,
        )
        prompt = build_decision_prompt(result["history"], step_max, attempt, max_attempts)
        decision = agent_fn(prompt, dry_run=dry_run)
        attempts_log.append({"step_max": step_max, "history": result["history"], "decision": decision})

        if decision["action"] != "retry" or attempt == max_attempts - 1:
            break
        if decision.get("new_step_max"):
            step_max = float(decision["new_step_max"])

    return {"result": result, "attempts": attempts_log}

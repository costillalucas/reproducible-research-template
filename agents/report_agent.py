#!/usr/bin/env python3
"""report_agent.py -- roadmap milestone 7's missing piece
(docs/roadmap_agentic_multispectral_pipeline.md): every other milestone
this session added its own numbers/claims/report section BY HAND
(scripts/compute_numbers.py, structure/claims.yaml, report/report.md) --
this agent automates that authoring step: given a new finding's already-
computed numbers, draft a claims.yaml-style claim and a report.md-style
paragraph quoting them through the project's [src:]/[srcnum:] tags.

Same architecture as the other two agents in this directory (Claude Code
itself via `claude -p --restricted --json-schema`, not a standalone
framework) and the same testing discipline (`agent_fn` injectable, tests
stub it, no real billed API call in the regular suite).

This agent does NOT decide what to compute or write data/numbers.json
(that's still scripts/compute_numbers.py, the sole writer, unchanged) --
it only drafts the claim/report TEXT around numbers that already exist in
the registry, and flags whether a finding seems worth reporting at all.
The human (or a future orchestrating session) still adds the draft to the
actual files and re-runs scripts/check_provenance.py to confirm it's
well-formed -- this agent's draft is not applied automatically.
"""
from __future__ import annotations

import json
import subprocess

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "worth_reporting": {"type": "boolean"},
        "claim_id": {"type": "string"},
        "claim_statement": {"type": "string"},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "report_markdown": {"type": "string"},
        "reasoning": {"type": "string"},
    },
    "required": ["worth_reporting", "claim_id", "claim_statement", "depends_on",
                 "report_markdown", "reasoning"],
}


def build_report_draft_prompt(numbers: dict, description: str, existing_claim_ids: list[str]) -> str:
    """`numbers`: {key: {"value": ..., "statement": ...}} -- a subset of
    data/numbers.json's entries this finding is about (already computed
    by scripts/compute_numbers.py; this agent never invents a number).
    `description`: what was found, in the same voice as this project's
    own commit messages/roadmap entries -- what changed, why it matters,
    any honest caveats (see docs/roadmap_agentic_multispectral_pipeline.md
    for the house style: state findings plainly, including negative ones).
    `existing_claim_ids`: structure/claims.yaml's current ids, so the
    agent can pick a `depends_on` that actually resolves and a `claim_id`
    that doesn't collide.
    """
    numbers_json = json.dumps({k: v.get("value") for k, v in numbers.items()}, indent=2)
    return (
        "You are drafting a claims.yaml entry and a report.md paragraph for a reproducible-research "
        "project (see its own README's 'The mechanism' section: report.md quotes "
        "data/numbers.json ONLY through [src:key] (existence) and [srcnum:key:value] (literal "
        "value, checked to match the registry at the displayed literal's own precision) tags -- "
        "scripts/check_provenance.py enforces this, no number may be written by hand).\n\n"
        f"Finding: {description}\n\n"
        f"Already-computed numbers available to cite (do NOT invent others):\n{numbers_json}\n\n"
        f"Existing claim ids already in structure/claims.yaml (pick depends_on from these, or []): "
        f"{existing_claim_ids}\n\n"
        "Draft: (1) worth_reporting -- is this a real, load-bearing finding worth a claim, or too "
        "minor/uncertain? (2) claim_id -- a new, short, snake_case id, distinct from the existing "
        "ones. (3) claim_statement -- 2-4 sentences, plain, honest (state real limitations/caveats "
        "if the numbers show them, don't oversell). (4) depends_on -- ids from the existing list "
        "this claim's truth relies on, or []. (5) report_markdown -- a short report.md-style "
        "paragraph (a heading plus 1-2 sentences) that quotes EVERY number in the numbers dict above "
        "using [srcnum:key:value] the first time and [src:key] if referenced again, with `value` "
        "written EXACTLY as it should be checked (a literal, at a sensible precision, since the gate "
        "checks it against the registry at that same precision -- do not round more coarsely than "
        "the number's own precision warrants, but you do not need every decimal digit either)."
    )


def call_agent_decision(prompt: str, model: str = "claude-haiku-4-5-20251001",
                         timeout_s: float = 120.0, dry_run: bool = False) -> dict:
    """See agents/reconstruction_orchestrator.py's `call_agent_decision`
    docstring for the measured cost/latency this pattern implies.
    """
    if dry_run:
        return {
            "worth_reporting": True, "claim_id": "dry_run_placeholder_claim",
            "claim_statement": "dry_run=True, no API call made.", "depends_on": [],
            "report_markdown": "## Dry run\n\ndry_run=True, no API call made.",
            "reasoning": "dry_run=True, no API call made",
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


def draft_claim_and_report(numbers: dict, description: str, existing_claim_ids: list[str],
                            dry_run: bool = False, agent_fn=call_agent_decision) -> dict:
    """The milestone 7 deliverable: draft a claim + report paragraph for
    a finding whose numbers are already in the registry. Returns the
    agent's structured decision as-is -- validate it yourself (e.g. paste
    `report_markdown` into a scratch copy of report.md and run
    scripts/check_provenance.py) before touching the real files; this
    function does not write anything.
    """
    prompt = build_report_draft_prompt(numbers, description, existing_claim_ids)
    return agent_fn(prompt, dry_run=dry_run)

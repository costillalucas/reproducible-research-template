"""tests/test_report_agent.py -- agents/report_agent.py's prompt-building
and wiring logic. Same discipline as
tests/test_reconstruction_orchestrator.py / tests/test_qc_agent.py: a
stub `agent_fn` is injected, no real `claude -p` call (billed, see that
module's docstring for measured cost) runs as part of this suite.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

import report_agent  # noqa: E402


def test_build_report_draft_prompt_includes_numbers_and_existing_ids():
    numbers = {"my_metric": {"value": 0.987, "statement": "some metric"}}
    prompt = report_agent.build_report_draft_prompt(
        numbers, "found a thing", ["existing_claim_a", "existing_claim_b"],
    )
    assert "0.987" in prompt
    assert "existing_claim_a" in prompt and "existing_claim_b" in prompt
    assert "found a thing" in prompt


def test_draft_claim_and_report_passes_prompt_to_agent_fn():
    captured = []

    def stub(prompt, dry_run=False):
        captured.append(prompt)
        return {
            "worth_reporting": True, "claim_id": "stub_claim",
            "claim_statement": "stub statement", "depends_on": ["existing_claim_a"],
            "report_markdown": "## Stub\n\n[srcnum:my_metric:0.987][src:my_metric]",
            "reasoning": "stub",
        }

    numbers = {"my_metric": {"value": 0.987, "statement": "some metric"}}
    result = report_agent.draft_claim_and_report(
        numbers, "found a thing", ["existing_claim_a"], agent_fn=stub,
    )

    assert len(captured) == 1
    assert result["claim_id"] == "stub_claim"
    assert result["depends_on"] == ["existing_claim_a"]


def test_call_agent_decision_dry_run_never_invokes_subprocess(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry_run=True must not call subprocess.run")

    monkeypatch.setattr(report_agent.subprocess, "run", fail_if_called)

    decision = report_agent.call_agent_decision("irrelevant prompt", dry_run=True)
    assert decision["worth_reporting"] is True
    assert "claim_id" in decision

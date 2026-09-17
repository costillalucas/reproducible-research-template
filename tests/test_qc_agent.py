"""tests/test_qc_agent.py -- roadmap milestone 5 (Agente #3):
agents/qc_agent.py's diagnostic-summarization and prompt-wiring logic.
Same testing discipline as tests/test_reconstruction_orchestrator.py: a
stub `agent_fn` is injected everywhere, no real `claude -p` call (which
costs real money -- see that module's docstring for the measured cost)
runs as part of this suite.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

import qc_agent  # noqa: E402


def test_summarize_run_diagnostics_reduces_arrays_to_scalars():
    channel_convergence = {
        "red": {"first_error": 3.5, "last_error": 0.5, "relative_improvement": 0.857,
                "fraction_of_epochs_that_improved": 0.9},
        "green": {"first_error": 3.5, "last_error": 0.1, "relative_improvement": 0.971,
                  "fraction_of_epochs_that_improved": 1.0},
        "blue": {"first_error": 3.5, "last_error": 0.2, "relative_improvement": 0.943,
                 "fraction_of_epochs_that_improved": 0.95},
    }
    pair_disagreement = {
        "red_green": np.array([[0.001, 0.002], [0.001, 0.5]]),  # one outlier pixel
        "green_blue": np.array([[0.0005, 0.0006], [0.0007, 0.0006]]),
    }

    summary = qc_agent.summarize_run_diagnostics(channel_convergence, pair_disagreement,
                                                   background_rows=4, hr_shape=(48, 48))

    assert summary["channels"]["green"]["relative_improvement"] == 0.971
    assert summary["pairs"]["red_green"]["max_um"] == 0.5
    assert summary["pairs"]["red_green"]["mean_um"] < summary["pairs"]["red_green"]["max_um"], (
        "the mean should be pulled down by the non-outlier pixels, not equal the single outlier"
    )
    assert summary["pairs"]["green_blue"]["max_um"] < 0.001
    assert summary["background_rows"] == 4
    assert summary["hr_shape"] == [48, 48]


def test_build_qc_prompt_includes_the_actual_numbers():
    channel_convergence = {"red": {"first_error": 1.0, "last_error": 0.1,
                                    "relative_improvement": 0.9,
                                    "fraction_of_epochs_that_improved": 1.0}}
    pair_disagreement = {"red_green": np.array([[0.012]])}
    diagnostics = qc_agent.summarize_run_diagnostics(channel_convergence, pair_disagreement,
                                                       background_rows=3, hr_shape=(20, 20))
    prompt = qc_agent.build_qc_prompt(diagnostics)

    assert "0.9" in prompt
    assert "0.012" in prompt
    assert "[20, 20]" in prompt


def test_qc_review_passes_summarized_diagnostics_to_the_agent():
    captured_prompts = []

    def stub(prompt, dry_run=False):
        captured_prompts.append(prompt)
        return {"confidence": "medium", "recommendation": "flag_for_review",
                "flagged_issues": ["red channel improvement looks low"], "reasoning": "stub"}

    channel_convergence = {"red": {"first_error": 1.0, "last_error": 0.5,
                                    "relative_improvement": 0.5,
                                    "fraction_of_epochs_that_improved": 0.6}}
    pair_disagreement = {"red_green": np.array([[0.02]])}

    out = qc_agent.qc_review(channel_convergence, pair_disagreement, background_rows=4,
                              hr_shape=(30, 30), agent_fn=stub)

    assert len(captured_prompts) == 1
    assert out["decision"]["recommendation"] == "flag_for_review"
    assert out["diagnostics"]["channels"]["red"]["relative_improvement"] == 0.5


def test_call_agent_decision_dry_run_never_invokes_subprocess(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry_run=True must not call subprocess.run")

    monkeypatch.setattr(qc_agent.subprocess, "run", fail_if_called)

    decision = qc_agent.call_agent_decision("irrelevant prompt", dry_run=True)
    assert decision["recommendation"] == "report"

"""tests/test_reconstruction_orchestrator.py -- roadmap milestone 3
(docs/roadmap_agentic_multispectral_pipeline.md): tests
agents/reconstruction_orchestrator.py's orchestration LOGIC (retry
bookkeeping, decision handling, prompt content) using a stubbed agent
decision function -- NOT the real `claude -p` subprocess call, which
costs real money per invocation (see that module's docstring for the
measured cost: ~$0.03-0.04 and ~10s per call). Running the real API on
every test-suite invocation would be both expensive and flaky (network
dependent) -- standard practice for code wrapping a paid external API is
to test the wiring with a stub and leave the live call to be exercised
manually/deliberately, which is what happened once during this module's
own development (see the roadmap for that one live smoke test's result).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import reconstruction_orchestrator as orchestrator  # noqa: E402
from ptyco_full_simulator import config, forward_model, led_array, optics  # noqa: E402


def _small_reconstruction_inputs():
    """A tiny, cheap-to-run setup, same style as
    tests/test_ptyco_simulator.py's `_small_setup` -- this file cares
    about the orchestration loop around `reconstruction.reconstruct`, not
    about reconstruction quality itself (already covered elsewhere), so
    keep every actual reconstruct() call as fast as possible.
    """
    setup = config.default_setup(channel="green", grid_size=9, objective="current",
                                  resolution_px=(10, 10))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((10, 10), factor)

    h, w = hr_shape
    amp = np.ones(hr_shape) * 0.8
    truth = amp * np.exp(1j * 0.02 * np.sin(2 * np.pi * np.linspace(0, 1, w)))
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, led_grid, (10, 10), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    return dict(lr_images=lr_images, led_grid=led_grid, hr_pixel_um=hr_pixel_um,
                lr_pixel_um=setup.lr_pixel_size_um, na=setup.objective.na,
                wavelength_um=setup.wavelength_um, factor=factor)


def test_orchestrate_stops_on_accept_first_attempt():
    calls = []

    def stub_always_accept(prompt, dry_run=False):
        calls.append(prompt)
        return {"action": "accept", "new_step_max": None, "reasoning": "looks converged"}

    inputs = _small_reconstruction_inputs()
    out = orchestrator.orchestrate_reconstruction(
        **inputs, initial_step_max=10.0, iterations=5, max_attempts=3, agent_fn=stub_always_accept,
    )

    assert len(out["attempts"]) == 1
    assert out["attempts"][0]["decision"]["action"] == "accept"
    assert len(calls) == 1


def test_orchestrate_retries_then_accepts_and_applies_new_step_max():
    decisions = [
        {"action": "retry", "new_step_max": 5.0, "reasoning": "looked stuck, try a smaller step"},
        {"action": "accept", "new_step_max": None, "reasoning": "converged this time"},
    ]

    def stub_sequence(prompt, dry_run=False):
        return decisions.pop(0)

    inputs = _small_reconstruction_inputs()
    out = orchestrator.orchestrate_reconstruction(
        **inputs, initial_step_max=10.0, iterations=5, max_attempts=3, agent_fn=stub_sequence,
    )

    assert len(out["attempts"]) == 2
    assert out["attempts"][0]["step_max"] == 10.0
    assert out["attempts"][0]["decision"]["action"] == "retry"
    assert out["attempts"][1]["step_max"] == 5.0, "the agent's new_step_max must actually be used on the next attempt"
    assert out["attempts"][1]["decision"]["action"] == "accept"


def test_orchestrate_give_up_stops_immediately_even_with_attempts_left():
    def stub_give_up(prompt, dry_run=False):
        return {"action": "give_up", "new_step_max": None, "reasoning": "local minimum, retrying won't help"}

    inputs = _small_reconstruction_inputs()
    out = orchestrator.orchestrate_reconstruction(
        **inputs, initial_step_max=10.0, iterations=5, max_attempts=5, agent_fn=stub_give_up,
    )

    assert len(out["attempts"]) == 1, "give_up should stop the loop, not burn through all max_attempts"


def test_orchestrate_stops_at_max_attempts_even_if_agent_keeps_saying_retry():
    def stub_always_retry(prompt, dry_run=False):
        return {"action": "retry", "new_step_max": 8.0, "reasoning": "let's keep trying"}

    inputs = _small_reconstruction_inputs()
    out = orchestrator.orchestrate_reconstruction(
        **inputs, initial_step_max=10.0, iterations=5, max_attempts=3, agent_fn=stub_always_retry,
    )

    assert len(out["attempts"]) == 3, "must not loop forever no matter what the agent decides"


def test_build_decision_prompt_reports_the_actual_history_and_parameters():
    history = [{"iteration": 0, "recovery_error": 3.5}, {"iteration": 1, "recovery_error": 1.2}]
    prompt = orchestrator.build_decision_prompt(history, step_max=12.5, attempt=1, max_attempts=4)

    assert "step_max=12.5" in prompt
    assert "3.5" in prompt and "1.2" in prompt
    assert "Attempt 2 of 4" in prompt


def test_call_agent_decision_dry_run_never_invokes_subprocess(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry_run=True must not call subprocess.run")

    monkeypatch.setattr(orchestrator.subprocess, "run", fail_if_called)

    decision = orchestrator.call_agent_decision("irrelevant prompt", dry_run=True)
    assert decision["action"] == "accept"

"""tests/test_objective_presets.py -- objective preset names, deprecated
aliases and the default (2026-09-23): the real 2025-12-12 capture was
taken with the 2x/NA 0.10 objective, but the old default "current" was
2.5x/NA 0.07, so every real-data run used the wrong objective. Presets are
now named by what they are, "current"/"future" kept as aliases.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "pipelines"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "agents"))

from ptyco_full_simulator import config  # noqa: E402


def test_named_presets_have_the_right_values():
    assert (config.OBJECTIVES["2x_na010"].na, config.OBJECTIVES["2x_na010"].magnification) == (0.10, 2.0)
    assert (config.OBJECTIVES["2_5x_na007"].na, config.OBJECTIVES["2_5x_na007"].magnification) == (0.07, 2.5)


def test_deprecated_aliases_resolve_to_the_same_objective():
    assert config.OBJECTIVES["current"] == config.OBJECTIVES["2_5x_na007"]
    assert config.OBJECTIVES["future"] == config.OBJECTIVES["2x_na010"]


def test_default_is_the_objective_real_captures_use():
    assert config.DEFAULT_OBJECTIVE == "2x_na010"
    setup = config.default_setup(channel="green", grid_size=9)
    assert setup.objective == config.OBJECTIVES["2x_na010"]
    assert setup.lr_pixel_size_um == pytest.approx(1.6)


@pytest.mark.parametrize("module_name, expected_default", [
    ("reconstruct_real_images", "2x_na010"),
    ("reconstruct_multispectral_independent", "2x_na010"),
    ("reconstruct_multispectral_coupled", "2x_na010"),
    ("sweep_real_reconstruction_quality", "2x_na010"),
    # synthetic pipeline keeps the preset its recorded results used
    ("simulate_and_reconstruct", "2_5x_na007"),
])
def test_cli_defaults_and_choices_accept_new_and_old_names(module_name, expected_default):
    module = __import__(module_name)
    base = ["--data-root", "x"] if module_name != "simulate_and_reconstruct" else [
        "--amplitude-image", "a.png", "--phase-image", "p.png"]
    if module_name == "sweep_real_reconstruction_quality":
        base += ["--reference-image", "r.tif", "--iterations", "1"]
    args = module.parse_args(base)
    assert args.objective == expected_default
    for name in ("2x_na010", "2_5x_na007", "current", "future"):
        assert module.parse_args(base + ["--objective", name]).objective == name

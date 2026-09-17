"""tests/test_simulate_and_reconstruct_tie.py -- CLI-level integration
test for pipelines/simulate_and_reconstruct.py's `--tie-defocus-um` flag
(the concrete pipeline wiring for the TIE-informed initialization found
in tests/test_tie_informed_initialization.py -- this project's other
tests exercise the underlying library functions directly, but nothing
had run the actual CLI end to end with this flag until this file).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipelines"))
import simulate_and_reconstruct as pipeline  # noqa: E402


def _write_mixed_frequency_images(tmp_path, shape=(64, 64)):
    """Same weak-low-frequency + higher-frequency phase mix as
    tests/test_tie_informed_initialization.py, saved as 8-bit PNGs the
    way a real user would hand this pipeline images -- io_utils.py
    normalizes amplitude to [0,1] and phase to [-pi, pi] from these on
    load, so exact round-trip precision isn't expected, just the same
    qualitative shape.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((xc - 0.1) ** 2 + (yc + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((xc + 0.15) ** 2 + (yc - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.3 * np.sin(2 * np.pi * 1 * xc) + 0.15 * np.sin(2 * np.pi * 6 * xc)

    amp_path = tmp_path / "amplitude.png"
    phase_path = tmp_path / "phase.png"
    Image.fromarray((amp * 255).astype(np.uint8)).save(amp_path)
    phase_img = ((phase / np.abs(phase).max() + 1) / 2 * 255).astype(np.uint8)
    Image.fromarray(phase_img).save(phase_path)
    return str(amp_path), str(phase_path)


def test_tie_defocus_flag_massively_improves_phase_correlation(tmp_path):
    amp_path, phase_path = _write_mixed_frequency_images(tmp_path)
    common_args = [
        "--amplitude-image", amp_path, "--phase-image", phase_path,
        "--channel", "green", "--grid-size", "9", "--objective", "current",
        "--lr-size", "32", "--iterations", "40",
    ]

    baseline_dir = tmp_path / "baseline"
    pipeline.main(common_args + ["--output-dir", str(baseline_dir)])
    with open(baseline_dir / "metrics.json") as fh:
        baseline_metrics = json.load(fh)

    tie_dir = tmp_path / "tie"
    pipeline.main(common_args + ["--tie-defocus-um", "30", "--output-dir", str(tie_dir)])
    with open(tie_dir / "metrics.json") as fh:
        tie_metrics = json.load(fh)

    baseline_corr = baseline_metrics["vs_ground_truth"]["phase_correlation"]
    tie_corr = tie_metrics["vs_ground_truth"]["phase_correlation"]

    assert tie_metrics["setup"]["tie_defocus_um"] == 30.0
    assert baseline_metrics["setup"]["tie_defocus_um"] is None
    assert baseline_corr < 0.3, f"baseline should still be clearly broken here, got {baseline_corr}"
    assert tie_corr > baseline_corr + 0.5, (tie_corr, baseline_corr)

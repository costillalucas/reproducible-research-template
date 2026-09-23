"""tests/test_sweep_real_reconstruction_quality.py -- exercises
scripts/sweep_real_reconstruction_quality.py on a TINY synthetic case
only (no real lab data touched, no expensive iteration counts). See that
script's module docstring for what it's for: sweeping --iterations for a
single-channel real reconstruction and correlating each result's amplitude
against a real HR reference image, instead of only the internal
amplitude-residual convergence_summary.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ptyco_full_simulator import config, forward_model, led_array, optics  # noqa: E402
import sweep_real_reconstruction_quality as sweep_tool  # noqa: E402


def _synthetic_object(shape):
    """Small amplitude-only phantom (no phase) -- deliberately simple so a
    handful of iterations at a tiny grid actually converges well, unlike
    this project's usual weak-phase test objects (this test checks the
    sweep tool's own plumbing, not reconstruction quality itself, which
    is already covered elsewhere).
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.1 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.08 ** 2))
    return np.clip(amp, 0, 1).astype(complex)


def _build_in_memory_case(grid_size=9, crop=12, objective="2_5x_na007", channel="green"):
    setup = config.default_setup(channel=channel, grid_size=grid_size, objective=objective,
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    truth = _synthetic_object(hr_shape)

    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        truth, hr_pixel_um, led_grid, (crop, crop),
        setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
    )
    return setup, factor, hr_pixel_um, led_grid, lr_images, truth


def test_sweep_runs_and_reports_expected_shape_in_memory():
    setup, factor, hr_pixel_um, led_grid, lr_images, truth = _build_in_memory_case()
    reference = np.abs(truth)  # exact-source-object reference, see the correlation test below

    rows = sweep_tool.sweep(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor,
        iteration_values=[2, 5, 10], reference=reference,
    )

    assert [r["iterations"] for r in rows] == [2, 5, 10]
    for row in rows:
        assert set(row) == {
            "iterations", "elapsed_s", "relative_improvement",
            "fraction_of_epochs_that_improved", "reference_correlation",
            "flipud", "fliplr",
        }
        assert row["elapsed_s"] >= 0
        assert -1.0 <= row["reference_correlation"] <= 1.0


def test_sweep_correlates_positively_against_its_own_exact_source_object():
    """Sanity check of the tool's own correctness (resize/z-score/flip
    machinery in metrics.correlate_against_hr_reference), separate from
    validating the reconstruction algorithms themselves: a reconstruction
    run against a reference that IS its own true source object should
    correlate clearly positively, with the flip-search picking the right
    (no-flip) orientation (flipud=fliplr=False expected here, same array
    orientation as the reference).

    The threshold is deliberately modest (0.5, not e.g. 0.9): at this
    tiny grid_size=9/crop=12 test size, `reconstruction.reconstruct`
    plateaus at ~0.655 correlation regardless of iteration count (checked
    at 40/150/400 while writing this test -- internal recovery_error
    saturates near-perfectly at >0.9999 well before that, so this is a
    small-grid local-minimum property of the solver at this scale, not a
    bug in this sweep tool or in `correlate_against_hr_reference`; the
    flipud/fliplr values stayed correctly False at every iteration count
    checked). This test only needs to catch a REAL bug in the tool's own
    plumbing (e.g. a wrong flip, a broken resize) -- those would produce
    near-zero or negative correlation, not a merely-imperfect ~0.65.
    """
    setup, factor, hr_pixel_um, led_grid, lr_images, truth = _build_in_memory_case()
    reference = np.abs(truth)

    rows = sweep_tool.sweep(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor,
        iteration_values=[40], reference=reference,
    )
    row = rows[0]
    assert row["reference_correlation"] > 0.5, row
    assert row["flipud"] is False and row["fliplr"] is False, row


def test_sweep_rejects_gd_amplitude_with_wirtinger_only_flags():
    setup, factor, hr_pixel_um, led_grid, lr_images, truth = _build_in_memory_case()
    reference = np.abs(truth)
    try:
        sweep_tool.sweep(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor,
            iteration_values=[2], reference=reference,
            solver="gd-amplitude", adaptive_step=True,
        )
    except ValueError as exc:
        assert "wirtinger-only" in str(exc)
    else:
        raise AssertionError("expected ValueError for gd-amplitude + adaptive_step")


def test_main_end_to_end_on_fake_lab_captures(tmp_path):
    """Exercises the CLI wiring (argument parsing, real_lr_stack loading,
    reference-image file loading, JSON output) via main(), not just the
    filesystem-free sweep() core -- same fake-lab-capture pattern as
    tests/test_reconstruct_multispectral_pipeline.py's
    _write_fake_lab_captures, but single-channel (this tool only ever
    reconstructs one channel per run, same as reconstruct_real_images.py).
    """
    grid_size, crop, channel = 9, 12, "green"
    setup, factor, hr_pixel_um, led_grid, lr_images, truth = _build_in_memory_case(
        grid_size=grid_size, crop=crop, channel=channel)

    subdir = tmp_path / channel / f"{grid_size}x{grid_size}_recortada_{crop}"
    subdir.mkdir(parents=True)
    for (row, col), intensity in lr_images.items():
        Image.fromarray(intensity.astype(np.float32), mode="F").save(
            subdir / f"fila{row}_columna{col}.tiff"
        )

    reference_path = tmp_path / "reference.tif"
    Image.fromarray(np.abs(truth).astype(np.float32), mode="F").save(reference_path)

    output_json = tmp_path / "sweep_out.json"
    rc = sweep_tool.main([
        "--data-root", str(tmp_path), "--channel", channel,
        "--grid-size", str(grid_size), "--crop", str(crop), "--objective", "2_5x_na007", "--z-distance-mm", "70", "--no-exposure-normalization", "--no-normalize-initial-guess",
        "--reference-image", str(reference_path),
        "--iterations", "3", "8",
        "--output-json", str(output_json),
    ])
    assert rc == 0
    assert output_json.exists()

    with open(output_json) as fh:
        payload = json.load(fh)
    assert payload["channel"] == channel
    assert [r["iterations"] for r in payload["rows"]] == [3, 8]
    for row in payload["rows"]:
        assert -1.0 <= row["reference_correlation"] <= 1.0

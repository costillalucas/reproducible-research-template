"""tests/test_edge_cases_gd_calibration.py -- edge cases the happy-path tests
(test_joint_calibration.py, test_gd_solver_pipelines.py, test_test_objects.py)
don't touch, for `joint_calibration.py`, the `gd-amplitude` solver wiring and
`test_objects.lena_map_object`:

- odd / non-square crop shapes (the continuous-k model, its gradient, and
  its equality with the bin-crop model);
- degenerate inputs (bad loss / led_model names, all-zero captures, missing
  LEDs, negative pixels from dark subtraction, unsigned-int and float32
  raw counts, arbitrary gain, `iterations=0`);
- LED far outside the pupil, and zero-amplitude object regions;
- flag exclusivity of `--solver gd-amplitude` at function level;
- the Lena/Map loader on synthetic images (no dependency on the real ones).

Bugs first found by this file have since been fixed and their tests are
regular ones now: a lone on-axis LED divided by zero in
`reconstruct_and_calibrate`, a 16-bit Map image saturated to a step in
`lena_map_object`, a missing center frame silently mis-initialized the
solver, `convergence_summary([])` crashed, and `simulate_and_reconstruct
--solver gd-amplitude` ran on bin-rounded data.

Every test uses tiny canvases (crop 8 or smaller, <= 25 LEDs) and runs in
well under 5 s on one core.
"""
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipelines"))
sys.path.insert(0, os.path.dirname(__file__))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import joint_calibration as jc, test_objects  # noqa: E402
import reconstruct_multispectral_independent as multispectral  # noqa: E402
import simulate_and_reconstruct as sim_pipeline  # noqa: E402
from test_joint_calibration import _synthetic_object  # noqa: E402

LOSSES = ["intensity", "amplitude", "poisson"]


# ---------------------------------------------------------------- fixtures

def _small_case(crop=8, grid_size=5):
    """Exact-k synthetic captures on a tiny real-optics setup."""
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                 resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hp = optics.actual_hr_pixel_size_um(setup, factor)
    hs = optics.hr_shape((crop, crop), factor)
    truth = _synthetic_object(hs)
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr = jc.simulate_lr_stack_continuous(truth, hp, grid, (crop, crop), setup.lr_pixel_size_um,
                                         setup.objective.na, setup.wavelength_um)
    return {"setup": setup, "factor": factor, "hp": hp, "hs": hs, "truth": truth, "grid": grid, "lr": lr,
            "args": (hp, setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um, factor)}


@pytest.fixture(scope="module")
def case():
    return _small_case()


def _gd(c, lr=None, grid=None, **kw):
    kw.setdefault("iterations", 8)
    return jc.reconstruct_gradient_descent(lr if lr is not None else c["lr"],
                                           grid if grid is not None else c["grid"], *c["args"], **kw)


# ------------------------------------------- odd / non-square crop shapes

# (lr_shape, factor): non-square even, square odd, odd with factor 3 (odd HR)
SHAPES = [((6, 9), 2), ((7, 7), 2), ((5, 7), 3)]
HP, NA, WL = 0.5, 0.2, 0.5


def _synthetic_math_case(lr_shape, factor):
    hs = (lr_shape[0] * factor, lr_shape[1] * factor)
    lp = HP * factor
    rng = np.random.default_rng(3)
    obj = (0.6 + 0.4 * rng.random(hs)) * np.exp(1j * 0.5 * rng.random(hs))
    bin_x, bin_y = 1.0 / (hs[1] * HP), 1.0 / (hs[0] * HP)
    # on-axis, bin-aligned off-axis, and two fractional-bin LEDs
    grid = [{"row": 0, "col": 0, "fx": 0.0, "fy": 0.0},
            {"row": 0, "col": 1, "fx": 1 * bin_x, "fy": -1 * bin_y},
            {"row": 1, "col": 0, "fx": 0.4 * bin_x, "fy": 0.7 * bin_y},
            {"row": 1, "col": 1, "fx": -1.3 * bin_x, "fy": 0.2 * bin_y}]
    return obj, hs, lp, grid, (bin_x, bin_y)


@pytest.mark.parametrize("lr_shape,factor", SHAPES)
def test_continuous_model_returns_lr_shape_real_nonnegative_images(lr_shape, factor):
    obj, hs, lp, grid, _ = _synthetic_math_case(lr_shape, factor)
    out = jc.simulate_lr_stack_continuous(obj, HP, grid, lr_shape, lp, NA, WL)
    assert set(out) == {(e["row"], e["col"]) for e in grid}
    for img in out.values():
        assert img.shape == lr_shape and img.dtype.kind == "f"
        assert np.isfinite(img).all() and img.min() >= 0


@pytest.mark.parametrize("lr_shape,factor", SHAPES)
def test_continuous_model_equals_bin_crop_model_on_bin_aligned_k_for_odd_and_nonsquare(lr_shape, factor):
    obj, hs, lp, grid, (bx, by) = _synthetic_math_case(lr_shape, factor)
    aligned = [{**e, "fx": round(e["fx"] / bx) * bx, "fy": round(e["fy"] / by) * by} for e in grid]
    crop = forward_model.simulate_lr_stack(obj, HP, aligned, lr_shape, lp, NA, WL)
    cont = jc.simulate_lr_stack_continuous(obj, HP, aligned, lr_shape, lp, NA, WL)
    scale = (hs[0] * hs[1]) / (lr_shape[0] * lr_shape[1])
    for key in crop:
        assert np.allclose(crop[key] / scale ** 2, cont[key], atol=1e-9), key


@pytest.mark.parametrize("loss_name", LOSSES)
@pytest.mark.parametrize("lr_shape,factor", SHAPES)
def test_gradient_matches_finite_differences_on_odd_and_nonsquare_shapes(lr_shape, factor, loss_name):
    obj, hs, lp, grid, (bx, by) = _synthetic_math_case(lr_shape, factor)
    truth_grid = [{**e, "fx": e["fx"] + 0.05 * bx} for e in grid]
    meas = jc.simulate_lr_stack_continuous(obj, HP, truth_grid, lr_shape, lp, NA, WL)
    guess = obj * (1 + 0.1 * np.random.default_rng(1).standard_normal(hs))

    def loss(o, g):
        return jc.loss_and_gradients(o, HP, g, meas, lr_shape, lp, NA, WL, loss_name)["loss"]

    out = jc.loss_and_gradients(guess, HP, grid, meas, lr_shape, lp, NA, WL, loss_name)
    h = 1e-6
    for i, axis, col, step in [(2, "fx", 0, bx), (3, "fy", 1, by)]:
        plus, minus = [dict(e) for e in grid], [dict(e) for e in grid]
        plus[i][axis] += h * step
        minus[i][axis] -= h * step
        fd = (loss(guess, plus) - loss(guess, minus)) / (2 * h * step)
        assert out["grad_k"][i][col] == pytest.approx(fd, rel=1e-4)
    r, c = hs[0] - 2, hs[1] // 2 + 1  # a pixel in the odd/last-row region
    for delta, part in [(1.0, np.real), (1j, np.imag)]:
        d = np.zeros(hs, complex)
        d[r, c] = delta
        fd = (loss(guess + h * d, grid) - loss(guess - h * d, grid)) / (2 * h)
        assert 2 * part(out["grad_object"][r, c]) == pytest.approx(fd, rel=1e-4)


@pytest.mark.parametrize("lr_shape,factor", SHAPES)
def test_loss_is_zero_at_the_truth_and_gradient_vanishes(lr_shape, factor):
    obj, hs, lp, grid, _ = _synthetic_math_case(lr_shape, factor)
    meas = jc.simulate_lr_stack_continuous(obj, HP, grid, lr_shape, lp, NA, WL)
    for loss_name in ("intensity", "amplitude"):
        out = jc.loss_and_gradients(obj, HP, grid, meas, lr_shape, lp, NA, WL, loss_name)
        assert out["loss"] == pytest.approx(0.0, abs=1e-20)
        assert np.abs(out["grad_object"]).max() < 1e-9
        assert np.abs(out["grad_k"]).max() < 1e-9


def test_initial_object_from_center_led_nonsquare_upsampling_and_units():
    center = np.array([[1.0, 4.0, 9.0], [16.0, 25.0, 36.0]])  # (2, 3)
    init = jc.initial_object_from_center_led(center, (6, 12))  # factor (3, 4)
    assert init.shape == (6, 12) and init.dtype == complex
    assert np.allclose(init.imag, 0)
    assert np.allclose(init.real[:3, :4], 1.0) and np.allclose(init.real[3:, 8:], 6.0)
    # negative pixels (dark-subtracted noise) clip to zero amplitude instead of NaN
    assert np.isfinite(jc.initial_object_from_center_led(-np.ones((2, 2)), (4, 4))).all()


# ------------------------------------------------------------ bad inputs

def test_loss_and_gradients_rejects_unknown_loss(case):
    c = case
    with pytest.raises(ValueError, match="loss must be"):
        jc.loss_and_gradients(c["truth"], c["hp"], c["grid"][:2], c["lr"], (8, 8),
                              c["setup"].lr_pixel_size_um, c["setup"].objective.na,
                              c["setup"].wavelength_um, "l1")


def test_reconstruct_and_calibrate_rejects_unknown_led_model(case):
    c = case
    with pytest.raises(ValueError, match="led_model must be"):
        jc.reconstruct_and_calibrate(c["lr"], c["grid"][:3], c["hs"], c["hp"], (8, 8),
                                     c["setup"].lr_pixel_size_um, c["setup"].objective.na,
                                     c["setup"].wavelength_um, c["truth"], n_iterations=1,
                                     led_model="affine")


def test_gd_rejects_unknown_loss(case):
    with pytest.raises(ValueError, match="loss must be"):
        _gd(case, loss="huber", iterations=1)


def test_all_zero_captures_raise_instead_of_returning_nan(case):
    c = case
    zeros = {k: np.zeros_like(v) for k, v in c["lr"].items()}
    for loss_name in LOSSES:
        with pytest.raises((ValueError, ZeroDivisionError)):
            jc.loss_and_gradients(c["truth"], c["hp"], c["grid"][:3], zeros, (8, 8),
                                  c["setup"].lr_pixel_size_um, c["setup"].objective.na,
                                  c["setup"].wavelength_um, loss_name)
    with pytest.raises(ValueError, match="non-positive mean"):
        _gd(case, lr=zeros)


def test_gd_rejects_lr_stack_with_no_matching_led_keys(case):
    with pytest.raises(ValueError, match="none of led_grid"):
        _gd(case, lr={(99, 99): np.ones((8, 8))})


def test_gd_wrong_shape_initial_object_raises_value_error(case):
    with pytest.raises(ValueError):
        _gd(case, initial_object=np.ones((3, 3)), iterations=1)


# --------------------------------------- gd solver: dtype, gain, missing

def test_gd_is_invariant_to_capture_gain_and_dtype_of_raw_counts(case):
    """Real captures are integer counts with an arbitrary gain; the solver
    divides by the center image's mean, so neither gain nor storage dtype
    (uint16 / float32 / float64 holding the same numbers) may matter."""
    c = case
    base = _gd(c)["object"]
    gained = _gd(c, lr={k: v * 250.0 for k, v in c["lr"].items()})["object"]
    assert np.allclose(gained, base, rtol=1e-6, atol=1e-9)
    counts = {k: np.round(v * 1000).astype(np.uint16) for k, v in c["lr"].items()}
    reference = _gd(c, lr={k: v.astype(np.float64) for k, v in counts.items()})["object"]
    assert np.isfinite(reference).all() and reference.shape == c["hs"]
    for dtype, tol in ((np.uint16, 1e-9), (np.float32, 1e-4)):
        out = _gd(c, lr={k: v.astype(dtype) for k, v in counts.items()})["object"]
        assert np.allclose(out, reference, rtol=tol, atol=tol), dtype


def test_gd_ignores_leds_missing_from_the_capture_and_does_not_mutate_grid(case):
    c = case
    snapshot = [dict(e) for e in c["grid"]]
    dropped = {(e["row"], e["col"]) for e in c["grid"][5:9]}
    sub = {k: v for k, v in c["lr"].items() if k not in dropped}
    out = _gd(c, lr=sub)
    assert out["object"].shape == c["hs"] and np.isfinite(out["object"]).all()
    assert c["grid"] == snapshot  # calibrate_leds=False path must not touch positions


def test_gd_rejects_a_capture_whose_center_frame_is_missing(case):
    """The normalization and initial object come from the center LED's frame;
    silently using an off-axis dark-field frame gave phase corr ~0.08."""
    c = case
    center = (c["grid"][0]["row"], c["grid"][0]["col"])
    with pytest.raises(ValueError, match="center LED"):
        _gd(c, lr={k: v for k, v in c["lr"].items() if k != center})


def test_convergence_summary_of_an_empty_history_does_not_crash():
    out = metrics.convergence_summary([])
    assert out["first_error"] is None and out["last_error"] is None
    assert out["relative_improvement"] == 0.0


def test_simulate_and_reconstruct_gd_uses_matched_data_and_recovers_phase(tmp_path):
    """Regression: --solver gd-amplitude used to run on bin-rounded simulated
    data (phase corr ~0.12); with the continuous-k simulator it reaches ~0.98
    at 100 iterations (0.86 at 40)."""
    setup = config.default_setup(channel="green", grid_size=9, objective="current", resolution_px=(16, 16))
    hs = optics.hr_shape((16, 16), optics.upsampling_factor(setup))
    obj = _synthetic_object(hs)
    amp = np.abs(obj) / np.abs(obj).max() * 255
    ph = (np.angle(obj) / np.pi + 1) / 2 * 255
    Image.fromarray(amp.astype(np.uint8)).save(tmp_path / "a.png")
    Image.fromarray(ph.astype(np.uint8)).save(tmp_path / "p.png")
    sim_pipeline.main(["--amplitude-image", str(tmp_path / "a.png"), "--phase-image", str(tmp_path / "p.png"),
                       "--lr-size", "16", "--iterations", "100", "--solver", "gd-amplitude",
                       "--output-dir", str(tmp_path / "out")])
    m = json.load(open(tmp_path / "out" / "metrics.json"))
    gt = m["vs_ground_truth"]
    assert gt["phase_correlation"] > 0.9, gt


@pytest.mark.parametrize("loss_name", LOSSES)
def test_gd_survives_negative_pixels_from_dark_subtraction(case, loss_name):
    c = case
    rng = np.random.default_rng(5)
    noisy = {k: v + 0.02 * rng.standard_normal(v.shape) for k, v in c["lr"].items()}
    assert min(v.min() for v in noisy.values()) < 0
    out = _gd(c, lr=noisy, loss=loss_name)
    assert np.isfinite(out["object"]).all()
    assert all(np.isfinite(h["recovery_error"]) for h in out["history"])


def test_gd_zero_iterations_returns_rescaled_initial_object_and_empty_history(case):
    out = _gd(case, iterations=0)
    assert out["history"] == []
    init = jc.initial_object_from_center_led(
        case["lr"][(case["grid"][0]["row"], case["grid"][0]["col"])]
        / np.mean(case["lr"][(case["grid"][0]["row"], case["grid"][0]["col"])]), case["hs"])
    assert np.allclose(out["object"], init)


@pytest.mark.parametrize("loss_name", ["intensity", "amplitude"])
def test_gd_noiseless_recovery_error_drops_for_zero_minimum_losses(case, loss_name):
    errs = [h["recovery_error"] for h in _gd(case, loss=loss_name, iterations=25)["history"]]
    assert errs[-1] < 0.6 * errs[0]


def test_gd_poisson_history_is_not_a_zero_based_error_but_does_not_increase(case):
    """`history["recovery_error"]` is sqrt(loss). For "poisson" the loss is the
    NLL up to a constant, whose minimum is NOT zero even on noiseless data,
    so the value is an offset quantity (~1.37 here) rather than an error --
    convergence_summary's relative_improvement is meaningless for it. Pinned
    so nobody reads it as an error; only 'not worse than the start' holds."""
    errs = [h["recovery_error"] for h in _gd(case, loss="poisson", iterations=25)["history"]]
    assert np.isfinite(errs).all() and errs[-1] <= errs[0]
    assert errs[-1] > 0.5 * errs[0]


# ----------------------------------- pupil edge and zero-amplitude object

def test_led_far_outside_the_pupil_gives_a_dark_but_finite_frame_and_gradients(case):
    c = case
    far = dict(c["grid"][1], fx=50.0 / (c["hs"][1] * c["hp"]), fy=0.0)  # 50 bins away: beyond band
    grid = [c["grid"][0], far]
    meas = jc.simulate_lr_stack_continuous(c["truth"], c["hp"], grid, (8, 8),
                                           c["setup"].lr_pixel_size_um, c["setup"].objective.na,
                                           c["setup"].wavelength_um)
    bright, dark = meas[(grid[0]["row"], grid[0]["col"])], meas[(far["row"], far["col"])]
    assert dark.mean() < 0.05 * bright.mean()
    for loss_name in LOSSES:
        out = jc.loss_and_gradients(c["truth"], c["hp"], grid, meas, (8, 8), c["setup"].lr_pixel_size_um,
                                    c["setup"].objective.na, c["setup"].wavelength_um, loss_name)
        assert np.isfinite(out["loss"]) and np.isfinite(out["grad_k"]).all()
        assert np.isfinite(out["grad_object"]).all()


def test_exactly_zero_measured_frame_for_one_led_is_finite_under_every_loss(case):
    c = case
    grid = c["grid"][:4]
    meas = {(e["row"], e["col"]): c["lr"][(e["row"], e["col"])] for e in grid}
    meas[(grid[3]["row"], grid[3]["col"])] = np.zeros((8, 8))  # a dead / fully dark frame
    for loss_name in LOSSES:
        out = jc.loss_and_gradients(c["truth"], c["hp"], grid, meas, (8, 8), c["setup"].lr_pixel_size_um,
                                    c["setup"].objective.na, c["setup"].wavelength_um, loss_name)
        assert np.isfinite(out["loss"]) and np.isfinite(out["grad_object"]).all()


@pytest.mark.parametrize("loss_name", LOSSES)
def test_zero_object_gives_finite_gradient_even_though_amplitude_loss_divides_by_amp(case, loss_name):
    c = case
    grid = c["grid"][:3]
    meas = {(e["row"], e["col"]): c["lr"][(e["row"], e["col"])] for e in grid}
    out = jc.loss_and_gradients(np.zeros(c["hs"], complex), c["hp"], grid, meas, (8, 8),
                                c["setup"].lr_pixel_size_um, c["setup"].objective.na,
                                c["setup"].wavelength_um, loss_name)
    assert np.isfinite(out["loss"]) and np.isfinite(out["grad_object"]).all()
    assert np.isfinite(out["grad_k"]).all()


# --------------------------------------- reconstruct_and_calibrate options

def _calib(c, grid, lr, **kw):
    return jc.reconstruct_and_calibrate(lr, grid, c["hs"], c["hp"], (8, 8), c["setup"].lr_pixel_size_um,
                                        c["setup"].objective.na, c["setup"].wavelength_um,
                                        c["truth"], **kw)


def test_warmup_longer_than_run_and_calibrate_false_leave_positions_at_nominal(case):
    c = case
    grid = c["grid"][:6]
    lr = {(e["row"], e["col"]): c["lr"][(e["row"], e["col"])] for e in grid}
    for kw in ({"warmup_iterations": 50, "n_iterations": 3}, {"calibrate_leds": False, "n_iterations": 3}):
        out = _calib(c, grid, lr, **kw)
        assert [(e["fx"], e["fy"]) for e in out["led_grid"]] == [(e["fx"], e["fy"]) for e in grid]
        assert out["similarity"]["scale"] == 1.0 and out["similarity"]["shift"] == (0.0, 0.0)


def test_calibration_returns_a_copy_and_never_mutates_the_nominal_grid(case):
    c = case
    grid = c["grid"][:6]
    lr = {(e["row"], e["col"]): c["lr"][(e["row"], e["col"])] for e in grid}
    before = [dict(e) for e in grid]
    for model in ("rigid", "per_led"):
        out = _calib(c, grid, lr, n_iterations=3, led_model=model)
        assert grid == before
        assert out["led_grid"] is not grid and len(out["history"]) == 3
        assert all(np.isfinite([e["fx"], e["fy"]]).all() for e in out["led_grid"])


def test_calibration_accepts_a_real_valued_initial_object_and_returns_complex(case):
    c = case
    grid = c["grid"][:4]
    lr = {(e["row"], e["col"]): c["lr"][(e["row"], e["col"])] for e in grid}
    out = jc.reconstruct_and_calibrate(lr, grid, c["hs"], c["hp"], (8, 8), c["setup"].lr_pixel_size_um,
                                       c["setup"].objective.na, c["setup"].wavelength_um,
                                       np.abs(c["truth"]), n_iterations=2, calibrate_leds=False)
    assert out["object"].dtype == complex and np.isfinite(out["object"]).all()


def test_single_on_axis_led_does_not_divide_by_zero(case):
    c = case
    center = c["grid"][:1]
    lr = {(center[0]["row"], center[0]["col"]): c["lr"][(center[0]["row"], center[0]["col"])]}
    out = _calib(c, center, lr, n_iterations=2, calibrate_leds=False)
    assert np.isfinite(out["object"]).all()


def test_gd_on_a_center_only_capture_runs(case):
    c = case
    key = (c["grid"][0]["row"], c["grid"][0]["col"])
    out = _gd(c, lr={key: c["lr"][key]}, iterations=2)
    assert np.isfinite(out["object"]).all()


# -------------------------------------------- solver flag exclusivity

_BAD_ROOT = "/nonexistent-data-root"  # validation must fire before any file access


@pytest.mark.parametrize("combo", [("recover_pupil",), ("adaptive_step",), ("use_reconstruction_agent",),
                                    ("recover_pupil", "adaptive_step"),
                                    ("adaptive_step", "use_reconstruction_agent")])
def test_gd_amplitude_rejects_every_wirtinger_only_flag_and_combination_before_touching_data(combo):
    with pytest.raises(ValueError, match="cannot be combined"):
        multispectral.reconstruct_all_channels(_BAD_ROOT, 9, crop=8, solver="gd-amplitude",
                                               **{k: True for k in combo})


@pytest.mark.parametrize("bad", ["", "GD-AMPLITUDE", "gd_amplitude", "gd", None])
def test_solver_name_is_matched_exactly(bad):
    with pytest.raises(ValueError, match="solver must be"):
        multispectral.reconstruct_all_channels(_BAD_ROOT, 9, crop=8, solver=bad)


@pytest.mark.parametrize("extra", [{"recover_pupil": True}, {"adaptive_step": True}])
def test_wirtinger_solver_still_accepts_its_own_flags_past_validation(extra):
    """Regression guard: the new solver check must not reject the default
    solver's flags. Validation passes, so the first failure is the missing
    data directory, not a ValueError about the solver."""
    with pytest.raises(Exception) as ei:
        multispectral.reconstruct_all_channels(_BAD_ROOT, 9, crop=8, solver="wirtinger", **extra)
    assert "solver" not in str(ei.value) and "cannot be combined" not in str(ei.value)


def test_simulate_and_reconstruct_cli_rejects_gd_amplitude_with_each_wirtinger_flag(tmp_path):
    Image.fromarray(np.full((32, 32), 200, np.uint8)).save(tmp_path / "a.png")
    Image.fromarray(np.full((32, 32), 100, np.uint8)).save(tmp_path / "p.png")
    for flag in ("--recover-pupil", "--adaptive-step", "--use-reconstruction-agent"):
        with pytest.raises(SystemExit) as ei:
            sim_pipeline.main(["--amplitude-image", str(tmp_path / "a.png"),
                               "--phase-image", str(tmp_path / "p.png"), "--lr-size", "16",
                               "--iterations", "1", "--solver", "gd-amplitude", flag,
                               "--output-dir", str(tmp_path / "out")])
        assert "cannot be combined" in str(ei.value)


# --------------------------------------------- Lena / Map loader (synthetic)

def _write_pair(d, lena, mp):
    Image.fromarray(lena).save(d / "Lena_512.png")
    Image.fromarray(mp).save(d / "Map_512.tiff")


def test_loader_constant_images_do_not_produce_nan(tmp_path):
    _write_pair(tmp_path, np.full((16, 16), 120, np.uint8), np.full((16, 16), 50, np.uint8))
    obj, phase = test_objects.lena_map_object((10, 14), data_dir=str(tmp_path))
    assert obj.shape == phase.shape == (10, 14) and obj.dtype == complex
    assert np.isfinite(obj).all()
    assert np.allclose(np.abs(obj), 0.1) and np.allclose(phase, 0.0)  # flat -> floor amplitude, zero phase


def test_loader_min_amplitude_one_gives_pure_phase_object_and_zero_phase_max_gives_pure_amplitude(tmp_path):
    rng = np.random.default_rng(0)
    _write_pair(tmp_path, rng.integers(0, 256, (16, 16), dtype=np.uint8),
                rng.integers(0, 256, (16, 16), dtype=np.uint8))
    obj, _ = test_objects.lena_map_object((12, 12), min_amplitude=1.0, data_dir=str(tmp_path))
    assert np.allclose(np.abs(obj), 1.0)
    obj, phase = test_objects.lena_map_object((12, 12), phase_max_rad=0.0, data_dir=str(tmp_path))
    assert np.allclose(phase, 0.0) and np.allclose(obj.imag, 0.0)


def test_loader_is_deterministic_and_upsamples_small_sources(tmp_path):
    rng = np.random.default_rng(1)
    _write_pair(tmp_path, rng.integers(0, 256, (8, 8), dtype=np.uint8),
                rng.integers(0, 256, (8, 8), dtype=np.uint8))
    a, _ = test_objects.lena_map_object((24, 40), data_dir=str(tmp_path))
    b, _ = test_objects.lena_map_object((24, 40), data_dir=str(tmp_path))
    assert a.shape == (24, 40) and np.array_equal(a, b)
    assert np.abs(a).min() == pytest.approx(0.1, abs=1e-9) and np.abs(a).max() == pytest.approx(1.0, abs=1e-9)


def test_loader_reads_data_dir_from_environment_and_argument_wins(tmp_path, monkeypatch):
    env_dir, arg_dir = tmp_path / "env", tmp_path / "arg"
    env_dir.mkdir(), arg_dir.mkdir()
    _write_pair(env_dir, np.full((8, 8), 10, np.uint8), np.full((8, 8), 10, np.uint8))
    rng = np.random.default_rng(2)
    _write_pair(arg_dir, rng.integers(0, 256, (8, 8), dtype=np.uint8), rng.integers(0, 256, (8, 8), dtype=np.uint8))
    monkeypatch.setenv("PTYCO_DATA_SOURCE", str(env_dir))
    from_env, _ = test_objects.lena_map_object((8, 8))
    assert np.allclose(np.abs(from_env), 0.1)  # the flat pair
    from_arg, _ = test_objects.lena_map_object((8, 8), data_dir=str(arg_dir))
    assert np.ptp(np.abs(from_arg)) > 0.5


def test_loader_missing_directory_or_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        test_objects.lena_map_object((8, 8), data_dir=str(tmp_path / "nope"))
    Image.fromarray(np.zeros((8, 8), np.uint8)).save(tmp_path / "Lena_512.png")  # Map missing
    with pytest.raises(FileNotFoundError):
        test_objects.lena_map_object((8, 8), data_dir=str(tmp_path))


def test_loader_rgb_and_palette_sources_are_converted_to_grayscale(tmp_path):
    rgb = np.zeros((16, 16, 3), np.uint8)
    rgb[..., 0] = np.linspace(0, 255, 16, dtype=np.uint8)[None, :]
    Image.fromarray(rgb, "RGB").save(tmp_path / "Lena_512.png")
    Image.fromarray(np.tile(np.arange(16, dtype=np.uint8) * 16, (16, 1))).save(tmp_path / "Map_512.tiff")
    obj, phase = test_objects.lena_map_object((16, 16), data_dir=str(tmp_path))
    assert obj.shape == (16, 16) and np.isfinite(obj).all()
    assert phase[:, -1].mean() > phase[:, 0].mean()


def test_loader_16bit_map_tiff_keeps_its_gradient(tmp_path):
    Image.fromarray(np.full((16, 16), 128, np.uint8)).save(tmp_path / "Lena_512.png")
    ramp = np.tile(np.linspace(0, 65535, 16).astype(np.uint16), (16, 1))
    Image.fromarray(ramp).save(tmp_path / "Map_512.tiff")
    _, phase = test_objects.lena_map_object((16, 16), data_dir=str(tmp_path))
    corr = np.corrcoef(phase[0], np.arange(16))[0, 1]
    assert corr > 0.95


def test_coupled_cli_rejects_gd_amplitude_with_wirtinger_flags_and_qc_cleanly(tmp_path):
    import reconstruct_multispectral_coupled as coupled
    for flag in ("--recover-pupil", "--adaptive-step", "--use-reconstruction-agent", "--qc"):
        with pytest.raises(SystemExit) as ei:
            coupled.main(["--data-root", _BAD_ROOT, "--solver", "gd-amplitude", flag,
                          "--output-dir", str(tmp_path / "out")])
        assert "cannot be combined" in str(ei.value)

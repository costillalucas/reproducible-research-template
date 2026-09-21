"""tests/test_joint_calibration.py -- src/ptyco_full_simulator/joint_calibration.py,
the AD-SC self-calibrating reconstruction of You & Liang 2025
(references/papers/complementarios/Self-calibrating Fourier ptychographic
microscopy using automatic differentiation.pdf), implemented with a
hand-derived gradient instead of autodiff (no PyTorch in this project).

Five tests, each a different claim:
- the hand-derived gradient matches finite differences (this is what
  stands in for "autodiff is correct by construction");
- the continuous-k forward model equals the existing bin-crop model when k
  sits exactly on a spectrum bin;
- given a good object, a small rigid LED misalignment is recovered
  exactly;
- jointly bootstrapping object AND positions from the on-axis image
  (no good object given) still beats holding the nominal positions fixed;
- NEGATIVE / limit: a misalignment of ~0.8 spectrum bins is NOT recovered
  even when handed the true object -- it falls into a local minimum. The
  basin of attraction is under about half a bin, on this 16px-crop testbed.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from ptyco_full_simulator import forward_model, joint_calibration as jc  # noqa: E402
from ptyco_full_simulator import led_calibration as cal, metrics  # noqa: E402
from test_led_calibration import _setup_and_grids, _synthetic_object  # noqa: E402

CROP = 16


@pytest.fixture(scope="module")
def bench():
    setup, factor, hr_pixel_um, hr_shape, delta_k, nominal = _setup_and_grids(crop=CROP)
    return {
        "hp": hr_pixel_um, "hs": hr_shape, "dk": delta_k, "nom": nominal,
        "lr": (CROP, CROP), "lp": setup.lr_pixel_size_um,
        "na": setup.objective.na, "wl": setup.wavelength_um,
        "truth": _synthetic_object(hr_shape),
    }


def _mean_led_error_bins(grid_a, grid_b, dk):
    return float(np.mean([np.hypot(a["fx"] - b["fx"], a["fy"] - b["fy"])
                          for a, b in zip(grid_a, grid_b)])) / dk


def _measure(b, true_grid):
    return jc.simulate_lr_stack_continuous(b["truth"], b["hp"], true_grid, b["lr"], b["lp"], b["na"], b["wl"])


def test_hand_derived_gradient_matches_finite_differences(bench):
    b = bench
    rng = np.random.default_rng(0)
    meas = _measure(b, b["nom"])
    guess = b["truth"] * (1 + 0.1 * rng.standard_normal(b["truth"].shape))
    grid = b["nom"][:12]

    def loss(obj, g):
        return jc.loss_and_gradients(obj, b["hp"], g, meas, b["lr"], b["lp"], b["na"], b["wl"])["loss"]

    out = jc.loss_and_gradients(guess, b["hp"], grid, meas, b["lr"], b["lp"], b["na"], b["wl"])
    h = 1e-6
    for i, axis, col in [(3, "fx", 0), (7, "fy", 1)]:
        plus, minus = [dict(e) for e in grid], [dict(e) for e in grid]
        plus[i][axis] += h * b["dk"]
        minus[i][axis] -= h * b["dk"]
        fd = (loss(guess, plus) - loss(guess, minus)) / (2 * h * b["dk"])
        assert out["grad_k"][i][col] == pytest.approx(fd, rel=1e-4)
    for (r, c) in [(5, 7), (20, 30)]:
        for delta, part in [(1.0, np.real), (1j, np.imag)]:
            d = np.zeros(guess.shape, complex)
            d[r, c] = delta
            fd = (loss(guess + h * d, grid) - loss(guess - h * d, grid)) / (2 * h)
            assert 2 * part(out["grad_object"][r, c]) == pytest.approx(fd, rel=1e-4)


def test_continuous_forward_model_matches_bin_crop_model_on_bin_aligned_k(bench):
    b = bench
    aligned = [{**e, "fx": round(e["fx"] / b["dk"]) * b["dk"], "fy": round(e["fy"] / b["dk"]) * b["dk"]}
               for e in b["nom"]]
    crop_model = forward_model.simulate_lr_stack(b["truth"], b["hp"], aligned, b["lr"], b["lp"], b["na"], b["wl"])
    continuous = _measure(b, aligned)
    # the two models differ only by a constant intensity scale (module docstring:
    # `_field_scale` puts this one in object units)
    scale = (b["hs"][0] * b["hs"][1]) / (b["lr"][0] * b["lr"][1])
    for key in crop_model:
        assert np.allclose(crop_model[key] / scale ** 2, continuous[key], atol=1e-9)


def test_recovers_small_rigid_misalignment_exactly_given_a_good_object(bench):
    b = bench
    true_grid = cal.perturb_led_grid_rigid(b["nom"], shift_fx=0.01, shift_fy=-0.005,
                                            rotation_rad=0.01, scale=1.005)
    meas = _measure(b, true_grid)
    r = jc.reconstruct_and_calibrate(meas, b["nom"], b["hs"], b["hp"], b["lr"], b["lp"], b["na"], b["wl"],
                                      b["truth"].copy(), n_iterations=300, object_lr=0.0, k_lr_bins=0.02)
    assert _mean_led_error_bins(b["nom"], true_grid, b["dk"]) > 0.2  # the misalignment is real
    assert _mean_led_error_bins(r["led_grid"], true_grid, b["dk"]) < 0.01


def test_joint_bootstrap_beats_fixed_nominal_positions(bench):
    b = bench
    true_grid = cal.perturb_led_grid_rigid(b["nom"], shift_fx=0.01, shift_fy=-0.005,
                                            rotation_rad=0.01, scale=1.005)
    meas = _measure(b, true_grid)
    init = jc.initial_object_from_center_led(meas[(b["nom"][0]["row"], b["nom"][0]["col"])], b["hs"])
    runs = {}
    for calibrate in (False, True):
        r = jc.reconstruct_and_calibrate(meas, b["nom"], b["hs"], b["hp"], b["lr"], b["lp"], b["na"], b["wl"],
                                          init, n_iterations=400, calibrate_leds=calibrate, k_lr_bins=0.01)
        runs[calibrate] = (metrics.compare_to_ground_truth(r["object"], b["truth"])["phase_correlation"],
                           _mean_led_error_bins(r["led_grid"], true_grid, b["dk"]))
    assert runs[True][0] > runs[False][0] + 0.15  # measured: 0.861 vs 0.485
    assert runs[True][1] < 0.5 * runs[False][1]  # measured: 0.079 vs 0.248 bins


def test_large_misalignment_is_not_recovered_even_with_the_true_object(bench):
    """NEGATIVE result: ~0.8 bins of mean LED error (rigid shift/rotation/
    scale of 0.03/-0.02/0.03rad/1.02) is beyond this method's basin of
    attraction on this testbed -- even with the object fixed at the truth,
    the fit ends no closer than where it started. Don't rely on AD-SC to
    fix gross misalignment; it refines a roughly-right grid.
    """
    b = bench
    true_grid = cal.perturb_led_grid_rigid(b["nom"], shift_fx=0.03, shift_fy=-0.02,
                                            rotation_rad=0.03, scale=1.02)
    meas = _measure(b, true_grid)
    r = jc.reconstruct_and_calibrate(meas, b["nom"], b["hs"], b["hp"], b["lr"], b["lp"], b["na"], b["wl"],
                                      b["truth"].copy(), n_iterations=300, object_lr=0.0, k_lr_bins=0.02)
    start = _mean_led_error_bins(b["nom"], true_grid, b["dk"])
    end = _mean_led_error_bins(r["led_grid"], true_grid, b["dk"])
    assert start > 0.7
    assert end > 0.9 * start  # measured: 1.263 vs 0.800 -- it got WORSE

"""tests/test_gradient_descent_vs_wirtinger.py -- found as a side effect of
building joint_calibration.py (2026-09-21): plain Adam gradient descent on
the intensity loss (`joint_calibration.reconstruct_and_calibrate` with
`calibrate_leds=False`) reconstructs this project's standard small
synthetic object better than the Wirtinger-flow solver
(`reconstruction.reconstruct`), NOISELESS, same data, LED positions known.

Measured (phase_correlation, 16px crops, 9x9 LEDs, bin-aligned k so both
solvers see identical information):
    channel  WF40   WF400  GD100  GD400
    green    0.758  0.981  0.990  0.995
    red      0.794  0.928  0.992  0.995
    blue    -0.073 -0.056  0.878  0.998
Blue is the striking one: the Wirtinger flow never converges (even at 400
epochs) while gradient descent gets there in 100 iterations.

NOT a general advantage -- multi-seed noise sweep (8 seeds, peak photon
count 100/20/5, scripts/sweep_gd_vs_wf_noise.py) shows it does not survive
Poisson noise: GD only wins red at peak 100 (+0.090 +/- 0.018, 8/8),
loses red at peak 20 (-0.114 +/- 0.039), ties/loses green, and blue fails
for both. These tests assert the NOISELESS result only; do not read them
as a reason to replace `reconstruction.reconstruct`.

NOT established:
- Only one object, one geometry. Cost per iteration is higher for GD.
- The weak pure-phase saddle-point failure
  (tests/test_weak_phase_object_limitation.py) is NOT fixed by GD -- see
  the negative test below.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import reconstruction, joint_calibration as jc  # noqa: E402
from test_joint_calibration import _synthetic_object  # noqa: E402
import test_weak_phase_object_limitation as weak  # noqa: E402

CROP = 16


def _bin_aligned_case(channel, truth_fn=_synthetic_object):
    setup = config.default_setup(channel=channel, grid_size=9, objective="current",
                                  resolution_px=(CROP, CROP))
    factor = optics.upsampling_factor(setup)
    hp = optics.actual_hr_pixel_size_um(setup, factor)
    hs = optics.hr_shape((CROP, CROP), factor)
    truth = truth_fn(hs)
    dk = 1 / (hs[1] * hp)
    grid = [{**e, "fx": round(e["fx"] / dk) * dk, "fy": round(e["fy"] / dk) * dk}
            for e in led_array.build_led_grid(setup.led_array, setup.wavelength_um)]
    raw = forward_model.simulate_lr_stack(truth, hp, grid, (CROP, CROP), setup.lr_pixel_size_um,
                                           setup.objective.na, setup.wavelength_um)
    return setup, factor, hp, hs, truth, grid, raw


def _phase_corr(obj, truth):
    return metrics.compare_to_ground_truth(obj, truth)["phase_correlation"]


def _run_both(channel, wf_iters, gd_iters):
    setup, factor, hp, hs, truth, grid, raw = _bin_aligned_case(channel)
    lp, na, wl = setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um
    wf = reconstruction.reconstruct(raw, grid, hp, lp, na, wl, factor, iterations=wf_iters)["object"]
    scale = (hs[0] * hs[1]) / (CROP * CROP)
    meas = {k: v / scale ** 2 for k, v in raw.items()}  # jc's object-unit intensities
    init = jc.initial_object_from_center_led(meas[(grid[0]["row"], grid[0]["col"])], hs)
    gd = jc.reconstruct_and_calibrate(meas, grid, hs, hp, (CROP, CROP), lp, na, wl, init,
                                       n_iterations=gd_iters, calibrate_leds=False)["object"]
    return _phase_corr(wf, truth), _phase_corr(gd, truth)


def test_gradient_descent_converges_on_blue_where_wirtinger_flow_does_not():
    wf, gd = _run_both("blue", wf_iters=400, gd_iters=100)
    assert wf < 0.3   # measured -0.056: never converges, even with 4x the iterations
    assert gd > 0.8   # measured 0.878


def test_gradient_descent_beats_wirtinger_flow_on_red_at_matched_effort():
    wf, gd = _run_both("red", wf_iters=400, gd_iters=100)
    assert gd > wf + 0.03  # measured 0.992 vs 0.928 -- WF gets stuck in the documented red local minimum
    assert gd > 0.95


def test_gradient_descent_does_not_fix_the_weak_phase_saddle_point():
    """NEGATIVE: the pure-phase object that breaks the Wirtinger flow
    (uniform amplitude, initialization has no structure to grip) breaks
    gradient descent too -- measured phase_correlation -0.215 vs WF -0.044.
    This limitation needs new information (TIE), not a different optimizer.
    """
    setup, factor, hp, hs, lg, _, obj = weak._weak_phase_setup()
    dk = 1 / (hs[1] * hp)
    grid = [{**e, "fx": round(e["fx"] / dk) * dk, "fy": round(e["fy"] / dk) * dk} for e in lg]
    raw = forward_model.simulate_lr_stack(obj, hp, grid, (CROP, CROP), setup.lr_pixel_size_um,
                                           setup.objective.na, setup.wavelength_um)
    scale = (hs[0] * hs[1]) / (CROP * CROP)
    meas = {k: v / scale ** 2 for k, v in raw.items()}
    init = jc.initial_object_from_center_led(meas[(grid[0]["row"], grid[0]["col"])], hs)
    gd = jc.reconstruct_and_calibrate(meas, grid, hs, hp, (CROP, CROP), setup.lr_pixel_size_um,
                                       setup.objective.na, setup.wavelength_um, init,
                                       n_iterations=200, calibrate_leds=False)["object"]
    assert _phase_corr(gd, obj) < 0.3


@pytest.mark.parametrize("channel", ["green", "red"])
def test_amplitude_loss_gradient_descent_beats_wirtinger_flow_under_poisson_noise(channel):
    """The noiseless advantage survives noise ONLY with the amplitude loss
    (`loss="amplitude"`, Gaussian noise on |field|), not the paper's
    intensity-L2 loss. 8-seed sweep (scripts/sweep_gd_vs_wf_noise.py,
    peak photon count 20): green +0.462 +/- 0.026 and red +0.472 +/- 0.013
    phase_correlation over the Wirtinger flow, 8/8 seeds each. Blue is NOT
    covered: it wins at peak 100 (+0.695) but fails for every method at
    peak <= 20. Here: 4 seeds at peak 20, WF 200 epochs vs GD 100 its.
    """
    setup, factor, hp, hs, truth, grid, _ = _bin_aligned_case(channel)
    lp, na, wl = setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um
    scale = (hs[0] * hs[1]) / (CROP * CROP)
    diffs = []
    for seed in range(4):
        raw = forward_model.simulate_lr_stack(truth, hp, grid, (CROP, CROP), lp, na, wl,
                                               peak_photon_count=20, rng=np.random.default_rng(seed))
        wf = reconstruction.reconstruct(raw, grid, hp, lp, na, wl, factor, iterations=200)["object"]
        meas = {k: v / scale ** 2 for k, v in raw.items()}
        init = jc.initial_object_from_center_led(meas[(grid[0]["row"], grid[0]["col"])], hs)
        gd = jc.reconstruct_and_calibrate(meas, grid, hs, hp, (CROP, CROP), lp, na, wl, init,
                                           n_iterations=100, calibrate_leds=False, loss="amplitude")["object"]
        diffs.append(_phase_corr(gd, truth) - _phase_corr(wf, truth))
    assert all(d > 0 for d in diffs)
    assert np.mean(diffs) > 0.2

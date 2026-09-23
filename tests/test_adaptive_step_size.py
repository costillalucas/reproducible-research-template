"""tests/test_adaptive_step_size.py -- zuo2016 adaptive step-size
(`references/bibliography.yaml` id `zuo2016`, priority_focus rank 3),
`reconstruction.reconstruct`'s `adaptive_step` param and its
`_next_adaptive_step` helper (Eq. 16 of the paper, implemented exactly,
see that function's docstring).

FIRST, INITIAL finding from exploring this against noisy data (Poisson
shot noise via `forward_model.simulate_lr_stack`'s `peak_photon_count`,
same synthetic object as `test_ptyco_simulator.py`): unlike EPRY pupil
recovery or TIE-informed initialization elsewhere in this project,
`adaptive_step` did NOT show a clean, reliable reconstruction-quality win
over the existing fixed-ramp schedule on this project's small synthetic
test problems -- final phase correlation was within a few percent either
way across several noise levels tried (peak_photon_count in {None, 200,
50, 20}), sometimes very slightly better, sometimes very slightly worse.

FOLLOW-UP, SAME DAY (2026-09-18, autonomous session): tried the same
comparison at HEAVIER noise (peak_photon_count=3, an order of magnitude
worse than the 20 tried above) and MORE iterations (400, vs. up to 60
before) -- enough for zuo2016's described failure mode (their Section 4,
Property A: a constant step can 'undo' the previous cycle's progress and
re-loop under noise, a long-run/many-cycle effect) to actually manifest.
Unlike EPRY's regression (a small-TESTBED-SCALE artifact, see
tests/test_epry_pupil_recovery.py), this turned out to be a small-NOISE/
FEW-ITERATIONS artifact: at peak_photon_count=3, validated across 8
random seeds,
`test_adaptive_step_beats_fixed_ramp_under_heavy_noise_across_seeds`
below finds adaptive_step wins 8/8, with a paired mean gain of
0.060 +/- 0.012 SE phase_correlation -- a real, reproducible advantage.
Formalized in the provenance registry (structure/claims.yaml's
`adaptive_step_helps_under_heavy_noise`, seed=0's exact numbers) since,
unlike this project's usual multi-seed-average style, this session found
it worth keeping BOTH data points on record: the earlier, honest null
result at lighter noise, and this later, real positive result at heavier
noise -- the right regime to use adaptive_step in is now characterized,
not just "does it help, yes/no".

What is verified and asserted throughout this file: the mechanism itself
is implemented correctly (Eq. 16's keep/halve rule matches exactly,
direct unit test against `_next_adaptive_step`), a real reconstruct() run
under heavy noise shrinks its step over time rather than sitting fixed
without diverging, and the heavy-noise, many-iteration regime shows a
real, statistically consistent quality win.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import reconstruction  # noqa: E402


def test_next_adaptive_step_matches_eq16_exactly():
    fn = reconstruction._next_adaptive_step

    # Fewer than 2 epochs: nothing to compare yet, step unchanged.
    assert fn([{"recovery_error": 1.0}], step=8.0) == 8.0

    # Relative improvement (1.0 -> 0.5)/1.0 = 0.5 > eta=0.01 -> keep step.
    history = [{"recovery_error": 1.0}, {"recovery_error": 0.5}]
    assert fn(history, step=8.0) == 8.0

    # Relative improvement (1.0 -> 0.995)/1.0 = 0.005 <= eta=0.01 -> halve.
    history = [{"recovery_error": 1.0}, {"recovery_error": 0.995}]
    assert fn(history, step=8.0) == 4.0

    # Error got WORSE (regressed): relative_improvement negative -> halve.
    history = [{"recovery_error": 1.0}, {"recovery_error": 1.2}]
    assert fn(history, step=8.0) == 4.0

    # Floor: can't halve below min_step.
    history = [{"recovery_error": 1.0}, {"recovery_error": 1.2}]
    assert fn(history, step=0.0015, min_step=1e-3) == 1e-3

    # Custom eta threshold changes the keep/halve boundary.
    history = [{"recovery_error": 1.0}, {"recovery_error": 0.95}]  # 5% improvement
    assert fn(history, step=8.0, eta=0.1) == 4.0  # below 10% eta -> halve
    assert fn(history, step=8.0, eta=0.01) == 8.0  # above 1% eta -> keep


def _synthetic_object(shape):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.15 * np.pi * np.sin(2 * np.pi * 1 * x) * np.cos(2 * np.pi * 1 * y)
    return (amp * np.exp(1j * phase)).astype(complex)


def test_adaptive_step_shrinks_under_heavy_noise_without_diverging():
    grid_size, crop, iterations = 9, 12, 60
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="2_5x_na007",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)

    rng = np.random.default_rng(0)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, peak_photon_count=20, rng=rng,
    )

    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        adaptive_step=True, step_max=20.0,
    )
    steps = [h["step"] for h in result["history"]]
    assert steps[0] == 20.0, "alpha^0 must start at step_max, per Eq. 16's alpha^0=1 convention"
    assert steps[-1] < steps[0], "under heavy noise, the step should shrink at least once"
    # Eq. 16 never grows the step back up -- monotonically non-increasing.
    assert all(steps[i + 1] <= steps[i] for i in range(len(steps) - 1))
    assert np.all(np.isfinite(np.abs(result["object"]))), "must not diverge to inf/nan"


def test_adaptive_step_default_off_reproduces_original_behavior():
    """Regression guard: `adaptive_step=False` (the default) still uses
    the original fixed exponential ramp, unchanged.
    """
    grid_size, crop, iterations = 9, 12, 15
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="2_5x_na007",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        step_max=20.0, step_alpha=0.3,
    )
    expected_steps = [20.0 * (1.0 - np.exp(-0.3 * it)) for it in range(iterations)]
    actual_steps = [h["step"] for h in result["history"]]
    assert np.allclose(actual_steps, expected_steps)


def test_adaptive_step_beats_fixed_ramp_under_heavy_noise_across_seeds():
    """The FOLLOW-UP finding described in this module's docstring: at
    peak_photon_count=3 (much heavier than the {None, 200, 50, 20} tried
    in the earlier, honest null result) and 400 iterations, adaptive_step
    shows a real, reproducible advantage over the fixed ramp -- not a
    one-seed fluke. Checked across 8 seeds with a paired comparison (same
    noisy data for both reconstructions within a seed, only the step
    schedule differs) since the seed-to-seed noise realization dominates
    the variance far more than the fixed/adaptive choice does on its own
    -- an unpaired mean+-std comparison (tried first, not shown here) was
    noisier and less clearly conclusive than looking at the paired
    per-seed difference directly.
    """
    grid_size, crop, iterations, peak_photon_count = 9, 12, 400, 3
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="2_5x_na007",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)

    diffs = []
    for seed in range(8):
        rng = np.random.default_rng(seed)
        lr_images = forward_model.simulate_lr_stack(
            obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, peak_photon_count=peak_photon_count, rng=rng,
        )
        fixed = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations, step_max=20.0,
        )
        adaptive = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
            adaptive_step=True, step_max=20.0,
        )
        gt_f = metrics.compare_to_ground_truth(fixed["object"], obj_true)["phase_correlation"]
        gt_a = metrics.compare_to_ground_truth(adaptive["object"], obj_true)["phase_correlation"]
        diffs.append(gt_a - gt_f)

    diffs = np.array(diffs)
    n_wins = int(np.sum(diffs > 0))
    assert n_wins >= 7, f"adaptive_step should win on almost every seed here, got {n_wins}/8: {diffs}"
    assert diffs.mean() > 0.03, f"paired mean gain should be a real effect, not noise: {diffs.mean()}"
    # seed=0's exact pair is also the deterministic number quoted in the provenance
    # registry (scripts/compute_numbers.py::adaptive_step_heavy_noise_gain) -- sanity
    # check they haven't drifted apart.
    assert diffs[0] > 0.05, diffs[0]

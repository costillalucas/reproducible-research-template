"""tests/test_adaptive_step_size.py -- zuo2016 adaptive step-size
(`references/bibliography.yaml` id `zuo2016`, priority_focus rank 3),
`reconstruction.reconstruct`'s `adaptive_step` param and its
`_next_adaptive_step` helper (Eq. 16 of the paper, implemented exactly,
see that function's docstring).

HONEST, NOT-overclaimed finding from exploring this against noisy data
(Poisson shot noise via `forward_model.simulate_lr_stack`'s
`peak_photon_count`, same synthetic object as `test_ptyco_simulator.py`):
unlike EPRY pupil recovery or TIE-informed initialization elsewhere in
this project, `adaptive_step` does NOT show a clean, reliable
reconstruction-quality win over the existing fixed-ramp schedule on this
project's small synthetic test problems -- final phase correlation was
within a few percent either way across several noise levels tried
(peak_photon_count in {None, 200, 50, 20}), sometimes very slightly
better, sometimes very slightly worse. This project's fixed ramp
(`step_max * (1 - exp(-alpha*it))`) already reaches a moderate,
non-oscillating step by the iteration counts used here, so the
noise-driven oscillation the paper targets (their Section 4, Property A)
may simply not be pronounced enough in this small-grid/low-iteration
regime to show the paper's benefit clearly. What IS verified and
asserted below is that the mechanism itself is implemented correctly:
Eq. 16's keep/halve rule matches exactly (direct unit test against
`_next_adaptive_step`), and a real reconstruct() run under heavy noise
does shrink its step over time rather than sitting fixed, without
diverging.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, optics  # noqa: E402
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
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
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
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
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

"""tests/test_multispectral_registration.py -- roadmap milestone 1
(docs/roadmap_agentic_multispectral_pipeline.md): the three RGB channels
must land on one common HR grid before anything cross-channel (2a's
independent-but-comparable reconstructions, 2b's coupled unwrapping/
dispersion fit) is possible.

No real lab captures are available in this Codespace (data/<channel>/...
isn't checked in -- see .gitignore), so this validates against a
simulated object instead, per the roadmap's "dado un mismo objeto
simulado" wording. Re-validating against real 9x9_recortada_* captures is
still open, noted in the roadmap.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, optics, reconstruction  # noqa: E402


def _rgb_setups(grid_size, lr_size, objective="future"):
    return {
        channel: config.default_setup(
            channel=channel, grid_size=grid_size, objective=objective,
            resolution_px=(lr_size, lr_size),
        )
        for channel in config.CHANNEL_WAVELENGTH_NM
    }


def test_per_channel_upsampling_factor_disagrees_across_wavelengths():
    """Documents the gap milestone 1 fixes: today's per-channel
    `optics.upsampling_factor` is a function of wavelength (shorter
    wavelength -> finer Nyquist target -> larger factor), so red/green/blue
    land on different HR grids if each just calls it independently.

    Uses `objective="future"` (default of `_rgb_setups`): the continuous
    Nyquist target always differs by channel, but the *rounded-to-odd-
    integer* `factor` can coincide by chance for some grid/objective
    combinations (e.g. grid_size=9 with the "current" objective all round
    to 3) -- that's a rounding coincidence, not the fix, and would make
    this negative-control test pass for the wrong reason.
    """
    setups = _rgb_setups(grid_size=9, lr_size=32)
    factors = {ch: optics.upsampling_factor(s) for ch, s in setups.items()}

    assert factors["blue"] >= factors["green"] >= factors["red"]
    assert len(set(factors.values())) > 1, (
        f"expected per-channel factors to disagree (that's the gap), got {factors}"
    )


def test_shared_upsampling_factor_puts_all_channels_on_one_hr_grid():
    lr_size = 32
    setups = _rgb_setups(grid_size=9, lr_size=lr_size)
    factor = optics.shared_upsampling_factor(list(setups.values()))

    # Every channel's own (unshared) requirement must still be satisfied:
    # the shared factor can only be coarser-than-needed for nobody.
    for ch, setup in setups.items():
        assert factor >= optics.upsampling_factor(setup), (ch, factor)

    hr_pixel_by_channel = {
        ch: optics.actual_hr_pixel_size_um(setup, factor)
        for ch, setup in setups.items()
    }
    hr_shape_by_channel = {
        ch: optics.hr_shape((lr_size, lr_size), factor)
        for ch in setups
    }

    assert len(set(hr_pixel_by_channel.values())) == 1, hr_pixel_by_channel
    assert len(set(hr_shape_by_channel.values())) == 1, hr_shape_by_channel


def _synthetic_object(shape):
    """Same style of deterministic phantom as
    tests/test_ptyco_simulator.py's `_synthetic_object` -- kept local so
    this file doesn't depend on that module's private helper.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5

    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)

    phase = 0.15 * np.pi * np.sin(2 * np.pi * 1 * x) * np.cos(2 * np.pi * 1 * y)
    return amp * np.exp(1j * phase)


def test_three_channel_reconstructions_share_one_grid_end_to_end():
    """Milestone 1's definition of done: given one simulated object, the
    three (red/green/blue) reconstructions come back expressed on the same
    HR grid -- same `hr_pixel_um`, same array shape -- so they can be
    stacked into an RGB-shaped array without any resizing/registration
    step. This does NOT test 2a/2b's actual fusion or dispersion fit, only
    that the grid mismatch (the milestone 1 gap) is gone.
    """
    lr_size = 12
    setups = _rgb_setups(grid_size=9, lr_size=lr_size)
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((lr_size, lr_size), factor)

    truth = _synthetic_object(hr_shape)

    reconstructions = {}
    for channel, setup in setups.items():
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            truth, hr_pixel_um, led_grid, (lr_size, lr_size),
            setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
        )
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=15,
        )
        reconstructions[channel] = result["object"]

    shapes = {ch: obj.shape for ch, obj in reconstructions.items()}
    assert len(set(shapes.values())) == 1, shapes
    assert shapes["red"] == hr_shape

    # Stackable into one RGB-shaped array is the concrete, checkable form
    # of "on one common HR grid" -- np.stack raises on shape mismatch.
    stacked = np.stack([reconstructions[ch] for ch in ("red", "green", "blue")])
    assert stacked.shape == (3,) + hr_shape

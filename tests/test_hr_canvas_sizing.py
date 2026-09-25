"""tests/test_hr_canvas_sizing.py -- the HR canvas has to be big enough to
hold every LED's crop window, which is a *separate* requirement from
Nyquist-sampling the synthetic aperture (2026-09-24, J3 T0).

`spectral_ops.led_crop_window` cuts an `lr_shape`-sized rectangle out of
the HR spectrum centered on the LED's frequency bin. The HR spectrum is
`factor`/(2*lr_pixel_um) wide each way; the crop is 1/(2*lr_pixel_um) wide
each way (HR and LR share one frequency spacing, so this does not depend on
`lr_shape`). So the outermost LED fits iff

    factor >= 1 + 2*lr_pixel_um*max_axis_illumination_na/wavelength_um.

The old `optics.upsampling_factor` only asked for
2*lr_pixel_um*(NA_obj + NA_illum_max)/wavelength_um, which implies the
bound above only when 2*lr_pixel_um*NA_obj/wavelength_um >= 1 -- i.e. when
the camera pixel already Nyquist-samples the objective's own passband. The
lab's 2.5x/NA 0.07 setup gives 0.34 there, and green 13x13 with
`center_offset_mm = (0, 3)` at z = 85 mm died with "falls outside the HR
array" on 3 of its 169 LEDs.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from ptyco_full_simulator import config, led_array, optics, spectral_ops  # noqa: E402


def _esferas_setup(z_mm, offset_mm, crop=128, channel="green"):
    """The 2026-09-24 esferas capture geometry: 2.5x/NA 0.07, 13x13 LEDs at
    6 mm pitch, lab row/col bases 12/9 (rows 12-24, cols 9-21)."""
    return config.default_setup(channel, 13, objective="2_5x_na007",
                                resolution_px=(crop, crop),
                                row_index_base=12, col_index_base=9,
                                z_distance_mm=z_mm,
                                led_center_offset_mm=offset_mm)


def _count_leds_outside_canvas(setup, crop):
    factor = optics.upsampling_factor(setup)
    hr_px = optics.actual_hr_pixel_size_um(setup, factor)
    hr_sh = optics.hr_shape((crop, crop), factor)
    outside = 0
    for entry in led_array.build_led_grid(setup.led_array, setup.wavelength_um):
        try:
            spectral_ops.led_crop_window(hr_sh, hr_px, (crop, crop),
                                         entry["fx"], entry["fy"])
        except ValueError:
            outside += 1
    return outside


# --------------------------------------------------------------------------
# The bug this file exists for: the geometry J3 T2 has to sweep.


def test_every_led_fits_for_the_reported_failing_geometry():
    """Green 13x13, offset (0, 3) mm, z = 85 mm, crop 128: the exact case
    that raised "LED ... falls outside the HR array" (3 of 169 LEDs).
    """
    setup = _esferas_setup(85.0, (0.0, 3.0), crop=128)
    assert _count_leds_outside_canvas(setup, 128) == 0


@pytest.mark.parametrize("z_mm", [55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0])
@pytest.mark.parametrize("dy_mm", [-3.0, 0.0, 3.0, 4.5])
@pytest.mark.parametrize("crop", [128, 400])
def test_every_led_fits_across_the_t2_geometry_sweep(z_mm, dy_mm, crop):
    """The whole z x center-offset grid T2 scans, at both crops."""
    setup = _esferas_setup(z_mm, (0.0, dy_mm), crop=crop)
    assert _count_leds_outside_canvas(setup, crop) == 0


@pytest.mark.parametrize("channel", ["red", "green", "blue"])
def test_every_led_fits_for_all_three_channels(channel):
    setup = _esferas_setup(85.0, (0.0, 3.0), crop=128, channel=channel)
    assert _count_leds_outside_canvas(setup, 128) == 0


def test_canvas_requirement_does_not_depend_on_crop_size():
    """The bound is lr_shape-independent, so one factor must serve every
    crop size -- if it didn't, a factor validated at crop 128 could still
    die at crop 400."""
    setup = _esferas_setup(85.0, (0.0, 3.0), crop=128)
    for crop in (16, 32, 64, 128, 256, 400):
        assert _count_leds_outside_canvas(setup, crop) == 0, crop


# --------------------------------------------------------------------------
# The formula itself.


def test_canvas_factor_equals_the_analytic_bound_rounded_up_to_odd():
    setup = _esferas_setup(85.0, (0.0, 3.0))
    na_axis = led_array.max_axis_illumination_na(setup.led_array)
    required = 1.0 + 2.0 * setup.lr_pixel_size_um * na_axis / setup.wavelength_um
    factor = optics.canvas_upsampling_factor(setup)
    assert factor % 2 == 1
    assert factor >= required
    assert factor - 2 < required  # smallest odd integer at or above the bound


def test_upsampling_factor_is_the_max_of_the_two_requirements():
    for z_mm, offset in [(55.0, (0.0, 0.0)), (75.0, (0.0, 3.0)),
                         (85.0, (0.0, 3.0)), (100.0, (0.0, 3.0))]:
        setup = _esferas_setup(z_mm, offset)
        assert optics.upsampling_factor(setup) == max(
            optics.nyquist_upsampling_factor(setup),
            optics.canvas_upsampling_factor(setup),
        ), (z_mm, offset)


def test_nyquist_factor_is_the_old_formula_unchanged():
    """`nyquist_upsampling_factor` must still be exactly what
    `upsampling_factor` used to compute, or the monotone-max argument (no
    recorded result changes unless it was crashing) has no anchor."""
    for z_mm, offset, channel, grid in [(70.0, (0.0, 0.0), "green", 9),
                                        (76.0, (0.0, 0.0), "blue", 31),
                                        (85.0, (0.0, 3.0), "red", 13)]:
        setup = config.default_setup(channel, grid, objective="2_5x_na007",
                                     z_distance_mm=z_mm,
                                     led_center_offset_mm=offset)
        ratio = setup.lr_pixel_size_um / optics.hr_pixel_size_um(setup)
        expected = int(np.ceil(ratio))
        expected = expected + 1 if expected % 2 == 0 else expected
        assert optics.nyquist_upsampling_factor(setup) == expected


#: The only two nominal-geometry (z = 70 mm, centered array) presets whose
#: factor the canvas term raises -- recorded here so the change can't happen
#: silently. Both are red (the longest wavelength needs the widest canvas in
#: units of the LR Nyquist band) at a large grid. `2_5x_na007` 15x15 red
#: already crashed at every crop size tried (>= 20 of 225 LEDs outside);
#: `2x_na010` 31x31 red ran at crop <= 100 and crashed from crop 128 up
#: (4 of 961 LEDs), so for it 5 -> 7 is a real change of a working
#: configuration, not only a crash being fixed. See reports/r01-worker-1.md.
CANVAS_LIMITED_NOMINAL_PRESETS = {
    ("2x_na010", 31, "red"): (5, 7),
    ("2_5x_na007", 15, "red"): (3, 5),
}


def test_pinned_synthetic_geometries_keep_their_factor():
    """Bit-identity guard for the synthetic results already recorded: the
    nominal simulator geometry (z = 70 mm, centered array) is not canvas
    limited except for the two presets listed above, so every other factor
    must be the Nyquist one, untouched."""
    for objective in ("2x_na010", "2_5x_na007"):
        for grid in (5, 9, 15, 31):
            for channel in ("red", "green", "blue"):
                if (objective, grid, channel) in CANVAS_LIMITED_NOMINAL_PRESETS:
                    continue
                setup = config.default_setup(channel, grid, objective=objective)
                assert optics.upsampling_factor(setup) == \
                    optics.nyquist_upsampling_factor(setup), (objective, grid, channel)


@pytest.mark.parametrize("key", sorted(CANVAS_LIMITED_NOMINAL_PRESETS))
def test_the_two_canvas_limited_nominal_presets_are_the_documented_ones(key):
    objective, grid, channel = key
    old_factor, new_factor = CANVAS_LIMITED_NOMINAL_PRESETS[key]
    setup = config.default_setup(channel, grid, objective=objective)
    assert optics.nyquist_upsampling_factor(setup) == old_factor
    assert optics.upsampling_factor(setup) == new_factor
    assert _count_leds_outside_canvas(setup, 128) == 0


# --------------------------------------------------------------------------
# max_axis_illumination_na: why per-axis, and why the whole grid.


def test_axis_na_is_below_the_radial_na_but_not_by_more_than_sqrt2():
    for z_mm, offset in [(55.0, (0.0, 0.0)), (85.0, (0.0, 3.0)), (100.0, (3.0, -3.0))]:
        cfg = _esferas_setup(z_mm, offset).led_array
        radial = led_array.max_illumination_na(cfg)
        axis = led_array.max_axis_illumination_na(cfg)
        assert axis <= radial + 1e-12, (z_mm, offset)
        assert axis >= radial / np.sqrt(2) - 1e-12, (z_mm, offset)


def test_axis_na_is_not_attained_at_a_corner_when_the_array_is_offset():
    """With a nonzero `center_offset_mm` the largest single-axis sin(theta)
    sits at an extreme column and the row of *smallest* |dy| -- an interior
    row. A corners-only search (what `max_illumination_na` does, correctly,
    for the radial quantity) underestimates it."""
    cfg = _esferas_setup(85.0, (0.0, 3.0)).led_array
    row_lo, row_hi = cfg.row_base, cfg.row_base + cfg.grid_size - 1
    col_lo, col_hi = cfg.col_base, cfg.col_base + cfg.grid_size - 1
    corners_only = 0.0
    for row in (row_lo, row_hi):
        for col in (col_lo, col_hi):
            dx, dy = led_array.led_position_mm(row, col, cfg)
            dist = np.sqrt(dx**2 + dy**2 + cfg.z_distance_mm**2)
            corners_only = max(corners_only, abs(dx) / dist, abs(dy) / dist)
    assert led_array.max_axis_illumination_na(cfg) > corners_only


def test_axis_na_matches_a_brute_force_scan_of_the_whole_grid():
    cfg = _esferas_setup(85.0, (1.0, 3.0)).led_array
    best = 0.0
    for row in range(cfg.row_base, cfg.row_base + cfg.grid_size):
        for col in range(cfg.col_base, cfg.col_base + cfg.grid_size):
            dx, dy = led_array.led_position_mm(row, col, cfg)
            dist = np.sqrt(dx**2 + dy**2 + cfg.z_distance_mm**2)
            best = max(best, abs(dx) / dist, abs(dy) / dist)
    assert led_array.max_axis_illumination_na(cfg) == pytest.approx(best)


# --------------------------------------------------------------------------
# The failure path still fails: an undersized canvas must raise, not
# silently wrap around.


def test_an_undersized_canvas_still_raises():
    setup = _esferas_setup(85.0, (0.0, 3.0))
    too_small = 3  # what the old formula returned for this geometry
    hr_px = optics.actual_hr_pixel_size_um(setup, too_small)
    hr_sh = optics.hr_shape((128, 128), too_small)
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    outside = 0
    for entry in grid:
        try:
            spectral_ops.led_crop_window(hr_sh, hr_px, (128, 128),
                                         entry["fx"], entry["fy"])
        except ValueError as exc:
            outside += 1
            assert "falls outside the HR" in str(exc)
    assert outside == 3, outside  # the 3 LEDs the intent reported

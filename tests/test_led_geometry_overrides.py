"""tests/test_led_geometry_overrides.py -- real LED-array geometry and the
real-data CLIs' geometry overrides (2026-09-23): the lab confirmed the
array sits 76 mm from the sample (the simulator's nominal geometry is
70 mm, kept for synthetic reproducibility), isn't sure the array is
centered on the optical axis, and the 2025-12-12 capture's measured
effective magnification/NA don't match the 2x/0.10 preset (roadmap 6.8),
so the CLIs take --z-distance-mm, --led-center-offset-mm, --na and
--magnification.
"""
from __future__ import annotations

import inspect
import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "pipelines"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "agents"))

from ptyco_full_simulator import config, forward_model, led_array, optics, reconstruction  # noqa: E402

REAL_CLIS = [
    "reconstruct_real_images",
    "reconstruct_multispectral_independent",
    "reconstruct_multispectral_coupled",
    "sweep_real_reconstruction_quality",
]


def _base_argv(module_name):
    base = ["--data-root", "x"]
    if module_name == "sweep_real_reconstruction_quality":
        base += ["--reference-image", "r.tif", "--iterations", "1"]
    return base


def test_real_z_distance_is_76mm_but_nominal_default_stays_70mm():
    assert config.REAL_CAPTURE_Z_DISTANCE_MM == 76.0
    assert config.LEDArrayConfig(grid_size=9).z_distance_mm == 70.0
    assert config.default_setup(channel="green", grid_size=9).led_array.z_distance_mm == 70.0
    assert config.default_setup(channel="green", grid_size=9,
                                z_distance_mm=76.0).led_array.z_distance_mm == 76.0


def test_zero_center_offset_leaves_the_led_grid_bit_identical():
    """Default (0, 0) offset must not move a single k -- every synthetic
    result recorded so far depends on it."""
    nominal = config.LEDArrayConfig(grid_size=9)
    explicit = config.LEDArrayConfig(grid_size=9, center_offset_mm=(0.0, 0.0))
    a = led_array.build_led_grid(nominal, 0.53)
    b = led_array.build_led_grid(explicit, 0.53)
    assert a == b
    assert a[0]["row"] == nominal.center_row and a[0]["col"] == nominal.center_col
    assert led_array.max_illumination_na(nominal) == led_array.max_illumination_na(explicit)


def test_center_offset_shifts_the_array_rigidly():
    pitch = 6.0
    cfg = config.LEDArrayConfig(grid_size=9, pitch_mm=pitch, center_offset_mm=(pitch, -pitch / 2))
    dx, dy = led_array.led_position_mm(int(cfg.center_row), int(cfg.center_col), cfg)
    assert (dx, dy) == (pitch, -pitch / 2)
    # One full pitch in +x: the LED one column left of nominal center is now on the x axis.
    fx, _ = led_array.illumination_spatial_freq(int(cfg.center_row), int(cfg.center_col) - 1, cfg, 0.53)
    assert fx == pytest.approx(0.0, abs=1e-15)


def test_center_offset_reorders_the_grid_by_distance_from_the_axis():
    cfg = config.LEDArrayConfig(grid_size=9, center_offset_mm=(6.0, 6.0))
    grid = led_array.build_led_grid(cfg, 0.53)
    assert (grid[0]["row"], grid[0]["col"]) == (cfg.center_row - 1, cfg.center_col - 1)
    assert grid[0]["radial_mm"] == pytest.approx(0.0)


def test_center_offset_raises_max_illumination_na_to_the_farthest_corner():
    centered = config.LEDArrayConfig(grid_size=9)
    shifted = config.LEDArrayConfig(grid_size=9, center_offset_mm=(3.0, 0.0))
    assert led_array.max_illumination_na(shifted) > led_array.max_illumination_na(centered)
    # The mirror shift gives the same value: the farthest corner is just on the other side.
    mirrored = config.LEDArrayConfig(grid_size=9, center_offset_mm=(-3.0, 0.0))
    assert led_array.max_illumination_na(mirrored) == pytest.approx(led_array.max_illumination_na(shifted))


def test_na_and_magnification_override_the_preset_without_mutating_it():
    setup = config.default_setup(channel="green", grid_size=9, na=0.11, magnification=1.83)
    assert (setup.objective.na, setup.objective.magnification) == (0.11, 1.83)
    assert setup.objective.name == "2x_na010+override"
    assert setup.lr_pixel_size_um == pytest.approx(3.2 / 1.83)
    assert (config.OBJECTIVES["2x_na010"].na, config.OBJECTIVES["2x_na010"].magnification) == (0.10, 2.0)
    only_na = config.default_setup(channel="green", grid_size=9, na=0.12)
    assert (only_na.objective.na, only_na.objective.magnification) == (0.12, 2.0)
    plain = config.default_setup(channel="green", grid_size=9)
    assert plain.objective is config.OBJECTIVES["2x_na010"]


@pytest.mark.parametrize("module_name", REAL_CLIS)
def test_real_cli_geometry_defaults_are_the_real_lab_setup(module_name):
    from ptyco_full_simulator import cli_args
    module = __import__(module_name)
    args = module.parse_args(_base_argv(module_name))
    assert args.z_distance_mm == 76.0
    assert tuple(args.led_center_offset_mm) == (0.0, 0.0)
    assert args.na is None and args.magnification is None
    setup = config.default_setup(channel="green", grid_size=9, **cli_args.geometry_kwargs(args))
    assert setup.led_array.z_distance_mm == 76.0
    assert setup.objective is config.OBJECTIVES["2x_na010"]


@pytest.mark.parametrize("module_name", REAL_CLIS)
def test_real_cli_geometry_flags_parse(module_name):
    module = __import__(module_name)
    args = module.parse_args(_base_argv(module_name) + [
        "--z-distance-mm", "70", "--led-center-offset-mm", "3", "-1.5",
        "--na", "0.11", "--magnification", "1.83"])
    assert args.z_distance_mm == 70.0
    assert tuple(args.led_center_offset_mm) == (3.0, -1.5)
    assert (args.na, args.magnification) == (0.11, 1.83)


def test_reconstruct_all_channels_defaults_to_the_real_z_distance():
    import reconstruct_multispectral_independent as independent
    params = inspect.signature(independent.reconstruct_all_channels).parameters
    assert params["z_distance_mm"].default == config.REAL_CAPTURE_Z_DISTANCE_MM
    assert params["led_center_offset_mm"].default == (0.0, 0.0)


def _tiny_case(crop=12, center_offset_mm=(0.0, 0.0)):
    setup = config.default_setup(channel="green", grid_size=9, objective="2_5x_na007",
                                 resolution_px=(crop, crop), led_center_offset_mm=center_offset_mm)
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    h, w = optics.hr_shape((crop, crop), factor)
    y, x = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None] - 0.5
    truth = (0.5 + 0.5 * np.exp(-(x ** 2 + y ** 2) / 0.02)) * np.exp(1j * 0.3 * np.sin(6 * x))
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr = forward_model.simulate_lr_stack(truth, hr_pixel_um, led_grid, (crop, crop),
                                         setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um)
    return setup, factor, hr_pixel_um, lr


def test_reconstructing_with_the_true_center_offset_fits_better_than_assuming_none():
    """Data from a half-pitch-misaligned array: the solver fits it better
    (lower internal residual) when told the true offset -- i.e. the offset
    actually reaches the forward model the solver uses, not just metadata."""
    offset = (3.0, -3.0)
    setup, factor, hr_pixel_um, lr = _tiny_case(center_offset_mm=offset)
    final = {}
    for label, off in (("true", offset), ("none", (0.0, 0.0))):
        cfg = config.LEDArrayConfig(grid_size=9, center_offset_mm=off)
        grid = led_array.build_led_grid(cfg, setup.wavelength_um)
        result = reconstruction.reconstruct(lr, grid, hr_pixel_um, setup.lr_pixel_size_um,
                                            setup.objective.na, setup.wavelength_um, factor,
                                            iterations=20)
        final[label] = result["history"][-1]["recovery_error"]
    assert final["true"] < final["none"], final


def test_reconstruct_real_images_records_effective_geometry(tmp_path):
    import reconstruct_real_images as real
    crop = 12
    setup, factor, hr_pixel_um, lr = _tiny_case(crop=crop)
    subdir = tmp_path / "green" / f"9x9_recortada_{crop}"
    subdir.mkdir(parents=True)
    for (row, col), intensity in lr.items():
        Image.fromarray(intensity.astype(np.float32), mode="F").save(subdir / f"fila{row}_columna{col}.tiff")
    out = tmp_path / "out"
    rc = real.main(["--data-root", str(tmp_path), "--channel", "green", "--grid-size", "9",
                    "--crop", str(crop), "--objective", "2_5x_na007", "--iterations", "2",
                    "--z-distance-mm", "70", "--led-center-offset-mm", "1.5", "-2",
                    "--na", "0.08", "--magnification", "2.4", "--output-dir", str(out)])
    assert rc == 0
    with open(out / "metrics.json") as fh:
        geometry = json.load(fh)["geometry"]
    assert geometry["z_distance_mm"] == 70.0
    assert geometry["led_center_offset_mm"] == [1.5, -2.0]
    assert (geometry["na"], geometry["magnification"]) == (0.08, 2.4)
    assert geometry["objective_name"] == "2_5x_na007+override"
    assert geometry["lr_pixel_um"] == pytest.approx(3.2 / 2.4)

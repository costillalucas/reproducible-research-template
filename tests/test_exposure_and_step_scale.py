"""tests/test_exposure_and_step_scale.py -- the three real-data fixes of
2026-09-23 (roadmap 6.8, fork F's measurements in
results/led_geometry_2025-12-12/):

1. Real captures use a different exposure per LED on top of a ~188-count
   camera bias; every real image is now (raw - dark) / exposure before
   reconstruction (io_utils.load_exposure_map / normalize_exposure).
2. The default initial guess is factor^2 too bright for the un-normalized
   forward model (reconstruction.initial_hr_guess's
   match_forward_model_scale).
3. A fixed step_max is ~1/lr_n_px of the ePIE unit step, so the solver
   freezes at large crops; step_relative gives a crop-independent step.
"""
from __future__ import annotations

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

from ptyco_full_simulator import (config, forward_model, io_utils, led_array, metrics,  # noqa: E402
                                  optics, reconstruction)

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


def _write_capture(root, channel, images, subdir="3x3_recortada_4"):
    d = root / channel / subdir
    d.mkdir(parents=True, exist_ok=True)
    for (row, col), img in images.items():
        Image.fromarray(np.asarray(img, dtype=np.float32), mode="F").save(d / f"fila{row}_col{col}.tiff")


def _write_lab_json(root, channel, exposures_us, discarded_us=None):
    by_time = {}
    for key, us in exposures_us.items():
        by_time.setdefault(str(us), []).append(list(key))
    data = {"LEDS_POR_TIEMPO": by_time,
            "LEDS_DESCARTADOS": {str(us): [list(k)] for k, us in (discarded_us or {}).items()}}
    (root / channel / "leds_por_tiempo_17.100.json").write_text(json.dumps(data))


# --- 1. exposure normalization ---------------------------------------------

def test_exposure_map_from_lab_json_is_in_microseconds_and_reads_discards(tmp_path):
    (tmp_path / "green").mkdir()
    _write_lab_json(tmp_path, "green", {(1, 1): 3000, (1, 2): 175000}, discarded_us={(0, 2): 35000})
    emap = io_utils.load_exposure_map(tmp_path, "green")
    assert emap["exposure_ms"] == {(1, 1): 3.0, (1, 2): 175.0}
    assert emap["discarded"] == {(0, 2)}
    assert emap["source"].endswith("leds_por_tiempo_17.100.json")


def test_exposure_map_falls_back_to_ms_folders(tmp_path):
    for ms, key in (("3ms", (1, 1)), ("175ms", (0, 2))):
        d = tmp_path / "red" / ms
        d.mkdir(parents=True)
        Image.fromarray(np.zeros((2, 2), np.float32), mode="F").save(d / f"fila{key[0]}_col{key[1]}.tiff")
    (tmp_path / "red" / "3x3_recortada_4").mkdir()  # not an exposure folder, must be ignored
    emap = io_utils.load_exposure_map(tmp_path, "red")
    assert emap["exposure_ms"] == {(1, 1): 3.0, (0, 2): 175.0}
    assert emap["discarded"] == set()


def test_exposure_map_missing_fails_loudly_and_ambiguous_json_is_rejected(tmp_path):
    (tmp_path / "blue").mkdir()
    with pytest.raises(FileNotFoundError, match="no-exposure-normalization"):
        io_utils.load_exposure_map(tmp_path, "blue")
    _write_lab_json(tmp_path, "blue", {(1, 1): 3000})
    (tmp_path / "blue" / "leds_por_tiempo_other.json").write_text("{}")
    with pytest.raises(ValueError, match="ambiguous"):
        io_utils.load_exposure_map(tmp_path, "blue")


def test_normalize_exposure_subtracts_dark_divides_by_exposure_and_drops():
    stack = {(1, 1): np.full((2, 2), 388.0),      # 3 ms on-axis
             (0, 0): np.full((2, 2), 588.0),      # 100 ms dark-field
             (0, 1): np.full((2, 2), 100.0),      # below dark -> clipped to 0
             (0, 2): np.full((2, 2), 999.0),      # lab-discarded
             (2, 2): np.full((2, 2), 999.0)}      # no exposure known
    exposure_ms = {(1, 1): 3.0, (0, 0): 100.0, (0, 1): 10.0, (0, 2): 5.0}
    out, info = io_utils.normalize_exposure(stack, exposure_ms, dark_level=188.0, discarded={(0, 2)})
    assert set(out) == {(1, 1), (0, 0), (0, 1)}
    np.testing.assert_allclose(out[(1, 1)], 200.0)          # (388-188)/3*3
    np.testing.assert_allclose(out[(0, 0)], 400.0 / 100 * 3)  # dark-field now dimmer than on-axis
    np.testing.assert_allclose(out[(0, 1)], 0.0)
    assert info["reference_exposure_ms"] == 3.0
    assert info["dropped_discarded"] == [[0, 2]] and info["dropped_no_exposure"] == [[2, 2]]


def test_load_real_lr_stack_normalized_end_to_end_and_opt_out(tmp_path):
    images = {(1, 1): np.full((4, 4), 388.0), (0, 0): np.full((4, 4), 588.0)}
    _write_capture(tmp_path, "green", images)
    _write_lab_json(tmp_path, "green", {(1, 1): 3000, (0, 0): 100000})
    out, info = io_utils.load_real_lr_stack_normalized(tmp_path, "green", 3, 4, index_base=0)
    np.testing.assert_allclose(out[(1, 1)], 200.0)
    np.testing.assert_allclose(out[(0, 0)], 12.0)
    assert info["exposure_normalized"] and info["dark_level"] == config.REAL_CAPTURE_DARK_LEVEL
    raw, raw_info = io_utils.load_real_lr_stack_normalized(tmp_path, "green", 3, 4, index_base=0,
                                                           normalize=False)
    np.testing.assert_allclose(raw[(0, 0)], 588.0)
    assert raw_info == {"exposure_normalized": False}


# --- 2. initial-guess scale --------------------------------------------------

def _flat_setup(crop=8):
    s = config.default_setup("green", 9, objective="2_5x_na007", resolution_px=(crop, crop))
    f = optics.upsampling_factor(s)
    hp = optics.actual_hr_pixel_size_um(s, f)
    grid = led_array.build_led_grid(s.led_array, s.wavelength_um)
    assert f > 1  # otherwise the factor^2 checks below are vacuous
    return s, f, hp, grid


def test_scaled_initial_guess_reproduces_the_measured_intensity_through_the_forward_model():
    s, f, hp, grid = _flat_setup()
    crop = 8
    obj = np.ones((crop * f, crop * f), complex)
    lr = forward_model.simulate_lr_stack(obj, hp, grid[:1], (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    center = (grid[0]["row"], grid[0]["col"])
    for scaled, expected_ratio in ((True, 1.0), (False, float(f) ** 4)):
        guess = reconstruction.initial_hr_guess(lr, grid, f, match_forward_model_scale=scaled)
        again = forward_model.simulate_lr_stack(guess, hp, grid[:1], (crop, crop), s.lr_pixel_size_um,
                                                s.objective.na, s.wavelength_um)
        np.testing.assert_allclose(again[center].mean() / lr[center].mean(), expected_ratio, rtol=1e-6)


def test_normalize_initial_guess_flag_is_the_scaled_guess_and_off_by_default():
    s, f, hp, grid = _flat_setup()
    crop = 8
    rng = np.random.default_rng(1)
    obj = (1 + 0.2 * rng.standard_normal((crop * f, crop * f))).astype(complex)
    lr = forward_model.simulate_lr_stack(obj, hp, grid, (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    args = (lr, grid, hp, s.lr_pixel_size_um, s.objective.na, s.wavelength_um, f)
    via_flag = reconstruction.reconstruct(*args, iterations=3, normalize_initial_guess=True)
    explicit = reconstruction.reconstruct(*args, iterations=3, initial_object=reconstruction.initial_hr_guess(
        lr, grid, f, match_forward_model_scale=True))
    np.testing.assert_array_equal(via_flag["object"], explicit["object"])
    default = reconstruction.reconstruct(*args, iterations=3)
    legacy = reconstruction.reconstruct(*args, iterations=3,
                                        initial_object=reconstruction.initial_hr_guess(lr, grid, f))
    np.testing.assert_array_equal(default["object"], legacy["object"])


# --- 3. crop-independent step -----------------------------------------------

def test_step_relative_is_step_max_in_units_of_lr_n_px():
    s, f, hp, grid = _flat_setup()
    crop = 8
    rng = np.random.default_rng(2)
    obj = (1 + 0.2 * rng.standard_normal((crop * f, crop * f))).astype(complex)
    lr = forward_model.simulate_lr_stack(obj, hp, grid, (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    args = (lr, grid, hp, s.lr_pixel_size_um, s.objective.na, s.wavelength_um, f)
    a = reconstruction.reconstruct(*args, iterations=3, step_relative=0.3)
    b = reconstruction.reconstruct(*args, iterations=3, step_max=0.3 * crop * crop)
    np.testing.assert_array_equal(a["object"], b["object"])
    with pytest.raises(ValueError, match="step_relative"):
        reconstruction.reconstruct(*args, iterations=1, step_relative=0.0)


def test_default_step_stalls_at_a_moderate_crop_but_step_relative_does_not():
    """Fork F's synthetic control, shrunk: noiseless smooth random object,
    2x/0.10, 9x9, crop 48, 20 iterations, same scaled initial guess --
    only the step differs. The legacy step_max=20 is ~20/2304 of the ePIE
    unit step here and barely moves; 0.3 of the unit step converges."""
    crop = 48
    s = config.default_setup("green", 9, objective="2x_na010", resolution_px=(crop, crop))
    f = optics.upsampling_factor(s)
    hp = optics.actual_hr_pixel_size_um(s, f)
    n = crop * f
    rng = np.random.default_rng(0)

    def smooth():
        noise = np.fft.fft2(rng.standard_normal((n, n)))
        fy = np.fft.fftfreq(n, d=hp)[:, None]
        fx = np.fft.fftfreq(n, d=hp)[None, :]
        return np.real(np.fft.ifft2(noise * (np.hypot(fx, fy) < 0.4 / 0.53)))

    a, p = smooth(), smooth()
    obj = (1 + 0.3 * a / a.std()) * np.exp(1j * 0.8 * p / p.std())
    grid = led_array.build_led_grid(s.led_array, s.wavelength_um)
    lr = forward_model.simulate_lr_stack(obj, hp, grid, (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    args = (lr, grid, hp, s.lr_pixel_size_um, s.objective.na, s.wavelength_um, f)
    legacy = reconstruction.reconstruct(*args, iterations=20, normalize_initial_guess=True)
    relative = reconstruction.reconstruct(*args, iterations=20, normalize_initial_guess=True,
                                          step_relative=0.3)
    imp_legacy = metrics.convergence_summary(legacy["history"])["relative_improvement"]
    imp_relative = metrics.convergence_summary(relative["history"])["relative_improvement"]
    phase_legacy = metrics.compare_to_ground_truth(legacy["object"], obj)["phase_correlation"]
    phase_relative = metrics.compare_to_ground_truth(relative["object"], obj)["phase_correlation"]
    assert imp_legacy < 0.5 and imp_relative > 0.8
    assert phase_relative > 0.85 and phase_relative > phase_legacy + 0.3


def test_step_relative_scales_epry_alpha_beta_by_lr_n_px_and_default_is_unchanged():
    """Under recover_pupil, step_relative multiplies EPRY's alpha/beta by
    step_relative * lr_n_px (bit-identical to passing them by hand); with
    no step_relative the EPRY branch is exactly what it was."""
    s, f, hp, grid = _flat_setup()
    crop = 8
    rng = np.random.default_rng(4)
    obj = (1 + 0.2 * rng.standard_normal((crop * f, crop * f))).astype(complex)
    lr = forward_model.simulate_lr_stack(obj, hp, grid, (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    args = (lr, grid, hp, s.lr_pixel_size_um, s.objective.na, s.wavelength_um, f)
    kw = dict(iterations=3, recover_pupil=True)
    a = reconstruction.reconstruct(*args, step_relative=0.5, **kw)
    b = reconstruction.reconstruct(*args, epry_alpha=0.5 * crop * crop,
                                   epry_beta=0.5 * crop * crop, **kw)
    np.testing.assert_array_equal(a["object"], b["object"])
    np.testing.assert_array_equal(a["pupil"], b["pupil"])
    c = reconstruction.reconstruct(*args, step_relative=0.5, epry_alpha=2.0, **kw)
    d = reconstruction.reconstruct(*args, epry_alpha=2.0 * 0.5 * crop * crop,
                                   epry_beta=0.5 * crop * crop, **kw)
    np.testing.assert_array_equal(c["object"], d["object"])
    default = reconstruction.reconstruct(*args, **kw)
    explicit = reconstruction.reconstruct(*args, epry_alpha=1.0, epry_beta=1.0, **kw)
    np.testing.assert_array_equal(default["object"], explicit["object"])
    assert not np.array_equal(default["object"], a["object"])


def test_default_epry_stalls_at_a_moderate_crop_but_step_relative_does_not():
    """Forks H/K: the EPRY branch divides its exit-wave correction by
    lr_n_px, so the paper's alpha=beta=1 is a 1/lr_n_px step and stays
    frozen at crop 48; step_relative=1.0 (== ou2014's unit step) converges."""
    crop = 48
    s = config.default_setup("green", 9, objective="2x_na010", resolution_px=(crop, crop))
    f = optics.upsampling_factor(s)
    hp = optics.actual_hr_pixel_size_um(s, f)
    n = crop * f
    rng = np.random.default_rng(0)

    def smooth():
        noise = np.fft.fft2(rng.standard_normal((n, n)))
        fy = np.fft.fftfreq(n, d=hp)[:, None]
        fx = np.fft.fftfreq(n, d=hp)[None, :]
        return np.real(np.fft.ifft2(noise * (np.hypot(fx, fy) < 0.4 / 0.53)))

    a, p = smooth(), smooth()
    obj = (1 + 0.3 * a / a.std()) * np.exp(1j * 0.8 * p / p.std())
    grid = led_array.build_led_grid(s.led_array, s.wavelength_um)
    lr = forward_model.simulate_lr_stack(obj, hp, grid, (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    args = (lr, grid, hp, s.lr_pixel_size_um, s.objective.na, s.wavelength_um, f)
    kw = dict(iterations=20, normalize_initial_guess=True, recover_pupil=True)
    legacy = reconstruction.reconstruct(*args, **kw)
    relative = reconstruction.reconstruct(*args, step_relative=1.0, **kw)
    imp_legacy = metrics.convergence_summary(legacy["history"])["relative_improvement"]
    imp_relative = metrics.convergence_summary(relative["history"])["relative_improvement"]
    phase_legacy = metrics.compare_to_ground_truth(legacy["object"], obj)["phase_correlation"]
    phase_relative = metrics.compare_to_ground_truth(relative["object"], obj)["phase_correlation"]
    assert imp_legacy < 0.1 and imp_relative > 0.8
    assert phase_relative > 0.8 and phase_relative > phase_legacy + 0.3


# --- CLI wiring --------------------------------------------------------------

def test_multispectral_rejects_invalid_combinations_before_loading_anything(tmp_path):
    import reconstruct_multispectral_independent as multispectral
    with pytest.raises(ValueError, match="defocus"):
        multispectral.reconstruct_all_channels(str(tmp_path), 9, crop=8, tie_defocus_um=30.0)
    for extra in ({"solver": "gd-amplitude"}, {"use_reconstruction_agent": True}):
        with pytest.raises(ValueError, match="step_relative"):
            multispectral.reconstruct_all_channels(str(tmp_path), 9, crop=8, step_relative=0.3,
                                                   exposure_normalization=False, **extra)


@pytest.mark.parametrize("module_name", REAL_CLIS)
def test_real_cli_defaults_normalize_exposure_and_guess_but_keep_legacy_step(module_name):
    module = __import__(module_name)
    args = module.parse_args(_base_argv(module_name))
    assert args.exposure_normalization is True
    assert args.dark_level == config.REAL_CAPTURE_DARK_LEVEL == 188.0
    assert args.normalize_initial_guess is True
    assert args.step_epie is None
    args = module.parse_args(_base_argv(module_name) + [
        "--no-exposure-normalization", "--dark-level", "190", "--step-epie", "0.3",
        "--no-normalize-initial-guess"])
    assert (args.exposure_normalization, args.dark_level, args.step_epie,
            args.normalize_initial_guess) == (False, 190.0, 0.3, False)


def _synthetic_real_capture(tmp_path, crop=8):
    s = config.default_setup("green", 9, objective="2_5x_na007", resolution_px=(crop, crop))
    f = optics.upsampling_factor(s)
    hp = optics.actual_hr_pixel_size_um(s, f)
    grid = led_array.build_led_grid(s.led_array, s.wavelength_um)
    rng = np.random.default_rng(3)
    obj = (1 + 0.2 * rng.standard_normal((crop * f, crop * f))).astype(complex)
    lr = forward_model.simulate_lr_stack(obj, hp, grid, (crop, crop), s.lr_pixel_size_um,
                                         s.objective.na, s.wavelength_um)
    exposures_us = {k: (3000 if k == (5, 5) else 100000) for k in lr}
    # what the camera would record: dark + intensity * exposure (arbitrary gain)
    raw = {k: 188.0 + v * exposures_us[k] / 3000.0 for k, v in lr.items()}
    _write_capture(tmp_path, "green", raw, subdir=f"9x9_recortada_{crop}")
    return lr, exposures_us


def test_reconstruct_real_images_normalizes_by_default_and_records_it(tmp_path):
    import reconstruct_real_images as real
    crop = 8
    lr, exposures_us = _synthetic_real_capture(tmp_path, crop)
    out = tmp_path / "out"
    argv = ["--data-root", str(tmp_path), "--channel", "green", "--grid-size", "9", "--crop", str(crop),
            "--objective", "2_5x_na007", "--z-distance-mm", "70", "--iterations", "2",
            "--output-dir", str(out)]
    with pytest.raises(FileNotFoundError, match="exposure metadata"):
        real.main(argv)
    _write_lab_json(tmp_path, "green", exposures_us, discarded_us={(1, 1): 100000})
    assert real.main(argv + ["--step-epie", "0.3"]) == 0
    with open(out / "metrics.json") as fh:
        m = json.load(fh)
    assert m["acquisition"]["exposure_normalized"] is True
    assert m["acquisition"]["dropped_discarded"] == [[1, 1]]
    assert m["n_leds_used"] == len(lr) - 1
    assert m["solver_scale"] == {"step_epie": 0.3, "normalize_initial_guess": True,
                                 "applies_to": "wirtinger only (gd-amplitude has its own normalized model)"}
    # normalized stack == the noiseless simulated intensities (dark removed, exposure divided)
    stack, _ = io_utils.load_real_lr_stack_normalized(tmp_path, "green", 9, crop, index_base=1)
    np.testing.assert_allclose(stack[(5, 5)], lr[(5, 5)], rtol=1e-4, atol=1e-3)

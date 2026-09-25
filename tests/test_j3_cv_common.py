"""tests/test_j3_cv_common.py -- the J3 shared cross-validation harness
(`results/captura_2026-09-24/j3/common/cv_common.py`).

That module is not library code under `src/`, but every J3 number (the T1
synthetic baseline, the T2 geometry search, the T3 cause separation, the T4 final
runs) is produced by it, so the properties the conclusions rest on are pinned
here rather than trusted:

* the four folds really PARTITION the LEDs, and `fold=1` still reproduces
  December's hard-coded `i % 4 == 1` rule (`results/geometry_search_2025-12-12/
  cv.py`) so the two campaigns' held-out scores stay comparable;
* the initialization LED (17, 15) is never held out -- if it were, the run would
  be initialized from an image it is then scored on;
* held-out LEDs genuinely do not reach the solver (checked by corrupting their
  images and demanding a bit-identical object);
* `per_led_amplitude_residual` is zero on the ground-truth object, i.e. it is
  the same forward model the stack was simulated with and not an approximation
  of it;
* the rotation `LEDArrayConfig` has no field for reduces to
  `led_array.build_led_grid` at theta = 0 and is a rigid rotation otherwise.
"""
import importlib.util
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, optics  # noqa: E402

_CV = os.path.join(os.path.dirname(__file__), "..", "results", "captura_2026-09-24",
                   "j3", "common", "cv_common.py")


@pytest.fixture(scope="module")
def cvc():
    if not os.path.exists(_CV):
        pytest.skip(f"{_CV} not present (results/ is not versioned)")
    spec =importlib.util.spec_from_file_location("j3_cv_common", _CV)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tiny(cvc):
    """A 5x5-LED / 16px problem with the capture's objective and z, small enough
    to reconstruct several times inside a unit test."""
    setup = config.default_setup("green", 5, objective="2_5x_na007",
                                  resolution_px=(16, 16), z_distance_mm=75.0,
                                  led_center_offset_mm=(0.0, 3.0))
    factor = optics.upsampling_factor(setup)
    hr_px = optics.actual_hr_pixel_size_um(setup, factor)
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    rng = np.random.default_rng(7)
    h = 16 * factor
    amp = 0.4 + 0.6 * rng.random((h, h))
    phase = 0.5 * rng.random((h, h))
    obj = amp * np.exp(1j * phase)
    stack = forward_model.simulate_lr_stack(obj, hr_px, grid, (16, 16),
                                             setup.lr_pixel_size_um,
                                             setup.objective.na, setup.wavelength_um)
    center = (grid[0]["row"], grid[0]["col"])
    return dict(setup=setup, factor=factor, hr_px=hr_px, grid=grid, obj=obj,
                stack=stack, center=center)


# --------------------------------------------------------------- fold logic ---

def test_folds_partition_every_led_except_the_init_led(cvc):
    keys = {(r, c) for r in range(12, 25) for c in range(9, 22)}
    holds = [cvc.heldout_keys(keys, fold=f) for f in range(cvc.N_FOLDS)]
    union = set().union(*holds)
    assert union == keys - {cvc.INIT_LED}
    assert sum(len(h) for h in holds) == len(union), "folds must be disjoint"
    assert all(cvc.INIT_LED not in h for h in holds)
    # 169 LEDs minus the init LED, split four ways
    assert sorted(len(h) for h in holds) == [41, 42, 42, 43]


def test_fold_1_reproduces_decembers_hardcoded_rule(cvc):
    keys = {(r, c) for r in range(13, 22) for c in range(11, 20)}
    december = {k for i, k in enumerate(sorted(keys)) if i % 4 == 1 and k != (17, 15)}
    assert cvc.heldout_keys(keys, fold=cvc.DECEMBER_FOLD) == december
    assert cvc.DECEMBER_FOLD == 1


def test_fold_index_out_of_range_is_rejected(cvc):
    keys = {(1, 1), (1, 2), (1, 3), (1, 4), (1, 5)}
    for bad in (-1, 4, 99):
        with pytest.raises(ValueError):
            cvc.heldout_keys(keys, fold=bad)


def test_init_led_is_the_grid_entry_the_solver_initializes_from(cvc):
    """`reconstruction.initial_hr_guess` uses led_grid[0]; with the measured
    centre offset (0, 3) mm both bright-field LEDs sit 3 mm off axis and the tie
    breaks row-major, so grid[0] is (17, 15) -- which is what INIT_LED pins."""
    setup = cvc.green_setup()
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    assert (grid[0]["row"], grid[0]["col"]) == cvc.INIT_LED
    assert grid[0]["radial_mm"] == pytest.approx(3.0)
    assert grid[1]["radial_mm"] == pytest.approx(3.0)


# ------------------------------------------------------------ residual metric ---

def test_residual_is_zero_on_the_ground_truth_object(cvc, tiny):
    r = cvc.per_led_amplitude_residual(tiny["obj"], tiny["grid"], tiny["stack"],
                                        tiny["hr_px"], tiny["setup"].lr_pixel_size_um,
                                        tiny["setup"].objective.na,
                                        tiny["setup"].wavelength_um)
    assert len(r) == len(tiny["stack"])
    assert max(r.values()) < 1e-10


def test_residual_is_large_on_a_wrong_object(cvc, tiny):
    r = cvc.per_led_amplitude_residual(np.ones_like(tiny["obj"]), tiny["grid"],
                                        tiny["stack"], tiny["hr_px"],
                                        tiny["setup"].lr_pixel_size_um,
                                        tiny["setup"].objective.na,
                                        tiny["setup"].wavelength_um)
    assert np.mean(list(r.values())) > 0.1


def test_residual_only_scores_leds_that_have_an_image(cvc, tiny):
    partial = {k: v for k, v in tiny["stack"].items() if k != tiny["center"]}
    keys = set(partial) | {tiny["center"]}
    r = cvc.per_led_amplitude_residual(tiny["obj"], tiny["grid"], partial,
                                        tiny["hr_px"], tiny["setup"].lr_pixel_size_um,
                                        tiny["setup"].objective.na,
                                        tiny["setup"].wavelength_um)
    assert set(r) == set(partial) and set(r) != keys


# --------------------------------------------------------------- no leakage ---

def test_heldout_images_never_reach_the_solver(cvc, tiny):
    """The whole point of the protocol: corrupting the held-out images must not
    change the reconstruction by a single bit -- only their score."""
    kw = dict(hr_pixel_um=tiny["hr_px"], lr_pixel_um=tiny["setup"].lr_pixel_size_um,
              na=tiny["setup"].objective.na, wavelength_um=tiny["setup"].wavelength_um,
              factor=tiny["factor"], fold=1, iterations=4,
              always_in=tiny["center"], return_object=True)
    clean = cvc.cv_run(tiny["stack"], tiny["grid"], **kw)
    hold = set(map(tuple, clean["heldout_leds"]))
    assert hold and tiny["center"] not in hold
    poisoned = {k: (v * 1e6 if k in hold else v) for k, v in tiny["stack"].items()}
    dirty = cvc.cv_run(poisoned, tiny["grid"], **kw)
    assert np.array_equal(clean["object"], dirty["object"])
    assert dirty["heldout_res"] != pytest.approx(clean["heldout_res"])
    assert dirty["train_res"] == pytest.approx(clean["train_res"])


def test_cv_run_pins_the_mandatory_solver_settings(cvc, tiny):
    out = cvc.cv_run(tiny["stack"], tiny["grid"], hr_pixel_um=tiny["hr_px"],
                      lr_pixel_um=tiny["setup"].lr_pixel_size_um,
                      na=tiny["setup"].objective.na,
                      wavelength_um=tiny["setup"].wavelength_um,
                      factor=tiny["factor"], fold=0, iterations=2,
                      always_in=tiny["center"])
    assert out["recon_kw"]["step_relative"] == 0.3
    assert out["recon_kw"]["normalize_initial_guess"] is True
    assert out["n_train"] + out["n_heldout"] == len(tiny["stack"])


def test_cv_all_folds_reports_the_spread_criterion_2_needs(cvc, tiny):
    out = cvc.cv_all_folds(tiny["stack"], tiny["grid"], tiny["hr_px"],
                            tiny["setup"].lr_pixel_size_um, tiny["setup"].objective.na,
                            tiny["setup"].wavelength_um, tiny["factor"],
                            iterations=2, always_in=tiny["center"])
    assert out["n_folds"] == 4 and len(out["folds"]) == 4
    assert out["heldout_res_min"] <= out["heldout_res_mean"] <= out["heldout_res_max"]
    assert out["heldout_res_std"] >= 0.0


# ------------------------------------------------------------------ geometry ---

def test_rotation_by_zero_is_bit_identical_to_build_led_grid(cvc):
    setup = cvc.green_setup()
    assert cvc.led_grid_rotated(setup, 0.0) == led_array.build_led_grid(
        setup.led_array, setup.wavelength_um)


def test_rotation_is_rigid_and_reversible(cvc):
    setup = cvc.green_setup(offset_mm=(0.0, 0.0))
    base = cvc.led_grid_rotated(setup, 0.0)
    rot = cvc.led_grid_rotated(setup, 90.0)
    # a 90 deg rotation of a square array centred on the axis permutes it
    key = lambda g: sorted((round(e["fx"], 12), round(e["fy"], 12)) for e in g)
    assert key(rot) == key(base)
    # radii preserved LED by LED, at an angle that is not a symmetry
    r37 = {(e["row"], e["col"]): e["radial_mm"] for e in cvc.led_grid_rotated(setup, 37.0)}
    r0 = {(e["row"], e["col"]): e["radial_mm"] for e in base}
    assert max(abs(r37[k] - r0[k]) for k in r0) < 1e-9


def test_rotation_moves_leds_when_the_offset_is_nonzero(cvc):
    setup = cvc.green_setup()
    base = {(e["row"], e["col"]): (e["fx"], e["fy"]) for e in cvc.led_grid_rotated(setup, 0.0)}
    rot = {(e["row"], e["col"]): (e["fx"], e["fy"]) for e in cvc.led_grid_rotated(setup, 3.0)}
    moved = max(np.hypot(rot[k][0] - base[k][0], rot[k][1] - base[k][1]) for k in base)
    assert moved > 1e-4


def test_scrambled_grid_permutes_frequencies_but_pins_the_init_led(cvc):
    setup = cvc.green_setup()
    base = cvc.led_grid_rotated(setup, 0.0)
    scr = cvc.scrambled_led_grid(base, seed=0)
    assert [(e["row"], e["col"]) for e in scr] == [(e["row"], e["col"]) for e in base]
    assert (sorted((e["fx"], e["fy"]) for e in scr)
            == sorted((e["fx"], e["fy"]) for e in base))
    b0 = next(e for e in base if (e["row"], e["col"]) == cvc.INIT_LED)
    s0 = next(e for e in scr if (e["row"], e["col"]) == cvc.INIT_LED)
    assert (s0["fx"], s0["fy"]) == (b0["fx"], b0["fy"])
    assert any((e["fx"], e["fy"]) != (b["fx"], b["fy"]) for e, b in zip(scr, base))


# -------------------------------------------------------------- lattice score ---

def test_lattice_score_fires_on_a_periodic_pattern_and_not_on_noise(cvc):
    n = 128
    yy, xx = np.mgrid[:n, :n]
    periodic = np.exp(1j * 0.0) * (1.0 + 0.3 * np.cos(2 * np.pi * 8 * xx / n))
    rng = np.random.default_rng(3)
    noise = 1.0 + 0.3 * rng.standard_normal((n, n))
    assert cvc.lattice_score(periodic.astype(complex)) > 0.5
    assert cvc.lattice_score(noise.astype(complex)) < 0.01


def test_lattice_score_is_nan_on_a_perfectly_flat_amplitude(cvc):
    """Known limitation of the score as copied verbatim from
    synth_overlap/run.py: it normalizes by the total out-of-band energy of
    |o| - mean|o|, which is exactly zero for a flat amplitude, so it returns
    nan rather than 0. It matters for the T1 phantoms, which are PURE PHASE
    (|truth| == 1): their `lattice_score_truth` is only finite because of
    floating-point residue, and must not be read as a meaningful zero. The
    score is trustworthy on reconstructions, which always carry amplitude
    structure. Pinned, not fixed -- changing the function would break
    comparability with synth_overlap/summary.json."""
    assert np.isnan(cvc.lattice_score(np.ones((128, 128), dtype=complex)))

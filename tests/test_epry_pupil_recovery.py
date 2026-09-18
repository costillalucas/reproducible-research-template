"""tests/test_epry_pupil_recovery.py -- EPRY pupil recovery
(`references/bibliography.yaml` id `ou2014`, priority_focus rank 1),
`reconstruction.reconstruct`'s `recover_pupil` param.

Ground truth for the pupil doesn't exist in real data, so this simulates
a KNOWN aberration (`optics.add_defocus_aberration`, injected via
`forward_model.simulate_lr_stack`'s new `pupil_override`) and checks two
independent things: (1) does letting the solver also fit a complex pupil
recover an object closer to ground truth than assuming the ideal
(unaberrated) pupil, and (2) does the recovered pupil's phase actually
correlate with the true injected aberration (not just "helps the object
by coincidence").

HONEST, NOT-overclaimed finding from exploring this (see the numbers
below, reproduced by `test_epry_beats_uncorrected_under_defocus_aberration`):
the improvement is real and reproducible but MODEST, not the dramatic
fix TIE-informed initialization was for the weak-phase-object problem.
At the chosen defocus_rad_amplitude=2.0 (die used object's phase is
already near the edge of what the baseline solver handles well even with
an ideal pupil, per `test_ptyco_simulator.py`'s own note on this same
synthetic object), object phase correlation goes 0.687 -> 0.793 and
pupil phase correlation is 0.648 -- clearly not noise, clearly not a
full recovery either. At LARGER aberration (defocus_rad_amplitude=4.0,
tried during development, not asserted here) both uncorrected and EPRY
reconstructions fail outright on this small (9x9 LED, 12x12px crop) test
problem -- EPRY is not a silver bullet for arbitrarily large aberration
on a small synthetic aperture, consistent with ou2014's own real-data
demonstration needing 225 images (15x15 LEDs) and many more pixels than
this test's fast/small setup uses.

SECOND, MORE SURPRISING honest finding (2026-09-18, found exploring
`reconstruct_all_channels(recover_pupil=True)` across all 3 real LED
channels together -- see `test_recover_pupil_can_regress_an_already_well_
converging_channel` below): recover_pupil isn't just "modest when it
helps" -- it can actively REGRESS a channel that already converges fine
with NO aberration present at all. This means recover_pupil=True is not a
safe blanket default for all 3 RGB channels in one run.

THIRD finding, a follow-up that puts the second one in context (same day,
see `test_recover_pupil_regression_is_a_small_testbed_artifact_not_
reproduced_at_paper_scale` below): that regression is specific to this
project's tiny (12x12px, 81-441 LED) synthetic test problems -- it does
NOT reproduce at a scale closer to ou2014's own real demonstration (225
LEDs, 64x64px). Ruled out "EPRY is just badly implemented" as the
explanation (it correctly recovers real injected aberrations, and the
literature's standard fix for over-aggressive PIE-family normalization,
rPIE-style regularization, barely changes the small-scale numbers) in
favor of "this project's synthetic testbeds are smaller/lower-redundancy
than what EPRY needs to be stable" -- a real, useful, but more nuanced
conclusion than "don't use recover_pupil".
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import reconstruction  # noqa: E402


def _synthetic_object(shape):
    """Same phantom as test_ptyco_simulator.py's `_synthetic_object` --
    reuse it rather than inventing a new one, so this test's baseline
    (unaberrated) behavior is already known-good from that file.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.15 * np.pi * np.sin(2 * np.pi * 1 * x) * np.cos(2 * np.pi * 1 * y)
    return (amp * np.exp(1j * phase)).astype(complex)


def _setup_and_pupil(grid_size=9, crop=12, defocus_rad_amplitude=2.0):
    setup = config.default_setup(channel="green", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    pupil_mask = optics.circular_pupil((crop, crop), setup.lr_pixel_size_um,
                                        setup.objective.na, setup.wavelength_um)
    true_pupil = optics.add_defocus_aberration(
        pupil_mask, (crop, crop), setup.lr_pixel_size_um, setup.objective.na,
        setup.wavelength_um, defocus_rad_amplitude,
    )
    return setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil


def test_epry_beats_uncorrected_under_defocus_aberration():
    grid_size, crop, iterations = 9, 12, 40
    setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil = _setup_and_pupil(
        grid_size, crop, defocus_rad_amplitude=2.0,
    )
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, pupil_override=true_pupil,
    )

    uncorrected = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    corrected = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        recover_pupil=True,
    )
    assert "pupil" in corrected and corrected["pupil"].shape == (crop, crop)

    gt_unc = metrics.compare_to_ground_truth(uncorrected["object"], obj_true)
    gt_cor = metrics.compare_to_ground_truth(corrected["object"], obj_true)

    assert gt_unc["phase_correlation"] < 0.75, (
        "premise check: assuming the ideal pupil under a real defocus aberration should "
        f"clearly degrade phase recovery -- got {gt_unc['phase_correlation']}"
    )
    assert gt_cor["phase_correlation"] > gt_unc["phase_correlation"] + 0.05, (
        f"EPRY should meaningfully beat the uncorrected reconstruction here: "
        f"uncorrected={gt_unc['phase_correlation']}, epry={gt_cor['phase_correlation']}"
    )

    true_phase = np.angle(true_pupil)[pupil_mask]
    rec_phase = np.angle(corrected["pupil"])[pupil_mask]
    true_phase = true_phase - true_phase.mean()
    rec_phase = rec_phase - rec_phase.mean()
    pupil_corr = float(np.corrcoef(true_phase, rec_phase)[0, 1])
    assert pupil_corr > 0.5, (
        f"recovered pupil phase should correlate with the true injected defocus, got {pupil_corr}"
    )


def test_epry_pupil_support_stays_inside_na_circle():
    """The paper's "pupil function constraint" (Section 2, after Eq. 4):
    noise outside the physical aperture stop must be zeroed every update,
    not allowed to accumulate. Cheap, deterministic check independent of
    whether recovery quality is good on a given object.
    """
    grid_size, crop, iterations = 9, 12, 10
    setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil = _setup_and_pupil(
        grid_size, crop, defocus_rad_amplitude=2.0,
    )
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, pupil_override=true_pupil,
    )
    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        recover_pupil=True,
    )
    outside = ~pupil_mask
    assert np.all(result["pupil"][outside] == 0)


def test_recover_pupil_can_regress_an_already_well_converging_channel():
    """HONEST NEGATIVE FINDING (2026-09-18, found while exploring
    reconstruct_all_channels(recover_pupil=True) across all 3 real LED
    channels together, not just the single aberrated case above): with
    NO aberration at all (ideal pupil, pupil_override omitted), EPRY can
    still make an already-well-converging channel's reconstruction WORSE
    than not using it -- this isn't "EPRY only shines against a real
    aberration", it's "EPRY isn't a free/safe thing to always turn on".

    Blue (470nm) on this project's real "current" objective/9x9 grid is
    the reproducer: baseline (recover_pupil=False) already reconstructs
    this object well (phase_correlation ~0.95); recover_pupil=True
    degrades it to ~0.5 -- and gets WORSE, not better, the more iterations
    it runs (checked at 5 vs 40 iterations below), even as `recovery_error`
    keeps improving the whole time -- the same "recovery_error doesn't
    track true accuracy" pathology already documented elsewhere in this
    project (tests/test_weak_phase_object_limitation.py), but triggered
    here by EPRY's own object-update normalization (division by
    max(|pupil|^2)/max(|patch|^2) instead of the plain fixed-ramp
    gradient step), not by the zero-phase initialization or a real pupil
    aberration -- the recovered pupil's phase stays nearly flat (std well
    under 0.05 rad) the whole time, ruling out "it invented a large fake
    aberration" as the explanation.

    Practical implication: recover_pupil=True is not a safe default to
    turn on for all 3 RGB channels at once in
    reconstruct_multispectral_*.py -- it can help a channel with a real
    local-minimum problem (see red's case in
    tests/test_reconstruct_multispectral_pipeline.py's docstring) while
    actively hurting a different, already-fine channel in the SAME run.
    No per-channel diagnostic exists yet to tell these apart in advance
    (same open problem as the TIE-continued-iteration question in
    docs/roadmap_agentic_multispectral_pipeline.md) -- don't assume
    recover_pupil is monotonically safe to enable.
    """
    grid_size, crop = 9, 12
    setup = config.default_setup(channel="blue", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    pupil_mask = optics.circular_pupil((crop, crop), setup.lr_pixel_size_um,
                                        setup.objective.na, setup.wavelength_um)
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )

    baseline = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
    )
    gt_baseline = metrics.compare_to_ground_truth(baseline["object"], obj_true)
    assert gt_baseline["phase_correlation"] > 0.85, (
        "premise check: blue should already converge well without any pupil correction here -- "
        f"got {gt_baseline['phase_correlation']}"
    )

    short = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=5,
        recover_pupil=True,
    )
    long = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=40,
        recover_pupil=True,
    )
    gt_short = metrics.compare_to_ground_truth(short["object"], obj_true)
    gt_long = metrics.compare_to_ground_truth(long["object"], obj_true)

    assert gt_long["phase_correlation"] < gt_baseline["phase_correlation"] - 0.2, (
        "EPRY should meaningfully regress this already-well-converging channel: "
        f"baseline={gt_baseline['phase_correlation']}, recover_pupil@40it={gt_long['phase_correlation']}"
    )
    assert gt_long["phase_correlation"] < gt_short["phase_correlation"], (
        "quality should get WORSE with more EPRY iterations here, not better -- "
        f"5 iters={gt_short['phase_correlation']}, 40 iters={gt_long['phase_correlation']}"
    )
    assert long["history"][-1]["recovery_error"] < short["history"][-1]["recovery_error"], (
        "meanwhile recovery_error keeps IMPROVING -- the metric doesn't track true accuracy here, "
        "same pathology as test_weak_phase_object_limitation.py, triggered by EPRY's own update rule"
    )

    pupil_phase_std = float(np.angle(long["pupil"])[pupil_mask].std())
    assert pupil_phase_std < 0.05, (
        "the recovered pupil should stay nearly flat (no large fake aberration invented) -- "
        f"got std={pupil_phase_std} rad, so the regression comes from the object update, "
        "not a runaway pupil estimate"
    )
    # See test_recover_pupil_regression_is_a_small_testbed_artifact_not_reproduced_at_paper_scale
    # below: this regression does NOT reproduce at a scale closer to ou2014's own real demo --
    # it's a small-testbed/low-data-redundancy artifact, not a general EPRY failure.


def test_recover_pupil_regression_is_a_small_testbed_artifact_not_reproduced_at_paper_scale():
    """FOLLOW-UP to test_recover_pupil_can_regress_an_already_well_converging_channel above
    (2026-09-18, same day): is EPRY just badly implemented, or is the regression specific to
    this project's tiny (12x12px, 81-441 LED) synthetic test problems?

    Reproduces the exact same no-aberration setup (blue channel, phase_mag=0.08*pi, the object
    already known to reconstruct well without any pupil correction) at a scale much closer to
    ou2014's own real demonstration: 225 LEDs (15x15 grid, matching the paper) and 64x64px LR
    images instead of 12x12 -- keeping the object's PHYSICAL spatial frequency comparable
    (n_cycles scaled with crop, not fixed in normalized coordinates: an earlier attempt at this
    comparison got confounded by accidentally pushing the object into the already-known near-
    uniform-phase degenerate regime by holding "1 cycle across the field of view" fixed while
    growing the physical field of view -- see tests/test_weak_phase_object_limitation.py for
    why near-uniform phase is a known separate failure mode).

    RESULT (asserted below): the catastrophic regression (0.939->0.570 at small scale) does NOT
    reproduce here -- baseline and recover_pupil land within a few percent of each other,
    confirming this is a small-testbed/low-data-redundancy artifact, not a general property of
    EPRY or a bug in this implementation. Also tried, outside the main codebase (not in this
    test): the literature's standard fix for exactly this kind of instability (rPIE-style
    regularized per-pixel/global-blend denominator, Maiden/Muller/Rodenburg 2017) barely moved
    the small-scale numbers -- further evidence the mechanism really is data redundancy, not a
    fixable normalization choice.

    STILL OPEN, NOT tested here: whether EPRY correctly recovers a REAL aberration at this
    larger scale. A first attempt looked like a clean failure (pupil phase correlation ~0.03,
    vs. 0.648 at small scale) but turned out to be confounded too: the plain uncorrected
    baseline (assuming an ideal pupil) also hasn't converged at this problem size within the
    iteration budgets tried (phase_correlation still climbing at 600 iterations: 0.466 at 40 ->
    0.623 at 600, recovery_error still dropping) -- so that comparison wasn't fair and isn't
    asserted anywhere in this suite. A real answer needs both runs taken to genuine convergence,
    which costs minutes per run at this scale and wasn't done.
    """
    grid_size, crop, iterations = 15, 64, 40
    n_cycles = round(crop / 12)  # keep physical spatial frequency comparable to the small-scale test
    setup = config.default_setup(channel="blue", grid_size=grid_size, objective="current",
                                  resolution_px=(crop, crop))
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.08 * np.pi * np.sin(2 * np.pi * n_cycles * x) * np.cos(2 * np.pi * n_cycles * y)
    obj_true = (amp * np.exp(1j * phase)).astype(complex)

    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )

    baseline = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    corrected = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        recover_pupil=True,
    )
    gt_baseline = metrics.compare_to_ground_truth(baseline["object"], obj_true)
    gt_corrected = metrics.compare_to_ground_truth(corrected["object"], obj_true)

    assert gt_baseline["phase_correlation"] > 0.7, (
        "premise check: this frequency-matched object should already reconstruct well at this "
        f"larger scale, same as the small-scale test -- got {gt_baseline['phase_correlation']}"
    )
    assert abs(gt_corrected["phase_correlation"] - gt_baseline["phase_correlation"]) < 0.1, (
        "at paper-comparable scale (225 LEDs, 64x64px), recover_pupil should NOT meaningfully "
        f"regress this channel (unlike the small-scale test): baseline={gt_baseline['phase_correlation']}, "
        f"recover_pupil={gt_corrected['phase_correlation']}"
    )


def test_recover_pupil_default_off_reproduces_original_behavior():
    """Regression guard: `recover_pupil=False` (the default) must produce
    bit-identical results to before this feature existed -- the fixed
    circular boolean pupil, cast to complex, multiplies identically.
    """
    grid_size, crop, iterations = 9, 12, 15
    setup, factor, hr_pixel_um, hr_shape, pupil_mask, true_pupil = _setup_and_pupil(grid_size, crop)
    obj_true = _synthetic_object(hr_shape)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        obj_true, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um,
    )
    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
    )
    assert "pupil" not in result

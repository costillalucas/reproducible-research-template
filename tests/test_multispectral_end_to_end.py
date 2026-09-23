"""tests/test_multispectral_end_to_end.py -- roadmap milestone 2 full
integration (docs/roadmap_agentic_multispectral_pipeline.md): wires
milestone 1 (shared HR grid) -> 2a (independent per-channel reconstruction)
-> 2b.i (piston removal + synthetic-wavelength unwrapping) -> 2b.ii
(Cauchy dispersion fit) together on ONE shared synthetic sample, instead
of each stage's own isolated synthetic test object.

Two tests, two different jobs -- do not conflate them:

- `test_full_pipeline_through_real_reconstruction_recovers_thickness_shape`
  runs the ACTUAL forward_model + reconstruction.py Wirtinger flow solver
  (not injected/simulated phase) end to end. It proves the software wiring
  is correct and recovers the right SHAPE of the thickness field, but its
  threshold is deliberately loose: getting here required a lot of manual
  tuning of the test object (see the comment above `_build_test_object`)
  because of a real solver limitation found in the process (see that
  comment) -- this test is evidence the pipeline runs, not a claim that
  today's baseline solver is production-ready for real dispersion
  measurements.

- `test_unwrapping_beats_naive_phase_on_a_large_dispersion_signal` isolates
  2b.i/2b.ii's VALUE PROPOSITION (does unwrapping+dispersion-fit recover
  the sample better than naively treating each channel's raw wrapped phase
  as already-unwrapped OPL) using DIRECTLY INJECTED synthetic phase, not
  the real solver -- deliberately, because the real solver cannot yet
  reconstruct phase objects large enough to need unwrapping at all (see
  that test's docstring). This tests 2b.i/2b.ii's logic on its own merits,
  decoupled from reconstruction.py's current limitations.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ptyco_full_simulator import config, forward_model, led_array, optics, reconstruction  # noqa: E402
from ptyco_full_simulator import multispectral as ms  # noqa: E402

A_TRUE = 1.34
B_TRUE = 0.004
WAVELENGTHS_UM = {ch: config.CHANNEL_WAVELENGTH_NM[ch] / 1000.0 for ch in ("red", "green", "blue")}


def _build_test_object(hr_shape, background_rows):
    """The amplitude/thickness combination this test actually uses, and
    why it looks like this (found through direct experimentation, not
    picked arbitrarily):

    1. UNIFORM amplitude (a pure phase object) makes this solver fail
       almost completely even at tiny phase magnitudes (phase_correlation
       went NEGATIVE, i.e. worse than noise) -- `initial_hr_guess`
       (reconstruction.py) bootstraps from the on-axis LED's amplitude
       image, which carries no spatial structure at all for a uniform
       object, starving the solver of the amplitude contrast it needs to
       localize phase corrections. Just 5-10% amplitude contrast recovers
       most of the achievable quality. THIS IS A REAL, PREVIOUSLY
       UNDOCUMENTED LIMITATION, separate from the phase-magnitude one
       milestone 2a already found -- and it matters a lot for this
       project's actual target (near-transparent biological samples,
       which are often close to phase-only). Reused here: the same
       amplitude phantom already validated in
       tests/test_ptyco_simulator.py / test_multispectral_registration.py.
    2. A smooth, LOW-spatial-frequency thickness bump (the physically
       "natural" shape for a sample thickness map) converged far worse
       than an OSCILLATING pattern of the same magnitude -- so the
       thickness field here reuses the sin*cos oscillation shape from
       those same known-good tests, tapered to ~0 in `background_rows` so
       there's a real bare-medium region for `reference_phase_to_background`.
    """
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5

    amp = 0.4 + 0.6 * np.exp(-((xc - 0.1) ** 2 + (yc + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((xc + 0.15) ** 2 + (yc - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)

    ramp = np.clip((y - background_rows) / 4.0, 0, 1)
    t_true = 0.012 * np.sin(2 * np.pi * xc) * np.cos(2 * np.pi * yc) * ramp
    t_true -= t_true.min()  # keep >= 0 -- an OPL sign doesn't need physical meaning for this test
    return amp, t_true


def test_full_pipeline_through_real_reconstruction_recovers_thickness_shape():
    grid_size, crop, iterations = 9, 16, 40
    background_rows = 4

    setups = {ch: config.default_setup(channel=ch, grid_size=grid_size, objective="2_5x_na007",
                                        resolution_px=(crop, crop))
              for ch in WAVELENGTHS_UM}
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)

    amp, t_true = _build_test_object(hr_shape, background_rows)

    phases_wrapped = {}
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        setup = setups[channel]
        opl_true = (A_TRUE + B_TRUE / wavelength_um**2) * t_true
        phase_true = 2 * np.pi / wavelength_um * opl_true
        obj = amp * np.exp(1j * phase_true)

        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            obj, hr_pixel_um, led_grid, (crop, crop),
            setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
        )
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        )
        phases_wrapped[channel] = np.angle(result["object"])

    background_mask = np.zeros(hr_shape, dtype=bool)
    background_mask[:background_rows, :] = True

    coupled = ms.couple_rgb_channels(phases_wrapped, WAVELENGTHS_UM, background_mask,
                                      baseline_index_A=A_TRUE)
    t_estimate = coupled["resolved"]["thickness_um"]

    assert t_estimate.shape == hr_shape
    correlation = float(np.corrcoef(t_estimate.ravel(), t_true.ravel())[0, 1])
    assert correlation > 0.5, (
        f"thickness shape correlation {correlation} -- if this regresses, check whether it's the "
        "known blue-channel convergence weakness (see this file's module docstring and "
        "docs/roadmap_agentic_multispectral_pipeline.md) getting worse, not necessarily a new bug"
    )


def test_unwrapping_beats_naive_phase_on_a_large_dispersion_signal():
    """`couple_rgb_channels` (proper unwrap + dispersion fit) vs. a naive
    baseline that treats each channel's raw wrapped phase as if it were
    already the true OPL (i.e. assumes wrap number 0 everywhere -- what
    you'd get by skipping milestone 2b.i entirely). Uses phase magnitude
    large enough to need real unwrapping (multiple 2*pi wraps) -- injected
    directly rather than run through reconstruction.py, because today's
    solver cannot reconstruct an object with this much phase excursion
    (see test_reconstruct_multispectral_pipeline.py and this project's
    other local-minimum findings) -- this test isolates whether 2b.i/2b.ii
    are WORTH having, independent of when the solver can supply real input
    this large. Noise level (0.02 rad std) is set a bit above what small
    real reconstructions in this test suite typically show (~0.03 rad, see
    reconstruction.py's own docstring finding), a reasonable stand-in.
    """
    shape = (50, 50)
    half_range = ms.unambiguous_opl_half_range(WAVELENGTHS_UM["red"], WAVELENGTHS_UM["green"])
    x = np.linspace(-1, 1, shape[1])
    t_true = np.tile(x, (shape[0], 1)) * (0.8 * half_range) / A_TRUE  # OPL stays within the unambiguous range

    background_mask = np.zeros(shape, dtype=bool)
    background_mask[:5, :] = True
    t_true[background_mask] = 0.0

    rng = np.random.default_rng(2)
    piston_by_channel = {"red": 1.1, "green": -0.6, "blue": 2.3}  # distinct, non-2*pi-multiple pistons
    phases_wrapped, opl_true_by_channel = {}, {}
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        opl_true = (A_TRUE + B_TRUE / wavelength_um**2) * t_true
        opl_true_by_channel[channel] = opl_true
        phase_true = 2 * np.pi / wavelength_um * opl_true
        noisy = phase_true + rng.normal(0, 0.02, shape) + piston_by_channel[channel]
        phases_wrapped[channel] = ms.wrap_phase(noisy)

    coupled = ms.couple_rgb_channels(phases_wrapped, WAVELENGTHS_UM, background_mask,
                                      baseline_index_A=A_TRUE)
    t_coupled = coupled["resolved"]["thickness_um"]

    # Naive baseline: reference to background (same piston-removal courtesy -- this isn't
    # what 2b.i/2b.ii is being tested for) but skip the wrap-number search entirely (k=0).
    naive_opls = []
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        referenced = ms.reference_phase_to_background(phases_wrapped[channel], background_mask)
        naive_opls.append(referenced * wavelength_um / (2 * np.pi))
    naive_fit = ms.fit_cauchy_dispersion(list(WAVELENGTHS_UM.values()), naive_opls)
    t_naive = ms.resolve_thickness_and_dispersion(naive_fit["C"], naive_fit["D"], A_TRUE)["thickness_um"]

    err_coupled = float(np.sqrt(np.mean((t_coupled - t_true) ** 2)))
    err_naive = float(np.sqrt(np.mean((t_naive - t_true) ** 2)))

    assert np.abs(t_true).max() > WAVELENGTHS_UM["blue"] / 2 / A_TRUE, (
        "test object should require unwrapping (exceed at least one channel's own range) "
        "for this comparison to mean anything"
    )
    assert err_coupled < err_naive, (err_coupled, err_naive)
    assert err_coupled < 0.05 * err_naive, (
        "expected unwrapping to be dramatically better here, not just marginally -- "
        f"coupled={err_coupled}, naive={err_naive}"
    )

"""tests/test_multispectral_unwrapping.py -- roadmap milestone 2b.i
(docs/roadmap_agentic_multispectral_pipeline.md): multi-wavelength phase
unwrapping via a synthetic wavelength, adapted from `shen2025`
(src/ptyco_full_simulator/multispectral.py -- see its module docstring for
the transmissive-vs-reflective adaptation).

No real reconstructed phases at two wavelengths are available in this
Codespace, so these tests build a known OPL field directly (skipping the
FPM forward/inverse problem entirely -- that's already covered by
tests/test_ptyco_simulator.py and test_reconstruct_multispectral_pipeline.py)
and check the unwrapping math against it.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import multispectral as ms  # noqa: E402

LAMBDA_RED_UM = 0.630
LAMBDA_GREEN_UM = 0.530


def _opl_ramp(shape, magnitude_um):
    """A smooth OPL field spanning [-magnitude_um, +magnitude_um] --
    smooth so `refine_opl_tv`'s TV term has something meaningful to do,
    and wide enough to require several different wrap numbers across the
    field, not just k=0.
    """
    x = np.linspace(-1, 1, shape[1])
    return np.tile(x, (shape[0], 1)) * magnitude_um


def test_synthetic_wavelength_matches_beat_formula():
    lam_s = ms.synthetic_wavelength(LAMBDA_RED_UM, LAMBDA_GREEN_UM)
    expected = LAMBDA_RED_UM * LAMBDA_GREEN_UM / abs(LAMBDA_RED_UM - LAMBDA_GREEN_UM)
    assert lam_s == expected
    assert lam_s > max(LAMBDA_RED_UM, LAMBDA_GREEN_UM), (
        "the synthetic wavelength must be longer than either real one -- "
        "that's the entire point, a longer effective wavelength means a "
        "wider unambiguous range"
    )


def test_search_wrap_numbers_recovers_opl_beyond_either_channels_own_range():
    """The whole reason to do this at all: a single channel alone can only
    resolve OPL within +/- wavelength_um/2 (one wrap period). Build a
    field that exceeds RED's own unambiguous range (+/-0.315um) by several
    times, and confirm the two-channel search recovers it exactly
    (noiseless) -- with a nonzero wrap number on at least one channel,
    proving actual unwrapping happened, not just a lucky k=0 guess.
    """
    half_range = ms.unambiguous_opl_half_range(LAMBDA_RED_UM, LAMBDA_GREEN_UM)
    opl_true = _opl_ramp((40, 40), magnitude_um=0.9 * half_range)
    assert np.abs(opl_true).max() > LAMBDA_RED_UM / 2, "test object should exceed red's own single-channel range"

    phase_red = ms.wrap_phase(2 * np.pi / LAMBDA_RED_UM * opl_true)
    phase_green = ms.wrap_phase(2 * np.pi / LAMBDA_GREEN_UM * opl_true)

    result = ms.search_wrap_numbers(phase_red, phase_green, LAMBDA_RED_UM, LAMBDA_GREEN_UM,
                                     k_range=range(-6, 7))

    assert np.abs(result["opl_estimate"] - opl_true).max() < 1e-6
    assert np.any(result["K1"] != 0) or np.any(result["K2"] != 0)


def test_search_wrap_numbers_fails_when_k_range_too_narrow():
    """Negative control, same style as tests/test_ptyco_simulator.py's
    single-LED case: the SAME object as the passing test above, through
    the SAME search function, but with a k_range too narrow to contain the
    wrap numbers actually needed -- proving the test setup is capable of
    catching a broken unwrap, not just praising a working one.
    """
    half_range = ms.unambiguous_opl_half_range(LAMBDA_RED_UM, LAMBDA_GREEN_UM)
    opl_true = _opl_ramp((40, 40), magnitude_um=0.9 * half_range)
    phase_red = ms.wrap_phase(2 * np.pi / LAMBDA_RED_UM * opl_true)
    phase_green = ms.wrap_phase(2 * np.pi / LAMBDA_GREEN_UM * opl_true)

    result = ms.search_wrap_numbers(phase_red, phase_green, LAMBDA_RED_UM, LAMBDA_GREEN_UM,
                                     k_range=range(-1, 2))

    assert np.abs(result["opl_estimate"] - opl_true).max() > 0.1, (
        "a too-narrow k_range should NOT be able to recover the true OPL"
    )


def test_search_is_robust_to_small_phase_noise():
    """Realistic FPM reconstructions have some phase noise. Within the
    unambiguous range and with a k_range wide enough to not itself be the
    limiting factor, most pixels should still land on the correct wrap
    pair despite modest (0.05 rad) per-channel phase noise -- a few pixels
    near a wrap boundary flipping to a neighboring (k1, k2) is expected
    and fine, judged here by the MEDIAN error, not the max (see module
    docstring: cross-wavelength consistency, not raw phase differencing,
    is what makes this robust at all).
    """
    half_range = ms.unambiguous_opl_half_range(LAMBDA_RED_UM, LAMBDA_GREEN_UM)
    opl_true = _opl_ramp((60, 60), magnitude_um=0.9 * half_range)
    phase_red = ms.wrap_phase(2 * np.pi / LAMBDA_RED_UM * opl_true)
    phase_green = ms.wrap_phase(2 * np.pi / LAMBDA_GREEN_UM * opl_true)

    rng = np.random.default_rng(0)
    noisy_red = phase_red + rng.normal(0, 0.05, phase_red.shape)
    noisy_green = phase_green + rng.normal(0, 0.05, phase_green.shape)

    result = ms.search_wrap_numbers(noisy_red, noisy_green, LAMBDA_RED_UM, LAMBDA_GREEN_UM,
                                     k_range=range(-6, 7))
    median_err_um = float(np.median(np.abs(result["opl_estimate"] - opl_true)))
    assert median_err_um < 0.01, median_err_um


def test_refine_opl_tv_reduces_total_variation_of_a_noisy_estimate():
    """`refine_opl_tv` is a simplified stand-in for the paper's convex
    solver (module docstring) -- this only checks its basic contract: it
    should smooth a noisy per-pixel estimate (lower total variation) while
    staying in the right ballpark of the true field, not that it exactly
    reproduces any particular published result.
    """
    shape = (30, 30)
    opl_true = _opl_ramp(shape, magnitude_um=0.5)
    rng = np.random.default_rng(1)
    noisy_estimate = opl_true + rng.normal(0, 0.03, shape)
    opl_min = np.minimum(opl_true, noisy_estimate) - 0.02
    opl_max = np.maximum(opl_true, noisy_estimate) + 0.02

    refined = ms.refine_opl_tv(noisy_estimate, opl_min, opl_max, iterations=200)

    def total_variation(field):
        return float(np.sum(np.abs(np.diff(field, axis=0)))
                      + np.sum(np.abs(np.diff(field, axis=1))))

    assert total_variation(refined) < total_variation(noisy_estimate)
    assert np.abs(refined - opl_true).max() < np.abs(noisy_estimate - opl_true).max() + 0.05


def test_reference_phase_to_background_removes_a_global_piston():
    """A reconstructed channel's phase is only known up to an arbitrary
    additive piston (see `reference_phase_to_background`'s docstring --
    found while building the full 2a->2b.i->2b.ii integration). Given a
    region known to be bare medium (true OPL 0), subtracting its mean
    phase should recover the true (piston-free) field, up to wrapping.
    """
    shape = (30, 30)
    true_phase = _opl_ramp(shape, magnitude_um=1.0)  # reuse as a generic smooth field, not literal OPL here
    background_mask = np.zeros(shape, dtype=bool)
    background_mask[:5, :] = True  # a strip where the true field is defined (not necessarily 0 -- see below)
    # Make the background strip genuinely flat/zero so it's a valid "bare medium" region.
    true_phase = true_phase - true_phase[background_mask].mean()

    piston = 1.7  # arbitrary, not a multiple of 2*pi
    observed = ms.wrap_phase(true_phase + piston)

    referenced = ms.reference_phase_to_background(observed, background_mask)

    assert np.allclose(ms.wrap_phase(referenced - true_phase), 0, atol=1e-9)


def test_reference_phase_to_background_rejects_empty_mask():
    observed = ms.wrap_phase(_opl_ramp((10, 10), magnitude_um=0.5))
    try:
        ms.reference_phase_to_background(observed, np.zeros((10, 10), dtype=bool))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for an all-False background_mask")

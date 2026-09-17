"""tests/test_dispersion_fit.py -- roadmap milestone 2b.ii
(docs/roadmap_agentic_multispectral_pipeline.md): fit the sample's
Cauchy-shaped dispersion from unwrapped multi-channel OPL
(src/ptyco_full_simulator/multispectral.py's `fit_cauchy_dispersion` /
`resolve_thickness_and_dispersion`).

No real 3-channel unwrapped OPL is available in this Codespace (this
builds directly on tests/test_multispectral_unwrapping.py's synthetic
approach: skip the FPM forward/inverse problem, construct OPL from a known
dispersion model directly, and check the fit against it).
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import multispectral as ms  # noqa: E402

WAVELENGTHS_UM = {"red": 0.630, "green": 0.530, "blue": 0.470}

A_TRUE = 1.34       # a plausible biological-sample baseline refractive index
B_TRUE = 0.004      # um^2, a plausible Cauchy dispersion coefficient
T_TRUE_UM = 0.5     # sample thickness


def _opl_from_model(wavelength_um, A=A_TRUE, B=B_TRUE, t=T_TRUE_UM):
    return (A + B / wavelength_um**2) * t


def test_fit_recovers_known_C_D_scalar():
    C_true, D_true = A_TRUE * T_TRUE_UM, B_TRUE * T_TRUE_UM
    wavelengths = list(WAVELENGTHS_UM.values())
    opls = [np.array([[_opl_from_model(w)]]) for w in wavelengths]

    fit = ms.fit_cauchy_dispersion(wavelengths, opls)

    assert fit["C"] == pytest.approx(C_true)
    assert fit["D"] == pytest.approx(D_true)
    assert np.abs(fit["residuals"]).max() < 1e-10, "noiseless 3-point Cauchy data should fit almost exactly"


def test_fit_recovers_known_C_D_per_pixel_field():
    """C, D can vary per pixel (a spatially varying sample) -- the fit
    must be applied independently at every pixel, not just work on scalars.
    """
    shape = (20, 20)
    x = np.linspace(0.7, 1.3, shape[1])  # a spatial thickness variation factor
    t_field = T_TRUE_UM * np.tile(x, (shape[0], 1))

    wavelengths = list(WAVELENGTHS_UM.values())
    opls = [_opl_from_model(w, t=t_field) for w in wavelengths]

    fit = ms.fit_cauchy_dispersion(wavelengths, opls)

    assert np.allclose(fit["C"], A_TRUE * t_field, atol=1e-9)
    assert np.allclose(fit["D"], B_TRUE * t_field, atol=1e-9)


def test_fit_with_only_two_channels_is_exact_but_no_more_robust_than_that():
    """With exactly 2 channels the 2x2 system is solved exactly (residual
    ~0 by construction) -- there's no redundancy to average out noise,
    unlike the 3-channel case (see the noise-robustness test below).
    """
    wavelengths = [WAVELENGTHS_UM["red"], WAVELENGTHS_UM["blue"]]
    opls = [np.array([[_opl_from_model(w)]]) for w in wavelengths]

    fit = ms.fit_cauchy_dispersion(wavelengths, opls)
    assert np.abs(fit["residuals"]).max() < 1e-10


def test_three_channels_are_more_robust_to_noise_than_any_two():
    """The whole point of using all 3 RGB channels for this fit instead of
    just 2: the 3rd equation is redundant (2 unknowns, 3 equations) and
    that redundancy averages out noise via least squares. Confirm the
    3-channel fit's error is smaller than picking any single pair.
    """
    rng = np.random.default_rng(0)
    shape = (50, 50)
    noise_um = 0.01  # ~10nm of OPL noise per channel, comparable to
    # tests/test_multispectral_unwrapping.py's noise-robustness margin

    channels = list(WAVELENGTHS_UM.items())
    wavelengths_all = [w for _, w in channels]
    true_opls = {name: np.full(shape, _opl_from_model(w)) for name, w in channels}
    noisy_opls = {name: opl + rng.normal(0, noise_um, shape) for name, opl in true_opls.items()}

    fit_three = ms.fit_cauchy_dispersion(wavelengths_all, list(noisy_opls.values()))
    C_true, D_true = A_TRUE * T_TRUE_UM, B_TRUE * T_TRUE_UM
    err_three = abs(np.mean(fit_three["C"]) - C_true) + abs(np.mean(fit_three["D"]) - D_true)

    pair_errors = []
    for i in range(len(channels)):
        for j in range(i + 1, len(channels)):
            (name_i, w_i), (name_j, w_j) = channels[i], channels[j]
            fit_pair = ms.fit_cauchy_dispersion(
                [w_i, w_j], [noisy_opls[name_i], noisy_opls[name_j]],
            )
            pair_errors.append(abs(np.mean(fit_pair["C"]) - C_true) + abs(np.mean(fit_pair["D"]) - D_true))

    assert err_three < min(pair_errors), (err_three, pair_errors)


def test_A_B_t_are_not_individually_identifiable_from_opl_alone():
    """The degeneracy `fit_cauchy_dispersion` documents: scale A and B
    down by some factor and t up by the same factor -- OPL(lambda) is
    IDENTICAL at every wavelength, so the fit cannot tell the two apart.
    """
    scale = 2.0
    A_alt, B_alt, t_alt = A_TRUE / scale, B_TRUE / scale, T_TRUE_UM * scale

    for w in WAVELENGTHS_UM.values():
        opl_true_model = _opl_from_model(w)
        opl_alt_model = _opl_from_model(w, A=A_alt, B=B_alt, t=t_alt)
        assert opl_true_model == pytest.approx(opl_alt_model)


def test_resolve_thickness_and_dispersion_needs_the_correct_baseline_index():
    """Positive case: given the CORRECT baseline index A, thickness and B
    are recovered exactly. Negative case (documents the real limitation,
    not a bug): given a WRONG baseline index, the function still returns
    a self-consistent (t, B) with no error signal -- because C, D alone
    can't distinguish a correct from an incorrect baseline assumption.
    """
    C_true, D_true = A_TRUE * T_TRUE_UM, B_TRUE * T_TRUE_UM

    correct = ms.resolve_thickness_and_dispersion(np.array(C_true), np.array(D_true), A_TRUE)
    assert correct["thickness_um"] == pytest.approx(T_TRUE_UM)
    assert correct["dispersion_B"] == pytest.approx(B_TRUE)

    wrong_A = A_TRUE * 1.5
    wrong = ms.resolve_thickness_and_dispersion(np.array(C_true), np.array(D_true), wrong_A)
    assert wrong["thickness_um"] != pytest.approx(T_TRUE_UM)
    # Both are "self-consistent": each (A, B, t) triple reproduces the same C, D.
    assert wrong["thickness_um"] * wrong_A == pytest.approx(C_true)
    assert wrong["dispersion_B"] * wrong["thickness_um"] == pytest.approx(D_true)

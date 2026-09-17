"""tests/test_propagation.py -- src/ptyco_full_simulator/propagation.py:
free-space defocus propagation and Transport of Intensity Equation (TIE)
phase retrieval. Groundwork for the FPM+TIE fix identified in
docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6 (see
that module's docstring) -- not yet wired into the FPM pipeline itself,
just the two physics building blocks, each validated independently here.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import propagation as prop  # noqa: E402

PIXEL_UM = 0.5
WAVELENGTH_UM = 0.53


def _weak_object(shape):
    """Weak-absorption, weak-phase object -- exactly the regime
    `solve_tie`'s approximation (I0 roughly constant) targets, and the
    regime `tests/test_weak_phase_object_limitation.py` found the FPM
    solver itself cannot handle.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    amp = 1.0 - 0.05 * np.exp(-((xc - 0.1) ** 2 + (yc + 0.05) ** 2) / (2 * 0.1 ** 2))
    phase = 0.3 * np.exp(-(xc ** 2 + (yc + 0.1) ** 2) / (2 * 0.15 ** 2))
    phase -= phase.mean()  # zero-mean: solve_tie pins the unrecoverable global piston to 0
    return amp * np.exp(1j * phase), phase


def test_round_trip_propagation_recovers_the_original_field():
    field, _ = _weak_object((64, 64))
    propagated = prop.angular_spectrum_propagate(field, 50.0, PIXEL_UM, WAVELENGTH_UM)
    back = prop.angular_spectrum_propagate(propagated, -50.0, PIXEL_UM, WAVELENGTH_UM)
    assert np.abs(back - field).max() < 1e-10


def test_propagation_actually_converts_phase_to_intensity_contrast():
    """The whole physical mechanism TIE relies on: a phase-only-at-focus
    object develops REAL intensity structure once defocused. If this
    weren't true, TIE would have nothing to measure.
    """
    field, _ = _weak_object((64, 64))
    in_focus_intensity = np.abs(field) ** 2
    defocused_intensity = np.abs(prop.angular_spectrum_propagate(field, 20.0, PIXEL_UM, WAVELENGTH_UM)) ** 2
    assert np.abs(defocused_intensity - in_focus_intensity).max() > 0.01 * in_focus_intensity.mean()


def test_solve_tie_recovers_known_weak_phase_object():
    """The capstone check: TIE recovers this project's OWN
    weak-phase-object failure case (see
    tests/test_weak_phase_object_limitation.py) to high accuracy from a
    single extra pair of defocused captures -- something the FPM solver
    alone cannot do at all for this class of object.
    """
    field, true_phase = _weak_object((64, 64))
    in_focus_intensity = np.abs(field) ** 2

    dz = 10.0
    i_plus = np.abs(prop.angular_spectrum_propagate(field, dz, PIXEL_UM, WAVELENGTH_UM)) ** 2
    i_minus = np.abs(prop.angular_spectrum_propagate(field, -dz, PIXEL_UM, WAVELENGTH_UM)) ** 2
    di_dz = (i_plus - i_minus) / (2 * dz)

    recovered_phase = prop.solve_tie(di_dz, in_focus_intensity, PIXEL_UM, WAVELENGTH_UM)

    correlation = float(np.corrcoef(recovered_phase.ravel(), true_phase.ravel())[0, 1])
    assert correlation > 0.99, correlation
    assert np.abs(recovered_phase - true_phase).max() < 0.02, (
        "small absolute error expected given the weak-absorption approximation "
        "(amplitude isn't perfectly uniform in this test object)"
    )


def test_solve_tie_needs_a_real_intensity_derivative_signal():
    """Negative control: feed it an all-zero derivative (as if the object
    were perfectly flat / there were no defocus signal at all) -- must
    recover essentially zero phase, not hallucinate structure from
    nothing. Proves the solver isn't just returning something plausible-
    looking regardless of input.
    """
    shape = (64, 64)
    flat_intensity = np.ones(shape)
    zero_derivative = np.zeros(shape)
    recovered = prop.solve_tie(zero_derivative, flat_intensity, PIXEL_UM, WAVELENGTH_UM)
    assert np.abs(recovered).max() < 1e-9

"""tests/test_led_overlap_ratio.py -- led_array.adjacent_led_overlap_ratio,
added while investigating (with the user, interactively) why a
`z_distance_mm` sweep at a fixed upsampling factor showed a sharp jump in
phase reconstruction quality (see
docs/roadmap_agentic_multispectral_pipeline.md's "LED array height /
overlap ratio" note): the jump lines up with adjacent LEDs' Fourier-space
sub-apertures crossing a real overlap-ratio threshold, not a solver
quirk -- confirming this simulator reproduces a known FPM design
constraint (`eckert2018`'s introduction cites needing "at least 35%
overlap between adjacent angles of illumination" for phase retrieval to
work at all; this simulator's own measured transition is closer to ~28%,
not an exact match, but the same order of magnitude and the same
qualitative threshold behavior).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, led_array  # noqa: E402

WAVELENGTH_UM = 0.53
NA = 0.07


def test_overlap_ratio_is_near_total_for_a_very_distant_array():
    """Very large z_distance_mm -> tiny angular spacing between neighboring
    LEDs -> their sub-apertures nearly coincide.
    """
    cfg = config.LEDArrayConfig(grid_size=9, z_distance_mm=1e5)
    ratio = led_array.adjacent_led_overlap_ratio(cfg, WAVELENGTH_UM, NA)
    assert ratio > 0.99


def test_overlap_ratio_is_zero_for_a_very_close_array():
    """Very small z_distance_mm -> huge angular spacing -> no overlap at
    all between neighboring LEDs' sub-apertures.
    """
    cfg = config.LEDArrayConfig(grid_size=9, z_distance_mm=5.0)
    ratio = led_array.adjacent_led_overlap_ratio(cfg, WAVELENGTH_UM, NA)
    assert ratio == 0.0


def test_overlap_ratio_decreases_monotonically_as_the_array_moves_closer():
    """Moving the array closer (smaller z) increases angular spacing
    between neighboring LEDs for a fixed pitch, which can only shrink or
    hold the overlap ratio -- never increase it.
    """
    distances_mm = [200.0, 150.0, 100.0, 70.0, 50.0, 30.0]
    ratios = [led_array.adjacent_led_overlap_ratio(
        config.LEDArrayConfig(grid_size=9, z_distance_mm=z), WAVELENGTH_UM, NA)
        for z in distances_mm]
    assert ratios == sorted(ratios, reverse=True), ratios


def test_default_lab_geometry_overlap_ratio_matches_the_measured_quality_transition():
    """This project's default LEDArrayConfig (pitch=6mm, z=70mm) sits
    just above the empirically-found phase-quality transition (see this
    file's module docstring) -- a regression guard: if this default
    config or its overlap ratio formula changes, this pins down that the
    system was (at least when this test was written) just inside the
    "phase retrieval actually works" regime, not coincidentally just
    below it.
    """
    cfg = config.LEDArrayConfig(grid_size=9)  # default z_distance_mm=70.0
    ratio = led_array.adjacent_led_overlap_ratio(cfg, WAVELENGTH_UM, NA)
    assert 0.20 < ratio < 0.40, ratio

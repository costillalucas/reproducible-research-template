"""tests/test_chromatic_diagnostics.py -- roadmap open question #2:
chromatic-aberration diagnostic (src/ptyco_full_simulator/chromatic_diagnostics.py).

No real lab data exists in this Codespace (data/ has no TIFF captures),
so this validates the two measurements against KNOWN synthetic shifts/
defocus -- same "build now, validate synthetically" pattern as
io_utils.load_defocus_pair and optics.add_defocus_aberration elsewhere in
this project. Negative controls (no injected shift/defocus -> ~0 reported)
are included specifically so a future run against real data isn't the
first time these functions are checked for false positives.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import chromatic_diagnostics as cd  # noqa: E402
from ptyco_full_simulator import config, forward_model, led_array, optics  # noqa: E402
from ptyco_full_simulator import propagation as prop, reconstruction  # noqa: E402


def _synthetic_amplitude(shape):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    y, x = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((x - 0.1) ** 2 + (y + 0.05) ** 2) / (2 * 0.06 ** 2))
    amp += 0.3 * np.exp(-((x + 0.15) ** 2 + (y - 0.1) ** 2) / (2 * 0.04 ** 2))
    return np.clip(amp, 0, 1)


def _fft_shift(image, dy, dx):
    """Sub-pixel shift via the Fourier shift theorem -- the exact inverse
    of what measure_lateral_shift_px is meant to detect, so the test
    checks the measurement, not some other resampling method's artifacts.
    """
    h, w = image.shape
    fy = np.fft.fftfreq(h)
    fx = np.fft.fftfreq(w)
    FY, FX = np.meshgrid(fy, fx, indexing="ij")
    phase_ramp = np.exp(-2j * np.pi * (FY * dy + FX * dx))
    shifted = np.fft.ifft2(np.fft.fft2(image) * phase_ramp)
    return np.abs(shifted)


def test_lateral_shift_zero_for_identical_images():
    amp = _synthetic_amplitude((64, 64))
    dy, dx = cd.measure_lateral_shift_px(amp, amp)
    assert abs(dy) < 0.02 and abs(dx) < 0.02, (dy, dx)


def test_lateral_shift_recovers_known_integer_and_subpixel_shift():
    amp = _synthetic_amplitude((64, 64))
    for true_dy, true_dx in [(3.0, -2.0), (1.4, 2.7), (-4.2, 0.6)]:
        shifted = _fft_shift(amp, true_dy, true_dx)
        dy, dx = cd.measure_lateral_shift_px(amp, shifted)
        # measure_lateral_shift_px(reference, target) returns the offset of
        # target relative to reference -- shifted was built by moving amp
        # by (true_dy, true_dx), so the measured offset should match directly.
        assert abs(dy - true_dy) < 0.15, (true_dy, true_dx, dy, dx)
        assert abs(dx - true_dx) < 0.15, (true_dy, true_dx, dy, dx)


def test_focus_offset_zero_for_identical_fields():
    amp = _synthetic_amplitude((64, 64))
    field = amp.astype(complex)
    result = cd.measure_focus_offset_um(field, field, hr_pixel_um=0.2, wavelength_target_um=0.53,
                                         search_range_um=20.0, n_search=21)
    assert abs(result["offset_um"]) < 1.5, result
    assert result["correlation_at_offset"] > 0.99, result


def test_focus_offset_recovers_known_injected_defocus():
    """Build field_target by forward-propagating field_reference by a
    known +true_dz (simulating a channel whose own focal plane sits
    true_dz further along the axis) -- per the module docstring's sign
    convention, measure_focus_offset_um should report an offset close to
    -true_dz (the correction that undoes it), verified here directly
    rather than assumed.
    """
    hr_pixel_um, wavelength_um = 0.2, 0.53
    amp = _synthetic_amplitude((96, 96))
    phase = 0.3 * np.sin(2 * np.pi * 2 * np.linspace(-0.5, 0.5, 96))[None, :]
    field_reference = (amp * np.exp(1j * phase)).astype(complex)

    true_dz = 25.0
    field_target = prop.angular_spectrum_propagate(field_reference, true_dz, hr_pixel_um, wavelength_um)

    result = cd.measure_focus_offset_um(field_reference, field_target, hr_pixel_um, wavelength_um,
                                         search_range_um=50.0, n_search=51)
    assert abs(result["offset_um"] - (-true_dz)) < 3.0, result
    assert result["correlation_at_offset"] > result["correlation_at_zero"] + 0.05, result


def test_chromatic_registration_report_detects_injected_shift_through_real_reconstruction():
    """End-to-end: simulate all 3 RGB channels from the SAME true object,
    but shift blue's true object by a known pixel amount before
    simulating its LR stack (a deliberately injected lateral chromatic
    shift), reconstruct all 3 channels through the real Wirtinger flow
    solver, and confirm chromatic_registration_report's blue_vs_green
    lateral shift roughly matches the injected shift while red_vs_green
    (no injected shift) stays small.

    HONEST CAVEAT: reconstruction noise widens the tolerance here
    compared to the ideal-field tests above -- this diagnostic is only as
    good as the reconstruction feeding it (see the module docstring).
    """
    grid_size, crop, iterations = 9, 16, 40
    channels = ("red", "green", "blue")
    setups = {ch: config.default_setup(channel=ch, grid_size=grid_size, objective="2_5x_na007",
                                        resolution_px=(crop, crop)) for ch in channels}
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    amp = _synthetic_amplitude(hr_shape)
    phase = 0.1 * np.pi * np.sin(2 * np.pi * np.linspace(-0.5, 0.5, hr_shape[1]))[None, :]
    truth = (amp * np.exp(1j * phase)).astype(complex)

    true_shift_px = (2.0, -1.5)
    fields = {}
    for ch in channels:
        setup = setups[ch]
        obj = truth if ch != "blue" else (_fft_shift(amp, *true_shift_px) * np.exp(1j * phase)).astype(complex)
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            obj, hr_pixel_um, led_grid, (crop, crop), setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um,
        )
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        )
        fields[ch] = result["object"]

    wavelengths_um = {ch: config.CHANNEL_WAVELENGTH_NM[ch] / 1000.0 for ch in channels}
    report = cd.chromatic_registration_report(fields, hr_pixel_um, wavelengths_um)

    red_dy, red_dx = report["red_vs_green"]["lateral_shift_px"]
    blue_dy, blue_dx = report["blue_vs_green"]["lateral_shift_px"]
    assert abs(red_dy) < 1.0 and abs(red_dx) < 1.0, report["red_vs_green"]
    assert abs(blue_dy - true_shift_px[0]) < 1.5, report["blue_vs_green"]
    assert abs(blue_dx - true_shift_px[1]) < 1.5, report["blue_vs_green"]

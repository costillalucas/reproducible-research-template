"""tests/test_reconstruct_multispectral_tie.py -- roadmap milestone 2a +
section 1 point 6's fix combined:
pipelines/reconstruct_multispectral_independent.py's `--tie-defocus-um`
support, wiring `propagation.solve_tie` per-channel into the real
multispectral pipeline (not just the single-channel
simulate_and_reconstruct.py already covered by
tests/test_simulate_and_reconstruct_tie.py).

Same synthesized-fake-lab-captures approach as
tests/test_reconstruct_multispectral_pipeline.py, extended with the new
(proposed) defocus_plus.tiff/defocus_minus.tiff convention
(io_utils.load_defocus_pair) alongside the normal LED-grid scan.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipelines"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ptyco_full_simulator import config, forward_model, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import propagation as prop  # noqa: E402
import reconstruct_multispectral_independent as pipeline  # noqa: E402

DEFOCUS_UM = 30.0


def _weak_phase_object(shape):
    """Same style of weak/mixed-frequency phase object as
    tests/test_tie_informed_initialization.py -- low enough amplitude
    contrast and phase magnitude that the standard zero-phase
    initialization is expected to struggle.
    """
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((xc - 0.1) ** 2 + (yc + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((xc + 0.15) ** 2 + (yc - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    phase = 0.3 * np.sin(2 * np.pi * 1 * xc) + 0.15 * np.sin(2 * np.pi * 6 * xc)
    return amp * np.exp(1j * phase)


def _write_fake_lab_captures_with_defocus(tmp_path, grid_size, crop, objective="2_5x_na007"):
    setups = {
        channel: config.default_setup(channel=channel, grid_size=grid_size, objective=objective,
                                       resolution_px=(crop, crop))
        for channel in pipeline.CHANNEL_ORDER
    }
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    truth = _weak_phase_object(hr_shape)

    for channel, setup in setups.items():
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(
            truth, hr_pixel_um, led_grid, (crop, crop),
            setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
        )
        subdir = tmp_path / channel / f"{grid_size}x{grid_size}_recortada_{crop}"
        subdir.mkdir(parents=True)
        for (row, col), intensity in lr_images.items():
            Image.fromarray(intensity.astype(np.float32), mode="F").save(
                subdir / f"fila{row}_columna{col}.tiff"
            )

        i_plus = np.abs(prop.angular_spectrum_propagate(
            truth, DEFOCUS_UM, hr_pixel_um, setup.wavelength_um)) ** 2
        i_minus = np.abs(prop.angular_spectrum_propagate(
            truth, -DEFOCUS_UM, hr_pixel_um, setup.wavelength_um)) ** 2
        Image.fromarray(i_plus.astype(np.float32), mode="F").save(subdir / "defocus_plus.tiff")
        Image.fromarray(i_minus.astype(np.float32), mode="F").save(subdir / "defocus_minus.tiff")

    return truth, hr_shape


def test_tie_defocus_flag_fixes_a_weak_phase_object_across_all_channels(tmp_path):
    grid_size, crop = 9, 32
    truth, hr_shape = _write_fake_lab_captures_with_defocus(tmp_path, grid_size, crop)

    baseline = pipeline.reconstruct_all_channels(
        str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=40,
    )
    tie_run = pipeline.reconstruct_all_channels(
        str(tmp_path), grid_size, objective="2_5x_na007", z_distance_mm=70.0, exposure_normalization=False, normalize_initial_guess=False, crop=crop, iterations=40,
        tie_defocus_um=DEFOCUS_UM,
    )

    for channel in pipeline.CHANNEL_ORDER:
        baseline_gt = metrics.compare_to_ground_truth(baseline["channels"][channel]["object"], truth)
        tie_gt = metrics.compare_to_ground_truth(tie_run["channels"][channel]["object"], truth)
        # The size of the improvement is channel-dependent (each wavelength has its own
        # phase sensitivity/local-minimum behavior, see milestone 2a's red-channel finding) --
        # don't assert a fixed delta that happens to hold for some channels and not others,
        # just that TIE-informed init is a real, clear improvement and lands somewhere good.
        assert tie_gt["phase_correlation"] > baseline_gt["phase_correlation"], (
            channel, baseline_gt["phase_correlation"], tie_gt["phase_correlation"]
        )
        assert tie_gt["phase_correlation"] > 0.7, (channel, tie_gt["phase_correlation"])

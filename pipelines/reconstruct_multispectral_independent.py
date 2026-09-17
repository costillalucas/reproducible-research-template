#!/usr/bin/env python3
"""reconstruct_multispectral_independent.py -- roadmap milestone 2a
(docs/roadmap_agentic_multispectral_pipeline.md): reconstruct all three
RGB channels independently -- same algorithm as reconstruct_real_images.py,
run three times, sharing nothing between channels -- but on the single
common HR grid milestone 1 (optics.shared_upsampling_factor) established,
so phi_red, phi_green, phi_blue come back aligned: same hr_pixel_um, same
array shape, stackable into one (3, H, W) array with no resize step.

This is the cheap baseline milestone 2b (coupled unwrapping + dispersion
fit) will be compared against -- it does NOT do any cross-channel
unwrapping or dispersion estimate itself.

Usage:
    python pipelines/reconstruct_multispectral_independent.py \\
        --data-root /path/to/data \\
        --grid-size 9 --objective current --crop 400 \\
        --output-dir results/multispectral_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import config, io_utils, led_array, metrics, optics, reconstruction  # noqa: E402

CHANNEL_ORDER = ("red", "green", "blue")


def reconstruct_all_channels(data_root, grid_size: int, objective: str = "current",
                              crop: int = 400, iterations: int = 20,
                              index_base: int = 1) -> dict:
    """Reconstruct red/green/blue independently on one shared HR grid.

    Returns {"factor": int, "hr_pixel_um": float, "hr_shape": (h, w),
             "channels": {channel: {"object": complex ndarray,
                                     "history": [...], "n_leds_used": int,
                                     "n_leds_expected": int}}}.
    """
    setups = {
        channel: config.default_setup(
            channel=channel, grid_size=grid_size, objective=objective,
            resolution_px=(crop, crop),
        )
        for channel in CHANNEL_ORDER
    }
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    n_expected = grid_size * grid_size

    channels = {}
    for channel in CHANNEL_ORDER:
        setup = setups[channel]
        lr_images = io_utils.load_real_lr_stack(
            data_root, channel, grid_size, crop, index_base=index_base,
        )
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
        )
        channels[channel] = {
            "object": result["object"],
            "history": result["history"],
            "n_leds_used": len(lr_images),
            "n_leds_expected": n_expected,
        }

    shapes = {ch: c["object"].shape for ch, c in channels.items()}
    if len(set(shapes.values())) != 1:
        raise AssertionError(f"channels landed on different HR grids: {shapes}")

    return {"factor": factor, "hr_pixel_um": hr_pixel_um, "hr_shape": hr_shape, "channels": channels}


def _save_rgb_composite(channels: dict, output_dir: str) -> None:
    """Amplitude-only RGB composite for eyeballing -- NOT the fusion
    milestone 2b will do; just a per-channel-normalized stack of
    |reconstructed object| into an RGB PNG, since the three are already on
    the same grid.
    """
    from PIL import Image

    planes = []
    for channel in CHANNEL_ORDER:
        amp = np.abs(channels[channel]["object"])
        plane = (amp / amp.max() * 255 if amp.max() > 0 else amp).astype(np.uint8)
        planes.append(plane)
    rgb = np.stack(planes, axis=-1)
    Image.fromarray(rgb, mode="RGB").save(os.path.join(output_dir, "rgb_amplitude_composite.png"))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", required=True,
                    help="folder containing <channel>/<grid>x<grid>_recortada_<crop>/fila*_columna*.tiff")
    p.add_argument("--grid-size", type=int, default=9, help="LED grid is grid_size x grid_size (must be odd)")
    p.add_argument("--objective", choices=sorted(config.OBJECTIVES), default="current")
    p.add_argument("--crop", type=int, default=400,
                    help="the crop size named in the lab's own folder naming (...recortada_<crop>)")
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--output-dir", default="results/reconstruct_multispectral_independent")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.output_dir, exist_ok=True)

    run = reconstruct_all_channels(
        args.data_root, args.grid_size, objective=args.objective,
        crop=args.crop, iterations=args.iterations,
    )
    print(f"grid={args.grid_size}x{args.grid_size}  objective={args.objective}  "
          f"shared_upsampling_factor={run['factor']}  hr_shape={run['hr_shape']}  "
          f"hr_pixel={run['hr_pixel_um']:.4f}um  (registered: all 3 channels share this grid)")

    metrics_out = {
        "factor": run["factor"], "hr_pixel_um": run["hr_pixel_um"], "hr_shape": list(run["hr_shape"]),
        "channels": {},
    }
    complex_objects = {}
    for channel in CHANNEL_ORDER:
        c = run["channels"][channel]
        conv = metrics.convergence_summary(c["history"])
        print(f"  {channel}: {c['n_leds_used']}/{c['n_leds_expected']} LEDs  "
              f"convergence={json.dumps(conv)}")
        io_utils.save_complex_as_images(c["object"], args.output_dir, channel)
        complex_objects[channel] = c["object"]
        metrics_out["channels"][channel] = {
            "convergence": conv, "history": c["history"],
            "n_leds_used": c["n_leds_used"], "n_leds_expected": c["n_leds_expected"],
        }

    _save_rgb_composite(run["channels"], args.output_dir)
    np.savez(os.path.join(args.output_dir, "complex_objects.npz"), **complex_objects)
    with open(os.path.join(args.output_dir, "metrics.json"), "w") as fh:
        json.dump(metrics_out, fh, indent=2)
    print(f"wrote results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

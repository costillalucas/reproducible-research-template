#!/usr/bin/env python3
"""reconstruct_real_images.py -- script 2: real lab LR captures -> HR
reconstruction, same algorithm as simulate_and_reconstruct.py but with no
ground truth to compare against (only internal convergence diagnostics).

Expects <data-root>/<channel>/<grid-size>x<grid-size>_recortada_<crop>/
fila<row>_columna<col>.tiff -- the lab's own folder naming. See
src/ptyco_full_simulator/io_utils.py's module docstring if your real
capture layout differs.

Usage:
    python pipelines/reconstruct_real_images.py \\
        --data-root /path/to/data --channel green \\
        --grid-size 9 --objective current --crop 400 \\
        --output-dir results/real_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import config, io_utils, led_array, metrics, optics, reconstruction  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", required=True,
                    help="folder containing <channel>/<grid>x<grid>_recortada_<crop>/fila*_columna*.tiff")
    p.add_argument("--channel", choices=sorted(config.CHANNEL_WAVELENGTH_NM), default="green")
    p.add_argument("--grid-size", type=int, default=9, help="LED grid is grid_size x grid_size (must be odd)")
    p.add_argument("--objective", choices=sorted(config.OBJECTIVES), default="current")
    p.add_argument("--crop", type=int, default=400,
                    help="the crop size named in the lab's own folder naming (...recortada_<crop>)")
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--output-dir", default="results/reconstruct_real_images")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    setup = config.default_setup(
        channel=args.channel, grid_size=args.grid_size, objective=args.objective,
        resolution_px=(args.crop, args.crop),
    )
    lr_images = io_utils.load_real_lr_stack(
        args.data_root, args.channel, args.grid_size, args.crop,
        index_base=setup.led_array.index_base,
    )
    n_expected = args.grid_size * args.grid_size
    subdir = f"{args.grid_size}x{args.grid_size}_recortada_{args.crop}"
    print(f"loaded {len(lr_images)}/{n_expected} LR images from "
          f"{args.data_root}/{args.channel}/{subdir}")
    if len(lr_images) < n_expected:
        print("  (scan looks incomplete -- reconstructing with what's available, "
              "at reduced synthetic-aperture resolution/SNR)")

    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    print(f"channel={args.channel} ({setup.wavelength_nm:.0f} nm)  objective={args.objective} "
          f"(NA={setup.objective.na}, mag={setup.objective.magnification})  "
          f"upsampling_factor={factor}  hr_pixel={hr_pixel_um:.4f}um")

    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=args.iterations,
    )

    conv = metrics.convergence_summary(result["history"])
    print("convergence (no ground truth available -- this is internal "
          "amplitude-residual only):", json.dumps(conv, indent=2))

    io_utils.save_complex_as_images(result["object"], args.output_dir, "reconstructed")
    with open(os.path.join(args.output_dir, "metrics.json"), "w") as fh:
        json.dump({
            "convergence": conv, "history": result["history"],
            "n_leds_used": len(lr_images), "n_leds_expected": n_expected,
            "setup": {
                "channel": args.channel, "wavelength_nm": setup.wavelength_nm,
                "grid_size": args.grid_size, "objective": args.objective,
                "na": setup.objective.na, "magnification": setup.objective.magnification,
                "crop": args.crop, "upsampling_factor": factor,
                "hr_pixel_um": hr_pixel_um, "lr_pixel_um": setup.lr_pixel_size_um,
                "iterations": args.iterations, "data_root": args.data_root,
            },
        }, fh, indent=2)
    print(f"wrote results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

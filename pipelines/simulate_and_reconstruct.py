#!/usr/bin/env python3
"""simulate_and_reconstruct.py -- script 1: data_source -> simulated LR
stack -> reconstructed HR -> compared against the known ground truth.

This is the closed-loop sanity check for the whole FPM pipeline: since
the "true" object is known (it's the input), reconstruction quality can
be measured directly, unlike script 2 (reconstruct_real_images.py) where
there is no ground truth.

Usage:
    python pipelines/simulate_and_reconstruct.py \\
        --amplitude-image path/to/amplitude.png \\
        --phase-image path/to/phase.png \\
        --channel green --grid-size 9 --objective current \\
        --output-dir results/sim_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import config, forward_model, io_utils, led_array, metrics, optics, reconstruction  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--amplitude-image", required=True, help="drives the object's amplitude")
    p.add_argument("--phase-image", required=True, help="drives the object's phase")
    p.add_argument("--channel", choices=sorted(config.CHANNEL_WAVELENGTH_NM), default="green")
    p.add_argument("--grid-size", type=int, default=9, help="LED grid is grid_size x grid_size (must be odd)")
    p.add_argument("--objective", choices=sorted(config.OBJECTIVES), default="current")
    p.add_argument("--lr-size", type=int, default=64, help="simulated LR image side, in pixels")
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--peak-photon-count", type=float, default=None,
                    help="add Poisson shot noise at this peak count; omit for noiseless")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output-dir", default="results/simulate_and_reconstruct")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    rng = np.random.default_rng(args.seed)

    setup = config.default_setup(
        channel=args.channel, grid_size=args.grid_size, objective=args.objective,
        resolution_px=(args.lr_size, args.lr_size),
    )
    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    hr_shape = optics.hr_shape((args.lr_size, args.lr_size), factor)

    print(f"channel={args.channel} ({setup.wavelength_nm:.0f} nm)  "
          f"grid={args.grid_size}x{args.grid_size}  objective={args.objective} "
          f"(NA={setup.objective.na}, mag={setup.objective.magnification})")
    print(f"lr_size={args.lr_size}px  upsampling_factor={factor}  hr_shape={hr_shape}  "
          f"hr_pixel={hr_pixel_um:.4f}um  lr_pixel={setup.lr_pixel_size_um:.4f}um")

    hr_object = io_utils.load_reference_object(
        args.amplitude_image, args.phase_image, target_shape=hr_shape,
    )

    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    lr_images = forward_model.simulate_lr_stack(
        hr_object, hr_pixel_um, led_grid, (args.lr_size, args.lr_size),
        setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
        peak_photon_count=args.peak_photon_count, rng=rng,
    )
    print(f"simulated {len(lr_images)} LR images")

    result = reconstruction.reconstruct(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor, iterations=args.iterations,
    )

    gt_metrics = metrics.compare_to_ground_truth(result["object"], hr_object)
    conv = metrics.convergence_summary(result["history"])
    print("convergence:", json.dumps(conv, indent=2))
    print("vs. ground truth:", json.dumps(gt_metrics, indent=2))

    io_utils.save_complex_as_images(result["object"], args.output_dir, "reconstructed")
    io_utils.save_complex_as_images(hr_object, args.output_dir, "ground_truth")
    with open(os.path.join(args.output_dir, "metrics.json"), "w") as fh:
        json.dump({
            "convergence": conv, "vs_ground_truth": gt_metrics,
            "history": result["history"],
            "setup": {
                "channel": args.channel, "wavelength_nm": setup.wavelength_nm,
                "grid_size": args.grid_size, "objective": args.objective,
                "na": setup.objective.na, "magnification": setup.objective.magnification,
                "lr_size": args.lr_size, "upsampling_factor": factor,
                "hr_pixel_um": hr_pixel_um, "lr_pixel_um": setup.lr_pixel_size_um,
                "iterations": args.iterations, "peak_photon_count": args.peak_photon_count,
                "seed": args.seed,
            },
        }, fh, indent=2)
    print(f"wrote results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

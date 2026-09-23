#!/usr/bin/env python3
"""sweep_real_reconstruction_quality.py -- sweep --iterations (and,
wirtinger-only, --adaptive-step/--recover-pupil) for a single-channel real
reconstruction (same real-data code path as
pipelines/reconstruct_real_images.py) and correlate EACH result's amplitude
against a real HR reference image via
ptyco_full_simulator.metrics.correlate_against_hr_reference, instead of
only the internal amplitude-residual convergence_summary
reconstruct_real_images.py reports.

Why this exists: docs/roadmap_agentic_multispectral_pipeline.md section 6.3
found that, on the project's first real lab capture, 200 Wirtinger-flow
iterations correlated slightly WORSE against a real HR reference than 20
iterations did, despite the internal residual continuing to improve at 200
-- flagged there as an open, unconfirmed finding (could be real overfitting
to sensor noise, could be within the correlation metric's own noise floor).
That comparison was done by hand-running reconstruct_real_images.py at each
iteration count and eyeballing/hand-correlating the outputs. This script
makes that kind of sweep a single reusable command instead.

Note: each iteration count is an INDEPENDENT reconstruction from scratch
(reconstruction.reconstruct / joint_calibration.reconstruct_gradient_descent
don't support resuming from a shorter run's history), so total cost is
roughly the sum of each individual run's cost, not shared.

Usage:
    python scripts/sweep_real_reconstruction_quality.py \\
        --data-root /path/to/data --channel green \\
        --grid-size 9 --objective 2x_na010 --crop 400 \\
        --row-index-base 13 --col-index-base 11 \\
        --reference-image /path/to/reference.tif \\
        --iterations 20 50 100 200 400 600 \\
        --output-json results/sweep_green.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import cli_args, config, io_utils, joint_calibration, led_array, metrics, optics, reconstruction  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", required=True,
                    help="folder containing <channel>/<grid>x<grid>_recortada_<crop>/fila*_col*.tiff")
    p.add_argument("--channel", choices=sorted(config.CHANNEL_WAVELENGTH_NM), default="green")
    p.add_argument("--grid-size", type=int, default=9, help="LED grid is grid_size x grid_size (must be odd)")
    p.add_argument("--objective", choices=sorted(config.OBJECTIVES), default=config.DEFAULT_OBJECTIVE,
                   help="objective preset (default %(default)s, the one real captures use; "
                        "\"current\"/\"future\" are deprecated aliases, see config.OBJECTIVES)")
    p.add_argument("--crop", type=int, default=400,
                    help="the crop size named in the lab's own folder naming (...recortada_<crop>)")
    p.add_argument("--row-index-base", type=int, default=None,
                    help="first row number in the lab's fila<R>_col<C> filenames, if different from "
                         "column numbering -- defaults to the same value as columns when omitted")
    p.add_argument("--col-index-base", type=int, default=None,
                    help="first column number in the lab's fila<R>_col<C> filenames, if different from "
                         "row numbering -- defaults to the same value as rows when omitted")
    p.add_argument("--reference-image", required=True,
                    help="path to a real HR grayscale/intensity reference image (any resolution -- "
                         "resized with Lanczos to match the reconstruction's HR grid, see "
                         "metrics.correlate_against_hr_reference)")
    p.add_argument("--iterations", type=int, nargs="+", required=True,
                    help="one independent reconstruction run per value, e.g. --iterations 20 50 200 600")
    p.add_argument("--solver", choices=["wirtinger", "gd-amplitude"], default="wirtinger")
    p.add_argument("--adaptive-step", action="store_true",
                    help="wirtinger only, see reconstruction.reconstruct's adaptive_step "
                         "(zuo2016) -- mutually exclusive with --recover-pupil per that "
                         "function's own convention (not separately enforced here)")
    p.add_argument("--recover-pupil", action="store_true",
                    help="wirtinger only, see reconstruction.reconstruct's recover_pupil (EPRY/ou2014)")
    cli_args.add_geometry_args(p)
    p.add_argument("--output-json", default=None,
                    help="if given, write the full per-run table as JSON here")
    return p.parse_args(argv)


def load_reference(path: str) -> np.ndarray:
    arr = np.asarray(Image.open(path), dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"reference image must be single-channel/grayscale, got shape {arr.shape}")
    return arr


def sweep(lr_images: dict, led_grid: list[dict], hr_pixel_um: float, lr_pixel_um: float,
          na: float, wavelength_um: float, factor: int, iteration_values: list[int],
          reference: np.ndarray, solver: str = "wirtinger",
          adaptive_step: bool = False, recover_pupil: bool = False) -> list[dict]:
    """Filesystem-free core: runs one independent reconstruction per value
    in `iteration_values` against the given in-memory LR stack/LED grid,
    and correlates each result's amplitude against `reference` (resized as
    needed by `metrics.correlate_against_hr_reference`). Returns a list of
    per-run dicts, one per iteration value, in the same order as
    `iteration_values` -- easy to unit test with tiny synthetic arrays.
    """
    if solver not in ("wirtinger", "gd-amplitude"):
        raise ValueError(f"solver must be 'wirtinger' or 'gd-amplitude', got {solver!r}")
    if solver == "gd-amplitude" and (adaptive_step or recover_pupil):
        raise ValueError("--adaptive-step/--recover-pupil are wirtinger-only "
                          "(see reconstruction.reconstruct)")

    rows = []
    for iterations in iteration_values:
        t0 = time.perf_counter()
        if solver == "gd-amplitude":
            result = joint_calibration.reconstruct_gradient_descent(
                lr_images, led_grid, hr_pixel_um, lr_pixel_um, na, wavelength_um, factor,
                iterations=iterations,
            )
        else:
            result = reconstruction.reconstruct(
                lr_images, led_grid, hr_pixel_um, lr_pixel_um, na, wavelength_um, factor,
                iterations=iterations, adaptive_step=adaptive_step, recover_pupil=recover_pupil,
            )
        elapsed_s = time.perf_counter() - t0

        conv = metrics.convergence_summary(result["history"])
        corr = metrics.correlate_against_hr_reference(np.abs(result["object"]), reference)
        rows.append({
            "iterations": iterations,
            "elapsed_s": elapsed_s,
            "relative_improvement": conv["relative_improvement"],
            "fraction_of_epochs_that_improved": conv["fraction_of_epochs_that_improved"],
            "reference_correlation": corr["correlation"],
            "flipud": corr["flipud"],
            "fliplr": corr["fliplr"],
        })
    return rows


def _print_table(rows: list[dict]) -> None:
    print(f"{'iterations':>10}  {'elapsed_s':>10}  {'rel_improve':>12}  {'ref_corr':>9}  flip")
    for row in rows:
        print(f"{row['iterations']:>10}  {row['elapsed_s']:>10.1f}  "
              f"{row['relative_improvement'] * 100:>11.3f}%  {row['reference_correlation']:>9.4f}  "
              f"flipud={row['flipud']} fliplr={row['fliplr']}")


def main(argv=None) -> int:
    args = parse_args(argv)

    setup = config.default_setup(
        channel=args.channel, grid_size=args.grid_size, objective=args.objective,
        resolution_px=(args.crop, args.crop),
        row_index_base=args.row_index_base, col_index_base=args.col_index_base,
        **cli_args.geometry_kwargs(args),
    )
    lr_images = io_utils.load_real_lr_stack(
        args.data_root, args.channel, args.grid_size, args.crop,
        row_index_base=setup.led_array.row_base, col_index_base=setup.led_array.col_base,
    )
    n_expected = args.grid_size * args.grid_size
    print(f"loaded {len(lr_images)}/{n_expected} LR images  channel={args.channel}")
    if len(lr_images) < n_expected:
        print("  (scan looks incomplete -- sweeping with what's available)")

    factor = optics.upsampling_factor(setup)
    hr_pixel_um = optics.actual_hr_pixel_size_um(setup, factor)
    led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    reference = load_reference(args.reference_image)

    rows = sweep(
        lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
        setup.objective.na, setup.wavelength_um, factor,
        args.iterations, reference, solver=args.solver,
        adaptive_step=args.adaptive_step, recover_pupil=args.recover_pupil,
    )
    _print_table(rows)

    if args.output_json:
        out_dir = os.path.dirname(args.output_json)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output_json, "w") as fh:
            json.dump({
                "channel": args.channel, "grid_size": args.grid_size, "objective": args.objective,
                "crop": args.crop, "solver": args.solver, "adaptive_step": args.adaptive_step,
                "recover_pupil": args.recover_pupil, "data_root": args.data_root,
                "reference_image": args.reference_image, "rows": rows,
                "geometry": config.setup_geometry_summary(setup),
            }, fh, indent=2)
        print(f"wrote {args.output_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

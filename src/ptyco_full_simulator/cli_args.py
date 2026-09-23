"""cli_args.py -- geometry-override flags shared by the real-data CLIs.

The four real-data entry points (pipelines/reconstruct_real_images.py,
reconstruct_multispectral_independent.py, reconstruct_multispectral_coupled.py
and scripts/sweep_real_reconstruction_quality.py) all take the same
physical-geometry flags; defining them once here keeps their defaults and
help text from drifting apart.

Defaults are the real lab setup: array-to-sample distance
`config.REAL_CAPTURE_Z_DISTANCE_MM` (76 mm), array centered on the axis,
and the objective preset's own NA/magnification.
"""
from __future__ import annotations

import argparse

from . import config


def add_geometry_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--z-distance-mm", type=float, default=config.REAL_CAPTURE_Z_DISTANCE_MM,
                   help="LED array-to-sample distance in mm (default %(default)s, the real lab "
                        "setup; synthetic data generated with the simulator's nominal geometry "
                        "needs 70)")
    p.add_argument("--na", type=float, default=None,
                   help="override the objective preset's NA (e.g. a measured effective value)")
    p.add_argument("--magnification", type=float, default=None,
                   help="override the objective preset's magnification (sets the LR pixel size "
                        "at the sample: camera pixel / magnification)")
    p.add_argument("--led-center-offset-mm", type=float, nargs=2, default=(0.0, 0.0),
                   metavar=("DX", "DY"),
                   help="where the array's nominal center LED sits relative to the optical "
                        "axis, in mm: DX along columns, DY along rows (default 0 0, aligned); "
                        "one LED pitch is 6 mm")


def geometry_kwargs(args: argparse.Namespace) -> dict:
    """The `config.default_setup` keyword arguments the flags above map to."""
    return {
        "z_distance_mm": args.z_distance_mm,
        "led_center_offset_mm": tuple(args.led_center_offset_mm),
        "na": args.na,
        "magnification": args.magnification,
    }

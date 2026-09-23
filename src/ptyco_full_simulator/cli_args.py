"""cli_args.py -- flags shared by the real-data CLIs: geometry overrides,
exposure normalization and Wirtinger-flow step/initial-guess scale.

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


def add_acquisition_args(p: argparse.ArgumentParser) -> None:
    """Exposure normalization of real captures (io_utils.normalize_exposure)."""
    p.add_argument("--no-exposure-normalization", dest="exposure_normalization",
                   action="store_false",
                   help="feed the TIFFs as-is instead of (raw - dark) / exposure. By default the "
                        "per-LED exposure is read from <channel>/leds_por_tiempo_*.json (or the "
                        "<N>ms/ folders) and the run fails if neither exists -- use this flag only "
                        "for already-normalized or synthetic images")
    p.add_argument("--dark-level", type=float, default=config.REAL_CAPTURE_DARK_LEVEL,
                   help="camera dark/bias counts subtracted before dividing by exposure (default "
                        "%(default)s, measured on the lab's no-LED capture, see "
                        "config.REAL_CAPTURE_DARK_LEVEL)")


def add_solver_scale_args(p: argparse.ArgumentParser) -> None:
    """Wirtinger-flow step / initial-guess scale (reconstruction.reconstruct)."""
    p.add_argument("--step-epie", type=float, default=None, metavar="FRACTION",
                   help="Wirtinger-flow step as a fraction of the classic ePIE unit step "
                        "(crop-independent; e.g. 0.3). Default: the legacy fixed step_max=20, "
                        "which is ~1/8000 of the unit step at crop 400 and leaves the solver "
                        "nearly frozen -- see reconstruction.py's module docstring. With "
                        "--recover-pupil it scales EPRY's alpha/beta the same way (1.0 = ou2014's "
                        "alpha=beta=1)")
    p.add_argument("--no-normalize-initial-guess", dest="normalize_initial_guess",
                   action="store_false",
                   help="keep the legacy initial guess that is factor^2 too bright for the "
                        "forward model (default: divide it out)")


def acquisition_kwargs(args: argparse.Namespace) -> dict:
    """`io_utils.load_real_lr_stack_normalized` keyword arguments."""
    return {"normalize": args.exposure_normalization, "dark_level": args.dark_level}


def geometry_kwargs(args: argparse.Namespace) -> dict:
    """The `config.default_setup` keyword arguments the flags above map to."""
    return {
        "z_distance_mm": args.z_distance_mm,
        "led_center_offset_mm": tuple(args.led_center_offset_mm),
        "na": args.na,
        "magnification": args.magnification,
    }

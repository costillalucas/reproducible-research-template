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

from ptyco_full_simulator import config, io_utils, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import propagation as prop, reconstruction  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
import reconstruction_orchestrator  # noqa: E402

CHANNEL_ORDER = ("red", "green", "blue")


def reconstruct_all_channels(data_root, grid_size: int, objective: str = "current",
                              crop: int = 400, iterations: int = 20,
                              index_base: int = 1, tie_defocus_um: float | None = None,
                              use_reconstruction_agent: bool = False,
                              agent_live: bool = False, max_attempts: int = 3) -> dict:
    """Reconstruct red/green/blue independently on one shared HR grid.

    `tie_defocus_um`, if given, initializes each channel's solver with a
    Transport-of-Intensity-Equation phase estimate instead of the default
    zero phase -- see `propagation.solve_tie` and
    `io_utils.load_defocus_pair` (the extra capture this needs, per
    channel, that most existing capture sets won't have yet).

    `use_reconstruction_agent`, if True, runs each channel through
    `agents/reconstruction_orchestrator.py`'s milestone-3 agent (accept/
    retry-with-different-step_max/give_up) instead of a single direct
    `reconstruction.reconstruct` call -- same agent, same dry-run-by-
    default cost discipline as `pipelines/simulate_and_reconstruct.py`'s
    `--use-reconstruction-agent`. `agent_live`/`max_attempts` are only
    used when this is True.

    Returns {"factor": int, "hr_pixel_um": float, "hr_shape": (h, w),
             "channels": {channel: {"object": complex ndarray,
                                     "history": [...], "n_leds_used": int,
                                     "n_leds_expected": int,
                                     "agent_attempts": [...] or None}}}.
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

        initial_object = None
        if tie_defocus_um is not None:
            center = led_grid[0]
            i_focus = lr_images[(center["row"], center["col"])]
            i_plus, i_minus = io_utils.load_defocus_pair(data_root, channel, grid_size, crop)
            di_dz = (i_plus - i_minus) / (2 * tie_defocus_um)
            tie_phase = prop.solve_tie(di_dz, i_focus, hr_pixel_um, setup.wavelength_um)
            amp0 = np.sqrt(np.clip(i_focus, 0, None))
            amp0_hr = np.kron(amp0, np.ones((factor, factor)))
            initial_object = (amp0_hr * np.exp(1j * tie_phase)).astype(complex)

        agent_attempts = None
        if use_reconstruction_agent:
            orchestrated = reconstruction_orchestrator.orchestrate_reconstruction(
                lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
                setup.objective.na, setup.wavelength_um, factor,
                iterations=iterations, max_attempts=max_attempts,
                dry_run=not agent_live, initial_object=initial_object,
            )
            result = orchestrated["result"]
            agent_attempts = orchestrated["attempts"]
        else:
            result = reconstruction.reconstruct(
                lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
                setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
                initial_object=initial_object,
            )
        channels[channel] = {
            "object": result["object"],
            "history": result["history"],
            "n_leds_used": len(lr_images),
            "n_leds_expected": n_expected,
            "agent_attempts": agent_attempts,
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
    p.add_argument("--tie-defocus-um", type=float, default=None,
                    help="if set, initialize each channel's solver with a Transport of Intensity "
                         "Equation phase estimate instead of the default zero -- requires an extra "
                         "on-axis defocus_plus.tiff/defocus_minus.tiff pair per channel, see "
                         "io_utils.load_defocus_pair's docstring for the (new, proposed) file "
                         "convention. See docs/roadmap_agentic_multispectral_pipeline.md section 1 "
                         "point 6 for why this matters, especially for weak-phase/low-contrast "
                         "samples.")
    p.add_argument("--use-reconstruction-agent", action="store_true",
                    help="use agents/reconstruction_orchestrator.py's milestone-3 agent per channel "
                         "instead of a single direct reconstruction.reconstruct call -- see "
                         "pipelines/simulate_and_reconstruct.py's flag of the same name for details. "
                         "Defaults to a canned dry-run decision; pass --agent-live for a real "
                         "(billed) claude -p call per channel.")
    p.add_argument("--agent-live", action="store_true",
                    help="make --use-reconstruction-agent call the real agent instead of a dry-run "
                         "stub -- COSTS MONEY per channel, see agents/reconstruction_orchestrator.py")
    p.add_argument("--max-attempts", type=int, default=3,
                    help="only used with --use-reconstruction-agent")
    p.add_argument("--output-dir", default="results/reconstruct_multispectral_independent")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.output_dir, exist_ok=True)

    run = reconstruct_all_channels(
        args.data_root, args.grid_size, objective=args.objective,
        crop=args.crop, iterations=args.iterations, tie_defocus_um=args.tie_defocus_um,
        use_reconstruction_agent=args.use_reconstruction_agent,
        agent_live=args.agent_live, max_attempts=args.max_attempts,
    )
    print(f"grid={args.grid_size}x{args.grid_size}  objective={args.objective}  "
          f"shared_upsampling_factor={run['factor']}  hr_shape={run['hr_shape']}  "
          f"hr_pixel={run['hr_pixel_um']:.4f}um  (registered: all 3 channels share this grid)")

    metrics_out = {
        "factor": run["factor"], "hr_pixel_um": run["hr_pixel_um"], "hr_shape": list(run["hr_shape"]),
        "tie_defocus_um": args.tie_defocus_um,
        "use_reconstruction_agent": args.use_reconstruction_agent, "channels": {},
    }
    complex_objects = {}
    for channel in CHANNEL_ORDER:
        c = run["channels"][channel]
        conv = metrics.convergence_summary(c["history"])
        print(f"  {channel}: {c['n_leds_used']}/{c['n_leds_expected']} LEDs  "
              f"convergence={json.dumps(conv)}")
        if c["agent_attempts"] is not None:
            for i, attempt in enumerate(c["agent_attempts"]):
                print(f"    agent attempt {i + 1}/{len(c['agent_attempts'])}: "
                      f"step_max={attempt['step_max']}  decision={attempt['decision']['action']}  "
                      f"reasoning={attempt['decision']['reasoning']!r}")
        io_utils.save_complex_as_images(c["object"], args.output_dir, channel)
        complex_objects[channel] = c["object"]
        metrics_out["channels"][channel] = {
            "convergence": conv, "history": c["history"], "agent_attempts": c["agent_attempts"],
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

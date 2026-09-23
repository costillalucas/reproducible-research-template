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
        --grid-size 9 --objective 2x_na010 --crop 400 \\
        --output-dir results/multispectral_run1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from ptyco_full_simulator import chromatic_diagnostics as cd  # noqa: E402
from ptyco_full_simulator import config, io_utils, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import joint_calibration, propagation as prop, reconstruction  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
import reconstruction_orchestrator  # noqa: E402

CHANNEL_ORDER = ("red", "green", "blue")


def reconstruct_all_channels(data_root, grid_size: int, objective: str = config.DEFAULT_OBJECTIVE,
                              crop: int = 400, iterations: int = 20,
                              index_base: int = 1,
                              row_index_base: int | None = None,
                              col_index_base: int | None = None,
                              tie_defocus_um: float | None = None,
                              use_reconstruction_agent: bool = False,
                              agent_live: bool = False, max_attempts: int = 3,
                              recover_pupil: bool = False, adaptive_step: bool = False,
                              solver: str = "wirtinger") -> dict:
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

    `adaptive_step` (per-channel zuo2016) CAN be combined with
    `use_reconstruction_agent` (2026-09-18, resolved): passed through to
    `agents/reconstruction_orchestrator.py`'s `orchestrate_reconstruction`,
    which threads it into every attempt and tells the agent's prompt
    `step_max` is only a starting point under this mode -- see that
    function's docstring for why this combination is sound.

    `recover_pupil` (per-channel EPRY/`ou2014`) CANNOT be combined with
    `use_reconstruction_agent` -- NOT an unimplemented feature, a real
    information deficit: `reconstruction.reconstruct` ignores `step_max`
    under `recover_pupil`, so the agent's only lever has nothing to
    adjust, and `recovery_error` (the agent's only signal) is proven
    blind to `recover_pupil`'s own small-testbed regression (see
    `tests/test_epry_pupil_recovery.py` and
    `agents/reconstruction_orchestrator.py`'s docstring). Same
    restriction as `pipelines/simulate_and_reconstruct.py`'s CLI.

    `solver`: "wirtinger" (default, `reconstruction.reconstruct`) or
    "gd-amplitude" (`joint_calibration.reconstruct_gradient_descent`, Adam
    on the amplitude loss -- measured to beat the Wirtinger flow under
    Poisson noise on synthetic and real-image objects, see roadmap
    milestones 11 & 13; never validated on real lab captures, and blue
    with moderate/heavy noise fails for every solver). Mutually exclusive
    with `recover_pupil`, `adaptive_step` and `use_reconstruction_agent`
    (they all tune Wirtinger-flow internals: its step schedule / pupil
    update / `step_max` retry lever). `iterations` are full-batch steps
    under "gd-amplitude" -- ~100 was used in every comparison.

    Returns {"factor": int, "hr_pixel_um": float, "hr_shape": (h, w),
             "channels": {channel: {"object": complex ndarray,
                                     "history": [...], "n_leds_used": int,
                                     "n_leds_expected": int,
                                     "agent_attempts": [...] or None,
                                     "pupil": complex ndarray or None}}}.
    """
    if solver not in ("wirtinger", "gd-amplitude"):
        raise ValueError(f"solver must be 'wirtinger' or 'gd-amplitude', got {solver!r}")
    if solver == "gd-amplitude" and (recover_pupil or adaptive_step or use_reconstruction_agent):
        raise ValueError("solver='gd-amplitude' cannot be combined with recover_pupil, "
                          "adaptive_step or use_reconstruction_agent -- those tune "
                          "Wirtinger-flow internals (pupil update, step schedule, step_max retries)")
    if recover_pupil and use_reconstruction_agent:
        raise ValueError("recover_pupil is not wired together with use_reconstruction_agent -- "
                          "reconstruct() ignores step_max under recover_pupil (nothing for the "
                          "agent's retry lever to adjust) and recovery_error is proven blind to "
                          "recover_pupil's own regression, see "
                          "agents/reconstruction_orchestrator.py's docstring")
    setups = {
        channel: config.default_setup(
            channel=channel, grid_size=grid_size, objective=objective,
            resolution_px=(crop, crop),
            row_index_base=row_index_base, col_index_base=col_index_base,
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
            row_index_base=setup.led_array.row_base, col_index_base=setup.led_array.col_base,
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
        if solver == "gd-amplitude":
            result = joint_calibration.reconstruct_gradient_descent(
                lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
                setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
                initial_object=initial_object,
            )
        elif use_reconstruction_agent:
            orchestrated = reconstruction_orchestrator.orchestrate_reconstruction(
                lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
                setup.objective.na, setup.wavelength_um, factor,
                iterations=iterations, max_attempts=max_attempts,
                dry_run=not agent_live, initial_object=initial_object,
                adaptive_step=adaptive_step,
            )
            result = orchestrated["result"]
            agent_attempts = orchestrated["attempts"]
        else:
            result = reconstruction.reconstruct(
                lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
                setup.objective.na, setup.wavelength_um, factor, iterations=iterations,
                initial_object=initial_object, recover_pupil=recover_pupil,
                adaptive_step=adaptive_step,
            )
        channels[channel] = {
            "object": result["object"],
            "history": result["history"],
            "n_leds_used": len(lr_images),
            "n_leds_expected": n_expected,
            "agent_attempts": agent_attempts,
            "pupil": result.get("pupil"),
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
    p.add_argument("--objective", choices=sorted(config.OBJECTIVES), default=config.DEFAULT_OBJECTIVE,
                   help="objective preset (default %(default)s, the one real captures use; "
                        "\"current\"/\"future\" are deprecated aliases, see config.OBJECTIVES)")
    p.add_argument("--crop", type=int, default=400,
                    help="the crop size named in the lab's own folder naming (...recortada_<crop>)")
    p.add_argument("--row-index-base", type=int, default=None,
                    help="first row number in the lab's fila<R>_col<C> filenames, if different from "
                         "column numbering (e.g. rows 13-21 vs cols 11-19 for the same on-axis-centered "
                         "scan) -- defaults to the same value as columns (1) when omitted")
    p.add_argument("--col-index-base", type=int, default=None,
                    help="first column number in the lab's fila<R>_col<C> filenames, if different from "
                         "row numbering -- defaults to the same value as rows (1) when omitted")
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
    p.add_argument("--recover-pupil", action="store_true",
                    help="use reconstruction.reconstruct's EPRY pupil-recovery mode (ou2014) per "
                         "channel instead of assuming the ideal NA-limited pupil -- see that "
                         "function's docstring and tests/test_epry_pupil_recovery.py for its honest, "
                         "modest measured benefit (and its real risk of REGRESSING an already-good "
                         "channel at this project's small testbed scale). Mutually exclusive with "
                         "--use-reconstruction-agent (a real information deficit, not just "
                         "unimplemented -- see agents/reconstruction_orchestrator.py's docstring) "
                         "and with --adaptive-step (EPRY has its own self-scaling step).")
    p.add_argument("--adaptive-step", action="store_true",
                    help="use reconstruction.reconstruct's zuo2016 adaptive step-size mode per "
                         "channel instead of the fixed ramp -- see that function's docstring and "
                         "tests/test_adaptive_step_size.py: no clean win at light noise/few "
                         "iterations, but a real gain at heavy noise (peak_photon_count<=3) and "
                         "many iterations (>=400). CAN be combined with --use-reconstruction-agent "
                         "(2026-09-18: resolved, see orchestrate_reconstruction's docstring). "
                         "Mutually exclusive with --recover-pupil.")
    p.add_argument("--solver", choices=["wirtinger", "gd-amplitude"], default="wirtinger",
                    help="reconstruction solver per channel. 'gd-amplitude' = Adam gradient descent on "
                         "the amplitude loss (joint_calibration.reconstruct_gradient_descent): beat the "
                         "Wirtinger flow under Poisson noise on synthetic and real-image test objects "
                         "(roadmap milestones 11/13) but is NOT validated on real lab data, and blue "
                         "with moderate/heavy noise fails for every solver. Use ~100 --iterations "
                         "(full-batch steps). Mutually exclusive with --recover-pupil, --adaptive-step "
                         "and --use-reconstruction-agent.")
    p.add_argument("--chromatic-report", action="store_true",
                    help="run src/ptyco_full_simulator/chromatic_diagnostics.py's "
                         "chromatic_registration_report on the 3 reconstructed channels (roadmap "
                         "open question #2 -- does the real objective have chromatic aberration) "
                         "and save chromatic_report.json to --output-dir. See that module's "
                         "docstring for the honest caveat: accuracy depends on this run's own "
                         "reconstruction quality, not a silent oracle.")
    p.add_argument("--output-dir", default="results/reconstruct_multispectral_independent")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    os.makedirs(args.output_dir, exist_ok=True)

    run = reconstruct_all_channels(
        args.data_root, args.grid_size, objective=args.objective,
        crop=args.crop, iterations=args.iterations, tie_defocus_um=args.tie_defocus_um,
        row_index_base=args.row_index_base, col_index_base=args.col_index_base,
        use_reconstruction_agent=args.use_reconstruction_agent,
        agent_live=args.agent_live, max_attempts=args.max_attempts,
        recover_pupil=args.recover_pupil, adaptive_step=args.adaptive_step,
        solver=args.solver,
    )
    print(f"grid={args.grid_size}x{args.grid_size}  objective={args.objective}  "
          f"shared_upsampling_factor={run['factor']}  hr_shape={run['hr_shape']}  "
          f"hr_pixel={run['hr_pixel_um']:.4f}um  (registered: all 3 channels share this grid)")

    metrics_out = {
        "factor": run["factor"], "hr_pixel_um": run["hr_pixel_um"], "hr_shape": list(run["hr_shape"]),
        "tie_defocus_um": args.tie_defocus_um,
        "use_reconstruction_agent": args.use_reconstruction_agent,
        "recover_pupil": args.recover_pupil, "adaptive_step": args.adaptive_step,
        "solver": args.solver, "channels": {},
    }
    complex_objects = {}
    pupils = {}
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
        if c["pupil"] is not None:
            print(f"    recovered pupil phase range: "
                  f"[{np.angle(c['pupil']).min():.3f}, {np.angle(c['pupil']).max():.3f}] rad")
            pupils[channel] = c["pupil"]
        io_utils.save_complex_as_images(c["object"], args.output_dir, channel)
        complex_objects[channel] = c["object"]
        metrics_out["channels"][channel] = {
            "convergence": conv, "history": c["history"], "agent_attempts": c["agent_attempts"],
            "n_leds_used": c["n_leds_used"], "n_leds_expected": c["n_leds_expected"],
        }

    if args.chromatic_report:
        wavelengths_um_cd = {ch: config.CHANNEL_WAVELENGTH_NM[ch] / 1000.0 for ch in CHANNEL_ORDER}
        chromatic_report = cd.chromatic_registration_report(complex_objects, run["hr_pixel_um"], wavelengths_um_cd)
        for pair, entry in chromatic_report.items():
            dy, dx = entry["lateral_shift_px"]
            print(f"  chromatic {pair}: lateral_shift=({dy:.3f}, {dx:.3f})px  "
                  f"focus_offset={entry['focus']['offset_um']:.2f}um "
                  f"(corr_at_offset={entry['focus']['correlation_at_offset']:.3f} vs. "
                  f"corr_at_zero={entry['focus']['correlation_at_zero']:.3f})")
        with open(os.path.join(args.output_dir, "chromatic_report.json"), "w") as fh:
            json.dump(
                {pair: {"lateral_shift_px": list(entry["lateral_shift_px"]), "focus": entry["focus"]}
                 for pair, entry in chromatic_report.items()},
                fh, indent=2,
            )

    _save_rgb_composite(run["channels"], args.output_dir)
    np.savez(os.path.join(args.output_dir, "complex_objects.npz"), **complex_objects)
    if pupils:
        np.savez(os.path.join(args.output_dir, "recovered_pupils.npz"), **pupils)
    with open(os.path.join(args.output_dir, "metrics.json"), "w") as fh:
        json.dump(metrics_out, fh, indent=2)
    print(f"wrote results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

from ptyco_full_simulator import config, forward_model, io_utils, joint_calibration, led_array, metrics, optics  # noqa: E402
from ptyco_full_simulator import propagation as prop, reconstruction  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents"))
import reconstruction_orchestrator  # noqa: E402


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
    p.add_argument("--tie-defocus-um", type=float, default=None,
                    help="if set, also simulate a +/- this many um on-axis defocused capture pair, "
                         "solve Transport of Intensity Equation (propagation.solve_tie), and use "
                         "that phase (instead of the default zero) to initialize the FPM solver -- "
                         "see docs/roadmap_agentic_multispectral_pipeline.md section 1 point 6 for "
                         "why the default initialization fails on weak/low-spatial-frequency phase "
                         "objects, and tests/test_tie_informed_initialization.py for how reliably "
                         "this fixes it. CAVEAT (same doc): whether running the full --iterations "
                         "after this better start further helps or slowly hurts is inconsistent -- "
                         "not resolved yet, inspect metrics.json's history yourself rather than "
                         "trusting it blindly for this mode.")
    p.add_argument("--use-reconstruction-agent", action="store_true",
                    help="use agents/reconstruction_orchestrator.py's milestone-3 agent instead of a "
                         "single reconstruction.reconstruct call: it decides accept/retry-with-"
                         "different-step_max/give_up after each attempt, up to --max-attempts. "
                         "Defaults to a canned dry-run decision (accept-first-attempt, matching a "
                         "single plain call); pass --agent-live for a real (billed) claude -p call, "
                         "see agents/reconstruction_orchestrator.py's docstring for measured cost.")
    p.add_argument("--agent-live", action="store_true",
                    help="make --use-reconstruction-agent call the real agent instead of a dry-run "
                         "stub -- COSTS MONEY per attempt, see agents/reconstruction_orchestrator.py")
    p.add_argument("--max-attempts", type=int, default=3,
                    help="only used with --use-reconstruction-agent")
    p.add_argument("--recover-pupil", action="store_true",
                    help="use agents/../reconstruction.reconstruct's EPRY pupil-recovery mode "
                         "(ou2014) instead of assuming the ideal NA-limited pupil -- see that "
                         "function's docstring and tests/test_epry_pupil_recovery.py for what it "
                         "does and its honest, modest measured benefit (and, at this project's "
                         "small testbed scale with no aberration present, its real risk of "
                         "REGRESSING an already-good reconstruction). Mutually exclusive with "
                         "--use-reconstruction-agent -- NOT just unimplemented: reconstruct() "
                         "ignores step_max under recover_pupil, so the agent's only lever (retry "
                         "with a new step_max) has nothing to adjust, and recovery_error (the "
                         "agent's only signal) is proven blind to recover_pupil's own regression "
                         "(see agents/reconstruction_orchestrator.py's docstring) -- combining them "
                         "would launder a known-blind signal into a false sense of automated safety. "
                         "Also mutually exclusive with --adaptive-step (EPRY has its own "
                         "self-scaling step).")
    p.add_argument("--adaptive-step", action="store_true",
                    help="use reconstruction.reconstruct's zuo2016 adaptive step-size mode instead "
                         "of the fixed ramp -- see that function's docstring and "
                         "tests/test_adaptive_step_size.py: no clean win at light noise/few "
                         "iterations, but a real, reproducible gain (8/8 seeds) at heavy noise "
                         "(peak_photon_count<=3) and many iterations (>=400). Can be combined with "
                         "--use-reconstruction-agent (2026-09-18: resolved -- step_max remains a "
                         "meaningful starting point for the agent to retry with even when the "
                         "schedule self-adjusts, see orchestrate_reconstruction's docstring). "
                         "Mutually exclusive with --recover-pupil.")
    p.add_argument("--solver", choices=["wirtinger", "gd-amplitude"], default="wirtinger",
                    help="reconstruction solver. 'gd-amplitude' = Adam gradient descent on the amplitude "
                         "loss (joint_calibration.reconstruct_gradient_descent): beat the Wirtinger flow "
                         "under Poisson noise on synthetic and real-image test objects (roadmap "
                         "milestones 11/13) but is NOT validated on real lab data, and blue with "
                         "moderate/heavy noise fails for every solver. Use ~100 --iterations "
                         "(full-batch steps). Mutually exclusive with --recover-pupil, --adaptive-step "
                         "and --use-reconstruction-agent.")
    p.add_argument("--output-dir", default="results/simulate_and_reconstruct")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.recover_pupil and args.use_reconstruction_agent:
        raise SystemExit("--recover-pupil is not wired together with --use-reconstruction-agent "
                          "-- reconstruct() ignores step_max under recover_pupil (nothing for the "
                          "agent's retry lever to adjust) and recovery_error is proven blind to "
                          "recover_pupil's own regression, see "
                          "agents/reconstruction_orchestrator.py's docstring")
    if args.recover_pupil and args.adaptive_step:
        raise SystemExit("--recover-pupil and --adaptive-step are mutually exclusive "
                          "(reconstruction.reconstruct ignores step_max/adaptive_step when "
                          "recover_pupil=True -- see that function's docstring)")
    if args.solver == "gd-amplitude" and (args.recover_pupil or args.adaptive_step or args.use_reconstruction_agent):
        raise SystemExit("--solver gd-amplitude cannot be combined with --recover-pupil, --adaptive-step "
                          "or --use-reconstruction-agent -- those tune Wirtinger-flow internals "
                          "(pupil update, step schedule, step_max retries)")
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
    if args.solver == "gd-amplitude":
        # The GD solver models each LED at its exact k; simulating with the bin-rounded
        # forward_model.simulate_lr_stack would hand it data from a different model
        # (phase corr ~0.12 vs ~0.99 on matched data), so use the continuous-k simulator.
        lr_images = joint_calibration.simulate_lr_stack_continuous(
            hr_object, hr_pixel_um, led_grid, (args.lr_size, args.lr_size),
            setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
            peak_photon_count=args.peak_photon_count, rng=rng,
        )
    else:
        lr_images = forward_model.simulate_lr_stack(
            hr_object, hr_pixel_um, led_grid, (args.lr_size, args.lr_size),
            setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
            peak_photon_count=args.peak_photon_count, rng=rng,
        )
    print(f"simulated {len(lr_images)} LR images")

    initial_object = None
    if args.tie_defocus_um is not None:
        dz = args.tie_defocus_um
        i_focus = np.abs(hr_object) ** 2
        i_plus = np.abs(prop.angular_spectrum_propagate(hr_object, dz, hr_pixel_um, setup.wavelength_um)) ** 2
        i_minus = np.abs(prop.angular_spectrum_propagate(hr_object, -dz, hr_pixel_um, setup.wavelength_um)) ** 2
        di_dz = (i_plus - i_minus) / (2 * dz)
        tie_phase = prop.solve_tie(di_dz, i_focus, hr_pixel_um, setup.wavelength_um)

        center = led_grid[0]
        center_image = lr_images[(center["row"], center["col"])]
        amp0 = np.sqrt(np.clip(center_image, 0, None))
        amp0_hr = np.kron(amp0, np.ones((factor, factor)))
        initial_object = (amp0_hr * np.exp(1j * tie_phase)).astype(complex)
        print(f"TIE-informed init: defocus=+/-{dz}um, on-axis pair simulated from the same known object")

    agent_attempts = None
    if args.solver == "gd-amplitude":
        result = joint_calibration.reconstruct_gradient_descent(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=args.iterations,
            initial_object=initial_object,
        )
    elif args.use_reconstruction_agent:
        orchestrated = reconstruction_orchestrator.orchestrate_reconstruction(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor,
            iterations=args.iterations, max_attempts=args.max_attempts,
            dry_run=not args.agent_live, initial_object=initial_object,
            adaptive_step=args.adaptive_step,
        )
        result = orchestrated["result"]
        agent_attempts = orchestrated["attempts"]
        for i, attempt in enumerate(agent_attempts):
            print(f"agent attempt {i + 1}/{len(agent_attempts)}: step_max={attempt['step_max']}  "
                  f"decision={attempt['decision']['action']}  reasoning={attempt['decision']['reasoning']!r}")
    else:
        result = reconstruction.reconstruct(
            lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
            setup.objective.na, setup.wavelength_um, factor, iterations=args.iterations,
            initial_object=initial_object, recover_pupil=args.recover_pupil,
            adaptive_step=args.adaptive_step,
        )
        if args.recover_pupil:
            print("EPRY pupil recovery: recovered pupil phase range "
                  f"[{np.angle(result['pupil']).min():.3f}, {np.angle(result['pupil']).max():.3f}] rad")

    gt_metrics = metrics.compare_to_ground_truth(result["object"], hr_object)
    conv = metrics.convergence_summary(result["history"])
    print("convergence:", json.dumps(conv, indent=2))
    print("vs. ground truth:", json.dumps(gt_metrics, indent=2))

    io_utils.save_complex_as_images(result["object"], args.output_dir, "reconstructed")
    io_utils.save_complex_as_images(hr_object, args.output_dir, "ground_truth")
    with open(os.path.join(args.output_dir, "metrics.json"), "w") as fh:
        json.dump({
            "convergence": conv, "vs_ground_truth": gt_metrics,
            "history": result["history"], "agent_attempts": agent_attempts,
            "setup": {
                "channel": args.channel, "wavelength_nm": setup.wavelength_nm,
                "grid_size": args.grid_size, "objective": args.objective,
                "na": setup.objective.na, "magnification": setup.objective.magnification,
                "lr_size": args.lr_size, "upsampling_factor": factor,
                "hr_pixel_um": hr_pixel_um, "lr_pixel_um": setup.lr_pixel_size_um,
                "iterations": args.iterations, "peak_photon_count": args.peak_photon_count,
                "seed": args.seed, "tie_defocus_um": args.tie_defocus_um,
                "use_reconstruction_agent": args.use_reconstruction_agent,
                "recover_pupil": args.recover_pupil, "adaptive_step": args.adaptive_step,
                "solver": args.solver,
            },
        }, fh, indent=2)
    print(f"wrote results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

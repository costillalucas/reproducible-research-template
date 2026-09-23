"""Extends tests/test_multispectral_end_to_end.py's first test (real solver,
through couple_rgb_channels) into an OPL-magnitude sweep, WF vs GD-amplitude,
to find where the COUPLED pipeline breaks -- not just an isolated channel
(see docs/roadmap_agentic_multispectral_pipeline.md milestone 19's phase
ceiling sweep, which used metrics.compare_to_ground_truth and hit a wrapping
artifact above ~pi rad; this uses correlation against the true, UNWRAPPED
thickness map instead, which has no such wrap issue)."""
import sys, os, json, time
sys.path.insert(0, "scripts")
sys.path.insert(0, "src")
from functools import partial
from multiprocessing import Pool
import numpy as np
from ptyco_full_simulator import config, forward_model, led_array, optics, reconstruction
from ptyco_full_simulator import joint_calibration as jc
from ptyco_full_simulator import multispectral as ms

A_TRUE, B_TRUE = 1.34, 0.004
WAVELENGTHS_UM = {ch: config.CHANNEL_WAVELENGTH_NM[ch] / 1000.0 for ch in ("red", "green", "blue")}
T_BASE = 0.012  # same base thickness amplitude as the existing end-to-end test


def _build_test_object(hr_shape, background_rows, t_scale):
    h, w = hr_shape
    y, x = np.mgrid[0:h, 0:w].astype(float)
    yc, xc = y / h - 0.5, x / w - 0.5
    amp = 0.4 + 0.6 * np.exp(-((xc - 0.1) ** 2 + (yc + 0.05) ** 2) / (2 * 0.08 ** 2))
    amp += 0.3 * np.exp(-((xc + 0.15) ** 2 + (yc - 0.1) ** 2) / (2 * 0.05 ** 2))
    amp = np.clip(amp, 0, 1)
    ramp = np.clip((y - background_rows) / 4.0, 0, 1)
    t_true = T_BASE * t_scale * np.sin(2 * np.pi * xc) * np.cos(2 * np.pi * yc) * ramp
    t_true -= t_true.min()
    return amp, t_true


def job(a, crop=16, wf_iters=100, gd_iters=100):
    t0 = time.time()
    grid_size, background_rows = 9, 4
    setups = {ch: config.default_setup(channel=ch, grid_size=grid_size, objective="2_5x_na007",
                                        resolution_px=(crop, crop)) for ch in WAVELENGTHS_UM}
    factor = optics.shared_upsampling_factor(list(setups.values()))
    hr_pixel_um = optics.actual_hr_pixel_size_um(next(iter(setups.values())), factor)
    hr_shape = optics.hr_shape((crop, crop), factor)
    amp, t_true = _build_test_object(hr_shape, background_rows, a["t_scale"])
    background_mask = np.zeros(hr_shape, dtype=bool)
    background_mask[:background_rows, :] = True
    rng = np.random.default_rng(a["seed"])

    phases_wrapped = {}
    max_phase_true = {}
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        setup = setups[channel]
        opl_true = (A_TRUE + B_TRUE / wavelength_um ** 2) * t_true
        phase_true = 2 * np.pi / wavelength_um * opl_true
        max_phase_true[channel] = float(np.abs(phase_true).max())
        obj = amp * np.exp(1j * phase_true)
        led_grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
        lr_images = forward_model.simulate_lr_stack(obj, hr_pixel_um, led_grid, (crop, crop),
                                                     setup.lr_pixel_size_um, setup.objective.na,
                                                     setup.wavelength_um, peak_photon_count=a["peak"],
                                                     rng=np.random.default_rng(rng.integers(1 << 30)))
        if a["solver"] == "wirtinger":
            result = reconstruction.reconstruct(lr_images, led_grid, hr_pixel_um, setup.lr_pixel_size_um,
                                                setup.objective.na, setup.wavelength_um, factor,
                                                iterations=wf_iters)
        else:
            # forward_model.simulate_lr_stack (WF's convention) needs converting to jc's expected
            # intensity units before feeding jc.* -- see plan_p3_object_phase_geometry.job()'s
            # identical `sc`/`meas` conversion; jc.initial_object_from_center_led's own docstring
            # flags this unit mismatch explicitly. Missing this made GD-amplitude look uniformly
            # broken in an earlier, buggy version of this sweep.
            sc = (hr_shape[0] * hr_shape[1]) / (crop * crop)
            meas = {k: v / sc ** 2 for k, v in lr_images.items()}
            init = jc.initial_object_from_center_led(meas[(led_grid[0]["row"], led_grid[0]["col"])], hr_shape)
            result = jc.reconstruct_and_calibrate(meas, led_grid, hr_shape, hr_pixel_um, (crop, crop),
                                                  setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um,
                                                  init, n_iterations=gd_iters, calibrate_leds=False, loss="amplitude")
        phases_wrapped[channel] = np.angle(result["object"])

    coupled = ms.couple_rgb_channels(phases_wrapped, WAVELENGTHS_UM, background_mask, baseline_index_A=A_TRUE)
    t_estimate = coupled["resolved"]["thickness_um"]
    corr = float(np.corrcoef(t_estimate.ravel(), t_true.ravel())[0, 1])

    # same coupling, TV refinement OFF -- isolates refine_opl_tv (vs. the wrap search / dispersion
    # fit / green-channel averaging, which are identical in both arms) as milestone 20's suspect #1
    coupled_norf = ms.couple_rgb_channels(phases_wrapped, WAVELENGTHS_UM, background_mask,
                                          baseline_index_A=A_TRUE, refine=False)
    t_estimate_norf = coupled_norf["resolved"]["thickness_um"]
    corr_norefine = float(np.corrcoef(t_estimate_norf.ravel(), t_true.ravel())[0, 1])

    # naive k=0 baseline for context (same as the existing test's second test)
    naive_opls = []
    for channel, wavelength_um in WAVELENGTHS_UM.items():
        referenced = ms.reference_phase_to_background(phases_wrapped[channel], background_mask)
        naive_opls.append(referenced * wavelength_um / (2 * np.pi))
    naive_fit = ms.fit_cauchy_dispersion(list(WAVELENGTHS_UM.values()), naive_opls)
    t_naive = ms.resolve_thickness_and_dispersion(naive_fit["C"], naive_fit["D"], A_TRUE)["thickness_um"]
    corr_naive = float(np.corrcoef(t_naive.ravel(), t_true.ravel())[0, 1])

    # diagnostic: fraction of pixels where the winning wrap number is nonzero (real unwrapping engaged)
    referenced = {ch: ms.reference_phase_to_background(phases_wrapped[ch], background_mask) for ch in WAVELENGTHS_UM}
    rg = ms.search_wrap_numbers(referenced["red"], referenced["green"], WAVELENGTHS_UM["red"], WAVELENGTHS_UM["green"])
    gb = ms.search_wrap_numbers(referenced["green"], referenced["blue"], WAVELENGTHS_UM["green"], WAVELENGTHS_UM["blue"])
    any_nonzero_k = (rg["K1"] != 0) | (rg["K2"] != 0) | (gb["K1"] != 0) | (gb["K2"] != 0)
    frac_nonzero_k = float(np.mean((rg["K1"] != 0) | (rg["K2"] != 0)))

    # corr_coupled_masked: exclude pixels either pair assigned a nonzero wrap number, before
    # scoring (fit_cauchy_dispersion/resolve_thickness_and_dispersion are per-pixel -- see their
    # docstrings -- so masking post-hoc for scoring doesn't touch other pixels' estimates). This
    # is the diagnostic that found milestone 20's real mechanism: a handful of spurious nonzero-k
    # pixels can dominate a whole-image Pearson correlation even when correct almost everywhere.
    keep = ~any_nonzero_k
    corr_masked = (float(np.corrcoef(t_estimate[keep].ravel(), t_true[keep].ravel())[0, 1])
                  if keep.sum() >= 2 else float("nan"))
    frac_masked_out = float(np.mean(any_nonzero_k))

    # diagnostic #2 (suspect #2, per advisor): reference_phase_to_background subtracts an
    # ARITHMETIC mean of already-wrapped background phase -- wrong if those values straddle
    # +/-pi. Compare to the correct circular mean; a large gap here (not noise "structure")
    # could be what's injecting spurious nonzero k at scale=1-2, where no real wrap exists.
    piston_diag = {}
    for ch in WAVELENGTHS_UM:
        bg = phases_wrapped[ch][background_mask]
        piston_arith = float(np.mean(bg))
        piston_circular = float(np.angle(np.mean(np.exp(1j * bg))))
        piston_diag[ch] = {"arith": piston_arith, "circular": piston_circular,
                           "gap": float(ms.wrap_phase(piston_arith - piston_circular)),
                           "straddles_pi": bool(bg.max() - bg.min() > np.pi)}

    return {**a, "hr": list(hr_shape), "max_phase_blue_pi": max_phase_true["blue"] / np.pi,
            "corr_coupled": corr, "corr_coupled_norefine": corr_norefine, "corr_naive": corr_naive,
            "corr_coupled_masked": corr_masked, "frac_masked_out": frac_masked_out,
            "frac_nonzero_k_rg": frac_nonzero_k, "piston_diag": piston_diag, "secs": time.time() - t0}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--procs", type=int, default=2)
    args = ap.parse_args()
    if args.smoke:
        for solver in ("wirtinger", "gd-amplitude"):
            r = job(dict(t_scale=8, peak=1000.0, seed=0, solver=solver), crop=16, wf_iters=5, gd_iters=5)
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                   if k in ("solver", "max_phase_blue_pi", "corr_coupled", "corr_naive", "frac_nonzero_k_rg", "secs")})
        raise SystemExit
    J = []
    for scale in (1, 2, 4, 8, 16, 24):
        for solver in ("wirtinger", "gd-amplitude"):
            for s in range(4):
                J.append(dict(t_scale=scale, peak=1000.0, seed=s, solver=solver))
    print(len(J), "jobs", flush=True)
    res = []
    with Pool(args.procs) as p:
        for r in p.imap(partial(job), J, chunksize=1):
            res.append(r)
            if args.out:
                json.dump(res, open(args.out, "w"))
            print(len(res), "/", len(J), "done", flush=True)

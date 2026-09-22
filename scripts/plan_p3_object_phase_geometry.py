"""Point 3 of the 2026-09-21 next steps: does the Adam/amplitude-loss
advantage over Wirtinger flow (WF) hold across objects, phase magnitudes,
amplitude contrast and geometry? Skeleton for the plan in
docs/plan_experimentos_punto3_y_hardware_real.md (E1-E4).

Data are bin-aligned (same as milestones 11-14: fair to both solvers, not
realistic -- see plan_p4_led_position_error.py for exact-k data).

  python3 scripts/plan_p3_object_phase_geometry.py --list
  python3 scripts/plan_p3_object_phase_geometry.py --dry-run        # ~10-20 s
  python3 scripts/plan_p3_object_phase_geometry.py --exp E1 --out e1.json [--procs 2]
"""
import argparse, json, time, os
from functools import partial
from plan_common import *  # noqa (sets single-thread env, sys.path)
from multiprocessing import Pool

PI = np.pi
PEAKS = (100.0, 1000.0)


def jobs_for(exp, seeds):
    S = range(seeds)
    J = []
    if exp == "E1":  # object kind x phase magnitude x photons
        for kind in ("lena_map", "map_lena", "phase_only", "blob", "siemens_star"):
            for ph in (0.05, 0.1, 0.2, 0.3):
                for pk in PEAKS:
                    for s in S:
                        J.append(dict(exp=exp, kind=kind, phase_max=ph * PI, peak=pk, seed=s))
    elif exp == "E2":  # amplitude contrast (min_amplitude 1.0 = phase-only) x weak/strong phase
        for ma in (0.1, 0.3, 0.6, 0.9, 1.0):
            for ph in (0.1, 0.3):
                for pk in PEAKS:
                    for s in S:
                        J.append(dict(exp=exp, kind="lena_map", min_amp=ma, phase_max=ph * PI, peak=pk, seed=s))
    elif exp == "E3a":  # natural z sweep, 9x9 @ 6mm (HR canvas GROWS/SHRINKS with z: confounded, hs is logged)
        for obj in ("current", "future"):
            for z in (50, 60, 70, 80, 90, 100):
                for pk in PEAKS:
                    for s in S:
                        J.append(dict(exp=exp, objective=obj, z_mm=z, peak=pk, seed=s))
    elif exp == "E3b":  # fixed span (=fixed HR canvas) per objective, vary LED count => overlap AND redundancy move together
        for obj in ("current", "future"):
            for g in (7, 9, 11, 15, 21):
                for pk in PEAKS:
                    for s in S:
                        J.append(dict(exp=exp, objective=obj, grid=g, span_mm=48.0, peak=pk, seed=s))
    elif exp == "E4":  # channel: does red/blue change the E1 conclusions? (blue failed under noise before)
        for ch in ("red", "green", "blue"):
            for pk in (20.0, 100.0, 1000.0):
                for s in S:
                    J.append(dict(exp=exp, channel=ch, peak=pk, seed=s))
    return J


def job(a, wf_epochs=200, gd_iters=100, crop=32):
    t = time.time()
    setup = build_setup(a.get("channel", "green"), a.get("grid", 9), a.get("objective", "current"), crop,
                        span_mm=a.get("span_mm"), z_mm=a.get("z_mm"))
    factor, hp, hs = geometry(setup, crop)
    truth, _ = make_object(a.get("kind", "lena_map"), hs, a.get("phase_max", 0.3 * PI), a.get("min_amp", 0.1))
    grid = bin_align(led_array.build_led_grid(setup.led_array, setup.wavelength_um), hs, hp)
    lp, na, wl = setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um
    raw = forward_model.simulate_lr_stack(truth, hp, grid, (crop, crop), lp, na, wl,
                                          peak_photon_count=a["peak"], rng=np.random.default_rng(a["seed"]))
    wf = reconstruction.reconstruct(raw, grid, hp, lp, na, wl, factor, iterations=wf_epochs)["object"]
    sc = (hs[0] * hs[1]) / (crop * crop)
    meas = {k: v / sc ** 2 for k, v in raw.items()}
    init = jc.initial_object_from_center_led(meas[(grid[0]["row"], grid[0]["col"])], hs)
    gd = jc.reconstruct_and_calibrate(meas, grid, hs, hp, (crop, crop), lp, na, wl, init,
                                      n_iterations=gd_iters, calibrate_leds=False, loss="amplitude")["object"]
    w, g = score(wf, truth), score(gd, truth)
    flat = score(np.abs(truth).astype(complex), truth)["phase_rmse"]  # RMSE of a "no phase" guess: the bar to beat
    return {**a, "hr": list(hs), "n_leds": len(grid),
            "wf_phase_rmse": w["phase_rmse"], "gd_phase_rmse": g["phase_rmse"], "flat_phase_rmse": flat,
            "overlap": led_array.adjacent_led_overlap_ratio(setup.led_array, wl, na),
            "redundancy": len(grid) * crop * crop / (hs[0] * hs[1]),
            "wf_phase": w["phase_corr"], "wf_amp": w["amp_corr"],
            "gd_phase": g["phase_corr"], "gd_amp": g["amp_corr"], "secs": time.time() - t}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="E1", choices=["E1", "E2", "E3a", "E3b", "E4"])
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--list", action="store_true", help="print job counts per experiment and exit")
    ap.add_argument("--dry-run", action="store_true", help="1 tiny job (16px crop, 3 epochs/iters) per experiment")
    ap.add_argument("--wf-epochs", type=int, default=200)
    ap.add_argument("--gd-iters", type=int, default=100)
    ap.add_argument("--crop", type=int, default=32)
    ap.add_argument("--where", action="append", default=[],
                    help="keep only jobs whose field matches, e.g. --where kind=lena_map,blob --where grid=7,9 "
                         "(phase_max is matched as multiples of pi via phase_pi)")
    args = ap.parse_args()
    if args.list:
        for e in ("E1", "E2", "E3a", "E3b", "E4"):
            print(e, len(jobs_for(e, args.seeds)), "jobs at", args.seeds, "seeds")
        raise SystemExit
    if args.dry_run:
        for e in ("E1", "E2", "E3a", "E3b", "E4"):
            r = job(jobs_for(e, 1)[0], wf_epochs=3, gd_iters=3, crop=16)
            print(e, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                      if k in ("kind", "objective", "grid", "hr", "overlap", "wf_phase", "gd_phase", "secs")})
        raise SystemExit
    opts = dict(wf_epochs=args.wf_epochs, gd_iters=args.gd_iters, crop=args.crop)
    J = jobs_for(args.exp, args.seeds)
    for w in args.where:
        key, vals = w.split("=", 1)
        vals = vals.split(",")
        def _keep(a):
            v = round(a["phase_max"] / PI, 4) if key == "phase_pi" else a.get(key)
            if isinstance(v, (int, float)):
                return any(abs(v - float(x)) < 1e-9 for x in vals)
            return str(v) in vals
        J = [a for a in J if _keep(a)]
    J.sort(key=lambda a: a["seed"])  # complete seed 0 first, so a cut-short run is still a full design at n=1
    res = []
    with Pool(args.procs) as p:
        for r in p.imap(partial(job, **opts), J, chunksize=1):
            res.append(r)
            if args.out:  # incremental: a killed run keeps what it finished
                json.dump(res, open(args.out, "w"))
            print(len(res), "/", len(J), "jobs done", flush=True)

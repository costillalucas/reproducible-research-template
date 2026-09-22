"""Impact of LED position error on exact-k data (the inverse-crime caveat of
milestones 11-14) and how much rigid AD-SC calibration recovers. Skeleton for
the plan in docs/plan_experimentos_punto3_y_hardware_real.md (P1-P4).

Data: continuous-k forward model + Poisson noise (what hardware produces),
generated from TRUE LED positions = nominal geometry + physical errors. Every
arm is handed the NOMINAL grid except `gd_true` (oracle upper bound).
Arms: wf (bin-rounds nominal k internally), gd_nominal (fixed nominal),
gd_rigid (joint object + similarity transform), gd_perled, gd_true.
Reported vs `k_err_bins` = RMS(true - nominal) in HR spectrum bins.

  python3 scripts/plan_p4_led_position_error.py --list
  python3 scripts/plan_p4_led_position_error.py --dry-run          # ~10 s
  python3 scripts/plan_p4_led_position_error.py --exp P1 --out p1.json [--procs 2]
"""
import argparse, json, time
from functools import partial
from plan_common import *  # noqa
from multiprocessing import Pool

PI = np.pi
# Realistic-ish lab magnitudes (mm / deg / fraction); zero row = control.
ERR = {
    "none":       dict(),
    "jitter0.05": dict(jitter_mm=0.05),   # printed-board placement tolerance
    "jitter0.2":  dict(jitter_mm=0.2),
    "offset0.5":  dict(offset_mm=(0.5, -0.3)),   # array not centered on axis
    "offset2":    dict(offset_mm=(2.0, -1.2)),
    "rot1deg":    dict(rot_deg=1.0),
    "rot3deg":    dict(rot_deg=3.0),
    "z+2mm":      dict(z_err_mm=2.0),     # height measured with a ruler
    "z+7mm":      dict(z_err_mm=7.0),
    "pitch+1%":   dict(pitch_err_frac=0.01),
    "combined":   dict(jitter_mm=0.1, offset_mm=(1.0, -0.6), rot_deg=1.5, z_err_mm=3.0, pitch_err_frac=0.005),
}


def jobs_for(exp, seeds):
    S = range(seeds)
    J = []
    if exp == "P1":   # error type/magnitude sweep at moderate noise, green
        for name in ERR:
            for s in S:
                J.append(dict(exp=exp, err=name, peak=1000.0, seed=s))
    elif exp == "P2":  # 'combined' error x photons x channel: does noise break calibration?
        for ch in ("green", "red", "blue"):
            for pk in (100.0, 1000.0, 10000.0):
                for s in S:
                    J.append(dict(exp=exp, err="combined", channel=ch, peak=pk, seed=s))
    elif exp == "P3":  # calibration-init robustness: scale the 'combined' error 0.1x..2x (~0.15-2.9 bins at 32px; finds the recovery cliff)
        for m in (0.1, 0.25, 0.5, 1, 2):
            for s in S:
                J.append(dict(exp=exp, err="combined", err_scale=m, peak=1000.0, seed=s))
    elif exp == "P4":  # crop-size dependence of rigid calibration (small crops overfit / weak k signal)
        for crop in (16, 32, 48):
            for s in S:
                J.append(dict(exp=exp, err="combined", crop=crop, peak=1000.0, seed=s))
    return J


def scaled(kw, m):
    out = {}
    for k, v in kw.items():
        out[k] = tuple(x * m for x in v) if isinstance(v, tuple) else v * m
    return out


def job(a, wf_epochs=200, gd_iters=100, cal_iters=150, crop_default=32):
    t = time.time()
    crop = a.get("crop", crop_default)
    setup = build_setup(a.get("channel", "green"), 9, "current", crop, span_mm=48.0)
    factor, hp, hs = geometry(setup, crop)
    lp, na, wl = setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um
    rng = np.random.default_rng(1000 + a["seed"])
    truth, _ = make_object("lena_map", hs, 0.3 * PI)
    nominal = led_array.build_led_grid(setup.led_array, wl)
    true_grid, k_err = perturbed_grid(setup, wl, hs, hp, rng, **scaled(ERR[a["err"]], a.get("err_scale", 1.0)))
    meas = simulate_exact_k(truth, hp, true_grid, (crop, crop), lp, na, wl, peak=a["peak"], rng=rng)
    init = jc.initial_object_from_center_led(meas[(nominal[0]["row"], nominal[0]["col"])], hs)
    run = lambda grid, cal, model="rigid", it=gd_iters: jc.reconstruct_and_calibrate(
        meas, grid, hs, hp, (crop, crop), lp, na, wl, init, n_iterations=it, calibrate_leds=cal,
        led_model=model, warmup_iterations=20 if cal else 0, loss="amplitude")
    res = {"wf": reconstruction.reconstruct({k: v * (hs[0] * hs[1] / crop ** 2) ** 2 for k, v in meas.items()},
                                            nominal, hp, lp, na, wl, factor, iterations=wf_epochs)["object"]}
    res["gd_nominal"] = run(nominal, False)["object"]
    rig = run(nominal, True, "rigid", cal_iters)
    res["gd_rigid"] = rig["object"]
    pl = run(nominal, True, "per_led", cal_iters)
    res["gd_perled"] = pl["object"]
    res["gd_true"] = run(true_grid, False)["object"]
    out = {**a, "k_err_bins": k_err, "hr": list(hs), "n_leds": len(nominal),
           "k_err_after_rigid": k_error_bins(rig["led_grid"], true_grid, hs, hp),
           "k_err_after_perled": k_error_bins(pl["led_grid"], true_grid, hs, hp)}
    for name, obj in res.items():
        sc = score(obj, truth)
        out[name + "_phase"], out[name + "_amp"] = sc["phase_corr"], sc["amp_corr"]
    out["secs"] = time.time() - t
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="P1", choices=["P1", "P2", "P3", "P4"])
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="1 tiny job (16px, 3 iters) per experiment")
    ap.add_argument("--wf-epochs", type=int, default=200)
    ap.add_argument("--gd-iters", type=int, default=100)
    ap.add_argument("--cal-iters", type=int, default=150)
    args = ap.parse_args()
    if args.list:
        for e in ("P1", "P2", "P3", "P4"):
            print(e, len(jobs_for(e, args.seeds)), "jobs at", args.seeds, "seeds")
        raise SystemExit
    if args.dry_run:
        for e in ("P1", "P2", "P3", "P4"):
            j = jobs_for(e, 1)[-1 if e == "P1" else 0]
            j = {**j, "crop": 16}
            r = job(j, wf_epochs=3, gd_iters=3, cal_iters=3)
            print(e, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                      if k in ("err", "k_err_bins", "k_err_after_rigid", "wf_phase", "gd_nominal_phase",
                               "gd_rigid_phase", "gd_perled_phase", "gd_true_phase", "secs")})
        raise SystemExit
    opts = dict(wf_epochs=args.wf_epochs, gd_iters=args.gd_iters, cal_iters=args.cal_iters)
    J = jobs_for(args.exp, args.seeds)
    with Pool(args.procs) as p:
        res = p.map(partial(job, **opts), J, chunksize=1)
    if args.out:
        json.dump(res, open(args.out, "w"))
    print(len(res), "jobs done")

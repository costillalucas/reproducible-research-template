"""Audit of milestone 14's "gradient descent beats Wirtinger flow under noise"
(findings A2 and A3 of the 2026-09-21 adversarial audit).
  A2: was the Wirtinger-flow baseline mis-tuned? Sweep step_max (1,2,5,10,20)
      and the zuo2016 adaptive step for WF, against the same data.
  A3: is it the amplitude LOSS or the full-batch Adam SCHEME that helps? 2x2:
      loss (intensity | amplitude) x scheme (full-batch Adam | incremental
      per-LED Adam), all with the same gradient budget (BUDGET gradient
      evaluations per LED). Wirtinger flow uses the amplitude loss with
      incremental per-LED updates, so incremental+amplitude is the closest
      Adam analogue of it.
Learning rates of the four Adam cells are picked on TUNE_SEEDS (disjoint from
the evaluation seeds) at peak 100, then frozen. Reports, per run, the phase
correlation, phase_rmse_rad and amplitude correlation, plus the same three
for the initial object (amplitude of the centre LED, zero phase).

Usage (repo root, 1 core by design; results are appended as JSON lines so
the run can be split into short chunks and resumed):
  python3 scripts/audit_wf_tuning_and_gd_ablation.py tune out_tune.jsonl
  python3 scripts/audit_wf_tuning_and_gd_ablation.py eval out_eval.jsonl [obj] [peak]
  python3 scripts/audit_wf_tuning_and_gd_ablation.py summary out_tune.jsonl out_eval.jsonl
Data are bin-aligned (fair to both solvers, as in milestones 11-14), NOT the
exact-k regime of real hardware. Not part of the provenance pipeline."""
import os
os.environ["OMP_NUM_THREADS"] = "1"; os.environ["OPENBLAS_NUM_THREADS"] = "1"; os.environ["MKL_NUM_THREADS"] = "1"
import sys, json, time, numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "tests")
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, reconstruction, joint_calibration as jc
from ptyco_full_simulator.test_objects import lena_map_object
from test_joint_calibration import _synthetic_object

CROP = 16
PEAKS = (20, 100, 1000)
EVAL_SEEDS = range(6)
TUNE_SEEDS = (100,)
BUDGET = 100          # gradient evaluations per LED for every Adam cell
WF_EPOCHS = BUDGET   # WF epochs = gradient evaluations per LED, same as the Adam cells (wf_s20_200 = milestones 11-14 setting)
WF_VARIANTS = [("wf_s1", dict(step_max=1.0)), ("wf_s2", dict(step_max=2.0)), ("wf_s5", dict(step_max=5.0)),
               ("wf_s10", dict(step_max=10.0)), ("wf_s20", dict(step_max=20.0)),
               ("wf_adapt20", dict(step_max=20.0, adaptive_step=True)),
               ("wf_adapt5", dict(step_max=5.0, adaptive_step=True))]
LR_GRID = {"full": (0.01, 0.02, 0.04), "incr": (0.001, 0.002, 0.005)}


def make_problem(obj_kind, peak, seed):
    setup = config.default_setup(channel="green", grid_size=9, objective="2_5x_na007", resolution_px=(CROP, CROP))
    factor = optics.upsampling_factor(setup); hp = optics.actual_hr_pixel_size_um(setup, factor)
    hs = optics.hr_shape((CROP, CROP), factor)
    truth = _synthetic_object(hs) if obj_kind == "phantom" else lena_map_object(hs, phase_max_rad=0.3 * np.pi)[0]
    dk = 1 / (hs[1] * hp)
    grid = [{**e, "fx": round(e["fx"] / dk) * dk, "fy": round(e["fy"] / dk) * dk}
            for e in led_array.build_led_grid(setup.led_array, setup.wavelength_um)]
    lp, na, wl = setup.lr_pixel_size_um, setup.objective.na, setup.wavelength_um
    raw = forward_model.simulate_lr_stack(truth, hp, grid, (CROP, CROP), lp, na, wl, peak_photon_count=peak,
                                          rng=np.random.default_rng(seed))
    scale = (hs[0] * hs[1]) / (CROP * CROP)
    meas = {k: v / scale ** 2 for k, v in raw.items()}
    init = jc.initial_object_from_center_led(meas[(grid[0]["row"], grid[0]["col"])], hs)
    return dict(raw=raw, meas=meas, grid=grid, hp=hp, hs=hs, lp=lp, na=na, wl=wl, factor=factor, truth=truth, init=init)


def score(o, truth):
    m = metrics.compare_to_ground_truth(o, truth)
    return {"ph": m["phase_correlation"], "rmse": m["phase_rmse_rad"], "amp": m["amplitude_correlation"]}


def gd_full(p, loss, lr, iters=BUDGET):
    return jc.reconstruct_and_calibrate(p["meas"], p["grid"], p["hs"], p["hp"], (CROP, CROP), p["lp"], p["na"], p["wl"],
                                        p["init"], n_iterations=iters, calibrate_leds=False, loss=loss, object_lr=lr)["object"]


def gd_incremental(p, loss, lr, epochs=BUDGET, seed=0):
    """Same loss as gd_full, but one Adam step per LED per epoch (LED order reshuffled each epoch). Each LED's
    gradient is re-weighted by norm_led/norm_global (x n_leds) so the LED weights match the full-batch loss."""
    grid = p["grid"]
    power = 2 if loss == "intensity" else 1
    # an all-zero image (dark field at low peak) makes loss_and_gradients' per-call normalizer 0: give it a 1e-12
    # floor (the target amplitude becomes 1e-6, i.e. still "dark"); the rescale below then recovers g_unnormalized/total
    meas = {k: (v if float(np.sum(v ** power)) > 0 else v + 1e-12) for k, v in p["meas"].items()}
    nrm = {(e["row"], e["col"]): float(np.sum(meas[(e["row"], e["col"])] ** power)) for e in grid}
    total = sum(nrm.values()); n = len(grid)
    obj = p["init"].astype(complex).copy()
    ore, oim = jc._Adam(obj.shape, lr), jc._Adam(obj.shape, lr)
    rng = np.random.default_rng(seed)
    for _ in range(epochs):
        for i in rng.permutation(n):
            e = grid[i]
            g = jc.loss_and_gradients(obj, p["hp"], [e], meas, (CROP, CROP), p["lp"], p["na"], p["wl"], loss)["grad_object"]
            g = g * (nrm[(e["row"], e["col"])] / total) * n
            obj = obj - ore.step(2 * g.real) - 1j * oim.step(2 * g.imag)
    return obj


def cells(p, which, lrs):
    out = {}
    for loss in ("intensity", "amplitude"):
        tag = "int" if loss == "intensity" else "amp"
        if which in ("both", "full"):
            out[f"full_{tag}"] = gd_full(p, loss, lrs[f"full_{tag}"])
        if which in ("both", "incr"):
            out[f"incr_{tag}"] = gd_incremental(p, loss, lrs[f"incr_{tag}"])
    return out


def run_eval(obj_kind, peak, seed, lrs):
    p = make_problem(obj_kind, peak, seed)
    t = time.time()
    row = {"obj": obj_kind, "peak": peak, "seed": seed, "init": score(p["init"], p["truth"])}
    for name, kw in WF_VARIANTS:
        row[name] = score(reconstruction.reconstruct(p["raw"], p["grid"], p["hp"], p["lp"], p["na"], p["wl"],
                                                     p["factor"], iterations=WF_EPOCHS, **kw)["object"], p["truth"])
    for name, o in cells(p, "both", lrs).items():
        row[name] = score(o, p["truth"])
    row["wf_s20_200"] = score(reconstruction.reconstruct(p["raw"], p["grid"], p["hp"], p["lp"], p["na"], p["wl"],
                                                         p["factor"], iterations=200, step_max=20.0)["object"], p["truth"])
    row["secs"] = time.time() - t
    return row


def run_tune(obj_kind, seed):
    p = make_problem(obj_kind, 100, seed)
    rows = []
    for loss, tag in (("intensity", "int"), ("amplitude", "amp")):
        for lr in LR_GRID["full"]:
            rows.append({"obj": obj_kind, "seed": seed, "cell": f"full_{tag}", "lr": lr, **score(gd_full(p, loss, lr), p["truth"])})
        for lr in LR_GRID["incr"]:
            rows.append({"obj": obj_kind, "seed": seed, "cell": f"incr_{tag}", "lr": lr, **score(gd_incremental(p, loss, lr), p["truth"])})
    return rows


def best_lrs(tune_rows):
    lrs = {}
    for cell in ("full_int", "full_amp", "incr_int", "incr_amp"):
        by_lr = {}
        for r in tune_rows:
            if r["cell"] == cell:
                by_lr.setdefault(r["lr"], []).append(r["ph"])
        lrs[cell] = max(by_lr, key=lambda k: np.nanmean(by_lr[k]))
    return lrs


def read(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


if __name__ == "__main__":
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "tune":
        for obj_kind in ("phantom", "lenamap"):
            for seed in TUNE_SEEDS:
                for r in run_tune(obj_kind, seed):
                    open(out, "a").write(json.dumps(r) + "\n")
    elif mode == "eval":
        lrs = best_lrs(read(sys.argv[2].replace("eval", "tune")))
        objs = (sys.argv[3],) if len(sys.argv) > 3 else ("phantom", "lenamap")
        peaks = (int(sys.argv[4]),) if len(sys.argv) > 4 else PEAKS
        done = {(r["obj"], r["peak"], r["seed"]) for r in read(out)}
        for s in EVAL_SEEDS:  # seed-major, so any prefix of a partial run covers every condition
            for o in objs:
                for pk in peaks:
                    if (o, pk, s) not in done:
                        r = run_eval(o, pk, s, lrs); r["lrs"] = lrs
                        open(out, "a").write(json.dumps(r) + "\n")
    elif mode == "summary":
        tune, ev = read(sys.argv[2]), read(sys.argv[3])
        print("chosen lrs:", best_lrs(tune))
        names = ["init"] + [n for n, _ in WF_VARIANTS] + ["full_int", "full_amp", "incr_int", "incr_amp", "wf_s20_200"]
        for o in ("phantom", "lenamap"):
            for pk in PEAKS:
                rs = [r for r in ev if r["obj"] == o and r["peak"] == pk]
                if not rs: continue
                print(f"\n{o} peak {pk} (n={len(rs)} seeds)   phase_corr mean+-sd | phase_rmse | amp_corr")
                for n in names:
                    f = lambda k: np.array([r[n][k] for r in rs], float)
                    print(f"  {n:11s} {np.nanmean(f('ph')):+.3f}+-{np.nanstd(f('ph')):.3f} | {np.nanmean(f('rmse')):.3f} | {np.nanmean(f('amp')):.3f}")

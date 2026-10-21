"""run.py -- task runner (3 processes) for the synthetic control and the real set-3 runs.

    python3 run.py synth        # C1-C3 on the synthetic control (calibration)
    python3 run.py real_z       # z in {70,74,78} with method B, 5-fold CV
    python3 run.py real_abl Z   # ablation at the chosen z
    python3 run.py real_final Z M   # full + split-half + null for the selected method M and A

Each stage appends to out/<stage>.json; objects go to out/obj_<name>.npy (complex64).
"""
import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

import fpm_red as F  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
ITERS = 40

METHODS = {
    "A": dict(init="kron17"),
    "A+init": dict(init="fourier_avg"),
    "A+w": dict(init="kron17", weights="noise"),
    "A+sb": dict(init="kron17", fit_sb=True),
    "B": dict(init="fourier_avg", weights="noise", fit_sb=True),
    "B+scap20": dict(init="fourier_avg", weights="noise", fit_sb=True, s_max=20.0),
    "B+epry": dict(init="fourier_avg", weights="noise", fit_sb=True, epry=True),
}

_cache = {}


def data(name):
    if name not in _cache:
        if name == "real":
            _cache[name] = F.load_real()
        else:
            import synth
            _cache[name] = synth.load_synth()
    return _cache[name]


def scrambled(geo, seed=0):
    g = dict(geo)
    ks = [k for k in geo["fxy"] if k not in F.BF]
    vals = [geo["fxy"][k] for k in ks]
    perm = np.random.default_rng(seed).permutation(len(ks))
    g["fxy"] = dict(geo["fxy"])
    for k, j in zip(ks, perm):
        g["fxy"][k] = vals[j]
    return g


def run_task(t):
    tp = os.path.join(OUT, "tasks", t["name"] + ".json")
    if os.path.exists(tp):
        return json.load(open(tp))
    D = data(t["data"])
    geo = F.geometry(t["z"], na=t.get("na"))
    if t.get("scramble"):
        geo = scrambled(geo)
    keys = D["keys"]
    train = [k for k in keys if k in set(map(tuple, t["train"]))] if t.get("train") else keys
    I = {k: D["I"][k] for k in train}
    m = dict(METHODS.get(t["method"], {}))
    if m.pop("weights", None) == "noise":
        m["weights"] = F.noise_weights(I, {k: D["V"][k] for k in train})
    if t["method"] == "nofpm":
        obj, pupil = F.initial_object(D["I"], geo["factor"], "fourier_avg"), None
        res = {}
    else:
        res = F.reconstruct(I, train, geo, iterations=ITERS, mask={k: D["mask"][k] for k in train}, **m)
        obj, pupil = res["object"], (res["pupil"] if m.get("epry") else None)
    out = {k: v for k, v in t.items() if k != "train"}
    evalk = [k for k in keys if k not in train] if t.get("train") else keys
    if t.get("eval_all"):
        evalk = keys
    pred = F.predict(obj, evalk, geo, pupil=pupil)
    out["per_led"] = {}
    for k in evalk:
        r, fl = F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k])
        out["per_led"][f"{k[0]},{k[1]}"] = [r, fl, F.ring(k), k in train]
    out["lattice"] = F.lattice_score(obj)
    if res:
        out["hist_last"] = res["hist"][-1]
        out["s"] = {f"{k[0]},{k[1]}": v for k, v in res["s"].items()}
        out["b"] = {f"{k[0]},{k[1]}": v for k, v in res["b"].items()}
    if "truth" in D and D["truth"].shape == obj.shape:
        fr = F.frc(obj, D["truth"], geo["hrpx"])
        out["frc_truth_band"] = F.band_mean(fr, 0.222, 0.45)
        out["frc_truth"] = fr.tolist()
    if t.get("save"):
        np.save(os.path.join(OUT, f"obj_{t['name']}.npy"), obj.astype(np.complex64))
        if pupil is not None:
            np.save(os.path.join(OUT, f"pupil_{t['name']}.npy"), pupil.astype(np.complex64))
    os.makedirs(os.path.dirname(tp), exist_ok=True)
    json.dump(out, open(tp, "w"))
    print("done", t["name"], "lattice %.4f" % out["lattice"], flush=True)
    return out


def cv_tasks(data_name, method, z, K=5, tag=""):
    keys = data(data_name)["keys"]
    fs = F.folds(keys, K)
    return [dict(name=f"{data_name}_{method}_z{z}_f{i}{tag}", data=data_name, method=method, z=z,
                 fold=i, train=[list(k) for k in keys if k not in fs[i]]) for i in range(K)]


def half_tasks(data_name, method, z, scramble=False):
    keys = data(data_name)["keys"]
    out = []
    for h in (0, 1):
        tr = [list(k) for k in keys if (k[0] + k[1]) % 2 == h]
        nm = f"{data_name}_{method}_z{z}_half{h}" + ("_scr" if scramble else "")
        out.append(dict(name=nm, data=data_name, method=method, z=z, half=h, train=tr,
                        scramble=scramble, save=True))
    return out


def full_task(data_name, method, z):
    return dict(name=f"{data_name}_{method}_z{z}_full", data=data_name, method=method, z=z,
                save=True, eval_all=True)


def stage_tasks(stage, args):
    if stage == "synth":
        z = 74.0
        T = []
        for m in ("A", "B"):
            T += cv_tasks("synth", m, z) + [full_task("synth", m, z)] + half_tasks("synth", m, z)
        T += half_tasks("synth", "B", z, scramble=True)
        T += [dict(name="synth_nofpm", data="synth", method="nofpm", z=z)]
        return T
    if stage == "real_z":
        zs = [float(a) for a in args] or [70.0, 74.0, 78.0]
        T = [dict(name=f"real_nofpm_z{z}", data="real", method="nofpm", z=z) for z in zs]
        for z in zs:
            T += cv_tasks("real", "B", z)
        return T
    if stage == "synth_z":  # does held-out CV find the TRUE z (74) on the synthetic?
        T = []
        for z in [float(a) for a in args]:
            T += cv_tasks("synth", "B", z)
        return T
    if stage == "real_na":  # z fixed at Lucas' 74 mm, effective NA free (z/NA near-degenerate paraxially)
        T = []
        for na in [float(a) for a in args]:
            for t in cv_tasks("real", "B", 74.0, tag=f"_na{na}"):
                t["na"] = na
                T.append(t)
        return T
    if stage == "real_abl":
        z = float(args[0])
        T = []
        for m in ("A", "A+init", "A+w", "A+sb", "B+scap20", "B+epry"):
            T += cv_tasks("real", m, z)
        return T
    if stage == "real_final":
        z, m = float(args[0]), args[1]
        T = []
        for mm in sorted({m, "A"}):
            T += [full_task("real", mm, z)] + half_tasks("real", mm, z)
        T += half_tasks("real", m, z, scramble=True)
        return T
    if stage == "b":  # 2026-09-28 (b): z 98, full + halves (+ null) + 5-fold CV + no-FPM
        z = 98.0
        return ([dict(name=f"real_nofpm_z{z}", data="real", method="nofpm", z=z)] + [full_task("real", "A+init", z)]
                + half_tasks("real", "A+init", z) + half_tasks("real", "A+init", z, scramble=True) + cv_tasks("real", "A+init", z))
    raise SystemExit(stage)


if __name__ == "__main__":
    stage, args = sys.argv[1], sys.argv[2:]
    T = stage_tasks(stage, args)
    print(len(T), "tasks", flush=True)
    with mp.get_context("fork").Pool(int(os.environ.get("NPROC", 3))) as pool:
        res = pool.map(run_task, T, chunksize=1)
    path = os.path.join(OUT, f"{stage}{'_' + '_'.join(args) if args else ''}.json")
    json.dump(res, open(path, "w"))
    print("wrote", path)

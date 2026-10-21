"""iter_runner.py -- reconstrucciones REALES en función de las épocas (estudio 2026-09-30).

Reproduce EXACTAMENTE el pipeline que dio los números de 28/09 (b) y del set 3 del 25/09
(A+init: init 'fourier_avg', sin pesos, sin s/b, sin EPRY, paso 0.3 con rampa
mu = 0.3 (1 - exp(-0.3 it)), máscara de saturados), pero guarda el estado en épocas
log-espaciadas (SNAPS). La rampa depende solo del índice de época, así que el snapshot
de la época e de una corrida larga es idéntico a una corrida de e épocas (verificado en
smoke.py contra F.reconstruct).

No modifica nada fuera de esta carpeta: importa fpm_red.py y run.py de cada dataset
(las mismas tareas: full_task / half_tasks / cv_tasks, por lo tanto los mismos LEDs de
entrenamiento, mitades y folds que criterios_b.py / INFORME) y copia aquí solo el lazo
del solver con un callback.

Uso:
    python3 iter_runner.py list                 # tareas y estado
    python3 iter_runner.py run [NPROC] [MAXEP]  # corre todo lo que falte (resumible)
    python3 iter_runner.py one DATASET TASK [MAXEP]   # una tarea (debug)

Salidas: ver README.md.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, ".."))

# dataset -> (carpeta con fpm_red.py/run.py/prep.npz, z, color)
DATASETS = {
    "b_red": (os.path.join(RES, "captura_2026-09-28b", "red"), 98.0, "red"),
    "b_green": (os.path.join(RES, "captura_2026-09-28b", "green"), 98.0, "green"),
    "b_blue": (os.path.join(RES, "captura_2026-09-28b", "blue"), 98.0, "blue"),
    "s3_red": (os.path.join(RES, "captura_2026-09-25_red"), 74.0, "red"),
}
ORDER = ["b_red", "b_green", "b_blue", "s3_red"]
SNAPS = [0, 1, 2, 3, 5, 8, 12, 20, 30, 40, 60, 80, 120, 160, 240, 320, 400]
METHOD = "A+init"
STEP = 0.3


def _load(ds):
    """Importa fpm_red y run de la carpeta del dataset (una vez por proceso)."""
    d = DATASETS[ds][0]
    sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location("fpm_red", os.path.join(d, "fpm_red.py"))
    F = importlib.util.module_from_spec(spec); sys.modules["fpm_red"] = F; spec.loader.exec_module(F)
    spec = importlib.util.spec_from_file_location("run_" + ds, os.path.join(d, "run.py"))
    R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
    return F, R


def task_defs(ds, R):
    z = DATASETS[ds][1]
    T = [R.full_task("real", METHOD, z)] + R.half_tasks("real", METHOD, z) \
        + R.half_tasks("real", METHOD, z, scramble=True) + R.cv_tasks("real", METHOD, z)
    for t in T:
        t["kind"] = ("full" if t["name"].endswith("_full") else
                     "fold" if "fold" in t else ("half_scr" if t.get("scramble") else "half"))
        t["save_snaps"] = t["kind"] != "fold"
    return T


def reconstruct_snap(F, I, keys, geo, snaps, callback, step=STEP, mask=None):
    """Copia del lazo de F.reconstruct para method A+init (init fourier_avg, weights None,
    fit_sb False, epry False). callback(epoch, spec, hist) se llama con el estado DESPUÉS de
    `epoch` épocas (epoch 0 = objeto inicial)."""
    lr_shape = I[keys[0]].shape
    P = F.circular_pupil(lr_shape, geo["lrpx"], geo["na"], geo["lam"]).astype(complex)
    o0 = F.initial_object(I, geo["factor"], "fourier_avg")
    hr = o0.shape
    spec = np.fft.fftshift(np.fft.fft2(o0))
    win = {k: F.led_crop_window(hr, geo["hrpx"], lr_shape, *geo["fxy"][k]) for k in keys}
    order = F._order(keys)
    w = {k: 1.0 for k in keys}
    s = {k: 1.0 for k in keys}
    b = {k: 0.0 for k in keys}
    hist = []
    snaps = sorted(snaps)
    if 0 in snaps:
        callback(0, spec, hist)
    for it in range(max(snaps)):
        mu = step * (1.0 - np.exp(-0.3 * it))
        err = 0.0
        for k in order:
            ys, xs = win[k]
            ps = spec[ys, xs]
            A = np.fft.ifft2(np.fft.ifftshift(ps * P))
            amp = np.abs(A)
            tgt = np.sqrt(np.clip((I[k] - b[k]) / s[k], 0, None))
            if mask is not None:
                tgt = np.where(mask[k], tgt, amp)
            err += float(np.mean((amp - tgt) ** 2))
            corr = tgt * A / np.maximum(amp, 1e-12)
            D = np.fft.fftshift(np.fft.fft2(corr - A))
            spec[ys, xs] = ps + mu * w[k] * P * D
        hist.append(err / len(keys))
        if it + 1 in snaps:
            callback(it + 1, spec, hist)
    return np.fft.ifft2(np.fft.ifftshift(spec)), hist


def outdir(ds, name):
    return os.path.join(HERE, "out", ds, name)


def run_task(arg):
    ds, name, maxep = arg
    od = outdir(ds, name)
    done = os.path.join(od, "done.json")
    if os.path.exists(done):
        return ds, name, "skip"
    F, R = _load(ds)
    t = next(x for x in task_defs(ds, R) if x["name"] == name)
    D = F.load_real()
    geo = F.geometry(t["z"])
    if t.get("scramble"):
        geo = R.scrambled(geo)
    keys = D["keys"]
    train = [k for k in keys if k in set(map(tuple, t["train"]))] if t.get("train") else keys
    trs = set(train)
    I = {k: D["I"][k] for k in train}
    os.makedirs(od, exist_ok=True)
    snaps = [e for e in SNAPS if e <= maxep]
    mfile = os.path.join(od, "metrics.jsonl")
    open(mfile, "w").close()   # una tarea incompleta se rehace entera
    t0 = time.time()
    tlast = [t0]

    def cb(ep, spec, hist):
        obj = np.fft.ifft2(np.fft.ifftshift(spec))
        te = time.time()
        pred = F.predict(obj, keys, geo)
        per = {}
        for k in keys:
            r, fl = F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k])
            per[f"{k[0]},{k[1]}"] = [r, fl, F.ring(k), k in trs]
        tr = [v[0] for v in per.values() if v[3]]
        ho = [v[0] for v in per.values() if not v[3] and v[2] < 7]
        row = dict(epoch=ep, train_R=float(np.mean(tr)),
                   heldout_R_ring_lt7=(float(np.mean(ho)) if ho else None),
                   n_train=len(tr), n_heldout_ring_lt7=len(ho),
                   solver_err=(hist[-1] if hist else None),
                   lattice=float(F.lattice_score(obj)),
                   wall_s=round(te - t0, 1), metric_s=None, per_led=per)
        if t["save_snaps"]:
            np.save(os.path.join(od, f"obj_e{ep:03d}.npy"), obj.astype(np.complex64))
        row["metric_s"] = round(time.time() - te, 1)
        with open(mfile, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(f"[{ds} {name}] ep {ep:3d}  trainR {row['train_R']:.4f}  hoR {row['heldout_R_ring_lt7']}  "
              f"{time.time() - tlast[0]:.0f}s", flush=True)
        tlast[0] = time.time()

    _, hist = reconstruct_snap(F, I, train, geo, snaps, cb, mask={k: D["mask"][k] for k in train})
    meta = {k: v for k, v in t.items() if k != "train"}
    meta.update(dataset=ds, color=DATASETS[ds][2], snaps=snaps, hist=hist, hrpx=geo["hrpx"], factor=geo["factor"],
                lam=geo["lam"], na=geo["na"], train=[list(k) for k in train], wall_s=round(time.time() - t0, 1))
    json.dump(meta, open(done, "w"))
    return ds, name, "done %.0fs" % (time.time() - t0)


def all_tasks(maxep, datasets=ORDER):
    out = []
    for ds in datasets:
        F, R = _load(ds)
        # full y mitades primero (son las que guardan objetos), después folds
        for t in sorted(task_defs(ds, R), key=lambda x: x["kind"] == "fold"):
            out.append((ds, t["name"], maxep))
        for m in ("fpm_red",):
            sys.modules.pop(m, None)
        sys.path.remove(DATASETS[ds][0])
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        maxep = int(sys.argv[2]) if len(sys.argv) > 2 else max(SNAPS)
        for ds, n, _ in all_tasks(maxep):
            print(ds, n, "DONE" if os.path.exists(os.path.join(outdir(ds, n), "done.json")) else "-")
    elif cmd == "one":
        print(run_task((sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else max(SNAPS))))
    elif cmd == "run":
        nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        maxep = int(sys.argv[3]) if len(sys.argv) > 3 else max(SNAPS)
        dss = sys.argv[4].split(",") if len(sys.argv) > 4 else ORDER
        T = all_tasks(maxep, dss)
        print(len(T), "tareas", flush=True)
        with mp.get_context("fork").Pool(nproc, maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(run_task, T, chunksize=1):
                print("FIN", *r, flush=True)
        print("TODO TERMINADO", flush=True)

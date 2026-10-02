"""runner.py -- re-reconstrucción de 28/09b R/G/B con offset de fuente LED POR COLOR (2026-10-02).

Copia de results/iteraciones_2026-09-30/iter_runner.py (mismo lazo A+init, mismas tareas
full/half/folds de run.py, misma máscara, mismo paso con rampa) con UNA diferencia: la
geometría se arma con offset_mm = (0, 3 + DELTA[variante][color]) en vez de (0, 3).
El objeto se guarda solo en épocas SAVE (full/mitades); en cada snapshot de 'full' se mide
además la rampa global de fase (mismo ajuste que docs/resultados_2026-10-01/fase/rampa/fit.py).

Uso:
    python3 runner.py one VARIANTE DATASET TAREA MAXEP
    python3 runner.py run VARIANTE NPROC MAXEP DATASETS(coma) [KINDS(coma)]
Variantes: ver VARIANTS.
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "iteraciones_2026-09-30"))
import iter_runner as IR  # noqa: E402  (DATASETS, _load, task_defs, reconstruct_snap: sin tocar)

# corrimiento (mm) que se SUMA a la componente de filas (y) del offset nominal (0, 3)
DIE = {"red": 1.06, "green": 0.63, "blue": 0.15}   # docs/resultados_2026-10-01/geometria/frontera
VARIANTS = {
    "nominal": {c: 0.0 for c in DIE},
    "die": dict(DIE),
    "die_neg": {c: -v for c, v in DIE.items()},
    # diagnóstico de rayas (solo rojo): Δ fino y z/NA de la frontera (radio 7.1 vs 6.88 mm -> z~101 o NA~0.072)
    "d090": {"red": 0.90}, "d120": {"red": 1.20},
    "d106_z101": {"red": 1.06, "_z": 101.0}, "d106_na072": {"red": 1.06, "_na": 0.072},
    # LEDs que con el die quedan a horcajadas del borde de pupila (bordes.py), fuera del entrenamiento
    "die_sin18": {"red": 1.06, "_excl": [(18, 14), (18, 16)]},
    "die_sin3": {"red": 1.06, "_excl": [(18, 14), (18, 16), (16, 15)]},
    "nom_sin18": {"red": 0.0, "_excl": [(18, 14), (18, 16)]},
    "g_die_sin18": {"green": 0.63, "_excl": [(18, 14), (18, 16)]},
    "nom_sin18_160": {"red": 0.0, "_excl": [(18, 14), (18, 16)]},
    "die_sin18_160": {"red": 1.06, "_excl": [(18, 14), (18, 16)]},
    "g_nom_sin18": {"green": 0.0, "_excl": [(18, 14), (18, 16)]},
    # configuración final (02/10): z=101 (NA 0.07), die por color, sin LEDs a horcajadas del borde (mapa_bfdf, r=7.07 mm)
    # igual pero con TODAS las LEDs; las de horcajadas con preprocesado DF (S - gauss(F,8)) como teselas/dfnorm_test.py
    "final_z101_dfnorm": {**DIE, "_z": 101.0, "_dfnorm": {"red": [(18, 14), (18, 16)], "green": [(18, 14), (18, 16)]}},
    "final_z101": {**DIE, "_z": 101.0, "_excl": {"red": [(18, 14), (18, 16)], "green": [(18, 14), (18, 16)], "blue": []}},
    # geometría de trabajo (02/10, aprobada): objetivo 2.5x/0.07 con tubo de 150 mm -> aumento 2.35x (lrpx 3.2/2.35 = 1.362 µm),
    # NA 0.069, z = 102 mm; die por color; horcajadas según mapa_z102.py (R_BF 7.055 mm): R,G sin (18,14),(18,16);
    # en azul esas dos quedan 96.6 % BF (esquina) y se dejan. Factor forzado al del nominal (R3/G5/B5; coincide con el natural).
    # control pareado del verde: final_z101 con factor 5 forzado (como el nominal y final_z102)
    "final_z101_f5": {**DIE, "_z": 101.0, "_factor": {"red": 3, "green": 5, "blue": 5},
                      "_excl": {"red": [(18, 14), (18, 16)], "green": [(18, 14), (18, 16)], "blue": []}},
    # barrido de lrpx a z = 102 fijo (02/10): lrpx 1.28 (mag 2.5) y 1.32 (mag 2.424); 1.362 = final_z102
    "z102_m250": {**DIE, "_z": 102.0, "_mag": 2.5, "_naobj": 0.069, "_factor": {"red": 3, "green": 5, "blue": 5},
                  "_excl": {"red": [(18, 14), (18, 16)], "green": [(18, 14), (18, 16)], "blue": []}},
    "z102_m242": {**DIE, "_z": 102.0, "_mag": 2.424, "_naobj": 0.069, "_factor": {"red": 3, "green": 5, "blue": 5},
                  "_excl": {"red": [(18, 14), (18, 16)], "green": [(18, 14), (18, 16)], "blue": []}},
    "final_z102": {**DIE, "_z": 102.0, "_mag": 2.35, "_naobj": 0.069, "_factor": {"red": 3, "green": 5, "blue": 5},
                   "_excl": {"red": [(18, 14), (18, 16)], "green": [(18, 14), (18, 16)], "blue": []}},
}
SNAPS = [0, 1, 2, 3, 5, 8, 12, 20, 30, 40, 60, 80, 120, 160]
SAVE_FULL = {5, 20, 40, 80, 160}
SAVE_HALF = {5, 40, 160}


def ramp(obj, hrpx, lam):
    """Igual que fase/rampa/fit.py: unwrap global, ajuste lineal; devuelve pendientes (rad/µm, ejes x=1,y=0),
    p-p de la rampa ajustada (rad) y corrimiento de LED equivalente a 98 mm (mm, con signo, eje filas)."""
    from skimage.restoration import unwrap_phase
    ph = unwrap_phase(np.angle(obj)); m = 8; ph = ph[m:-m, m:-m]
    y, x = np.mgrid[:ph.shape[0], :ph.shape[1]] * hrpx; x = x - x.mean(); y = y - y.mean()
    A = np.c_[np.ones(x.size), x.ravel(), y.ravel()]
    c, *_ = np.linalg.lstsq(A, ph.ravel(), rcond=None)
    sx, sy = float(c[1]), float(c[2])
    return dict(slope_x=sx, slope_y=sy, ptp=float(np.ptp(A @ c)),
                dy_mm=float(98 * lam * sy / (2 * np.pi)), dx_mm=float(98 * lam * sx / (2 * np.pi)))


def outdir(var, ds, name):
    return os.path.join(HERE, "out", var, ds, name)


def run_task(arg):
    var, ds, name, maxep = arg
    od = outdir(var, ds, name)
    done = os.path.join(od, "done.json")
    if os.path.exists(done):
        return var, ds, name, "skip"
    F, R = IR._load(ds)
    t = next(x for x in IR.task_defs(ds, R) if x["name"] == name)
    color = IR.DATASETS[ds][2]
    V = VARIANTS[var]
    off = (0.0, 3.0 + V[color])
    D = F.load_real()
    dfn = V.get("_dfnorm", {}).get(color, [])
    if dfn:
        from scipy.ndimage import gaussian_filter
        pz = np.load(os.path.join(IR.DATASETS[ds][0], "prep.npz")); pk = [tuple(map(int, k)) for k in pz["keys"]]
        for k in dfn:
            i = pk.index(k)
            D["I"][k] = pz["S"][i].astype(float) - gaussian_filter(pz["F"][i].astype(float), 8.0)
    if "_mag" in V or "_naobj" in V:   # hook: objetivo efectivo (aumento -> lrpx, NA) sin tocar fpm_red/cv_common
        from dataclasses import replace as _rep
        _setup0 = F.setup
        def _setup(*a, **kw):
            s0 = _setup0(*a, **kw)
            return _rep(s0, objective=_rep(s0.objective, magnification=V.get("_mag", s0.objective.magnification),
                                            na=V.get("_naobj", s0.objective.na), name=s0.objective.name + "+override"))
        F.setup = _setup
    if "_factor" in V:
        from ptyco_full_simulator import optics as _opt
        fz = V["_factor"][color]
        F.cc.factor_for = lambda s0, fz=fz: max(fz, _opt.canvas_upsampling_factor(s0))
    geo = F.geometry(V.get("_z", t["z"]), offset_mm=off, na=V.get("_na"))
    print(f"[{var} {ds} {name}] geo: z={V.get('_z', t['z'])} off={off} lrpx={geo['lrpx']:.4f} na={geo['na']} "
          f"factor={geo['factor']} hrpx={geo['hrpx']:.4f} lam={geo['lam']}", flush=True)
    if t.get("scramble"):
        geo = R.scrambled(geo)
    keys = D["keys"]
    train = [k for k in keys if k in set(map(tuple, t["train"]))] if t.get("train") else keys
    excl = V.get("_excl", [])
    if isinstance(excl, dict):
        excl = excl.get(color, [])
    train = [k for k in train if k not in set(excl)]
    trs = set(train)
    I = {k: D["I"][k] for k in train}
    os.makedirs(od, exist_ok=True)
    snaps = [e for e in SNAPS if e <= maxep]
    save = SAVE_FULL if t["kind"] == "full" else (SAVE_HALF if t["kind"] in ("half", "half_scr") else set())
    mfile = os.path.join(od, "metrics.jsonl")
    open(mfile, "w").close()
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
        if t["kind"] == "full":
            row["ramp"] = ramp(obj, geo["hrpx"], geo["lam"])
        if ep in save:
            np.save(os.path.join(od, f"obj_e{ep:03d}.npy"), obj.astype(np.complex64))
        row["metric_s"] = round(time.time() - te, 1)
        with open(mfile, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        rp = row.get("ramp")
        print(f"[{var} {ds} {name}] ep {ep:3d}  trainR {row['train_R']:.4f}  hoR {row['heldout_R_ring_lt7']}"
              + (f"  ramp_ptp {rp['ptp']:.2f} dy {rp['dy_mm']:+.3f}mm" if rp else "")
              + f"  {time.time() - tlast[0]:.0f}s", flush=True)
        tlast[0] = time.time()

    _, hist = IR.reconstruct_snap(F, I, train, geo, snaps, cb, mask={k: D["mask"][k] for k in train})
    meta = {k: v for k, v in t.items() if k != "train"}
    meta.update(variant=var, offset_mm=list(off), z_used=V.get("_z", t["z"]), dataset=ds, color=color, snaps=snaps, hist=hist, hrpx=geo["hrpx"],
                factor=geo["factor"], lam=geo["lam"], na=geo["na"], lrpx=geo["lrpx"], train=[list(k) for k in train],
                wall_s=round(time.time() - t0, 1))
    json.dump(meta, open(done, "w"))
    return var, ds, name, "done %.0fs" % (time.time() - t0)


def all_tasks(var, maxep, datasets, kinds):
    out = []
    for ds in datasets:
        F, R = IR._load(ds)
        for t in sorted(IR.task_defs(ds, R), key=lambda x: x["kind"] == "fold"):
            if t["kind"] in kinds:
                out.append((var, ds, t["name"], maxep))
        sys.modules.pop("fpm_red", None)
        sys.path.remove(IR.DATASETS[ds][0])
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "one":
        print(run_task((sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))), flush=True)
    elif cmd == "run":
        var, nproc, maxep = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        dss = sys.argv[5].split(",")
        kinds = sys.argv[6].split(",") if len(sys.argv) > 6 else ["full", "half", "fold"]
        T = all_tasks(var, maxep, dss, kinds)
        print(len(T), "tareas", flush=True)
        with mp.get_context("fork").Pool(nproc, maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(run_task, T, chunksize=1):
                print("FIN", *r, flush=True)
        print("TODO TERMINADO", flush=True)

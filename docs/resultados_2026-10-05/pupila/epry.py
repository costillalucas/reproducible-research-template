"""epry.py -- 28/09b rojo, tarea full, geometría z102_m* de offset_color_2026-10-02, CON recuperación de pupila (EPRY).

No edita nada fuera de esta carpeta. Copia (no importa) la parte de geometría de
results/offset_color_2026-10-02/runner.py (variantes z102_m250 / final_z102, hook _mag/_naobj/_factor) porque
otro agente está editando ese archivo. Usa iter_runner (DATASETS, _load, task_defs) sin tocarlo.

Lazo: idéntico a iter_runner.reconstruct_snap (A+init, mu = 0.3 (1 - exp(-0.3 it)), máscara de saturados) salvo:
  - actualización del objeto con conj(P)/max|P|^2 (con P ideal es exactamente lo mismo que A+init);
  - desde la época PSTART, además, P <- (P + mu * conj(ps)/max|ps|^2 * D) * Pm   (ou2014 Eq. 4, como fpm_red epry,
    pero con la misma rampa mu del objeto y arranque diferido; soporte fijo = círculo NA ideal).
Con PSTART > MAXEP reproduce bit a bit la corrida de pupila fija (control).

Métrica: train_R con la pupila recuperada (la que usa el modelo) y, aparte, con la pupila ideal.

Uso: python3 epry.py VARIANTE MAXEP PSTART [TAG] [BETA]
  BETA multiplica el paso de la pupila (default 1 = mismo mu que el objeto).
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "iteraciones_2026-09-30"))
import iter_runner as IR  # noqa: E402

DIE = {"red": 1.06, "green": 0.63, "blue": 0.15}
EXCL = [(18, 14), (18, 16)]
VARIANTS = {   # copia de offset_color_2026-10-02/runner.py (solo rojo)
    "z102_m250": dict(z=102.0, mag=2.5, naobj=0.069, factor=3),
    "final_z102": dict(z=102.0, mag=2.35, naobj=0.069, factor=3),
}
SNAPS = [0, 1, 2, 3, 5, 8, 12, 20, 30, 40, 60, 80]
DS = "b_red"


def predict(F, obj, keys, geo, P, lr_shape=(400, 400)):
    spec = np.fft.fftshift(np.fft.fft2(obj))
    out = {}
    for k in keys:
        ys, xs = F.led_crop_window(obj.shape, geo["hrpx"], lr_shape, *geo["fxy"][k])
        out[k] = np.abs(np.fft.ifft2(np.fft.ifftshift(spec[ys, xs] * P))) ** 2
    return out


def main(var, maxep, pstart, tag, beta=1.0):
    V = VARIANTS[var]
    F, R = IR._load(DS)
    t = next(x for x in IR.task_defs(DS, R) if x["kind"] == "full")
    D = F.load_real()
    from dataclasses import replace as _rep
    _setup0 = F.setup

    def _setup(*a, **kw):
        s0 = _setup0(*a, **kw)
        return _rep(s0, objective=_rep(s0.objective, magnification=V["mag"], na=V["naobj"],
                                        name=s0.objective.name + "+override"))
    F.setup = _setup
    from ptyco_full_simulator import optics as _opt
    F.cc.factor_for = lambda s0, fz=V["factor"]: max(fz, _opt.canvas_upsampling_factor(s0))
    off = (0.0, 3.0 + DIE["red"])
    geo = F.geometry(V["z"], offset_mm=off)
    print(f"[{var} {tag}] geo z={V['z']} off={off} lrpx={geo['lrpx']:.4f} na={geo['na']} factor={geo['factor']} "
          f"hrpx={geo['hrpx']:.4f} lam={geo['lam']} pstart={pstart}", flush=True)
    keys = D["keys"]
    train = [k for k in keys if k not in set(EXCL)]
    trs = set(train)
    I = {k: D["I"][k] for k in train}
    mask = {k: D["mask"][k] for k in train}
    od = os.path.join(HERE, "out", f"{var}_{tag}")
    os.makedirs(od, exist_ok=True)
    mfile = os.path.join(od, "metrics.jsonl")
    open(mfile, "w").close()

    lr_shape = I[train[0]].shape
    Pm = F.circular_pupil(lr_shape, geo["lrpx"], geo["na"], geo["lam"])
    P0 = Pm.astype(complex)
    P = P0.copy()
    o0 = F.initial_object(I, geo["factor"], "fourier_avg")
    hr = o0.shape
    spec = np.fft.fftshift(np.fft.fft2(o0))
    win = {k: F.led_crop_window(hr, geo["hrpx"], lr_shape, *geo["fxy"][k]) for k in train}
    order = F._order(train)
    hist = []
    t0 = time.time()

    def cb(ep):
        obj = np.fft.ifft2(np.fft.ifftshift(spec))
        row = dict(epoch=ep, solver_err=(hist[-1] if hist else None), wall_s=round(time.time() - t0, 1))
        for lab, PP in (("rec", P), ("ideal", P0)):
            pred = predict(F, obj, keys, geo, PP)
            rs = [F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k])[0] for k in train]
            row[f"train_R_{lab}"] = float(np.mean(rs))
            if lab == "rec":
                row["per_led"] = {f"{k[0]},{k[1]}": [float(r), F.ring(k)] for k, r in zip(train, rs)}
        if ep in (5, 20, 40, 80) or ep == maxep:
            np.save(os.path.join(od, f"obj_e{ep:03d}.npy"), obj.astype(np.complex64))
            np.save(os.path.join(od, f"pupil_e{ep:03d}.npy"), P.astype(np.complex64))
        with open(mfile, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(f"[{var} {tag}] ep {ep:3d} R_rec {row['train_R_rec']:.4f} R_ideal {row['train_R_ideal']:.4f} "
              f"err {row['solver_err']}  {row['wall_s']}s", flush=True)

    snaps = [e for e in SNAPS if e <= maxep]
    cb(0)
    for it in range(maxep):
        mu = 0.3 * (1.0 - np.exp(-0.3 * it))
        upd_p = it >= pstart
        err = 0.0
        for k in order:
            ys, xs = win[k]
            ps = spec[ys, xs]
            A = np.fft.ifft2(np.fft.ifftshift(ps * P))
            amp = np.abs(A)
            tgt = np.sqrt(np.clip(I[k], 0, None))
            tgt = np.where(mask[k], tgt, amp)
            err += float(np.mean((amp - tgt) ** 2))
            corr = tgt * A / np.maximum(amp, 1e-12)
            Dk = np.fft.fftshift(np.fft.fft2(corr - A))
            pm = max(float(np.max(np.abs(P) ** 2)), 1e-12)
            spec[ys, xs] = ps + mu * np.conj(P) / pm * Dk
            if upd_p:
                sm = max(float(np.max(np.abs(ps) ** 2)), 1e-12)
                P = (P + beta * mu * np.conj(ps) / sm * Dk) * Pm
        hist.append(err / len(train))
        if it + 1 in snaps:
            cb(it + 1)
    json.dump(dict(variant=var, tag=tag, pstart=pstart, beta=beta, maxep=maxep, geo={k: v for k, v in geo.items() if k != "fxy"},
                   offset_mm=list(off), excl=[list(k) for k in EXCL], hist=hist, wall_s=round(time.time() - t0, 1)),
              open(os.path.join(od, "done.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "epry",
         float(sys.argv[5]) if len(sys.argv) > 5 else 1.0)

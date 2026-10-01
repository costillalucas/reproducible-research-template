"""particiones.py -- C2 con K particiones aleatorias en mitades (estudio 2026-09-30, fase B).

Reconstruye cada mitad con EXACTAMENTE el mismo solver que iter_runner.py (importa iter_runner y usa
iter_runner.reconstruct_snap, A+init, paso 0.3 con rampa, máscara de saturados; no se modifica iter_runner.py).

Regla de las mitades (respeta run.half_tasks de captura_2026-09-28b/<color>/run.py):
- run.half_tasks parte TODOS los LEDs en damero, (fila + col) % 2 == h. Los LEDs de campo claro (F.BF) NO van en
  las dos mitades: quedan repartidos por el damero (28/09 b: 3 y 3, que además fijan el objeto inicial fourier_avg
  de cada mitad). Esa asignación de BF se mantiene fija, igual a la partición oficial.
- El resto (campo oscuro, 219 LEDs en 28/09 b) se reparte al azar 50/50 con semilla s (0..K-1), estratificado por
  anillo: se ordenan por (anillo, clave) como F._order, se agrupan de a pares consecutivos y en cada par una moneda
  (np.random.default_rng(s)) decide cuál va a la mitad 0. Un sobrante impar va a la mitad 0 o 1 con otra moneda.
Snapshots guardados: solo SNAPS_P = 20, 40, 120, 400 (obj_eNNN.npy, complex64). Sin métricas por LED.

Uso:
    python3 particiones.py list  [DS,...]
    python3 particiones.py run   NPROC MAXEP DS[,DS...] [K]     # resumible: salta tareas con done.json
    python3 particiones.py check DS                              # partición oficial (damero) a 20 épocas vs
                                                                 # out/<DS>/..._half0/obj_e020.npy (debe dar 0)
Salidas: out_part/<DS>/p<seed>_h<h>/{obj_e020,obj_e040,obj_e120,obj_e400}.npy y done.json; log en particiones.log
(cuando se lanza con run_part.sh).
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
sys.path.insert(0, HERE)
import iter_runner as IR  # noqa: E402

SNAPS_P = [20, 40, 120, 400]
K_DEF = 5


def split(F, keys, seed):
    """Devuelve (half0, half1) como listas de claves, con la regla del docstring."""
    bf = [k for k in keys if k in F.BF]
    h = {0: [k for k in bf if (k[0] + k[1]) % 2 == 0], 1: [k for k in bf if (k[0] + k[1]) % 2 == 1]}
    df = F._order([k for k in keys if k not in F.BF])
    rng = np.random.default_rng(seed)
    for i in range(0, len(df) - 1, 2):
        a, b = df[i], df[i + 1]
        if rng.random() < 0.5:
            a, b = b, a
        h[0].append(a); h[1].append(b)
    if len(df) % 2:
        h[int(rng.random() < 0.5)].append(df[-1])
    return h[0], h[1]


def pdir(ds, seed, hh):
    return os.path.join(HERE, "out_part", ds, f"p{seed}_h{hh}")


def run_one(arg):
    ds, seed, hh, maxep = arg
    od = pdir(ds, seed, hh)
    done = os.path.join(od, "done.json")
    if os.path.exists(done):
        return ds, seed, hh, "skip"
    F, R = IR._load(ds)
    D = F.load_real()
    z = IR.DATASETS[ds][1]
    geo = F.geometry(z)
    keys = D["keys"]
    tr = set(split(F, keys, seed)[hh])
    train = [k for k in keys if k in tr]       # mismo orden que iter_runner.run_task
    I = {k: D["I"][k] for k in train}
    os.makedirs(od, exist_ok=True)
    snaps = [e for e in SNAPS_P if e <= maxep]
    t0 = time.time()

    def cb(ep, spec, hist):
        obj = np.fft.ifft2(np.fft.ifftshift(spec))
        np.save(os.path.join(od, f"obj_e{ep:03d}.npy"), obj.astype(np.complex64))
        print(f"[{ds} p{seed} h{hh}] ep {ep:3d}  err {hist[-1]:.5f}  {time.time() - t0:.0f}s", flush=True)

    _, hist = IR.reconstruct_snap(F, I, train, geo, snaps, cb, mask={k: D["mask"][k] for k in train})
    meta = dict(dataset=ds, seed=seed, half=hh, z=z, method=IR.METHOD, step=IR.STEP, snaps=snaps, hist=hist,
                hrpx=geo["hrpx"], lam=geo["lam"], na=geo["na"], n_train=len(train),
                n_bf=sum(k in F.BF for k in train), train=[list(k) for k in train],
                wall_s=round(time.time() - t0, 1))
    json.dump(meta, open(done, "w"))
    return ds, seed, hh, "done %.0fs" % (time.time() - t0)


def tasks(dss, maxep, K):
    return [(ds, s, hh, maxep) for ds in dss for s in range(K) for hh in (0, 1)]


def check(ds):
    """Partición oficial (damero) por este camino, 20 épocas, contra el half0 de iter_runner."""
    F, R = IR._load(ds)
    D = F.load_real()
    z = IR.DATASETS[ds][1]
    geo = F.geometry(z)
    keys = D["keys"]
    t = R.half_tasks("real", IR.METHOD, z)[0]
    tr = set(map(tuple, t["train"]))
    train = [k for k in keys if k in tr]
    I = {k: D["I"][k] for k in train}
    got = {}
    IR.reconstruct_snap(F, I, train, geo, [20], lambda e, s, h: got.update(o=np.fft.ifft2(np.fft.ifftshift(s))),
                        mask={k: D["mask"][k] for k in train})
    ref = np.load(os.path.join(IR.outdir(ds, t["name"]), "obj_e020.npy"))
    d = float(np.max(np.abs(got["o"].astype(np.complex64) - ref)))
    h0, h1 = split(F, keys, 0)
    print(json.dumps(dict(dataset=ds, check_maxabsdiff_e20=d, n_keys=len(keys), seed0_sizes=[len(h0), len(h1)],
                          seed0_bf=[sum(k in F.BF for k in h0), sum(k in F.BF for k in h1)])), flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        dss = sys.argv[2].split(",") if len(sys.argv) > 2 else ["b_red", "b_blue"]
        for ds, s, hh, _ in tasks(dss, 400, K_DEF):
            print(ds, f"p{s}_h{hh}", "DONE" if os.path.exists(os.path.join(pdir(ds, s, hh), "done.json")) else "-")
    elif cmd == "check":
        check(sys.argv[2])
    elif cmd == "run":
        nproc, maxep, dss = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4].split(",")
        K = int(sys.argv[5]) if len(sys.argv) > 5 else K_DEF
        T = tasks(dss, maxep, K)
        print(len(T), "tareas", flush=True)
        with mp.get_context("fork").Pool(nproc, maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(run_one, T, chunksize=1):
                print("FIN", *r, flush=True)
        print("TODO TERMINADO", flush=True)

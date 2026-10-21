"""run.py -- tareas del estudio de diseño (2026-10-21).

Una 'config' = geometría (z, eje, conjunto de LEDs) × política de exposición × error de modelo.
Por config: gen (imágenes con ruido) -> 4 reconstrucciones (full, half0, half1 = tablero (i+j)%2, fold0 = 1/5 de
las DF estratificadas por NA) -> métricas (metricas.py).

Uso:  python3 run.py geom                 (tabla analítica: LEDs, BF, margen al borde de pupila, solapamiento)
      python3 run.py run NPROC CONFIGS... (o 'A' / 'B' = lotes)
"""
from __future__ import annotations

import json
import os
import sys
import time
import zlib

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim as S  # noqa: E402

N_LR = 160
EPOCHS = 80
SEED_OBJ = 0
T_CAP = 1000.0       # ms, exposición máxima por cuadro (SUPUESTO práctico)
TARGET = 3000.0      # cuentas sobre oscuro en el p99.9 de la imagen (escalera)
EXCL_TOL = 0.004     # |NA_ill - NA| < tol -> LED a horcajadas del borde: excluida
OUTER_NA = 0.25      # 'anillos externos' para el promediado de N cuadros

AR = 0.5 + 1.06 / 6      # eje del rojo: mitad de paso + dado 1.06 mm (docs/resultado_rojo_2026-10.md)
GEOMS = {
    "hoy": dict(z=102.0, a=AR, square=15),                 # 20/10: 15x15, z 102, eje entre LEDs + dado rojo
    "z130r": dict(z=130.0, a=AR),                          # b2 rojo, mejor z cerca de 130 (margen 0.13 paso)
    "z148n": dict(z=148.0, a=0.5),                         # b2 de Lucas (mitad de paso, sin dado)
    "z148r": dict(z=148.0, a=AR),                          # b2 a 148 con el dado rojo real
    "z160r": dict(z=160.0, a=AR),                          # b2 rojo, mejor z en 140-160 (margen 0.11)
    "b1i": dict(z=150.0, a=0.0),                           # b1 ideal: eje local sobre LED, sin aberración
    "b1s": dict(z=150.0, a=0.0, ab=dict(astig=0.1, defocus=0.0, vig=0.05)),   # b1, ROI corrida 1.94 mm (rojo)
    "b1L": dict(z=150.0, a=0.0, ab=dict(astig=0.3, defocus=0.1, vig=0.15)),   # b1, campo ~9 mm del centro
    "b1h": dict(z=102.0, a=0.0, square=15, ab=dict(astig=0.1, defocus=0.0, vig=0.05)),   # b1 a z 102 (verificado 21/10)
    "sq25": dict(z=150.0, a=0.0, square=25, ab=dict(astig=0.1, defocus=0.0, vig=0.05)),
    "sq19": dict(z=150.0, a=0.0, square=19, ab=dict(astig=0.1, defocus=0.0, vig=0.05)),
}
POLICIES = ["limpio", "U", "L1", "L4", "L8", "Lfill"]
ERRS = {"ideal": {}, "err": dict(jitter_mm=0.3, kscale=1.03, na_true=S.NA * 0.98),
        "zp2": dict(dz=2.0), "zm2": dict(dz=-2.0), "h": dict(heights=True), "sph": dict(sph=2.5), "sph7": dict(sph=7.0)}


def geometry(gname, err=None):
    G = GEOMS[gname]
    err = err or {}
    pos = S.led_set(G["z"], G["a"], square=G.get("square"))
    fxy = S.fxy_of(pos, G["z"])
    nas = S.na_ill(fxy)
    excl = {k for k, a in nas.items() if abs(a - S.NA) < EXCL_TOL}
    bf = [k for k, a in nas.items() if a < S.NA and k not in excl]
    tp = pos
    if "jitter_mm" in err:
        rng = np.random.default_rng(12345)
        jit = {k: rng.normal(0, err["jitter_mm"], 2) for k in sorted(pos)}
        tp = {k: (X + jit[k][0], Y + jit[k][1]) for k, (X, Y) in pos.items()}
    true_fxy = S.fxy_of(tp, G["z"] + err.get("dz", 0.0), kscale=err.get("kscale", 1.0))
    na_true = err.get("na_true", S.NA)
    ab = G.get("ab")
    pupil = S.aberrated_pupil(N_LR, na_true, **ab) if ab else (S.aberrated_pupil(N_LR, na_true) if "na_true" in err else None)
    return dict(z=G["z"], pos=pos, fxy=fxy, nas=nas, excl=excl, bf=bf, true_fxy=true_fxy, na_true=na_true, pupil=pupil)


def overlap(dk, R):
    """fracción de área común de dos círculos de radio R a distancia dk."""
    x = dk / (2 * R)
    if x >= 1:
        return 0.0
    return float((2 * np.arccos(x) - 2 * x * np.sqrt(1 - x * x)) / np.pi)


def geom_table():
    R = S.NA / S.LAM
    rows = {}
    for g in GEOMS:
        q = geometry(g)
        nas = np.array(sorted(q["nas"].values()))
        dk = S.PITCH / q["z"] / S.LAM                    # paso de LED en k cerca del eje
        marg = float(np.min(np.abs(nas - S.NA)))
        used = [a for k, a in q["nas"].items() if k not in q["excl"]]
        rows[g] = dict(z=q["z"], eje_a=GEOMS[g]["a"], n_led=len(nas), n_excl=len(q["excl"]), n_bf=len(q["bf"]),
                       na_ill_max=float(max(used)), na_sint=float(max(used) + S.NA),
                       margen_borde_NA=marg, solap_vecinas=overlap(dk, R), solap_mitades=overlap(dk * np.sqrt(2), R))
    return rows


def frames(q, policy, budget_s):
    """Exposición t_k (ms) y cuadros N_k por LED, según la política, para un presupuesto total (s) incluyendo
    S.OVERHEAD_S por cuadro. peak_k (cuentas/ms) se toma de las imágenes limpias (pre-escaneo)."""
    keys = [k for k in q["pos"] if k not in q["excl"]]
    pk = q["peak"]
    if policy == "U":
        N = {k: 2 for k in keys}
        bf = {k for k in keys if q["nas"][k] < S.NA}
        t_bf = 5.0
        fixed = sum(N[k] * (t_bf / 1e3 + S.OVERHEAD_S) for k in bf)
        dfk = [k for k in keys if k not in bf]
        tdf = (budget_s - fixed - sum(N[k] * S.OVERHEAD_S for k in dfk)) / sum(N[k] for k in dfk) * 1e3
        tdf = float(np.clip(tdf, 1.0, T_CAP))
        t = {k: (t_bf if k in bf else tdf) for k in keys}
        return t, N
    if policy == "Lfill":      # escalera a 3000 sin escalar (tope T_CAP) + N cuadros en las topadas, hasta el presupuesto
        t = {k: min(TARGET / pk[k], T_CAP) for k in keys}
        capped = {k for k in keys if TARGET / pk[k] > T_CAP}
        best = 1
        for n in range(1, 33):
            N = {k: (n if k in capped else 1) for k in keys}
            if capture_time(t, N) <= budget_s:
                best = n
        return t, {k: (best if k in capped else 1) for k in keys}
    nfr = {"L1": 1, "L4": 4, "L8": 8}[policy]
    N = {k: (nfr if q["nas"][k] > OUTER_NA else 1) for k in keys}
    t3 = {k: min(TARGET / pk[k], T_CAP) for k in keys}

    def total(c):
        return sum(N[k] * (min(c * t3[k], t3[k]) / 1e3 + S.OVERHEAD_S) for k in keys)
    lo, hi = 1e-4, 1.0
    if total(hi) <= budget_s:
        c = hi
    else:
        for _ in range(60):
            m = np.sqrt(lo * hi)
            lo, hi = (m, hi) if total(m) < budget_s else (lo, m)
        c = lo
    t = {k: max(min(c * t3[k], t3[k]), 0.5) for k in keys}
    return t, N


def capture_time(t, N):
    return float(sum(N[k] * (t[k] / 1e3 + S.OVERHEAD_S) for k in t))


def budget_T0():
    """Tiempo de la captura de hoy (20/10): 15x15, BF 5 ms, DF 257 ms, 2 cuadros, + overhead supuesto."""
    q = geometry("hoy")
    t = sum(2 * ((5.0 if q["nas"][k] < S.NA else 257.0) / 1e3 + S.OVERHEAD_S) for k in q["pos"])
    return float(t)


def budget_of(bud):
    if bud == "T0":
        return budget_T0()
    if bud == "T4":
        return 4 * budget_T0()
    if bud == "Tinf":
        return 1e9
    if bud.startswith("T@"):          # tiempo natural (escalera L1 sin tope de presupuesto) de otra geometría
        m = json.load(open(os.path.join(HERE, "out", cname(bud[2:], "L1", "ideal", "Tinf"), "meta.json")))
        return m["capture_s"]
    raise ValueError(bud)


def cname(g, pol, err, bud):
    return f"{g}__{pol}__{err}__{bud}"


def gen(cfg):
    g, pol, err, bud = cfg.split("__")
    od = os.path.join(HERE, "out", cfg); os.makedirs(od, exist_ok=True)
    f = os.path.join(od, "data.npz")
    if os.path.exists(f):
        return f
    q = geometry(g, ERRS[err])
    sph, L = S.phantom(N_LR, seed=SEED_OBJ)
    o = S.truth_object(sph, L, N_LR)
    keys = sorted(q["pos"])
    if ERRS[err].get("sph"):
        clean = S.predict_spherical(o, q["pos"], q["z"], keys, N_LR, q["true_fxy"], s=ERRS[err]["sph"], pupil=q["pupil"])
    elif ERRS[err].get("heights"):
        clean = S.predict_heights(sph, L, N_LR, q["true_fxy"], keys, pupil=q["pupil"], na=q["na_true"])
    else:
        clean = S.predict(o, q["true_fxy"], keys, N_LR, na=q["na_true"], pupil=q["pupil"])
    B = S.brightness(q["nas"], q["z"])
    st = {k: S.stray(q["nas"][k], q["z"]) for k in keys}
    q["peak"] = {k: float(np.percentile(B[k] * clean[k] + st[k], 99.9)) for k in keys}
    use = [k for k in keys if k not in q["excl"]]
    I, V, M, T, NF = {}, {}, {}, {}, {}
    if pol == "limpio":
        for k in use:
            I[k], V[k], M[k], T[k], NF[k] = clean[k], 1e-12, np.ones_like(clean[k], bool), 0.0, 0
    else:
        budget = budget_of(bud)
        t, N = frames(q, pol, budget)
        rng = np.random.default_rng(zlib.crc32(cfg.encode()))
        for k in use:
            mu = t[k] * (B[k] * clean[k] + st[k])           # cuentas sobre oscuro
            acc = np.zeros_like(mu); sat = np.zeros(mu.shape, bool)
            for _ in range(N[k]):
                fr = S.GAIN * rng.poisson(mu / S.GAIN) + rng.normal(0, S.SIG_R, mu.shape) + S.DARK
                fr = np.clip(np.round(fr), 0, S.SAT)
                sat |= fr >= S.SAT
                acc += fr
            s = (acc / N[k] - S.DARK) / t[k]                 # cuentas/ms, oscuro conocido
            I[k] = (s - st[k]) / B[k]                        # parásita restada (media conocida), normalizado
            V[k] = float((S.GAIN * mu.mean() + S.SIG_R ** 2) / N[k] / (t[k] * B[k]) ** 2)
            M[k] = ~sat; T[k] = t[k]; NF[k] = N[k]
    meta = dict(cfg=cfg, n_used=len(use), n_excl=len(q["excl"]), n_bf=len(q["bf"]),
                capture_s=(capture_time(T, NF) if pol != "limpio" else 0.0),
                t_ms={f"{k[0]},{k[1]}": T[k] for k in use}, N={f"{k[0]},{k[1]}": NF[k] for k in use},
                na={f"{k[0]},{k[1]}": q["nas"][k] for k in use},
                peak_counts={f"{k[0]},{k[1]}": q["peak"][k] * T[k] for k in use},
                sat_px={f"{k[0]},{k[1]}": int((~M[k]).sum()) for k in use})
    json.dump(meta, open(os.path.join(od, "meta.json"), "w"))
    np.savez(f, keys=np.array(use), I=np.array([I[k] for k in use], np.float32),
             M=np.array([M[k] for k in use]), V=np.array([V[k] for k in use]))
    np.save(os.path.join(od, "truth.npy"), o.astype(np.complex64))
    json.dump(dict(sph=sph, L=L), open(os.path.join(od, "phantom.json"), "w"))
    return f


def split(q, use, kind):
    if kind == "full":
        return use
    if kind in ("half0", "half1"):
        h = int(kind[-1])
        tr = [k for k in use if (k[0] + k[1]) % 2 == h]
        return tr
    if kind == "fold0":
        df = sorted([k for k in use if k not in q["bf"]], key=lambda k: (q["nas"][k], k))
        ho = set(df[0::5])
        return [k for k in use if k not in ho]
    raise ValueError(kind)


def recon(arg):
    cfg, kind = arg
    od = os.path.join(HERE, "out", cfg)
    of = os.path.join(od, f"obj_{kind}.npy")
    if os.path.exists(of):
        return cfg, kind, "skip"
    t0 = time.time()
    gen(cfg)
    g, pol, err, bud = cfg.split("__")
    q = geometry(g, ERRS[err])
    d = np.load(os.path.join(od, "data.npz"))
    use = [tuple(int(v) for v in k) for k in d["keys"]]
    I = {k: d["I"][i].astype(float) for i, k in enumerate(use)}
    M = {k: d["M"][i] for i, k in enumerate(use)}
    tr = split(q, use, kind)
    bf = [k for k in q["bf"] if k in tr]
    obj, hist, snap = S.reconstruct({k: I[k] for k in tr}, tr, q["fxy"], N_LR, bf, iterations=EPOCHS,
                                    mask={k: M[k] for k in tr}, snaps=(40,) if kind == "full" else ())
    np.save(of, obj.astype(np.complex64))
    for e, o in snap.items():
        np.save(os.path.join(od, f"obj_{kind}_e{e:03d}.npy"), o)
    json.dump(dict(hist=hist, train=[list(k) for k in tr], wall_s=time.time() - t0),
              open(os.path.join(od, f"rec_{kind}.json"), "w"))
    return cfg, kind, f"{time.time() - t0:.0f}s nLED={len(tr)}"


BATCH = {
    "F": ["b1h__L1__ideal__T0", "b1h__L1__err__T0"],
    "E": ["hoy__limpio__ideal__T0", "hoy__U__ideal__T0", "hoy__L1__ideal__T0", "hoy__limpio__err__T0", "hoy__L1__err__T0",
          "b1s__L1__ideal__T0", "b1s__L1__err__T0", "z148n__L1__err__T0", "z148r__L1__err__T0",
          "hoy__L1__h__T0", "b1s__L1__h__T0", "hoy__L1__sph__T0", "b1s__L1__sph__T0",
          "b1s__limpio__ideal__T0", "b1s__U__ideal__T0", "b1i__L1__err__T0", "z130r__L1__err__T0", "z160r__L1__err__T0",
          "sq25__L1__ideal__Tinf", "sq19__Lfill__ideal__T@sq25", "b1s__L1__ideal__T4", "b1s__L8__ideal__T4",
          "z148n__L1__zp2__T0"],
}

if __name__ == "__main__":
    if sys.argv[1] == "geom":
        T = geom_table()
        print(f"T0 = {budget_T0():.0f} s")
        for g, r in T.items():
            print(g, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
        json.dump(dict(T0_s=budget_T0(), geoms=T), open(os.path.join(HERE, "geom.json"), "w"), indent=1)
    elif sys.argv[1] == "run":
        npr = int(sys.argv[2])
        cfgs = []
        for a in sys.argv[3:]:
            cfgs += BATCH.get(a, [a])
        for c in cfgs:
            gen(c)
        def kinds(c):
            g, pol, err, bud = c.split("__")
            lite = err in ("h", "sph", "sph7", "zp2", "zm2") or bud != "T0"
            return ("full", "half0", "half1") if lite else ("full", "half0", "half1", "fold0")
        tasks = [(c, k) for c in cfgs for k in kinds(c)]
        print(len(tasks), "tareas", flush=True)
        with mp.get_context("fork").Pool(npr, maxtasksperchild=1) as p:
            for r in p.imap_unordered(recon, tasks, chunksize=1):
                print(*r, flush=True)
        print("TODO TERMINADO", flush=True)

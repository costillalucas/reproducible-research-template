"""barrido_lrpx.py -- residuo vs lrpx a z=102, NA 0.069 (05/10). R_train (época EP, full) y, si existen, R held-out de
los folds (media de f0..f4, heldout_R_ring_lt7). Ajuste parabólico y bootstrap sobre LEDs. Uso: python3 barrido_lrpx.py [EP]"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
EXC = {"18,14", "18,16"}
V = {"z102_m276": 1.16, "z102_m267": 1.20, "z102_m258": 1.24, "z102_m250": 1.28, "z102_m242": 3.2 / 2.424, "final_z102": 3.2 / 2.35}


def row(var, ds, task):
    f = os.path.join(HERE, "out", var, ds, task, "metrics.jsonl")
    if not os.path.exists(f): return None
    for l in open(f):
        r = json.loads(l)
        if r["epoch"] == EP: return r
    return None


def fit(x, y):
    c = np.polyfit(x, y, 2)
    return c, (-c[1] / (2 * c[0]) if c[0] > 0 else None)


out = {"ep": EP, "colores": {}}
for ds in ("b_red", "b_green", "b_blue"):
    pts = []
    for var, lr in sorted(V.items(), key=lambda t: t[1]):
        r = row(var, ds, "real_A+init_z98.0_full")
        if r is None: continue
        per = {k: v[0] for k, v in r["per_led"].items() if v[3]}
        folds = [row(var, ds, f"real_A+init_z98.0_f{i}") for i in range(5)]
        # held-out propio: LEDs fuera del entrenamiento del fold, anillo < 7, SIN las de horcajadas excluidas siempre
        ho = [float(np.mean([v[0] for k, v in f["per_led"].items() if not v[3] and v[2] < 7 and k not in EXC]))
              for f in folds] if all(folds) else None
        tr_f = [f["train_R"] for f in folds if f] if all(folds) else None
        hoper = {k: v[0] for f in folds if f for k, v in f["per_led"].items() if not v[3] and v[2] < 7 and k not in EXC} if all(folds) else None
        pts.append(dict(hoper=hoper, var=var, lrpx=lr, train_R=r["train_R"], n=r["n_train"], per=per,
                        fold_heldout=(float(np.mean(ho)) if ho else None), fold_train=(float(np.mean(tr_f)) if tr_f else None)))
    if not pts: continue
    res = {"puntos": [{k: v for k, v in p.items() if k not in ("per", "hoper")} for p in pts]}
    x = np.array([p["lrpx"] for p in pts]); y = np.array([p["train_R"] for p in pts])
    if len(pts) >= 3:
        c, xm = fit(x, y); res["parabola"] = dict(coef=c.tolist(), xmin=xm)
        # incertidumbre: bootstrap de LEDs (mismo conjunto en todos los puntos) + residuos del ajuste
        keys = sorted(set.intersection(*[set(p["per"]) for p in pts]))
        M = np.array([[p["per"][k] for k in keys] for p in pts])
        rng = np.random.default_rng(0); bs = []
        for _ in range(2000):
            idx = rng.integers(0, len(keys), len(keys)); _, xb = fit(x, M[:, idx].mean(1))
            if xb is not None: bs.append(xb)
        res["boot_xmin"] = dict(p16=float(np.percentile(bs, 16)), p50=float(np.median(bs)), p84=float(np.percentile(bs, 84)), n=len(bs))
        # sensibilidad a qué puntos entran: los 3 alrededor del mínimo observado
        i = int(np.argmin(y))
        if 0 < i < len(y) - 1:
            _, x3 = fit(x[i - 1:i + 2], y[i - 1:i + 2]); res["xmin_3pts"] = x3
        # bootstrap pareado de diferencias consecutivas (¿es significativa la caída?)
        res["dR_consecutivas"] = [dict(de=float(x[j]), a=float(x[j + 1]), dR=float((M[j + 1] - M[j]).mean()),
                                       se=float((M[j + 1] - M[j]).std(ddof=1) / np.sqrt(len(keys)))) for j in range(len(x) - 1)]
    xh = [p for p in pts if p["fold_heldout"] is not None]
    if len(xh) >= 3:
        c, xm = fit(np.array([p["lrpx"] for p in xh]), np.array([p["fold_heldout"] for p in xh]))
        res["parabola_heldout"] = dict(coef=c.tolist(), xmin=xm)
        keys = sorted(set.intersection(*[set(p["hoper"]) for p in xh]))
        M = np.array([[p["hoper"][k] for k in keys] for p in xh])
        res["heldout_pareado"] = dict(n_led=len(keys), lrpx=[p["lrpx"] for p in xh], media=M.mean(1).tolist(),
                                      dR_vs_primero=[float((M[j] - M[0]).mean()) for j in range(len(xh))],
                                      se=[float((M[j] - M[0]).std(ddof=1) / np.sqrt(len(keys))) for j in range(len(xh))])
    out["colores"][ds] = res
    print(ds, json.dumps(res, indent=1))
json.dump(out, open(os.path.join(HERE, "barrido_lrpx.json"), "w"), indent=1)

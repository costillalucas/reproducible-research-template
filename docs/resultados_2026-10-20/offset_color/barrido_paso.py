"""barrido_paso.py -- barrido de PASO solo (05/10 tarde): radio de pupila en px fijo (NA·lrpx = 0.069·1.25), z 102/100.
R_train (época EP, full) en el conjunto de entrenamiento propio y en el conjunto COMÚN (sin (17,14),(17,16), que con
lrpx >= 1.35 quedan a horcajadas/DF en el modelo); diferencias pareadas por LED vs lrpx 1.25 (EE y bootstrap); parábola
con bootstrap; held-out de 5 folds en 1.25 y 1.40 (pareado por LED y por fold). Uso: python3 barrido_paso.py [EP] [DATASET]"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
DS = sys.argv[2] if len(sys.argv) > 2 else "b_red"
EXC = {"18,14", "18,16"}; X4 = {"17,14", "17,16"}
FULL = "real_A+init_z98.0_full"
rng = np.random.default_rng(0)


def row(var, task):
    f = os.path.join(HERE, "out", var, DS, task, "metrics.jsonl")
    if not os.path.exists(f): return None
    for l in open(f):
        r = json.loads(l)
        if r["epoch"] == EP: return r
    return None


def pair(a, b, keys):
    d = np.array([b[k] - a[k] for k in keys]); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    return dict(dR=float(d.mean()), se=float(d.std(ddof=1) / np.sqrt(len(d))), boot_p2_5=float(np.percentile(bs, 2.5)),
                boot_p97_5=float(np.percentile(bs, 97.5)), n=len(d))


out = {"ep": EP, "full": {}, "pares": {}}
per = {}
for z in (102, 100):
    for lr in (1.15, 1.20, 1.25, 1.30, 1.35, 1.40, 1.45):
        for sfx in ("", "_x4"):
            v = f"z{z}_p{round(lr*100)}{sfx}"; r = row(v, FULL)
            if r is None: continue
            p = {k: x[0] for k, x in r["per_led"].items() if x[3]}
            per[v] = {k: x[0] for k, x in r["per_led"].items()}
            com = [k for k in p if k not in X4]
            out["full"][v] = dict(z=z, lrpx=lr, mag=3.2 / lr, na=0.069 * 1.25 / lr, zNA=z * 0.069 * 1.25 / lr,
                                  train_R=r["train_R"], n=r["n_train"], R_comun=float(np.mean([p[k] for k in com])),
                                  R_x4=float(np.mean([per[v][k] for k in X4])), n_comun=len(com))
            print(v, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in out["full"][v].items()})
# conjunto común: LEDs entrenadas en TODAS las variantes, sin X4
tr_all = None
for v in out["full"]:
    s = {k for k, x in row(v, FULL)["per_led"].items() if x[3]} - X4
    tr_all = s if tr_all is None else tr_all & s
keys = sorted(tr_all)
for v in out["full"]:
    ref = v.split("_p")[0] + "_p125" + ("_x4" if v.endswith("_x4") else "")
    if ref in per and v != ref:
        out["pares"][f"{v} - {ref}"] = pair(per[ref], per[v], keys)
for a, b in (("z102_p125", "z100_p125"), ("z102_p140", "z100_p140"), ("z102_p125", "z102_p125_x4"), ("z102_p140", "z102_p140_x4")):
    if a in per and b in per: out["pares"][f"{b} - {a}"] = pair(per[a], per[b], keys)
for k, d in out["pares"].items(): print(k, {a: round(b, 5) if isinstance(b, float) else b for a, b in d.items()})
# parábola en R_comun (z 102, sin _x4) con bootstrap de LEDs
vs = [v for v in out["full"] if v.startswith("z102_p") and not v.endswith("_x4")]
if len(vs) >= 3:
    x = np.array([out["full"][v]["lrpx"] for v in vs]); M = np.array([[per[v][k] for k in keys] for v in vs])
    def fit(y):
        c = np.polyfit(x, y, 2); return c, (-c[1] / (2 * c[0]) if c[0] > 0 else None)
    c, xm = fit(M.mean(1)); bs = [fit(M[:, rng.integers(0, len(keys), len(keys))].mean(1))[1] for _ in range(2000)]
    bs = [b for b in bs if b is not None]
    out["parabola_comun"] = dict(coef=c.tolist(), xmin=xm, p16=float(np.percentile(bs, 16)), p84=float(np.percentile(bs, 84)),
                                 p2_5=float(np.percentile(bs, 2.5)), p97_5=float(np.percentile(bs, 97.5)), n_led=len(keys))
    print("parabola_comun", out["parabola_comun"])
# held-out de folds (pares 1.25 vs 1.40; '_x4' agregado 20/10: sin (17,14),(17,16) en el entrenamiento de ambos)
for sfx in ("", "_x4"):
    ho = {}
    for v in (f"z102_p125{sfx}", f"z102_p140{sfx}"):
        fs = [row(v, f"real_A+init_z98.0_f{i}") for i in range(5)]
        if not all(fs): continue
        hp = [{k: x[0] for k, x in f["per_led"].items() if not x[3] and x[2] < 7 and k not in EXC} for f in fs]
        ho[v] = hp
        out.setdefault("heldout", {})[v] = dict(media=float(np.mean([np.mean(list(h.values())) for h in hp])),
                                                por_fold=[float(np.mean(list(h.values()))) for h in hp],
                                                train_por_fold=[f["train_R"] for f in fs])
    if len(ho) == 2:
        a, b = ho[f"z102_p125{sfx}"], ho[f"z102_p140{sfx}"]
        allk = {}
        for i in range(5):
            for k in a[i]:
                if k in b[i]: allk[(i, k)] = b[i][k] - a[i][k]
        d = np.array(list(allk.values()))
        df = [np.mean([b[i][k] - a[i][k] for k in a[i] if k in b[i]]) for i in range(5)]
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        out[f"heldout_pareado_140_menos_125{sfx}"] = dict(dR=float(d.mean()), se_led=float(d.std(ddof=1) / np.sqrt(len(d))), n_led=len(d),
                                                     por_fold=[float(x) for x in df], se_fold=float(np.std(df, ddof=1) / np.sqrt(5)),
                                                     boot_p2_5=float(np.percentile(bs, 2.5)), boot_p97_5=float(np.percentile(bs, 97.5)),
                                                     dR_X4_excl=float(np.mean([v for (i, k), v in allk.items() if k not in X4])))
        print("heldout" + sfx, {v: out["heldout"][v] for v in ho}, out[f"heldout_pareado_140_menos_125{sfx}"])
json.dump(out, open(os.path.join(HERE, "barrido_paso.json" if DS == "b_red" else f"barrido_paso_{DS}.json"), "w"), indent=1)

"""analizar.py -- comparación pareada base (results/iteraciones_2026-09-30/out, offset nominal) vs offset por color
(out/die). Escribe analisis.json. Uso: nice python3 analizar.py [VARIANTE=die]"""
import glob, importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
BASE = os.path.join(RES, "iteraciones_2026-09-30", "out")
sys.path.insert(0, HERE)
import volumen  # noqa: E402
from runner import ramp  # noqa: E402

VAR = sys.argv[1] if len(sys.argv) > 1 else "die"
COL = {"b_red": "red", "b_green": "green", "b_blue": "blue"}
LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}
T = "real_A+init_z98.0_"
EP_C2 = [5, 40, 160]


def F_of(ds):
    d = os.path.join(RES, "captura_2026-09-28b", COL[ds])
    s = importlib.util.spec_from_file_location("F_" + ds, os.path.join(d, "fpm_red.py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def metrics(root, ds, task):
    f = os.path.join(root, ds, T + task, "metrics.jsonl")
    return {r["epoch"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else {}


def c1(root, ds):
    M = [metrics(root, ds, f"f{i}") for i in range(5)]
    eps = sorted(set.intersection(*[set(m) for m in M])) if all(M) else []
    return {e: dict(media=float(np.mean([m[e]["heldout_R_ring_lt7"] for m in M])),
                    folds=[m[e]["heldout_R_ring_lt7"] for m in M]) for e in eps}


def c2(F, root, ds, e, hrpx, lam):
    p = [os.path.join(root, ds, T + h, f"obj_e{e:03d}.npy") for h in ("half0", "half1")]
    if not all(map(os.path.exists, p)): return None
    a, b = (np.load(x).astype(complex) for x in p)
    sys.path.insert(0, os.path.join(RES, "iteraciones_2026-09-30", "analisis"))
    import particiones_c2 as PC
    return PC.both(F, a, b, hrpx, 2 * 0.07 / lam)


out = {"variante": VAR, "por_color": {}}
for ds, c in COL.items():
    F = F_of(ds); lam = LAM[c]
    hrpx = 512.0 / (1200 if c == "red" else 2000)
    r = dict(C1_base=c1(BASE, ds), C1_off=c1(os.path.join(HERE, "out", VAR), ds), C2={}, rampa={})
    for e in EP_C2:
        r["C2"][e] = dict(base=c2(F, BASE, ds, e, hrpx, lam), off=c2(F, os.path.join(HERE, "out", VAR), ds, e, hrpx, lam))
    mo = metrics(os.path.join(HERE, "out", VAR), ds, "full")
    for e, row in mo.items():
        fb = os.path.join(BASE, ds, T + "full", f"obj_e{e:03d}.npy")
        rb = ramp(np.load(fb), hrpx, lam) if os.path.exists(fb) else None
        r["rampa"][e] = dict(base=rb, off=row.get("ramp"))
    mb = metrics(BASE, ds, "full")
    r["trainR_full"] = {e: dict(base=mb[e]["train_R"], off=mo[e]["train_R"]) for e in mo if e in mb}
    out["por_color"][c] = r
    print(c, "listo", flush=True)

out["volumen"] = {}
for e in (40, 160):
    for tag, root in (("base", BASE), ("off", os.path.join(HERE, "out", VAR))):
        p = {c: os.path.join(root, ds, T + "full", f"obj_e{e:03d}.npy") for ds, c in COL.items()}
        if all(map(os.path.exists, p.values())):
            out["volumen"][f"{tag}_e{e}"] = volumen.medir({c: np.load(v) for c, v in p.items()})
            print("volumen", tag, e, flush=True)
json.dump(out, open(os.path.join(HERE, f"analisis_{VAR}.json"), "w"), indent=1, default=float)

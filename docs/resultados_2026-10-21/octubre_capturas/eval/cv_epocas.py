"""cv_epocas.py -- R held-out (5 folds, anillos < 7, = C1) por época, sin FPM en la misma geometría, y lattice (C3) del full.

    python3 cv_epocas.py [VARIANTE]     (por defecto rojo_final; z102_p129 = mismas corridas a 40 épocas)
Held-out de un fold = LEDs no entrenados, fuera de los 2 excluidos a horcajadas (18,14),(18,16) (en metrics.jsonl
'heldout_R_ring_lt7' SÍ los cuenta: se recalcula desde per_led). Sin FPM = objeto inicial (fourier_avg de los 6 BF),
evaluado en todos los LEDs no BF con anillo < 7 (= run.py 'nofpm'). Escribe cv_<variante>.json."""
import json, os, sys
import numpy as np
import comun as C

var = sys.argv[1] if len(sys.argv) > 1 else "rojo_final"
O = os.path.join(C.OC, "out", var, C.DS)
ex = {f"{a},{b}" for a, b in C.EXCL}
per = {}
for f in range(5):
    for l in open(os.path.join(O, f"real_A+init_z98.0_f{f}", "metrics.jsonl")):
        r = json.loads(l)
        v = [x[0] for k, x in r["per_led"].items() if not x[3] and x[2] < 7 and k not in ex]
        per.setdefault(r["epoch"], [None] * 5)[f] = float(np.mean(v))
ep = sorted(e for e, v in per.items() if None not in v)
M = np.array([per[e] for e in ep])
lat = {}
fp = os.path.join(O, "real_A+init_z98.0_full", "metrics.jsonl")
if os.path.exists(fp):
    for l in open(fp):
        r = json.loads(l); lat[r["epoch"]] = r["lattice"]
F, geo, D = C.load(var)
o0 = F.initial_object(D["I"], geo["factor"], "fourier_avg")
ks = [k for k in D["keys"] if k not in F.BF and F.ring(k) < 7]
pred = F.predict(o0, ks, geo)
nf = float(np.mean([F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k])[0] for k in ks]))
out = dict(variante=var, sin_fpm=nf, epocas=ep, media=M.mean(1).tolist(), sd=M.std(1).tolist(), por_fold=M.tolist(),
           lattice_full={str(k): v for k, v in lat.items()})
for a, b in [(40, 80), (40, 160), (80, 160)]:
    if a in ep and b in ep:
        d = M[ep.index(b)] - M[ep.index(a)]
        out[f"dif_{b}_menos_{a}"] = dict(media=float(d.mean()), sd=float(d.std()), por_fold=d.tolist())
for e, m, s in zip(ep, out["media"], out["sd"]):
    print(f"ep {e:3d}  R {m:.4f} ± {s:.4f}  lattice {lat.get(e, float('nan')):.2e}")
print("sin FPM", round(nf, 4), {k: v for k, v in out.items() if k.startswith("dif")})
json.dump(out, open(os.path.join(C.HERE, f"cv_{C.DS}_{var}.json"), "w"), indent=1)

"""vol_pareado.py -- volumen de fase partícula a partícula, rojo, die vs base en la misma época (emparejadas por centroide
< 2 µm y diámetro compatible, d >= 5 µm en ambas). Evita el sesgo de umbral (el umbral es max(0.3, 5 ruido))."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import volumen
T = "real_A+init_z98.0_full"
P = {"base": os.path.join(HERE, "..", "iteraciones_2026-09-30", "out", "b_red", T), "die": os.path.join(HERE, "out", "die", "b_red", T)}
out = {}
for e in (5, 40, 160):
    R = {}
    for tag, p in P.items():
        rows, _ = volumen.particulas(np.load(os.path.join(p, f"obj_e{e:03d}.npy")))
        R[tag] = [r for r in rows if not r["bad"] and not r["merged"]]
    yb = np.array([[r["y"], r["x"]] for r in R["base"]]); q = []
    for r in R["die"]:
        dd = np.hypot(*(yb - [r["y"], r["x"]]).T); j = dd.argmin(); b = R["base"][j]
        if dd[j] < 2 and min(r["d"], b["d"]) >= 5 and abs(r["d"] - b["d"]) < 0.5 * max(r["d"], b["d"]) and b["V"] > 0:
            q.append((r["V"] / b["V"], r["d"] / b["d"], r["phi"] / b["phi"]))
    q = np.array(q)
    out[e] = dict(N=len(q), V_die_sobre_base=float(np.median(q[:, 0])), p25=float(np.percentile(q[:, 0], 25)),
                  p75=float(np.percentile(q[:, 0], 75)), d_die_sobre_base=float(np.median(q[:, 1])), pico_die_sobre_base=float(np.median(q[:, 2])))
    print(e, {k: round(v, 3) for k, v in out[e].items()})
json.dump(out, open(os.path.join(HERE, "vol_pareado.json"), "w"), indent=1)

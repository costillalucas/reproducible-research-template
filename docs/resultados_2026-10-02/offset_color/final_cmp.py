"""final_cmp.py -- compara final_z101 (z=101, die por color, sin LEDs a horcajadas) con base/die/sin18 a la época 40:
rayas (rayas2.rayas), rampa y R_train (metrics.jsonl; R_train también sobre el conjunto común sin (18,14),(18,16)),
volumen con máscara fija (vol_fijo.analizar, segmentación en el nominal 'base') y cocientes V_G/V_R, V_B/V_R.
Uso: nice python3 final_cmp.py [EP]"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rayas2 import rayas, path
import vol_fijo as VF
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
EXC = {"18,14", "18,16"}
RUNS = {"b_red": ["base", "die", "nom_sin18", "die_sin18", "d106_z101", "final_z101", "final_z101_dfnorm"],
        "b_green": ["base", "die", "g_nom_sin18", "g_die_sin18", "final_z101", "final_z101_dfnorm"],
        "b_blue": ["base", "die", "final_z101"]}


def metrics(var, ds):
    root = os.path.join(HERE, "..", "iteraciones_2026-09-30", "out") if var == "base" else os.path.join(HERE, "out", var)
    f = os.path.join(root, ds, "real_A+init_z98.0_full", "metrics.jsonl")
    if not os.path.exists(f): return None
    for l in open(f):
        r = json.loads(l)
        if r["epoch"] == EP:
            com = [v[0] for k, v in r["per_led"].items() if v[3] and k not in EXC]
            allr = [v[0] for k, v in r["per_led"].items()]
            return dict(train_R=r["train_R"], n_train=r["n_train"], train_R_comun=float(np.mean(com)),
                        R_todas=float(np.mean(allr)), ramp_ptp=(r.get("ramp") or {}).get("ptp"))
    return None


out = {"ep": EP, "runs": {}, "vol": {}}
for ds, vs in RUNS.items():
    for v in vs:
        p = path(v, ds, EP)
        if not os.path.exists(p): continue
        o = np.load(p); rr = rayas(o); m = metrics(v, ds) or {}
        out["runs"][f"{v}:{ds}"] = dict(N=o.shape[0], rayas_rms=rr["rms_perfil_rad"], mad=rr["mad_fondo_rad"], **m)
        print(v, ds, o.shape[0], {k: (round(x, 4) if isinstance(x, float) else x) for k, x in out["runs"][f"{v}:{ds}"].items()}, flush=True)
for var in ("final_z101", "final_z101_dfnorm", "die"):
    out["vol"][var] = VF.analizar(EP, var=var, ref="base"); print(var, json.dumps(out["vol"][var]), flush=True)
json.dump(out, open(os.path.join(HERE, "final_cmp.json"), "w"), indent=1)

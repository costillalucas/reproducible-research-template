"""final_cmp_z102.py -- como final_cmp.py, para final_z102 (z=102, NA 0.069, lrpx 1.362 µm, die, sin horcajadas R/G) contra
base (nominal z98, lrpx 1.28) y final_z101, época EP. Volumen con máscara fija segmentada en 'base' (vol_fijo.analizar): mismo
factor que el nominal en los 3 colores (R3/G5/B5) -> mismas N, pareado píxel a píxel. vol_fijo usa hr = 512/N (lrpx 1.28):
para z102 el área real por píxel es s^2 mayor (s = 1.3617/1.28), así que se reporta también d_vol/d corregido (x s^-1/3) y
V_z102/V_ref x s^2. Los cocientes entre colores no dependen de s. Uso: nice python3 final_cmp_z102.py [EP]"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rayas2 import rayas, path
import vol_fijo as VF
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
EXC = {"18,14", "18,16"}
S = (3.2 / 2.35) / 1.28
RUNS = {ds: ["base", "final_z101", "final_z102"] + (["final_z101_f5"] if ds == "b_green" else []) for ds in ("b_red", "b_green", "b_blue")}


def metrics(var, ds):   # = final_cmp.metrics
    root = os.path.join(HERE, "..", "iteraciones_2026-09-30", "out") if var == "base" else os.path.join(HERE, "out", var)
    f = os.path.join(root, ds, "real_A+init_z98.0_full", "metrics.jsonl")
    if not os.path.exists(f): return None
    for l in open(f):
        r = json.loads(l)
        if r["epoch"] == EP:
            com = [v[0] for k, v in r["per_led"].items() if v[3] and k not in EXC]
            return dict(train_R=r["train_R"], n_train=r["n_train"], train_R_comun=float(np.mean(com)), n_comun=len(com),
                        ramp_ptp=(r.get("ramp") or {}).get("ptp"))
    return None


out = {"ep": EP, "s": S, "runs": {}, "vol": {}}
for ds, vs in RUNS.items():
    for v in vs:
        p = path(v, ds, EP)
        if not os.path.exists(p): continue
        o = np.load(p); rr = rayas(o); m = metrics(v, ds) or {}
        out["runs"][f"{v}:{ds}"] = dict(N=o.shape[0], rayas_rms=rr["rms_perfil_rad"], **m)
        print(v, ds, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in out["runs"][f"{v}:{ds}"].items()}, flush=True)
out["vol"]["z102_vs_base"] = VF.analizar(EP, var="final_z102", ref="base")
out["vol"]["z102_vs_z101_RB"] = VF.analizar(EP, var="final_z102", ref="final_z101", cols=("red", "blue"))
out["vol"]["z101f5_vs_base_G"] = VF.analizar(EP, var="final_z101_f5", ref="base", cols=("green",))
out["vol"]["z102_vs_z101f5_G"] = VF.analizar(EP, var="final_z102", ref="final_z101_f5", cols=("green",))
for c, r in out["vol"]["z102_vs_base"]["por_color"].items():
    r["dvol_d_die_corr_s"] = r["dvol_d_die"] * S ** (-1 / 3); r["Vdie_Vnom_x_s2"] = r["Vdie_Vnom"] * S ** 2
print(json.dumps(out["vol"], indent=1), flush=True)
json.dump(out, open(os.path.join(HERE, "final_cmp_z102.json"), "w"), indent=1)

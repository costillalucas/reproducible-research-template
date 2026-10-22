"""vol_p129.py -- volumen de fase con la geometría medida (20/10): z102_p129 (lrpx 1.29 del micrómetro, NA 0.0669, z 102,
die) contra base (nominal z98, lrpx 1.28), época EP, los tres colores. Máscara fija segmentada en base (vol_fijo.analizar);
mismo factor R3/G5/B5 -> mismas N. Escala s = 1.29/1.28 (d_vol/d corregido x s^-1/3, V/V x s^2); los cocientes entre
colores no dependen de s. Pregunta: ¿con la geometría medida V_G/V_R y V_B/V_R se acercan a lo esperado (1.23 / 1.42)?
Uso: nice python3 vol_p129.py [EP]"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rayas2 import rayas, path
import vol_fijo as VF
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
S = 1.29 / 1.28
out = {"ep": EP, "s": S, "rayas": {}}
for v in ("base", "z102_p129"):
    for ds in ("b_red", "b_green", "b_blue"):
        p = path(v, ds, EP)
        if os.path.exists(p): out["rayas"][f"{v}:{ds}"] = rayas(np.load(p))["rms_perfil_rad"]
out["vol"] = VF.analizar(EP, var="z102_p129", ref="base")
for c, r in out["vol"]["por_color"].items():
    r["dvol_d_die_corr_s"] = r["dvol_d_die"] * S ** (-1 / 3); r["Vdie_Vnom_x_s2"] = r["Vdie_Vnom"] * S ** 2
print(json.dumps(out, indent=1), flush=True)
json.dump(out, open(os.path.join(HERE, "vol_p129.json"), "w"), indent=1)

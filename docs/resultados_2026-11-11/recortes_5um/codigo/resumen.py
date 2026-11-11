#!/usr/bin/env python3
"""resumen.py -- medianas [p25, p75] por brazo y diferencias pareadas contra r400, desde medidas.json. Escribe resumen.json."""
import json, numpy as np
P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/"
F = json.load(open(P0 + "medidas.json"))
ARMS = ["r400", "b400", "r200", "r20", "r20sc", "r40", "r80", "n400", "n20"]
MET = ["fase_fwhm_g", "fase_fwhm_r", "fase_borde", "fase_pico", "fase_vol", "fase_vol35", "fase_fondo_rms", "marco_std_fase",
       "amp_fwhm_g", "amp_fwhm_r", "amp_borde", "amp_p0", "desplaz"]
q = lambda v: (float(np.nanmedian(v)), float(np.nanpercentile(v, 25)), float(np.nanpercentile(v, 75)), int(np.isfinite(v).sum()))
noenv = [f for f in F if not f.get("r400_fase_envuelta")]
out = {"n_esferas": len(F), "excluidas_por_envoltura_r400": [f["id"] for f in F if f.get("r400_fase_envuelta")], "brazos": {}, "pareado": {}}
L = {m: q(np.array([f.get(f"LR_amp_{m.split('_', 1)[1]}", np.nan) for f in F])) for m in ["amp_fwhm_g", "amp_fwhm_r", "amp_borde"]}
out["brazos"]["LR"] = L
print(f"{'brazo':6} {'métrica':15} mediana [p25, p75] n")
for m, v in L.items():
    print(f"{'LR':6} {m:15} {v[0]:7.2f} [{v[1]:6.2f}, {v[2]:6.2f}] {v[3]}")
for a in ARMS:
    out["brazos"][a] = {}
    for m in MET:
        base = noenv if m.startswith("fase") else F
        v = np.array([f.get(f"{a}_{m}", np.nan) for f in base], float)
        if np.isfinite(v).sum() == 0:
            continue
        out["brazos"][a][m] = q(v)
        r = out["brazos"][a][m]
        print(f"{a:6} {m:15} {r[0]:7.2f} [{r[1]:6.2f}, {r[2]:6.2f}] {r[3]}")
for a in ARMS[1:] + ["LR"]:
    out["pareado"][a] = {}
    for m in ["fase_fwhm_g", "fase_borde", "fase_vol", "fase_vol35", "amp_fwhm_g", "amp_borde"]:
        if a == "LR" and not m.startswith("amp"):
            continue
        base = noenv if m.startswith("fase") else F
        ka = f"LR_{m}" if a == "LR" else f"{a}_{m}"
        d = np.array([f.get(ka, np.nan) - f.get(f"r400_{m}", np.nan) for f in base], float)
        if np.isfinite(d).sum() == 0:
            continue
        out["pareado"][a][m] = dict(dif_mediana=float(np.nanmedian(d)), p25=float(np.nanpercentile(d, 25)),
                                    p75=float(np.nanpercentile(d, 75)), n=int(np.isfinite(d).sum()),
                                    n_menor=int((d < 0).sum()))
        r = out["pareado"][a][m]
        print(f"pareado {a}-r400 {m:12} {r['dif_mediana']:+7.2f} [{r['p25']:+.2f}, {r['p75']:+.2f}] n {r['n']}, menor en {r['n_menor']}")
json.dump(out, open(P0 + "resumen.json", "w"), indent=1)

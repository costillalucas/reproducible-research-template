"""Paso por columnas (LEDs (17,14),(17,15),(17,16): BF completos, misma fila) desde paso_espectral.json.
Geometria exacta: sin_x = x/sqrt(x^2+y^2+z^2), x = 6 mm, y ~ -1 mm (fila 17 con offset+die)."""
import json, numpy as np
d = json.load(open("paso_espectral.json")); LAM = dict(red=0.63, green=0.53, blue=0.47); N, PX, P = 400, 1.28, 6.0
out = {}
for c, lam in LAM.items():
    L = {tuple(r["led"]): r for r in d[c]["leds"]}
    s1, s2 = L[(17,16)]["c1"] - L[(17,15)]["c1"], L[(17,15)]["c1"] - L[(17,14)]["c1"]
    s = (L[(17,16)]["c1"] - L[(17,14)]["c1"]) / 2; ss = abs(s1 - s2) / 2 + 0.25   # asimetria + 0.25 bin piso
    sin = s * lam / (N * PX); z = np.sqrt((P / sin)**2 - P**2 - 1.0); sz = z * ss / s
    rb, srb = d[c]["rb_bins"], d[c]["rb_se"]
    NA = rb * lam / (N * PX); zNA = P / (s / rb)
    out[c] = dict(step_bins=s, step_se=ss, sin_step=sin, z_mm_dx128=z, z_se=sz, NA_dx128=NA,
                  zNA_mm=zNA, zNA_se=zNA*np.hypot(ss/s, srb/rb), dx_needed_for_z98=PX*98/z, dx_needed_for_z101=PX*101/z)
zs = np.array([out[c]["z_mm_dx128"] for c in out]); out["media_z_dx128"] = dict(z=zs.mean(), sd=zs.std(ddof=1))
json.dump(out, open("resumen.json", "w"), indent=1); print(json.dumps(out, indent=1))

"""analitica.py -- (1) deriva del eje local de iluminación a través de una tesela (no telecentricidad medida por
Lucas 21/10: d_ep ≈ 324 mm) y (2) residuo de fase no paraxial dependiente de la LED de la onda esférica, que el modelo
de onda plana NO absorbe: δφ ≈ k h² [1 - cosθ (1 - sin²θ)] / 2z en el borde de la tesela (h = semilado), peor
dirección, LED a NA_ill 0.40. La parte cuadrática común (k h²/2z) y la no telecentricidad (cuadrática común
k h²/2 d_ep) se absorben exactamente en el objeto (Fresnel): solo dan un 'bowl' de fase de fondo. Escribe analitica.json."""
import json
import numpy as np
LRPX, LAM, DEP, P = 1.29e-3, 0.63e-3, 324.0, 6.0     # mm
k = 2 * np.pi / LAM
out = []
for z in (102.0, 130.0, 150.0):
    for n in (160, 256, 400, 1120):
        h = n * LRPX / 2
        s = 0.40; c = np.sqrt(1 - s * s)
        res = k * h * h * (1 - c * (1 - s * s)) / (2 * z)
        bowl = k * h * h * (1 / z + 1 / DEP) / 2
        drift_mrad = n * LRPX * (1 / z + 1 / DEP) * 1e3
        drift_steps = n * LRPX * (1 + z / DEP) / P
        out.append(dict(z=z, tesela_px=n, deriva_mrad=round(drift_mrad, 2), deriva_pasos=round(drift_steps, 3),
                        bowl_rad=round(bowl, 2), residuo_rad_NA040=round(res, 3)))
        print(out[-1])
json.dump(out, open("analitica.json", "w"), indent=1)

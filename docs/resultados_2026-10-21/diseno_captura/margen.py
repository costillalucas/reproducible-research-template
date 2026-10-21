"""margen.py -- analítico: margen (en pasos de LED) entre el borde de campo claro y la LED más cercana, vs z,
para distintos corrimientos del eje a lo largo de filas a (pasos): 0 = eje sobre LED (b1, ROI corrida),
0.5 = mitad de paso (nominal), 0.677/0.605/0.525 = mitad + offset de dado R/G/B (1.06/0.63/0.15 mm, docs/resultado_rojo).
Borde: r_edge = z·tan(asin NA)/pitch. Escribe margen.json."""
import json
import numpy as np
P = 6.0
A = {"b1_eje_en_LED": 0.0, "mitad_nominal": 0.5, "rojo(+1.06)": 0.5 + 1.06 / 6, "verde(+0.63)": 0.5 + 0.63 / 6,
     "azul(+0.15)": 0.5 + 0.15 / 6}
ii, jj = np.mgrid[-8:9, -8:9]
def marg(z, a, na=0.067):
    r = np.hypot(ii - a, jj).ravel()
    e = z * np.tan(np.arcsin(na)) / P
    d = r - e
    return float(np.min(np.abs(d))), int((d < 0).sum())
zs = np.arange(95, 170.1, 0.5)
out = {n: {f"{z:.1f}": marg(z, a) for z in zs} for n, a in A.items()}
json.dump(out, open("margen.json", "w"), indent=0)
print("z     " + "  ".join(f"{n[:12]:>12s}" for n in A))
for z in [100, 102, 110, 120, 130, 140, 144, 146, 148, 150, 152, 155, 160, 165]:
    print(f"{z:5.0f} " + "  ".join(f"{marg(z, a)[0]:6.3f}/{marg(z, a)[1]:3d}bf" for a in A.values()))
for n, a in A.items():
    m = [(marg(z, a)[0], z) for z in zs if 140 <= z <= 160]
    best = max(m)
    rob = [(min(marg(z + dz, a)[0] for dz in np.arange(-2, 2.01, 0.5)), z) for z in zs if 140 <= z <= 160]
    print(n, "mejor z 140-160: %.1f (margen %.3f)" % (best[1], best[0]), "| robusto a ±2 mm: z %.1f (margen peor %.3f)" % (max(rob)[1], max(rob)[0]),
          "| NA 0.070 a ese z: %.3f" % marg(max(rob)[1], a, 0.070)[0])

"""Selección de esferas de 5 µm aisladas sobre la imagen BF cruda del LED central (17,15), q = S/F (oscuro restado, flat),
en el recorte de 400 px (filas 360:760, cols 80:480 del ROI) = datos/prep.npz de plan_2026-11-04/epocas_400b (idéntico píxel a
píxel a epocas_200/datos/prep.npz en el solape 100:300). En BF las esferas se ven como un disco OSCURO de ~5-7 px con halo claro.
  oscuro  o = gauss1(mediana31(q) - q); esfera = máximo local 9x9 de o con o > 0.25.
  energía e = sqrt(gauss2.5(h^2)), h = q - mediana31(q); 'cualquier cosa' = máximo local 11x11 de e con e > 0.06.
Aislada si: (1) ningún otro objeto (máximo de e > 0.08) a menos de 20 px (25.8 µm) del centro; (2) a >= 20 px del borde del recorte
de 400 px; (3) una sola componente oscura (o > 0.25) dentro de 12 px; (4) esfera simple: o > 0.4 en el centro, componente o > 0.25
de área <= 60 px y razón de ejes (2º momento) < 1.4 (descarta dobletes/grumos alargados y manchas débiles o desenfocadas).
Centro = centroide de o (o>0) en 7x7, redondeado al píxel. en_200 = cae a >= 12 px del borde del recorte de 200 px (100:300)."""
import json, numpy as np
from scipy import ndimage as ndi
P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/"
q = np.load(P0 + "datos/q_bf400.npy")
med = ndi.median_filter(q, 31); h = q - med
o = ndi.gaussian_filter(med - q, 1)
e = np.sqrt(ndi.gaussian_filter(h ** 2, 2.5))
ys, xs = np.nonzero((o == ndi.maximum_filter(o, 9)) & (o > 0.25))
ey, ex = np.nonzero((e == ndi.maximum_filter(e, 11)) & (e > 0.08))
lab, _ = ndi.label(o > 0.25)
out = []
yy, xx = np.mgrid[-3:4, -3:4]
for y, x in sorted(zip(ys, xs)):
    if not (20 <= y < 380 and 20 <= x < 380):
        continue
    w = np.clip(o[y - 3:y + 4, x - 3:x + 4], 0, None)
    cy, cx = y + (w * yy).sum() / w.sum(), x + (w * xx).sum() / w.sum()
    d = np.hypot(ey - cy, ex - cx); d = d[d > 4]
    vec = float(d.min()) if d.size else 1e9
    comp = np.unique(lab[max(0, y - 12):y + 13, max(0, x - 12):x + 13]); ncomp = int((comp > 0).sum())
    if vec <= 20 or ncomp != 1 or o[y, x] <= 0.4:
        continue
    m = lab == lab[y, x]; Y, X = np.nonzero(m); ev = np.linalg.eigvalsh(np.cov(np.vstack([Y, X])))
    razon = float(np.sqrt(ev[1] / ev[0]))
    if m.sum() > 60 or razon >= 1.4:
        continue
    fy, fx = int(round(cy)), int(round(cx))
    en200 = bool(112 <= fy < 288 and 112 <= fx < 288)
    out.append(dict(fila400=fy, col400=fx, fila_roi=fy + 360, col_roi=fx + 80, oscuro=round(float(o[y, x]), 3),
                    vecino_px=round(vec, 1), vecino_um=round(vec * 1.29, 1), area_px=int(m.sum()), razon_ejes=round(razon, 2), en_200=en200))
for i, p in enumerate(out):
    p["id"] = f"S{i + 1:02d}"
json.dump(dict(criterio=__doc__, recorte400=[360, 80, 400], recorte200=[460, 180, 200], particulas=out),
          open(P0 + "particulas.json", "w"), indent=1, ensure_ascii=False)
print(len(out), "en 200:", sum(p["en_200"] for p in out))
for p in out: print(p)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(12, 12)); ax.imshow(q, cmap="gray", vmin=0.4, vmax=1.2)
ax.plot(ex, ey, "c.", ms=4)
for p in out:
    ax.add_patch(plt.Rectangle((p["col400"] - 10.5, p["fila400"] - 10.5), 20, 20, fill=False, ec="r"))
    ax.text(p["col400"] + 11, p["fila400"], p["id"], color="r", fontsize=9)
ax.add_patch(plt.Rectangle((99.5, 99.5), 200, 200, fill=False, ec="y"))
plt.tight_layout(); plt.savefig(P0 + "fig_seleccion.png", dpi=70)

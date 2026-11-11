"""Selección de partículas aisladas sobre la imagen BF cruda (LED (17,15) / flat, ROI entero, 18 ms; = codigo/explorar_bf.py).
Las perlas en BF se ven como un lóbulo claro + uno oscuro (no un mínimo simple), así que el detector usa la ENERGÍA local del
contraste: h = q - mediana31(q), e = sqrt(gauss2.5(h^2)); candidato = máximo local 11x11 de e con e > 0.06 (~2x el piso de e).
Aislada si: (1) ningún candidato con e > 0.10 a menos de 20 px (25.8 µm); (2) ninguna mancha grande (|gauss1(h)| > 0.15,
área > 60 px) a menos de 20 px; (3) 0.12 < e < 0.45 (perla clara, no grumo); (4) a >= 20 px del borde de su recorte de 200 px.
Centro refinado = centroide de e^2 en una ventana de 9x9 (redondeado al píxel; el recorte de 20 px se centra en ese píxel).
Regiones de 200 px (esquina fila,col en el ROI): A 440,380; B 770,460; C 520,180 (A y B lanzadas con un detector anterior
que confundía los dos lóbulos de una perla con dos partículas; C = mejor región extra con este detector; ver INFORME)."""
import json, numpy as np
from scipy import ndimage as ndi
P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes/"
q = np.load(P0 + "datos/q_bf_roi.npy").astype(float)
bg = ndi.median_filter(q, 31); h = q - bg
e = np.sqrt(ndi.gaussian_filter(h ** 2, 2.5))
ys, xs = np.nonzero((e == ndi.maximum_filter(e, 11)) & (e > 0.06)); s = e[ys, xs]
dev = np.abs(ndi.gaussian_filter(h, 1)) > 0.15
lab, n = ndi.label(dev); area = ndi.sum(dev, lab, range(1, n + 1))
big = np.isin(lab, 1 + np.nonzero(area > 60)[0]); dist_big = ndi.distance_transform_edt(~big)
P = np.stack([ys, xs], 1); dd = np.hypot(*(P[:, None, :] - P[None, :, :]).transpose(2, 0, 1)); np.fill_diagonal(dd, 1e9)
ds = np.where((s > 0.10)[None, :], dd, 1e9).min(1)
ok = (ds > 20) & (dist_big[ys, xs] > 20) & (s > 0.12) & (s < 0.45)
REG = {"A": (440, 380), "B": (770, 460), "C": (520, 180)}
out = []
yy, xx = np.mgrid[-4:5, -4:5]
for r, (f0, c0) in REG.items():
    m = ok & (ys >= f0 + 20) & (ys < f0 + 180) & (xs >= c0 + 20) & (xs < c0 + 180)
    k = 0
    for i in np.nonzero(m)[0]:
        w = e[ys[i] - 4:ys[i] + 5, xs[i] - 4:xs[i] + 5] ** 2
        cy, cx = ys[i] + (w * yy).sum() / w.sum(), xs[i] + (w * xx).sum() / w.sum()
        k += 1
        out.append(dict(id=f"{r}{k:02d}", region=r, fila_roi=int(round(cy)), col_roi=int(round(cx)),
                        fila_rec=int(round(cy)) - f0, col_rec=int(round(cx)) - c0, energia=round(float(s[i]), 3),
                        vecino_px=round(float(ds[i]), 1), vecino_um=round(float(ds[i]) * 1.29, 1),
                        mancha_grande_px=round(float(dist_big[ys[i], xs[i]]), 1)))
json.dump(dict(criterio=__doc__, regiones={k: [v[0], v[1], 200] for k, v in REG.items()}, particulas=out),
          open(P0 + "particulas.json", "w"), indent=1, ensure_ascii=False)
print(len(out)); [print(o) for o in out]

#!/usr/bin/env python3
"""rampa.py -- rampa lineal de fase de cada reconstrucción en la huella de la esfera, en BINS de Fourier del recorte de 20 px
(1 bin = 2π a lo largo de 25.8 µm): g = angle(sum z(x+1)·conj z(x)) por eje, excluyendo r < 6 µm (la esfera), ·60/2π.
Comparada con el error de redondeo predicho del LED central (17,15) y de la media de los 5 BF para la geometría de cada recorte de
20 px: (f_redondeado - f_exacto)/dk (spectral_ops.py:34-35). Salida: rampa.json."""
import json, os, sys
import numpy as np
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/codigo")
import recortes as RC  # noqa: E402
RP = RC.RP
P0, B = RC.P0 + "/", "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/"
yy, xx = np.mgrid[:60, :60]; Rm = np.hypot(xx - 30, yy - 30) * 0.43 >= 6


def rampa(o):
    z = o / np.abs(o).clip(1e-12)
    mx = Rm[:, 1:] & Rm[:, :-1]; my = Rm[1:, :] & Rm[:-1, :]
    gx = np.angle((z[:, 1:] * np.conj(z[:, :-1]))[mx].sum()); gy = np.angle((z[1:, :] * np.conj(z[:-1, :]))[my].sum())
    return gx * 60 / (2 * np.pi), gy * 60 / (2 * np.pi)


def redondeo(f0, c0, tam=20):
    F, _ = RP.cargar_solver("red", RP.FACTOR["red"])
    eje_x, eje_y = RP.ROI_CAL[0] + RP.ROI_CAL[2] / 2, RP.ROI_CAL[1] + RP.ROI_CAL[2] / 2
    geo = F.geometry(RP.Z_MM, offset_mm=((eje_x - (RC.ROI[0] + c0 + tam / 2)) * RP.MM_POR_PX,
                                         (eje_y - (RC.ROI[1] + f0 + tam / 2)) * RP.MM_POR_PX), crop=tam)
    H = tam * geo["factor"]; dk = 1 / (H * geo["hrpx"]); ax = (np.arange(H) - H // 2) * dk
    out = {}
    for k in [(17, 15), (16, 15), (17, 14), (17, 16), (18, 15)]:
        fx, fy = geo["fxy"][k]
        ys, xs = F.led_crop_window((H, H), geo["hrpx"], (tam, tam), fx, fy)
        out[k] = ((ax[xs.start + tam // 2] - fx) / dk, (ax[ys.start + tam // 2] - fy) / dk)
    return out


J = json.load(open(P0 + "particulas.json"))["particulas"]
o400 = np.load(B + "epocas_400b/snapshots/objeto_full_e160.npy"); n400 = np.load(B + "red_nulo_df/objeto_complejo.npy")
res = []
for p in J:
    y, x = 3 * p["fila400"], 3 * p["col400"]
    f = dict(id=p["id"], r400=rampa(o400[y - 30:y + 30, x - 30:x + 30]), n400=rampa(n400[y - 30:y + 30, x - 30:x + 30]))
    for nom, c in (("r20", "r20"), ("n20", "r20_nulo"), ("r20_sincambian", "r20_sincambian")):
        fz = P0 + f"runs/{c}/{p['id']}.npz"
        if os.path.exists(fz):
            f[nom] = rampa(np.load(fz)["obj"])
    rd = redondeo(360 + p["fila400"] - 10, 80 + p["col400"] - 10)
    f["redondeo_centro"] = rd[(17, 15)]; f["redondeo_media_BF"] = tuple(np.mean(list(rd.values()), 0))
    res.append(f)
    print(f["id"], " ".join(f"{k} ({v[0]:+.2f},{v[1]:+.2f})" for k, v in f.items() if k != "id"))
json.dump(res, open(P0 + "rampa.json", "w"), indent=1, default=float)

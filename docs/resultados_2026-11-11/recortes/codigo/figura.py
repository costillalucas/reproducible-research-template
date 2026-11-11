#!/usr/bin/env python3
"""figura.py -- fig_recortes.png: algunas partículas lado a lado (ventana de ±11 µm alrededor de cada una).
Columnas: LR BF crudo (sqrt I, LED (17,15)) | 200 px amp | 200 px fase | 20 px amp | 20 px fase | nulo 200 amp | nulo 200 fase
| nulo 20 amp. Amplitud = |o|/|b| (gris, percentiles 1–99), fase = angle(o/b) (RdBu, ±p99.5 de |fase| de cada panel), b = media compleja del anillo 7.5–11 µm (= medir.py).
Abajo: recorte de 20 px entero (amp) de la primera partícula, para ver bordes / wrap-around."""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes"
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo")
os.environ.setdefault("Z_MM", "99.5"); os.environ.setdefault("NA_OBJ", "0.0720"); os.environ.setdefault("LAM_NM", "617")
import reconstruir_plan as RP  # noqa: E402

W = 11.0


def ventana(img, cy, cx, px):
    r = int(round(W / px))
    H = img.shape[0]
    y0, y1, x0, x1 = max(cy - r, 0), min(cy + r + 1, H), max(cx - r, 0), min(cx + r + 1, H)
    sub = img[y0:y1, x0:x1]
    ext = ((x0 - cx - .5) * px, (x1 - cx - .5) * px, (y1 - cy - .5) * px, (y0 - cy - .5) * px)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    R = np.hypot(yy - cy, xx - cx) * px
    return sub, ext, R


def norm(sub, R, cual):
    an = (R >= 7.5) & (R <= 11)
    if cual == "lr":
        return sub / np.median(sub[an])
    b = sub[an].mean()
    z = sub / b
    return np.abs(z) if cual == "amp" else np.angle(z)


def main():
    ids = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    F, _ = RP.cargar_solver("red", 3)
    J = json.load(open(os.path.join(P0, "particulas.json")))["particulas"]
    med = {r["id"]: r for r in json.load(open(os.path.join(P0, "medidas.json")))}
    if ids:
        J = [p for p in J if p["id"] in ids]
    lr, objs = {}, {}
    cols = ["LR BF crudo\n(√I, 1.29 µm/px)", "200 px\namplitud", "200 px\nfase (rad)", "20 px\namplitud", "20 px\nfase (rad)",
            "nulo DF 200 px\namplitud", "nulo DF 200 px\nfase", "nulo DF 20 px\namplitud"]
    fig, ax = plt.subplots(len(J), len(cols), figsize=(2.3 * len(cols), 2.35 * len(J)))
    for i, p in enumerate(J):
        reg = p["region"]
        if reg not in lr:
            lr[reg] = np.sqrt(np.clip(F.load_real(os.path.join(P0, "runs", f"ref_{reg}", "datos", "prep.npz"))["I"][RP.CENTRO_LED], 0, None))
            objs[("ref", reg)] = np.load(os.path.join(P0, "runs", f"ref_{reg}", "objeto_complejo.npy"))
            objs[("nulo", reg)] = np.load(os.path.join(P0, "runs", f"nulo_{reg}", "objeto_complejo.npy"))
        fr, cr = p["fila_rec"], p["col_rec"]
        c20 = np.load(os.path.join(P0, "runs", "chicos_20", f"{p['id']}.npz"))["obj"]
        n20 = np.load(os.path.join(P0, "runs", "chicos_20_nulo", f"{p['id']}.npz"))["obj"]
        paneles = [(lr[reg], fr, cr, 1.29, "lr"), (objs[("ref", reg)], 3 * fr, 3 * cr, .43, "amp"),
                   (objs[("ref", reg)], 3 * fr, 3 * cr, .43, "fase"), (c20, 30, 30, .43, "amp"), (c20, 30, 30, .43, "fase"),
                   (objs[("nulo", reg)], 3 * fr, 3 * cr, .43, "amp"), (objs[("nulo", reg)], 3 * fr, 3 * cr, .43, "fase"),
                   (n20, 30, 30, .43, "amp")]
        claves = ["LR", "ref200_amp", "ref200_fase", "c20_amp", "c20_fase", "nulo200_amp", "nulo200_fase", "c20_nulo_amp"]
        for j, ((img, cy, cx, px, cual), cl) in enumerate(zip(paneles, claves)):
            sub, ext, R = ventana(img, cy, cx, px)
            v = norm(sub, R, cual)
            a = ax[i, j]
            if cual == "fase":
                vm = max(float(np.percentile(np.abs(v), 99.5)), 0.05)
                a.imshow(v, cmap="RdBu_r", vmin=-vm, vmax=vm, extent=ext, interpolation="nearest")
            else:
                lo, hi = np.percentile(v, [1, 99])
                a.imshow(v, cmap="gray", vmin=lo, vmax=hi, extent=ext, interpolation="nearest")
            fw = med.get(p["id"], {}).get(f"{cl}_fwhm", np.nan)
            ok = med.get(p["id"], {}).get(f"{cl}_ok", True)
            a.text(0.03, 0.03, f"FWHM {fw:.1f} µm" + ("" if ok else " (×)"), transform=a.transAxes, color="yellow", fontsize=7,
                   bbox=dict(fc="black", alpha=.5, lw=0, pad=1))
            a.set_xticks([-10, 0, 10]); a.set_yticks([-10, 0, 10]); a.tick_params(labelsize=6)
            if i == 0:
                a.set_title(cols[j], fontsize=8)
            if j == 0:
                camb = med.get(p["id"], {}).get("c20_cambian", [])
                a.set_ylabel(p["id"] + ("\n20 px: LED " + ",".join(f"({k[0]},{k[1]})" for k in camb) + "\nDF→BF por redondeo" if camb
                                        else "\n20 px: sin LED\nque cambie BF/DF"), fontsize=7)
    plt.suptitle("2026-10-30-red-c: misma partícula en LR crudo, reconstrucción 200 px, recorte 20 px y nulos DF "
                 "(z 99.5 mm, NA 0.072, λ 0.617, 160 épocas; ejes en µm)", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(P0, "fig_recortes.png"), dpi=110)
    print("ok")


if __name__ == "__main__":
    main()

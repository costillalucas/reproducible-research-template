#!/usr/bin/env python3
"""figura.py -- fig_recortes_5um.png: por esfera (filas), la misma huella de 25.8 µm en LR BF, fase y amplitud de r400 / r200 /
b400 (r400 filtrado a la banda BF) / r20 / r20sc (sin LEDs que cambian BF/DF) / nulo 400 / nulo 20 (normalizadas por la media compleja del anillo 7.5-11 µm), y perfiles radiales de fase (plano del anillo
restado, como en medir.py)."""
import json, sys, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/codigo")
import medir as M
P0, B = M.P0, M.B
IDS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["S06", "S07", "S10", "S14"]
J = {p["id"]: p for p in json.load(open(P0 + "particulas.json"))["particulas"]}
o400 = np.load(B + "epocas_400b/snapshots/objeto_full_e160.npy"); o200 = np.load(B + "epocas_200/snapshots/objeto_full_e160.npy")
n400 = np.load(B + "red_nulo_df/objeto_complejo.npy")
_S = np.fft.fftshift(np.fft.fft2(o400)); _f = np.fft.fftshift(np.fft.fftfreq(_S.shape[0], d=0.43)); _FX, _FY = np.meshgrid(_f, _f)
b400 = np.fft.ifft2(np.fft.ifftshift(_S * (np.hypot(_FX, _FY) < 0.069 * 1.25 / 1.29 / 0.63)))   # = medir.py
cols = ["LR BF", "fase r400", "fase r200", "fase b400", "fase r20", "fase r20sc", "fase nulo400", "fase nulo20", "amp r400", "amp r20",
        "amp r20sc", "perfil fase"]
fig, ax = plt.subplots(len(IDS), len(cols), figsize=(2.3 * len(cols), 2.4 * len(IDS)))
ext = [-12.9, 12.9, 12.9, -12.9]
yy, xx = np.mgrid[:60, :60]
X, Y = (xx - 30) * 0.43, (yy - 30) * 0.43
R = np.hypot(X, Y); AN = (R >= 7.5) & (R <= 11)
for i, pid in enumerate(IDS):
    p = J[pid]; y, x = 3 * p["fila400"], 3 * p["col400"]
    d20 = np.load(P0 + f"runs/r20/{pid}.npz"); dn = np.load(P0 + f"runs/r20_nulo/{pid}.npz")
    dsc = np.load(P0 + f"runs/r20_sincambian/{pid}.npz")
    im = {"r400": o400[y - 30:y + 30, x - 30:x + 30], "r20": d20["obj"], "nulo400": n400[y - 30:y + 30, x - 30:x + 30],
          "nulo20": dn["obj"], "r20sc": dsc["obj"], "b400": b400[y - 30:y + 30, x - 30:x + 30]}
    if p["en_200"]:
        im["r200"] = o200[y - 330:y - 270, x - 330:x - 270]
    ax[i, 0].imshow(d20["lr_bf"], cmap="gray", extent=ext); ax[i, 0].set_ylabel(pid)
    for j, c in enumerate(cols[1:11], 1):
        tipo, nom = c.split()
        if nom not in im:
            ax[i, j].axis("off")
            ax[i, j].text(0.5, 0.5, "fuera del\nrecorte 200", ha="center", va="center", transform=ax[i, j].transAxes, fontsize=8)
            continue
        z = im[nom] / im[nom][AN].mean()
        if tipo == "fase":
            ax[i, j].imshow(np.angle(z), cmap="RdBu_r", vmin=-2.5, vmax=2.5, extent=ext)
        else:
            ax[i, j].imshow(np.abs(z), cmap="gray", vmin=0.3, vmax=1.7, extent=ext)
    for nom, col in (("r400", "k"), ("b400", "C1"), ("r20", "C3"), ("r20sc", "C4"), ("nulo400", "C0"), ("nulo20", "C2")):
        if nom not in im:
            continue
        z = im[nom] / im[nom][AN].mean(); ph = M.plano(np.angle(z), X, Y, AN)
        r = M.metricas(ph, 0.43, X, Y, R); Rc = np.hypot(X - r["cx"], Y - r["cy"])
        e = np.arange(0, 9, 0.43); k = np.digitize(Rc.ravel(), e) - 1; ok = (k >= 0) & (k < len(e) - 1)
        pr = np.bincount(k[ok], ph.ravel()[ok], len(e) - 1) / np.maximum(np.bincount(k[ok], None, len(e) - 1), 1)
        ax[i, 11].plot(e[:-1] + 0.215, pr, color=col, label=nom)
    ax[i, 11].axhline(0, color="0.8", lw=0.5); ax[i, 11].set_xlabel("r (µm)", fontsize=7); ax[i, 11].tick_params(labelsize=7)
for j, c in enumerate(cols):
    ax[0, j].set_title(c, fontsize=9)
ax[0, 11].legend(fontsize=6)
for a in ax[:, :11].ravel():
    a.set_xticks([]); a.set_yticks([])
fig.suptitle("Esferas 5 µm, captura 2026-11-03-red, geometría B (z 102, NA 0.0669, λ 0.63), 160 épocas; huella 25.8 µm; "
             "fase en [-2.5, 2.5] rad, amplitud en [0.3, 1.7]", fontsize=9)
plt.tight_layout(); plt.savefig(P0 + "fig_recortes_5um.png", dpi=110)

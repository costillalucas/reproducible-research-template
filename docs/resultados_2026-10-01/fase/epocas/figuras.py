import json, numpy as np
from skimage.restoration import unwrap_phase
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import cm, colors
import sys; sys.path.insert(0, "results/fase_2026-10-01/epocas")
OUT = "results/fase_2026-10-01/epocas/"
B = "results/iteraciones_2026-09-30/out/b_{}/real_A+init_z98.0_full/obj_e{:03d}.npy"
import os; COL = [c for c in ["red", "green", "blue"] if os.path.exists(OUT + f"fase_epocas_{c}.json")]; NOM = {"red": "Rojo", "green": "Verde", "blue": "Azul"}
R = {c: json.load(open(OUT + f"fase_epocas_{c}.json"))[c] for c in COL}
plt.rcParams.update({"font.size": 12})
norm = colors.LogNorm(1, 12); cmap = cm.viridis

def curvas(clave, ylab, fn):
    fig, ax = plt.subplots(1, len(COL), figsize=(5 * len(COL), 4.6), squeeze=False)
    ax = ax[0]
    for a, c in zip(ax, COL):
        r = R[c]; ep = np.array(r["ep"]); x = np.where(ep == 0, 0.5, ep)
        for i, p in enumerate(r["parts"]):
            y = [r["p"][str(e)][i][clave] for e in ep]
            a.plot(x, y, "-o", ms=3, color=cmap(norm(np.clip(p["d_um"], 1, 12))))
        a.set_xscale("log"); a.set_title(NOM[c]); a.set_xlabel("época (0 dibujada en 0.5)"); a.grid(alpha=.3)
        a.axvline(40, color="k", ls=":", lw=1)
    ax[0].set_ylabel(ylab)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap); cb = fig.colorbar(sm, ax=ax, pad=0.01)
    cb.set_label("diámetro equivalente (µm)")
    plt.savefig(OUT + fn, dpi=110, bbox_inches="tight"); plt.close(); print(OUT + fn)

curvas("peak", "fase pico (p95 − fondo local, rad)", "fig_a_fase_pico.png")
curvas("vol", "volumen de fase (Σφ·área, rad·µm²)", "fig_b_volumen_fase.png")

def quitar_fondo(p, frac=70):
    n = p.shape[0]; y, x = np.mgrid[0:n, 0:n] / n
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    d = np.abs(p - np.median(p)); m = d < np.percentile(d, frac)
    c, *_ = np.linalg.lstsq(A[m], p[m], rcond=None); q = p - A @ c
    return q - np.median(q)

EPS = [0, 5, 40, 400]; L_UM = 48.0
crops = {}
for c in COL:
    r = R[c]; px = r["px"]; p = max(r["parts"], key=lambda q: q["d_um"])
    L = int(L_UM / px); cy, cx = int(p["cy"]) - L // 2, int(p["cx"]) - L // 2
    cy = min(max(cy, 0), r["n"] - L); cx = min(max(cx, 0), r["n"] - L)
    crops[c] = [quitar_fondo(unwrap_phase(np.angle(np.load(B.format(c, e))[cy:cy + L, cx:cx + L]))) if e > 1
                else np.zeros((L, L)) for e in EPS]
vmax = max(np.percentile(crops[c][-1], 99.8) for c in COL); vmin = -0.5
fig, ax = plt.subplots(len(COL), 4, figsize=(13, 3.4 * len(COL)), squeeze=False)
for i, c in enumerate(COL):
    for j, e in enumerate(EPS):
        a = ax[i, j]; im = a.imshow(crops[c][j], cmap="magma", vmin=vmin, vmax=vmax, extent=[0, L_UM, L_UM, 0])
        a.set_xticks([]); a.set_yticks([])
        if i == 0: a.set_title(f"época {e}")
        if j == 0: a.set_ylabel(NOM[c], fontsize=14)
        a.plot([3, 13], [L_UM - 4, L_UM - 4], color="w", lw=4)
        a.text(8, L_UM - 6, "10 µm", color="w", ha="center", fontsize=11)
cb = fig.colorbar(im, ax=ax, pad=0.01, shrink=0.9, extend="both"); cb.set_label("fase desenrollada (rad)")
plt.savefig(OUT + "fig_c_tira_fase.png", dpi=100, bbox_inches="tight"); plt.close(); print(OUT + "fig_c_tira_fase.png", vmax)

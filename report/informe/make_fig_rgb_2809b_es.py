"""Figura de los tres colores, captura 28/09 (b), con rótulos en castellano, para la charla de 5 minutos.

Reproduce exactamente la figura de results/captura_2026-09-28b/comparar_colores.py (figs/tres_colores.png, copiada como
report/informe/img/fig_rgb_2809b.png): mismos datos, misma zona (píxeles 450-750 de la grilla del rojo, 128 µm), mismos
registros laterales (leídos de comparar_colores.json en vez de recalcularlos) y mismo estiramiento de grises (percentiles
1 y 99.5). Solo cambian los textos. No importa multiespectral.py (que reescribe sus salidas al importarse): repite aquí
sus dos funciones de carga (obj, to_grid).
Correr desde la raíz del repo: python3 report/informe/make_fig_rgb_2809b_es.py -> report/informe/img/fig_rgb_2809b_es.png
"""
import importlib.util
import json
import os
import sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

B = "results/captura_2026-09-28b"
OUT = "report/informe/img/fig_rgb_2809b_es.png"
CHARLA = "--charla" in sys.argv  # versión charla: sin la nota de pie y con barra de escala de 30 µm en los 6 paneles
if CHARLA:
    os.makedirs("report/presentacion_agentes/img_charla", exist_ok=True)
    OUT = "report/presentacion_agentes/img_charla/fig_rgb_2809b_es.png"
LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}
NOMBRE = {"red": "rojo", "green": "verde", "blue": "azul"}


def mod(c):
    s = importlib.util.spec_from_file_location("F_" + c, os.path.join(B, c, "fpm_red.py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def to_grid(o, n=1200):  # igual que multiespectral.to_grid
    H = o.shape[0]
    if H == n:
        return o
    S = np.fft.fftshift(np.fft.fft2(o)); a = (H - n) // 2
    return np.fft.ifft2(np.fft.ifftshift(S[a:a + n, a:a + n])) * (n / H) ** 2


cmp = json.load(open(os.path.join(B, "comparar_colores.json")))
raw = {c: mod(c).load_real()["I"][(18, 15)] for c in LAM}
A = {c: np.abs(to_grid(np.load(os.path.join(B, c, "out", "obj_real_A+init_z98.0_full.npy")).astype(complex))) for c in LAM}
reg = {c: (A[c] if c == "green" else np.roll(A[c], tuple(-np.array(cmp["reconstrucciones"][f"corrimiento_{c}_px_HR"])), (0, 1))) for c in LAM}
z = (slice(450, 750), slice(450, 750))
fig, ax = plt.subplots(2, 3, figsize=(13, 8.6))
for j, c in enumerate(LAM):
    s = cmp["crudas"].get(f"{c}_green", {"corrimiento_px_LR": [0, 0]})["corrimiento_px_LR"]
    im = np.kron(np.roll(raw[c], tuple(-np.array(s)), (0, 1)), np.ones((3, 3)))
    for i, (x, t) in enumerate([(im, "foto cruda (luz directa)"), (reg[c], "reconstrucción: amplitud")]):
        lo, hi = np.percentile(x[z], [1, 99.5]); ax[i, j].imshow(x[z], cmap="gray", vmin=lo, vmax=hi, extent=[0, 128, 128, 0]); ax[i, j].axis("off")
        ax[i, j].set_title(f"{NOMBRE[c]} ({int(round(LAM[c] * 1000))} nm): {t}", fontsize=14)
        if CHARLA:  # misma barra que make_fig_fase_2809b.py (misma zona de 128 µm, ejes ya en µm por extent)
            # color según el brillo bajo la barra (negra sobre fondo claro, blanca sobre oscuro) y borde del color opuesto
            from matplotlib import patheffects as pe
            cc, oc = ("k", "w") if np.clip((x[z][-50:, :110] - lo) / (hi - lo), 0, 1).mean() > 0.5 else ("w", "k")
            ax[i, j].plot([8, 38], [120, 120], color=cc, lw=5, solid_capstyle="butt", path_effects=[pe.withStroke(linewidth=7, foreground=oc)])
            ax[i, j].text(23, 113, "30 µm", color=cc, ha="center", fontsize=17, path_effects=[pe.withStroke(linewidth=2.5, foreground=oc)])
fig.suptitle("Porción de una muestra, con cada canal en su foco y la matriz de LEDs a ~98 mm", fontsize=16)
if not CHARLA:
    fig.text(0.5, 0.01, "Amplitud = raíz del brillo.", ha="center", fontsize=13, color="0.35")
plt.tight_layout(rect=(0, 0 if CHARLA else 0.03, 1, 0.95)); plt.savefig(OUT, dpi=90); plt.close()
print(OUT)

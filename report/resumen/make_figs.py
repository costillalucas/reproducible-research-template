"""Figuras propias del resumen (las demás se toman de report/informe/img/).
Correr desde la raíz del repo: python3 report/resumen/make_figs.py"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

OUT = "report/resumen/img"
os.makedirs(OUT, exist_ok=True)
INK, MUTED, ACC, ACC2 = "#14213D", "#6A7382", "#D9692B", "#2F6FB0"
plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})

# 1. esquema del montaje, con los valores del 25/09
fig, ax = plt.subplots(figsize=(6.4, 5.0))
ax.set_xlim(0, 10); ax.set_ylim(0.9, 10); ax.axis("off")
for i in range(9):
    x = 1.2 + i * 0.95  # 9 dibujados, 13 reales
    on = i == 6
    ax.add_patch(Circle((x, 9.0), 0.22, fc=ACC if on else "white", ec=ACC if on else MUTED, lw=1.5))
ax.text(5.0, 9.65, "matriz de LEDs (13 × 13, paso 6 mm)", va="center", ha="center", fontsize=10, color=INK)
ax.annotate("", xy=(5.0, 5.35), xytext=(1.2 + 6 * 0.95, 8.75), arrowprops=dict(arrowstyle="-|>", color=ACC, lw=2))
ax.text(7.2, 7.2, "luz inclinada\n(un LED por foto)", color=ACC, fontsize=10)
ax.add_patch(Rectangle((3.2, 5.0), 3.6, 0.35, fc="#F6D9C6", ec=MUTED))
ax.text(7.0, 5.17, "muestra", va="center", fontsize=10)
ax.annotate("", xy=(0.6, 5.2), xytext=(0.6, 9.0), arrowprops=dict(arrowstyle="<->", color=MUTED))
ax.text(0.75, 7.1, "z ≈ 74 mm", rotation=90, va="center", color=MUTED, fontsize=10)
ax.add_patch(Polygon([[4.1, 4.4], [5.9, 4.4], [5.5, 3.4], [4.5, 3.4]], closed=True, fc="white", ec=INK, lw=1.5))
ax.text(6.2, 3.9, "objetivo 2,5x, NA 0,07", va="center", fontsize=10)
ax.plot([5, 5], [3.4, 2.2], color=INK, lw=1.5)
ax.add_patch(FancyBboxPatch((4.2, 1.2), 1.6, 1.0, boxstyle="round,pad=0.05", fc="white", ec=INK, lw=1.5))
ax.text(6.2, 1.7, "cámara (píxel 3,2 µm,\n1,28 µm en la muestra)", va="center", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/fig_montaje.png", dpi=160); plt.close()

# 2. señal útil por LED en la captura del 24/09 (verde, 100 ms)
import sys
sys.path.insert(0, "scripts")
from resumen_numbers import leds_utiles_2409      # misma cuenta que el número del texto (fórmula de an.py)
_, _, snr = leds_utiles_2409()
M = np.full((13, 13), np.nan)
for (r, c), v in snr.items():
    M[r - 12, c - 9] = v
fig, ax = plt.subplots(figsize=(5.2, 4.4))
im = ax.imshow(np.clip(M, 0, 20), cmap="Blues", vmin=0, vmax=20, extent=[8.5, 21.5, 24.5, 11.5])
ax.contour(np.arange(9, 22), np.arange(12, 25), M, levels=[3], colors=ACC, linewidths=1.8)
ax.set_xlabel("columna del LED"); ax.set_ylabel("fila del LED")
cb = plt.colorbar(im, ax=ax, fraction=0.046); cb.set_label("señal / ruido (tope en 20)")
n3 = int(np.sum(M > 3))
ax.set_title(f"{n3} de {M.size} LEDs con señal/ruido > 3 (línea naranja)", fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/fig_senal.png", dpi=160); plt.close()
print("figuras en", OUT)

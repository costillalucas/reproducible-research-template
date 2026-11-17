"""Diagrama de descarte para el slide '66 hipótesis descartadas'. Salida: descartes.png (2400x1000 px)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from idioma import T, salida

BG, BOX, TXT, SEC, GRIS, AC = "#16202E", "#22303F", "#F3EFE6", "#B8C2CF", "#6B7280", "#E8925E"
DPI = 100
px = lambda p: p * 72 / DPI  # px reales -> puntos

fig = plt.figure(figsize=(24, 10), dpi=DPI, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 2400); ax.set_ylim(0, 1000); ax.axis("off")
plt.rcParams["font.family"] = "DejaVu Sans"


def caja(x0, y0, w, h, borde=None, lw=0):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=14",
                                fc=BOX, ec=borde or BOX, lw=px(lw), zorder=2))


def txt(x, y, s, size, color=TXT, bold=False, ha="left", va="center"):
    return ax.text(x, y, s, fontsize=px(size), color=color, ha=ha, va=va,
                   fontweight="bold" if bold else "normal", zorder=4)


# --- pregunta central ---
QX, QY, QW, QH = 40, 320, 580, 360
caja(QX, QY, QW, QH, borde=SEC, lw=2.5)
txt(QX + 34, 612, T("¿Por qué con datos reales", "Why is the model worse"), 34, bold=True)
txt(QX + 34, 560, T("el modelo predice peor?", "on real data?"), 34, bold=True)
ax.plot([QX + 34, QX + QW - 34], [505, 505], color=GRIS, lw=px(2), zorder=3)
txt(QX + 34, 448, T("residuo real ≈ 0,68", "real residual ≈ 0.68"), 32)
txt(QX + 34, 398, T("contra 0,15 en simulación", "versus 0.15 in simulation"), 30, color=SEC)

# --- ramas ---
descartadas = [
    (T("Ruido", "Noise"), T("4× exposición: el error baja 9 %; 2× (13/11): C1 igual", "4× exposure: error −9 %; 2× (13/11): C1 same")),
    (T("Pocas iteraciones", "Too few iterations"), T("20 → 400 épocas: C1 0,597 → 0,585", "20 → 400 epochs: C1 0.597 → 0.585")),
    (T("Posición de la matriz", "Array position"), T("rotación ±1°, inclinación 1–3°: invisibles", "rotation ±1°, tilt 1–3°: not visible")),
    (T("Aberraciones", "Aberrations"), T("recuperar la pupila (EPRY) no mejora", "recovering the pupil (EPRY) does not help")),
    (T("Magnificación", "Magnification"), T("micrómetro: 1,290 µm/px", "micrometer: 1.290 µm/px")),
    (T("Espesor de las esferas", "Sphere thickness"), T("simulación BPM: cambia 1–4 %", "BPM simulation: changes 1–4 %")),
]
BX, BW, H, GAP, TOP = 770, 900, 104, 16, 955
XBUS, YQ = 695, QY + QH / 2
r = fig.canvas.get_renderer()
inv = ax.transData.inverted()

ax.plot([QX + QW, XBUS], [YQ, YQ], color=GRIS, lw=px(4), zorder=1)
ycs = []
for i, (tit, ev) in enumerate(descartadas):
    y0 = TOP - i * (H + GAP) - H
    yc = y0 + H / 2; ycs.append(yc)
    ax.plot([XBUS, BX], [yc, yc], color=GRIS, lw=px(4), zorder=1)
    caja(BX, y0, BW, H)
    # cruz dibujada (dos líneas cruzadas)
    cx, s = BX + 58, 24
    ax.plot([cx - s, cx + s], [yc - s, yc + s], color=GRIS, lw=px(9), solid_capstyle="round", zorder=4)
    ax.plot([cx - s, cx + s], [yc + s, yc - s], color=GRIS, lw=px(9), solid_capstyle="round", zorder=4)
    t = txt(BX + 118, yc + 21, tit, 34, color=SEC, bold=True)
    bb = t.get_window_extent(r).transformed(inv)
    ax.plot([bb.x0 - 6, bb.x1 + 6], [yc + 19, yc + 19], color=GRIS, lw=px(2.5), zorder=5)  # tachado
    txt(BX + 118, yc - 25, ev, 27, color=SEC)

# rama viva
LH = 190
ly0 = TOP - 6 * (H + GAP) - LH
lyc = ly0 + LH / 2
ax.plot([XBUS, XBUS], [ycs[0], YQ], color=GRIS, lw=px(4), zorder=1, solid_capstyle="round")
ax.plot([XBUS, XBUS], [ycs[-1], YQ], color=GRIS, lw=px(4), zorder=1)
ax.plot([XBUS, XBUS, BX], [YQ, lyc, lyc], color=AC, lw=px(7), zorder=1.5, solid_joinstyle="round")
caja(BX, ly0, BW, LH, borde=AC, lw=5)
txt(BX + 40, lyc + 36, T("Error de modelo no geométrico", "Non-geometric model error"), 40, color=AC, bold=True)
txt(BX + 40, lyc - 36, T("luz parásita · brillo de cada LED · forma de la pupila", "stray light · brightness of each LED · pupil shape"), 27, color=TXT)
txt(BX + BW - 62, lyc + 2, "?", 120, color=AC, bold=True, ha="center")

# --- esquina: 66 ---
CX = 2040
txt(CX, 820, "66", 150, bold=True, ha="center")
txt(CX, 700, T("hipótesis puestas a prueba", "hypotheses tested"), 34, ha="center")
txt(CX, 640, T("+ 60 más, en el documento de recorrido", "+ 60 more, in the walkthrough document"), 26, color=SEC, ha="center")

fig.savefig(salida("descartes.png", os.path.dirname(os.path.abspath(__file__))), dpi=DPI, facecolor=BG)

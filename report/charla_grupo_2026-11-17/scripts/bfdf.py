"""Slide «bfdf»: qué LEDs dan campo claro y cuáles campo oscuro.

Izquierda: vista lateral (muestra arriba, matriz de LEDs abajo, escala vertical
comprimida) con el cono de aceptación del objetivo. Derecha: vista desde arriba
de los 5x5 LEDs centrales con el borde de la pupila proyectado sobre la matriz.

La geometría sale de los números (z, paso, NA); el layout está en píxeles de la
figura original (3328x1280), con el eje y hacia abajo.

Uso:  python bfdf.py                 (español, junto al script)
      FIG_LANG=en python bfdf.py     (inglés, ../figuras_en/)
      BFDF_OUT=ruta.png python bfdf.py   (salida a otra ruta, p. ej. para comparar)
"""
import os
import numpy as np
from idioma import EN, T, num, salida
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

# ---------- física ----------
Z = 102.0            # mm, distancia matriz-muestra
PASO = 6.0           # mm
NA = 0.067           # objetivo
R_BORDE = Z * np.tan(np.arcsin(NA))                  # mm: radio del cono sobre la matriz
na_ilum = lambda x, y=0.0: np.hypot(x, y) / np.sqrt(x * x + y * y + Z * Z)
claro = lambda x, y=0.0: np.hypot(x, y) < R_BORDE    # equivale a na_ilum < NA
NA_BF = na_ilum(PASO)                                # primer vecino sobre un eje
NA_DF = na_ilum(PASO, PASO)                          # primer vecino en diagonal
print(f"borde del cono: ±{R_BORDE:.3f} mm | NA_ilum eje {NA_BF:.4f} (BF: {claro(PASO)}) | "
      f"diagonal {NA_DF:.4f} (BF: {claro(PASO, PASO)})")
assert claro(PASO) and not claro(PASO, PASO) and not claro(2 * PASO)
assert num(R_BORDE, 1) == num(6.8, 1) and num(NA_BF, 3) == num(0.059, 3) and num(NA_DF, 3) == num(0.083, 3)

# ---------- estilo (colores de la figura original de esta slide) ----------
BG, T1, T2 = "#F7F6F2", "#14213D", "#4A5568"
AZ, NJ, NJC, PUNT = "#2F6FB0", "#B3541A", "#F6D9C6", "#9AA3B5"
DPI = 200
W, H = 3328, 1280
px = lambda p: p * 72.0 / DPI          # tamaño en px -> pt
plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans", "text.color": T1})

fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")


def led(x, y, lado, on):
    """Cuadrado de LED centrado en (x, y) px: azul lleno (campo claro) o hueco (campo oscuro)."""
    if on:
        ax.add_patch(Rectangle((x - lado / 2, y - lado / 2), lado, lado, fc=AZ, ec="none", zorder=5))
    else:
        b = 5.0                                                    # grosor del borde, hacia adentro
        ax.add_patch(Rectangle((x - lado / 2, y - lado / 2), lado, lado, fc=T2, ec="none", zorder=4))
        ax.add_patch(Rectangle((x - lado / 2 + b, y - lado / 2 + b), lado - 2 * b, lado - 2 * b, fc="white", ec="none", zorder=4.1))


# ================= vista lateral =================
X0, YM, YL = 1057.5, 150.0, 1058.5     # px: eje óptico, muestra, matriz
S1 = 119.0 / PASO                      # px por mm (horizontal)
X = lambda x_mm: X0 + x_mm * S1
N1 = 7                                 # LEDs a cada lado del central

ax.plot([102, 2014], [YM, YM], color=T1, lw=px(8), solid_capstyle="butt", zorder=6)
ax.text(126, 106, T("muestra", "sample"), fontsize=16, ha="left", va="baseline")

# cono de aceptación (NA del objetivo) proyectado sobre la matriz
ax.add_patch(Polygon([(X0, YM), (X(-R_BORDE), YL), (X(R_BORDE), YL)], closed=True, fc=NJC, ec=NJ, lw=px(5.6), joinstyle="miter", zorder=2))
# rayo al LED más alejado
ax.plot([X0, X(N1 * PASO)], [YM, YL], color=PUNT, lw=px(4), ls=(0, (1, 2.2)), zorder=3)

for k in range(-N1, N1 + 1):
    led(X(k * PASO), YL, 34, claro(k * PASO))

ax.annotate("", xy=(145.5, YL - 6), xytext=(145.5, YM + 6),
            arrowprops=dict(arrowstyle="<->", color=T2, lw=px(4), shrinkA=0, shrinkB=0, mutation_scale=px(50)))
ax.text(176, 616, f"z = {Z:.0f} mm", fontsize=16, color=T2, ha="left", va="baseline")

ax.text(X(-5 * PASO) + 1, 960, T("campo oscuro", "dark field"), fontsize=16, color=T2, weight="bold", ha="center", va="baseline")
ax.text(X(5 * PASO) + 1, 960, T("campo oscuro", "dark field"), fontsize=16, color=T2, weight="bold", ha="center", va="baseline")
ax.text(X0 + 1, 1173, T("campo claro", "bright field"), fontsize=16, color=AZ, weight="bold", ha="center", va="baseline")
ax.text(126, 1173, T("matriz de LEDs (paso 6 mm)", "LED array (6 mm pitch)"), fontsize=16, ha="left", va="baseline")
ax.text(1234, 779, T(f"cono NA = {num(NA)}", f"NA cone = {num(NA)},"), fontsize=16, color=NJ, ha="left", va="baseline")
ax.text(1234, 829, T(f"borde a ±{num(R_BORDE, 1)} mm", f"edge at ±{num(R_BORDE, 1)} mm"), fontsize=16, color=NJ, ha="left", va="baseline")
ax.text(2010, 1237, T("escala vertical comprimida", "vertical scale compressed"), fontsize=14, color=T2, ha="right", va="baseline")

# ================= vista desde arriba =================
CX, CY = 2692.0, 678.0                # px: LED central
S2 = 230.5 / PASO                      # px por mm
N2 = 2
ax.text(2174, 83, T("vista desde arriba", "top view"), fontsize=16, ha="left", va="baseline")
ax.add_patch(Circle((CX, CY), R_BORDE * S2, fc=NJC, ec=NJ, lw=px(7), zorder=2))
for i in range(-N2, N2 + 1):
    for j in range(-N2, N2 + 1):
        led(CX + i * PASO * S2, CY - j * PASO * S2, 42, claro(i * PASO, j * PASO))


def rotulo(i, j, xt, yt, valor, nombre, col, lw):
    """NA de iluminación del LED (i, j), con flecha desde el rótulo."""
    ax.annotate(rf"NA$_{{ilum}}$ {num(valor)}" + f"\n({nombre})", xy=(CX + i * PASO * S2, CY - j * PASO * S2), xytext=(xt, yt),
                fontsize=15, color=col, ha="center", va="center", linespacing=1.2, zorder=7,
                arrowprops=dict(arrowstyle="->", color=col, lw=px(lw), shrinkA=2.2, shrinkB=0))


rotulo(1, 1, 3019, 123, NA_DF, T("campo oscuro", "dark field"), T2, 3.0)
rotulo(1, 0, 2865, 1045, NA_BF, T("campo claro", "bright field"), AZ, 2.6)

out = os.environ.get("BFDF_OUT") or salida("bfdf.png", os.path.dirname(os.path.abspath(__file__)))
fig.savefig(out, dpi=DPI, facecolor=BG)
print(out)

"""Slide «na_cono»: qué es la apertura numérica (NA), en tres pasos que se revelan con clics.

  na_1.png  1 · qué es la NA: el cono de aceptación, NA = n sen θ; 2,5× (0,07) dentro de 10× (0,25)
  na_2.png  + 2 · los objetivos se rotulan por su NA: conos A ESCALA de 2,5×, 10×, 40× y 100× aceite
  na_3.png  + 3 · el precio de un cono grande: campo y profundidad de campo, 2,5× contra 10×

Las tres imágenes tienen el mismo tamaño (3200x1400) y son acumulativas. Todos los ángulos
están a escala. Sólo NA: nada de redes, órdenes de difracción, LEDs ni números de resolución
(eso viene después, en las slides m2, m0s, geom y bfdf).

Uso:  python3 na_cono.py               (español, junto al script)
      FIG_LANG=en python3 na_cono.py   (inglés, ../figuras_en/)
"""
import os
import numpy as np
from idioma import EN, T, num, salida
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle, Arc

AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- física
LAM = 0.63                    # µm
N_ACEITE = 1.515
# (aumento, NA, índice del medio entre muestra y lente)
OBJ = [("2.5×", 0.07, 1.0), ("10×", 0.25, 1.0), ("40×", 0.65, 1.0), ("100×", 1.25, N_ACEITE)]
TH = [np.degrees(np.arcsin(na / n)) for _, na, n in OBJ]
for (m, na, n), th in zip(OBJ, TH):
    print(f"{m:>5} NA {na:.2f} n {n:.3f}: sen θ = {na / n:.4f}  θ = {th:.2f}°")
assert np.allclose(TH, [4.01, 14.48, 40.54, 55.60], atol=0.02)
assert abs(1.25 / N_ACEITE - 0.825) < 0.001
# campo sobre nuestra cámara: 1,4 mm con 2,5× (slide de motivación), escala como 1/aumento
CAMPO25 = 1.4
CAMPO10 = CAMPO25 * 2.5 / 10
# profundidad de campo ≈ n λ / NA²
DOF25, DOF10 = LAM / 0.07 ** 2, LAM / 0.25 ** 2
print(f"campo: 2,5x {CAMPO25:.3f} mm | 10x {CAMPO10:.3f} mm")
print(f"profundidad de campo n*lam/NA^2: 2,5x {DOF25:.2f} um | 10x {DOF10:.2f} um")
assert abs(CAMPO10 - 0.35) < 1e-9 and 125 < DOF25 < 132 and 9.9 < DOF10 < 10.2

# ---------------------------------------------------------------- estilo (puente.py / montaje.py)
BG, T1, T2 = "#F6F4EE", "#1B2333", "#3E4756"
AZ, NJ, NJC = "#2F6690", "#A9471A", "#E8925E"
CONO = "#1F4E79"                   # bordes a rayas del cono (como en montaje)
G1, G2 = "#C9CCD1", "#8A909B"
ACEITE = "#E9C46A"
DPI = 100
W, H = 3200, 1400
FS, FST = 26, 31                   # pt a 100 dpi -> 36 px y 43 px
plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans", "text.color": T1})
SEN = T("sen", "sin")
c = lambda x, n=2: num(x, n)
mag = lambda m: m if EN else m.replace(".", ",")

fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
ax.set_aspect("equal")             # 1 px = 1 px: los ángulos quedan a escala


def titulo(x, n, fuerte, suave=""):
    ax.text(x, 1325, str(n), fontsize=FST, color="white", weight="bold", ha="center", va="center",
            bbox=dict(boxstyle="circle,pad=0.25", fc=NJ, ec="none"))
    t = ax.text(x + 50, 1325, fuerte, fontsize=FST, weight="bold", ha="left", va="center")
    if suave:
        fig.canvas.draw()
        x1 = ax.transData.inverted().transform(t.get_window_extent())[1, 0]
        ax.text(x1 + 14, 1325, suave, fontsize=FS - 2, color=T2, ha="left", va="center")


def cono(x0, y0, sen_t, h, alpha=0.15, lw=3.0, fc=T2):
    """Cono de semiángulo asin(sen_t) con vértice en (x0, y0) y altura h (px)."""
    a = h * np.tan(np.arcsin(sen_t))
    ax.add_patch(Polygon([(x0, y0), (x0 - a, y0 + h), (x0 + a, y0 + h)], fc=fc, alpha=alpha, ec="none", zorder=2))
    for s in (-1, 1):
        ax.plot([x0, x0 + s * a], [y0, y0 + h], color=CONO, lw=lw, ls=(0, (5, 3)), zorder=3)
    return a


def separador(x):
    ax.plot([x, x], [70, 1250], color=G1, lw=2, zorder=1)


def guardar(nombre):
    out = salida(nombre, AQUI)
    fig.savefig(out, dpi=DPI, facecolor=BG)
    print(out)


# ================================================================= 1 · qué es la NA
X1, YS, L = 330, 400.0, 750.0
titulo(40, 1, T("Qué es la NA", "What NA is"), T("(ángulos a escala)", "(angles to scale)"))
ax.plot([X1, X1], [280, YS + L + 110], color=G2, lw=1.5, ls=(0, (8, 4, 2, 4)), zorder=1)
for a_ in (-40, -28, -20, 20, 28, 40):               # luz que sale en todas direcciones
    r = np.radians(a_)
    ax.plot([X1, X1 + 430 * np.sin(r)], [YS, YS + 430 * np.cos(r)], color=G2, lw=2, alpha=0.7, zorder=1)
a10 = cono(X1, YS, 0.25, L, alpha=0.08, lw=2.6)
a25 = cono(X1, YS, 0.07, L, alpha=0.22, lw=3.0)
ax.add_patch(Rectangle((X1 - 290, YS - 9), 600, 18, fc="#DDE6EC", ec=T2, lw=1.5, zorder=4))
ax.add_patch(Circle((X1, YS), 9, fc=T2, ec="none", zorder=5))
ax.text(X1 - 290, YS - 50, T("muestra", "sample"), va="center", ha="left", fontsize=FS, color=T2)
for th, r in ((TH[0], 700), (TH[1], 480)):
    ax.add_patch(Arc((X1, YS), 2 * r, 2 * r, theta1=90 - th, theta2=90, color=CONO, lw=2.6, zorder=6))
ax.annotate(f"10×: NA {c(0.25)}\nθ ≈ {num(TH[1], 1)}°", (X1 + a10 * 0.9, YS + L * 0.9), (X1 + 240, 1120),
            ha="left", va="center", fontsize=FS - 2, color=CONO, linespacing=1.25,
            arrowprops=dict(arrowstyle="-", color=CONO, lw=1.8, shrinkA=6, shrinkB=2))
ax.annotate(T(f"nuestro {mag('2.5×')}:\nNA {c(0.07)}, θ ≈ {num(TH[0], 1)}°", f"our 2.5×:\nNA {c(0.07)}, θ ≈ {num(TH[0], 1)}°"),
            (X1 + a25 * 0.88, YS + L * 0.88), (X1 + 240, 930), ha="left", va="center", fontsize=FS - 2, color=CONO,
            weight="bold", linespacing=1.25, arrowprops=dict(arrowstyle="-", color=CONO, lw=1.8, shrinkA=6, shrinkB=2))
ax.text(X1 + 18, 1225, T("hacia el objetivo y la cámara", "to objective and camera"), ha="left", va="center",
        fontsize=FS - 4, color=T2)
ax.annotate("", (X1, 1255), (X1, 1180), arrowprops=dict(arrowstyle="-|>", color=T2, lw=2.5))
ax.text(X1 + 440, 690, r"$\mathrm{NA} = n\,\mathrm{" + SEN + r"}\,\theta$", fontsize=FS + 12, ha="center", va="center")
ax.text(X1 + 440, 610, T("(aire: n = 1)", "(air: n = 1)"), fontsize=FS - 2, color=T2, ha="center", va="center")
ax.text(X1 + 150, 190, T("sólo la luz dentro del cono\nllega a la cámara", "only light inside the cone\nreaches the camera"),
        fontsize=FS, ha="center", va="center", weight="bold", linespacing=1.25)
ax.text(X1 - 230, 960, T("luz que\nse pierde", "light that\nis lost"), fontsize=FS - 4, color=G2, ha="center",
        va="center", linespacing=1.2)

guardar("na_1.png")

# ================================================================= 2 · los objetivos se rotulan por su NA
separador(950)
titulo(990, 2, T("Los objetivos se rotulan por su NA", "Objectives are labelled by their NA"),
       T("(conos a escala)", "(cones to scale)"))
Y2, H2, HB = 740.0, 160.0, 150.0    # muestra, altura de los conos, alto del barril
xs = [1090, 1320, 1622, 2093]       # centros
ax.add_patch(Rectangle((990, Y2 - 8), 1400, 16, fc="#DDE6EC", ec=T2, lw=1.5, zorder=4))
for (m, na, n), th, x0 in zip(OBJ, TH, xs):
    if n > 1:                       # gota de aceite entre la muestra y la lente
        a = H2 * np.tan(np.radians(th))
        ax.add_patch(Polygon([(x0 - a - 70, Y2 + 8), (x0 + a + 70, Y2 + 8), (x0 + a + 20, Y2 + H2), (x0 - a - 20, Y2 + H2)],
                             fc=ACEITE, alpha=0.45, ec="none", zorder=1))
    a = cono(x0, Y2, na / n, H2, alpha=0.18)
    wb = max(a + 25, 90)
    ax.add_patch(Polygon([(x0 - a - 6, Y2 + H2), (x0 + a + 6, Y2 + H2), (x0 + wb, Y2 + H2 + 40), (x0 + wb, Y2 + H2 + HB),
                          (x0 - wb, Y2 + H2 + HB), (x0 - wb, Y2 + H2 + 40)], fc=G1, ec=T2, lw=2, zorder=6))
    rot = f"{mag(m)}{T(' aceite', ' oil') if n > 1 else ''}\n{c(na)}"
    ax.text(x0, Y2 + H2 + 40 + (HB - 40) / 2, rot, ha="center", va="center", fontsize=FS - 2, weight="bold",
            linespacing=1.2, zorder=7)
    extra = T(" en aceite\n(n = ", " in oil\n(n = ") + num(N_ACEITE, 3) + ")" if n > 1 else ""
    ax.text(x0, Y2 - 30, f"θ ≈ {num(th, 1)}°" + extra, ha="center", va="top", linespacing=1.2, fontsize=FS - 2, color=CONO)
ax.text(xs[0], Y2 + H2 + HB + 45, T("nuestro", "ours"), ha="center", va="center", fontsize=FS - 2, color=NJ, weight="bold")

# recta de NA: 0 -> 1,6, con el techo del aire en 1
NX0, NS, NY = 1030, 820.0, 400      # px de NA 0, px por unidad de NA, altura
nx = lambda v: NX0 + v * NS
ax.add_patch(Rectangle((nx(0.95), NY - 14), nx(N_ACEITE) - nx(0.95), 28, fc=ACEITE, alpha=0.55, ec="none", zorder=2))
ax.plot([nx(0), nx(1.6)], [NY, NY], color=T2, lw=3, zorder=3)
ax.plot([nx(1.0)] * 2, [NY - 40, NY + 95], color=NJ, lw=3, ls=(0, (4, 3)), zorder=3)
ax.text(nx(1.0) - 20, NY + 70, T("techo en aire: NA = 1  (θ → 90°)", "ceiling in air: NA = 1  (θ → 90°)"),
        ha="right", va="center", fontsize=FS - 4, color=NJ, weight="bold")
ax.text(nx(1.0) + 20, NY + 70, T("> 0,95: con aceite", "> 0.95: immersion oil"), ha="left", va="center",
        fontsize=FS - 4, color="#8A6A12", weight="bold")
for (m, na, n) in OBJ:
    ax.plot(nx(na), NY, marker="o", ms=13, color=CONO, zorder=4)
    ax.text(nx(na), NY - 45, c(na), ha="center", va="center", fontsize=FS - 4, color=CONO)
ax.text(nx(1.6) + 15, NY, "NA", ha="left", va="center", fontsize=FS - 4, color=T2, weight="bold")
ax.text(1680, 130, T("la NA viene grabada en cada objetivo: es el ángulo del cono",
                     "the NA is engraved on every objective: it is the cone angle"),
        ha="center", va="center", fontsize=FS - 2, weight="bold")

guardar("na_2.png")

# ================================================================= 3 · el precio de un cono grande
separador(2420)
titulo(2455, 3, T("El precio de un cono grande", "The price of a large cone"))
CX = [2640, 3010]                   # columnas 2,5× y 10×
COL = [AZ, NJ]
for x, (m, na, _), col in zip(CX, OBJ[:2], COL):
    ax.text(x, 1235, f"{mag(m)} / {c(na)}", ha="center", va="center", fontsize=FS, weight="bold", color=col)
# campo (a escala entre sí)
SC = 300 / CAMPO25                  # px por mm
ax.text(2825, 1175, T("campo visto (a escala)", "field of view (to scale)"), ha="center", va="center",
        fontsize=FS - 4, color=T2)
TOP = 1140
for x, f, col in zip(CX, (CAMPO25, CAMPO10), COL):
    s = f * SC
    ax.add_patch(Rectangle((x - s / 2, TOP - 300), s, s, fc=col, alpha=0.18, ec="none", zorder=3))
    ax.add_patch(Rectangle((x - s / 2, TOP - 300), s, s, fc="none", ec=col, lw=3, zorder=3))
    ax.text(x, TOP - 340, f"{num(f, 2 if f < 1 else 1)} mm", ha="center", va="center", fontsize=FS, weight="bold", color=col)
# profundidad de campo (a escala entre sí): franja de muestra que queda enfocada
SD = 260 / DOF25                    # px por µm
ax.text(2825, 715, T("profundidad de campo ≈ nλ/NA² (a escala)", "depth of field ≈ nλ/NA² (to scale)"), ha="center", va="center",
        fontsize=FS - 5, color=T2)
TOPD = 680
for x, d, col in zip(CX, (DOF25, DOF10), COL):
    h = d * SD
    yc = TOPD - 130
    ax.add_patch(Rectangle((x - 130, yc - h / 2), 260, h, fc=col, alpha=0.25, ec="none", zorder=3))
    ax.add_patch(Rectangle((x - 130, yc - h / 2), 260, h, fc="none", ec=col, lw=3, zorder=3))
    ax.plot([x - 150, x + 150], [yc, yc], color=T2, lw=1.5, ls=(0, (6, 4)), zorder=4)
    ax.text(x, TOPD - 300, f"≈ {d:.0f} µm" if d < 50 else f"≈ {round(d, -1):.0f} µm", ha="center", va="center",
            fontsize=FS, weight="bold", color=col)
ax.text(2810, 175, T("NA grande: detalle fino, pero\ncampo chico y foco angosto\nNA chica: campo amplio",
                     "large NA: fine detail, but\nsmall field and thin focus\nsmall NA: wide field"),
        ha="center", va="center", fontsize=FS - 2, weight="bold", linespacing=1.3)

guardar("na_3.png")

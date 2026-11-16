"""Figuras para la pregunta 3 (solapamiento / alejar la matriz). Charla FPM.
Genera sin_solap.png (1000x700) y alejar.png (1300x700) en la carpeta del script."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Arc, FancyArrowPatch

AQUI = os.path.dirname(os.path.abspath(__file__))
BG, TXT, SEC, AZ, AC = "#16202E", "#F3EFE6", "#B8C2CF", "#6FA8D6", "#E8925E"
DPI = 100
plt.rcParams["font.family"] = "DejaVu Sans"


def px(p):  # tamaño de fuente en px reales -> pt
    return p * 72.0 / DPI


def coma(x, n):
    return f"{x:.{n}f}".replace(".", ",")


# ---------- física ----------
NA, LAM, PASO, BORDE = 0.070, 0.63, 6.0, 60.0   # -, µm, mm, mm
R = NA / LAM                                    # radio de pupila, µm^-1


def geometria(z):
    d = PASO / np.hypot(PASO, z) / LAM          # separación de centros, µm^-1
    u = d / (2 * R)
    eta = (2 / np.pi) * (np.arccos(u) - u * np.sqrt(1 - u * u))
    na_ilum = BORDE / np.hypot(BORDE, z)
    return d, eta, na_ilum


def lienzo(w, h):
    fig = plt.figure(figsize=(w / DPI, h / DPI), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def disco(ax, x, y, r):
    ax.add_patch(Circle((x, y), r, fc=AZ, ec="none", alpha=0.16))
    ax.add_patch(Circle((x, y), r, fc="none", ec=AZ, lw=3.5))


# ---------- Imagen A ----------
def fig_a():
    fig, ax = lienzo(1000, 700)
    ax.text(500, 640, "Sin solapamiento", color=TXT, fontsize=px(46),
            fontweight="bold", ha="center", va="center")
    r, cy = 150, 400
    for cx, a0 in ((320, 60), (680, 200)):
        disco(ax, cx, cy, r)
        ax.text(cx, cy - 4, "?", color=TXT, fontsize=px(110), fontweight="bold",
                ha="center", va="center")
        # flecha circular: fase libre
        rr = 105
        ax.add_patch(Arc((cx, cy), 2 * rr, 2 * rr, theta1=a0, theta2=a0 + 285,
                         ec=AC, lw=4))
        t = np.deg2rad(a0 + 285)
        p0 = (cx + rr * np.cos(t), cy + rr * np.sin(t))
        p1 = (p0[0] - 6 * np.sin(t), p0[1] + 6 * np.cos(t))
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=34,
                                     color=AC, lw=0, shrinkA=0, shrinkB=0))
    ax.text(500, 178, "cada ventana tiene su fase libre:", color=TXT,
            fontsize=px(34), ha="center", va="center")
    ax.text(500, 128, "nada las ata → la solución no es única", color=AC,
            fontsize=px(34), fontweight="bold", ha="center", va="center")
    ax.text(500, 50, "regla práctica: solapamiento ≥ 40–60 %", color=SEC,
            fontsize=px(30), ha="center", va="center")
    fig.savefig(os.path.join(AQUI, "sin_solap.png"), dpi=DPI, facecolor=BG)
    plt.close(fig)


# ---------- Imagen B ----------
def fig_b():
    W, H = 1300, 700
    S = 1100.0                                   # px por µm^-1 (MISMA en ambos paneles)
    fig, ax = lienzo(W, H)
    ax.text(W / 2, 645, "Alejar la matriz de LEDs", color=TXT, fontsize=px(46),
            fontweight="bold", ha="center", va="center")
    cy = 322
    for cx, z in ((335, 99.5), (965, 143.0)):
        d, eta, na_il = geometria(z)
        r, h = R * S, d * S / 2
        phi = np.arccos((d / 2) / R)
        t = np.linspace(-phi, phi, 200)
        izq = np.c_[cx - h + r * np.cos(t), cy + r * np.sin(t)]          # arco del disco izq.
        der = np.c_[cx + h - r * np.cos(t[::-1]), cy + r * np.sin(t[::-1])]
        disco(ax, cx - h, cy, r); disco(ax, cx + h, cy, r)
        ax.add_patch(Polygon(np.r_[izq, der], closed=True, fc=AC, ec="none", alpha=0.55))
        ax.plot([cx - h, cx + h], [cy, cy], "o", color=AZ, ms=7)
        ax.text(cx, 572, f"z = {coma(z, 1) if z % 1 else int(z)} mm", color=TXT,
                fontsize=px(36), fontweight="bold", ha="center", va="center")
        ax.text(cx, 497, f"≈ {eta * 100:.0f} %", color=AC, fontsize=px(58),
                fontweight="bold", ha="center", va="center")
        ax.text(cx, 158, f"NA de iluminación máx. {coma(na_il, 2)}", color=SEC,
                fontsize=px(31), ha="center", va="center")
    # barra de escala común
    L = 0.1 * S
    ax.plot([W / 2 - L / 2, W / 2 + L / 2], [250, 250], color=SEC, lw=3, solid_capstyle="butt")
    for xx in (W / 2 - L / 2, W / 2 + L / 2):
        ax.plot([xx, xx], [241, 259], color=SEC, lw=3)
    ax.text(W / 2, 285, "0,1 µm⁻¹", color=SEC, fontsize=px(30), ha="center", va="center")
    # línea final
    ax.plot([120, W - 120], [108, 108], color=SEC, lw=1, alpha=0.4)
    kw = dict(fontsize=px(38), fontweight="bold", va="center")
    ax.text(W / 2 - 22, 55, "ganamos solapamiento", color=AC, ha="right", **kw)
    ax.text(W / 2, 55, "·", color=SEC, ha="center", **kw)
    ax.text(W / 2 + 22, 55, "perdemos NA sintética", color=AZ, ha="left", **kw)
    fig.savefig(os.path.join(AQUI, "alejar.png"), dpi=DPI, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    print(f"R = NA/lambda = {R:.4f} um^-1")
    for z in (99.5, 143.0):
        d, eta, na_il = geometria(z)
        print(f"z = {z} mm: d = {d:.4f} um^-1, u = {d/(2*R):.4f}, eta = {eta*100:.1f} %, "
              f"NA_ilum_max = {na_il:.3f}, NA_sint = {NA + na_il:.3f}")
    fig_a(); fig_b()

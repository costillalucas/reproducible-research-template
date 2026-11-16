"""Figuras a escala para las respuestas q1 y q2 (charla FPM). Genera q1.png y q2.png."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Arc, Rectangle, Ellipse
from matplotlib.ticker import FuncFormatter, MultipleLocator

AQUI = os.path.dirname(os.path.abspath(__file__))
BG, TXT, SEC, ACC = "#16202E", "#F3EFE6", "#B8C2CF", "#E8925E"
AZUL, AZUL_CLARO, NARANJA, GRIS = "#2F6690", "#6FA8D6", "#A9471A", "#9AA5B1"
DPI = 100
FS, FT = 24, 29          # pt -> 33 px y 40 px a 100 dpi
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": FS, "text.color": TXT,
                     "axes.edgecolor": SEC, "axes.labelcolor": TXT, "xtick.color": SEC,
                     "ytick.color": SEC, "figure.facecolor": BG, "axes.facecolor": BG,
                     "savefig.facecolor": BG})

def coma(x, nd=3):
    return f"{x:.{nd}f}".replace(".", ",")
def fmt(nd):
    return FuncFormatter(lambda v, _: coma(v, nd).replace("-", "\u2212"))

# ---------------- numeros ----------------
LAM, NA, NA_S = 0.63, 0.07, 0.45
P1, P2 = 9.0, 1.4
R_PUP, R_SIN = NA / LAM, NA_S / LAM
F1, F2 = 1 / P1, 1 / P2
Z, D = 100.0, 6.0
SIN6 = D / np.hypot(D, Z); K6 = SIN6 / LAM
DD = np.hypot(D, D); SIND = DD / np.hypot(DD, Z); KD = SIND / LAM
KDx = (D / np.sqrt(2 * D**2 + Z**2)) / LAM
NUM = dict(R_PUP=R_PUP, R_SIN=R_SIN, F1=F1, F2=F2, SIN6=SIN6, K6=K6, DD=DD, SIND=SIND, KD=KD, KDx=KDx,
           NA_para_1_4=LAM / P2, p_min=LAM / NA)

def box(c=BG):
    return dict(boxstyle="round,pad=0.15", fc=c, ec="none", alpha=0.85)

# ---------------- q1 ----------------
def q1(etapa="b"):
    B = etapa == "b"
    fig = plt.figure(figsize=(20, 11), dpi=DPI)
    fig.text(0.5, 0.945, "¿Qué períodos pasan por la pupila? (iluminación coherente, λ = 0,63 µm)",
             ha="center", va="center", fontsize=FT, fontweight="bold")
    ax = fig.add_axes([0.075, 0.115, 0.60, 0.60 * 2000 / 1100 * (1.64 / 2.4)])
    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.82, 0.82); ax.set_aspect("equal")
    ax.axhline(0, color=SEC, lw=1, alpha=0.35); ax.axvline(0, color=SEC, lw=1, alpha=0.35)
    if B: ax.add_patch(Circle((0, 0), R_SIN, fill=False, ec=ACC, lw=3.5, ls=(0, (2, 2.5))))
    ax.add_patch(Circle((0, 0), R_PUP, fc=AZUL_CLARO, ec=AZUL_CLARO, alpha=0.45, lw=0))
    ax.add_patch(Circle((0, 0), R_PUP, fill=False, ec=AZUL_CLARO, lw=3))
    ax.plot([0], [0], "o", ms=11, color=TXT, zorder=5)
    ax.plot([-F1, F1], [0, 0], "o", ms=17, mfc=TXT, mec=BG, mew=2, zorder=6)
    if B: ax.plot([-F2, F2], [0, 0], "D", ms=18, mfc=ACC, mec=BG, mew=2, zorder=6)
    ax.annotate("pupila NA 0,07", xy=(0.06, 0.095), xytext=(0, 0.27), ha="center", color=AZUL_CLARO,
                fontweight="bold", arrowprops=dict(arrowstyle="-", color=AZUL_CLARO, lw=2))
    if B: ax.text(0, 0.50, "NA sintética 0,45\n(meta FPM)", ha="center", va="center", color=ACC,
            fontweight="bold", linespacing=1.15)
    ax.annotate("p = 9 µm: en el borde", xy=(F1, -0.015), xytext=(0, -0.22), ha="center", va="center",
                arrowprops=dict(arrowstyle="-", color=TXT, lw=2, shrinkB=8))
    ax.annotate("", xy=(-F1, -0.015), xytext=(-0.05, -0.19), arrowprops=dict(arrowstyle="-", color=TXT, lw=2, shrinkB=8))
    if B: ax.text(0, -0.50, "p = 1,4 µm:\nnecesita NA 0,45", ha="center", va="center", color=ACC, fontweight="bold",
            linespacing=1.15)
    for s in ((-1, 1) if B else ()):
        ax.annotate("", xy=(s * F2, -0.02), xytext=(s * 0.31, -0.46),
                    arrowprops=dict(arrowstyle="-", color=ACC, lw=2, shrinkB=10))
    if B: ax.text(F2 + 0.05, 0.09, f"1/1,4 =\n{coma(F2)} µm⁻¹", ha="left", va="center", color=SEC, linespacing=1.15)
    ax.xaxis.set_major_locator(MultipleLocator(0.5)); ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.xaxis.set_major_formatter(fmt(1)); ax.yaxis.set_major_formatter(fmt(1))
    ax.set_xlabel("fx (µm⁻¹)"); ax.set_ylabel("fy (µm⁻¹)")
    ax.tick_params(length=8, width=1.5)
    # panel derecho: redes en espacio real, misma escala
    W, H = 27.0, 15.0
    x = np.linspace(0, W, 1600)
    wax = 0.215; hax = wax * 2000 / 1100 * H / W
    for (p, y0, col) in ((P1, 0.50, TXT), (P2, 0.135, ACC))[: 2 if B else 1]:
        a = fig.add_axes([0.745, y0, wax, hax])
        img = np.tile(0.5 + 0.5 * np.cos(2 * np.pi * x / p), (10, 1))
        a.imshow(img, extent=[0, W, 0, H], cmap="gray", vmin=-0.15, vmax=1.05, aspect="equal",
                 interpolation="bilinear")
        a.set_xticks([]); a.set_yticks([])
        for sp in a.spines.values(): sp.set_color(col); sp.set_linewidth(3)
        a.set_title(f"red de período p = {coma(p, 0) if p == 9 else coma(p, 1)} µm", color=col,
                    fontsize=FS, pad=12, fontweight="bold")
    fig.text(0.745 + wax / 2, 0.865, "espacio real (misma escala)", ha="center", color=SEC, fontsize=FS)
    # barra de escala 9 um
    b = fig.add_axes([0.745, 0.045, wax, 0.06]); b.set_xlim(0, W); b.set_ylim(0, 1); b.axis("off")
    b.plot([0, 9], [0.75, 0.75], color=TXT, lw=5, solid_capstyle="butt")
    b.text(10, 0.75, "9 µm", va="center", ha="left")
    fig.savefig(os.path.join(AQUI, f"q1{etapa}.png"), dpi=DPI)
    plt.close(fig)

# ---------------- q2 ----------------
def q2():
    fig = plt.figure(figsize=(20, 11), dpi=DPI)
    fig.text(0.5, 0.945, "La pupila no se mueve ni cambia de tamaño; el LED corre el espectro",
             ha="center", va="center", fontsize=FT, fontweight="bold")
    # esquema lateral
    s = fig.add_axes([0.015, 0.10, 0.30, 0.76]); s.set_xlim(-3.3, 3.3); s.set_ylim(-1.7, 7.5); s.axis("off")
    s.plot([0, 0], [-0.3, 7.0], color=SEC, lw=1.5, ls="--")
    s.add_patch(Rectangle((-2.7, -0.28), 5.4, 0.2, fc="#33465C", ec=SEC, lw=1.5))
    for xl in (-2, -1, 0, 1, 2):
        s.plot([xl], [0], "o", ms=20, mfc=(NARANJA if xl == 1 else "#4A5D73"), mec=(ACC if xl == 1 else SEC), mew=2)
    s.plot([1, 0], [0.12, 5], color=ACC, lw=4)
    s.plot([-1.6, 1.6], [5, 5], color=TXT, lw=6, solid_capstyle="round")
    s.text(-1.7, 5.0, "muestra", ha="right", va="center")
    s.add_patch(Ellipse((0, 6.3), 2.2, 0.55, fc=AZUL, ec=AZUL_CLARO, lw=2))
    s.text(1.25, 6.3, "objetivo", ha="left", va="center", color=AZUL_CLARO)
    s.add_patch(Arc((0, 5), 4.6, 4.6, theta1=-90, theta2=np.degrees(np.arctan2(-4.88, 1)), color=TXT, lw=2.5))
    s.text(0.24, 2.25, "θ", ha="center", va="center", fontsize=FS + 4)
    s.annotate("", xy=(0, -0.75), xytext=(1, -0.75), arrowprops=dict(arrowstyle="<->", color=ACC, lw=2.5))
    s.text(0.5, -1.2, "6 mm", ha="center", va="center", color=ACC)
    s.annotate("", xy=(-2.9, 0), xytext=(-2.9, 5), arrowprops=dict(arrowstyle="<->", color=SEC, lw=2.5))
    s.text(-2.75, 2.5, "100 mm", ha="left", va="center", color=SEC)
    s.text(0, -0.02 + 0, "", ha="center")
    s.text(-2.6, -0.75, "matriz LED", ha="left", va="center", color=SEC)
    s.text(0, 7.2, "esquema lateral (no a escala)", ha="center", va="center", color=SEC)
    # plano de Fourier a escala
    xl, yl = (-0.14, 0.30), (-0.17, 0.17)
    w = 0.56
    ax = fig.add_axes([0.40, 0.115, w, w * 2000 / 1100 * (yl[1] - yl[0]) / (xl[1] - xl[0])])
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal")
    ax.axhline(0, color=SEC, lw=1, alpha=0.35); ax.axvline(0, color=SEC, lw=1, alpha=0.35)
    ax.add_patch(Circle((0, 0), R_PUP, fc=AZUL_CLARO, alpha=0.40, lw=0))
    ax.add_patch(Circle((0, 0), R_PUP, fill=False, ec=AZUL_CLARO, lw=3.5))
    ax.plot([0], [0], "+", ms=18, mew=2.5, color=TXT)
    ax.annotate("", xy=(KDx, KDx), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=GRIS, lw=3.5,
                mutation_scale=30, shrinkA=0, shrinkB=12))
    ax.annotate("", xy=(K6, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=ACC, lw=4.5,
                mutation_scale=32, shrinkA=0, shrinkB=12))
    ax.plot([KDx], [KDx], "*", ms=38, mfc=GRIS, mec=BG, mew=1.5, zorder=6)
    ax.plot([K6], [0], "*", ms=42, mfc=NARANJA, mec=ACC, mew=2.5, zorder=7)
    ax.text(K6 / 2 - 0.004, -0.012, f"{coma(K6)} µm⁻¹", ha="center", va="top", color=ACC, fontweight="bold")
    ax.text(0.128, -0.012, f"LED a 6 mm\nsin θ = {coma(SIN6, 4)}\nk = {coma(K6, 4)} µm⁻¹\n"
            "dentro → campo claro", ha="left", va="center", color=ACC, linespacing=1.2, fontweight="bold")
    ax.text(0.118, 0.118, f"LED diagonal ({coma(DD, 2)} mm)\nsin θ = {coma(SIND, 4)}\nk = {coma(KD)} µm⁻¹\n"
            "fuera → campo oscuro", ha="left", va="center", color=GRIS, linespacing=1.2, fontweight="bold")
    ax.text(0, -0.142, f"pupila NA 0,07\nradio NA/λ = {coma(R_PUP)} µm⁻¹", ha="center", va="center", linespacing=1.15,
            color=AZUL_CLARO, fontweight="bold")
    ax.text(-0.132, 0.152, "★ = orden cero (DC) de la muestra", ha="left", va="center", color=SEC)
    ax.xaxis.set_major_locator(MultipleLocator(0.1)); ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.xaxis.set_major_formatter(fmt(1)); ax.yaxis.set_major_formatter(fmt(1))
    ax.set_xlabel("fx (µm⁻¹)"); ax.set_ylabel("fy (µm⁻¹)")
    ax.tick_params(length=8, width=1.5)
    fig.savefig(os.path.join(AQUI, "q2.png"), dpi=DPI)
    plt.close(fig)

if __name__ == "__main__":
    for k, v in NUM.items():
        print(f"{k:12s} {v:.6f}")
    q1("a"); q1("b"); q2()

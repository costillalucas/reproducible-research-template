"""Slide puente: de la matriz de LEDs al espacio de Fourier, en tres pasos."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc, FancyArrowPatch, Polygon

BG, T1, T2 = "#F6F4EE", "#1B2333", "#3E4756"
AZ, NJ, NJC = "#2F6690", "#A9471A", "#E8925E"
DPI = 100
px = lambda p: p * 72.0 / DPI          # tamaño en px -> pt
plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
                     "text.color": T1, "axes.edgecolor": T2})
com = lambda x, n=3: f"{x:.{n}f}".replace(".", ",")

# ---------- números del ejemplo resuelto ----------
r_mm, z_mm, lam, NA = 12.0, 100.0, 0.63, 0.07
sen = r_mm / np.hypot(r_mm, z_mm)
k = sen / lam
kp = NA / lam
print(f"sen theta = {sen:.5f}  k = {k:.5f} um^-1  NA/lambda = {kp:.5f} um^-1  DF: {sen > NA}")
assert com(sen) == "0,119" and com(k) == "0,189" and com(kp) == "0,111"
assert com(0.119 / 0.63) == "0,189"     # la cuenta con valores redondeados da lo mismo

# ---------- simulación de las mini-fotos ----------
def foto(sen_led, N=512, dx=0.4, seed=3):
    """Imagen coherente de discos de fase/absorción débil con iluminación inclinada."""
    rng = np.random.default_rng(seed)
    x = (np.arange(N) - N / 2) * dx
    X, Y = np.meshgrid(x, x)
    fase, absn = np.zeros((N, N)), np.zeros((N, N))
    centros = []
    while len(centros) < 7:
        c = rng.uniform(-70, 70, 2); R = rng.uniform(14, 24)
        if all(np.hypot(*(c - c2)) > R + R2 + 8 for c2, R2 in centros):
            centros.append((c, R))
    for c, R in centros:
        m = np.hypot(X - c[0], Y - c[1]) < R
        fase[m], absn[m] = 0.6, 0.10
    obj = (1 - absn) * np.exp(1j * fase)
    f = np.fft.fftfreq(N, dx)
    df = f[1] - f[0]
    k0 = np.round(sen_led / lam / df) * df            # sobre la grilla de la FFT
    FX, FY = np.meshgrid(f, f)
    pupila = np.hypot(FX, FY) <= NA / lam
    campo = np.fft.ifft2(np.fft.fft2(obj * np.exp(2j * np.pi * k0 * X)) * pupila)
    return np.abs(campo) ** 2

I_bf = foto(0.03)      # sen θ < NA
I_df = foto(sen)       # el ejemplo: sen θ > NA
print(f"BF: fondo {np.median(I_bf):.3f}  |  DF: fondo {np.median(I_df):.2e}, max {I_df.max():.3f}")

# ---------- figura ----------
fig = plt.figure(figsize=(24, 10.5), dpi=DPI, facecolor=BG)

def titulo(x, n, txt):
    fig.text(x, 0.925, str(n), fontsize=px(36), color="white", weight="bold", ha="center", va="center",
             bbox=dict(boxstyle="circle,pad=0.25", fc=NJ, ec="none"))
    fig.text(x + 0.021, 0.925, txt, fontsize=px(36), weight="bold", ha="left", va="center")

titulo(0.019, 1, "Geometría: el ángulo del LED")
titulo(0.328, 2, "Fourier: cuánto se corre")
titulo(0.617, 3, "Regla: ¿entra el orden cero?")

for x0 in (0.283, 0.578):
    fig.add_artist(FancyArrowPatch((x0, 0.52), (x0 + 0.03, 0.52), transform=fig.transFigure,
                                   arrowstyle="simple,head_width=34,head_length=30,tail_width=13", fc=NJC, ec="none"))

# ---- panel 1: esquema lateral ----
a1 = fig.add_axes([0.01, 0.40, 0.265, 0.46]); a1.set_facecolor(BG)
a1.set_xlim(-1.25, 1.75); a1.set_ylim(-0.42, 2.02); a1.set_aspect("equal"); a1.axis("off")
R_, Z_ = 1.0, 1.55
a1.add_patch(Rectangle((-1.1, -0.13), 2.55, 0.10, fc="#D9D5C9", ec=T2, lw=1.5))
for xl in np.arange(-1.0, 1.41, 0.25):
    on = abs(xl - R_) < 1e-6
    a1.add_patch(Rectangle((xl - 0.055, -0.03), 0.11, 0.07, fc=NJ if on else "#9AA0A8", ec="none", zorder=4))
a1.plot([0, 0], [-0.03, 1.95], ls=(0, (6, 5)), color=T2, lw=2)
a1.add_patch(Polygon([[0, 0.04], [R_, 0.04], [0, Z_]], closed=True, fc=NJC, alpha=0.22, ec="none"))
a1.plot([0, R_], [0.04, 0.04], color=T1, lw=3); a1.plot([0, 0], [0.04, Z_], color=T1, lw=3)
a1.plot([0, 0.09, 0.09], [0.13, 0.13, 0.04], color=T1, lw=2)
a1.annotate("", xy=(0, Z_), xytext=(R_, 0.05), arrowprops=dict(arrowstyle="-|>,head_width=0.5,head_length=1.0", color=NJ, lw=4))
a1.add_patch(Rectangle((-0.62, Z_), 1.24, 0.07, fc=AZ, ec="none"))
ang = np.degrees(np.arctan2(R_, Z_ - 0.04))
a1.add_patch(Arc((0, Z_), 1.0, 1.0, theta1=270, theta2=270 + ang, color=T1, lw=2.5))
a1.text(0.14, Z_ - 0.72, r"$\theta$", fontsize=px(40), ha="center", va="center")
a1.text(0.72, Z_ + 0.10, "muestra", fontsize=px(31), color=AZ, ha="left", va="bottom")
a1.text(-1.15, -0.22, "matriz de LEDs", fontsize=px(31), color=T2, ha="left", va="top")
a1.text(R_ / 2, 0.10, r"$r$", fontsize=px(40), ha="center", va="bottom")
a1.text(-0.10, Z_ / 2, r"$z$", fontsize=px(40), ha="right", va="center")
a1.text(R_ + 0.10, 0.16, "LED", fontsize=px(31), color=NJ, weight="bold", ha="left", va="bottom")
a1.text(0.62, 0.95, "rayo", fontsize=px(31), color=NJ, ha="left", va="center")
a1.text(1.72, -0.22, "(no a escala)", fontsize=px(30), color=T2, style="italic", ha="right", va="top")

fig.text(0.142, 0.295, r"$\mathrm{sen}\,\theta=\frac{r}{\sqrt{r^{2}+z^{2}}}$", fontsize=px(58), ha="center", va="center")
fig.text(0.142, 0.185, "Ejemplo:  r = 12 mm,  z = 100 mm", fontsize=px(30), color=T2, ha="center", va="center")
fig.text(0.142, 0.118, r"$\mathrm{sen}\,\theta=\frac{12}{\sqrt{144+10000}}\approx$" + com(sen), fontsize=px(40), ha="center", va="center")

# ---- panel 2a: por qué k = sen θ / λ (onda inclinada sobre la muestra) ----
WM, HM = 710, 230                                   # px reales del mini-dibujo (1 unidad = 1 px)
am_ = fig.add_axes([715 / 2400, 1 - 342 / 1050, WM / 2400, HM / 1050]); am_.set_facecolor(BG)
am_.set_xlim(0, WM); am_.set_ylim(0, HM); am_.set_aspect("equal"); am_.axis("off")
TH = np.radians(35.0)                               # ángulo exagerado: esquema
sT, cT = np.sin(TH), np.cos(TH)
ys, per, Lf = 150.0, 125.0, 165.0                   # altura de la muestra, período sobre la muestra, largo de frente
lam_px = per * sT                                   # separación entre frentes (perpendicular) = período · sen θ
xm = 160.0 + per * np.arange(4)                     # donde cada frente toca la muestra
for x0 in xm:                                       # frentes: forman θ con la muestra
    am_.plot([x0, x0 - Lf * cT], [ys, ys - Lf * sT], color=NJC, lw=5, solid_capstyle="round", zorder=2)
am_.plot([8, WM - 8], [ys, ys], color=AZ, lw=6, solid_capstyle="butt", zorder=3)
am_.plot(xm, [ys] * 4, "o", ms=13, color=NJ, mec=BG, mew=1.5, zorder=5)
dim = dict(arrowstyle="<|-|>,head_width=0.3,head_length=0.6", color=T1, lw=2.2, shrinkA=0, shrinkB=0)
# cota λ, perpendicular a los frentes
s0 = 50.0
P = np.array([xm[0] - s0 * cT, ys - s0 * sT]); Q = P + lam_px * np.array([sT, -cT])
assert s0 + per * cT < Lf                            # el pie de la cota cae sobre el frente dibujado
am_.annotate("", xy=Q, xytext=P, arrowprops=dim, zorder=6)
mid = (P + Q) / 2 - 27 * np.array([cT, sT])
am_.text(mid[0], mid[1], r"$\lambda$", fontsize=px(36), ha="center", va="center")
# cota λ / sen θ, sobre la muestra
for x0 in xm[1:3]:
    am_.plot([x0, x0], [ys + 8, ys + 34], color=T1, lw=1.8)
am_.annotate("", xy=(xm[2], ys + 24), xytext=(xm[1], ys + 24), arrowprops=dim, zorder=6)
am_.text((xm[1] + xm[2]) / 2, ys + 54, r"$\lambda\,/\,\mathrm{sen}\,\theta$", fontsize=px(34), ha="center", va="center")
# ángulo θ entre frente y muestra
am_.add_patch(Arc((xm[0], ys), 190, 190, theta1=180, theta2=215, color=T1, lw=2.2, zorder=4))
am_.text(xm[0] - 122 * np.cos(TH / 2), ys - 122 * np.sin(TH / 2), r"$\theta$", fontsize=px(34), ha="center", va="center")
# dirección de propagación: θ respecto de la normal a la muestra
xr, Lr = 605.0, 128.0
am_.plot([xr, xr], [ys - 6, ys - 122], ls=(0, (6, 5)), color=T2, lw=2, zorder=1)
am_.annotate("", xy=(xr, ys - 3), xytext=(xr + Lr * sT, ys - Lr * cT),
             arrowprops=dict(arrowstyle="-|>,head_width=0.45,head_length=0.9", color=NJ, lw=4, shrinkA=0, shrinkB=0), zorder=6)
am_.add_patch(Arc((xr, ys), 150, 150, theta1=270, theta2=305, color=T1, lw=2.2, zorder=4))
am_.text(xr + 100 * np.sin(TH / 2), ys - 100 * np.cos(TH / 2), r"$\theta$", fontsize=px(34), ha="center", va="center")
am_.text(WM - 4, ys + 14, "muestra", fontsize=px(31), color=AZ, ha="right", va="bottom")
am_.text(4, ys + 14, "(esquema)", fontsize=px(30), color=T2, style="italic", ha="left", va="bottom")
am_.text(150, 22, "frentes de onda", fontsize=px(30), color=NJ, ha="left", va="center")

fig.text(0.445, 1 - 372 / 1050, "una onda inclinada pone sobre la muestra", fontsize=px(30), color=T2, ha="center", va="center")
fig.text(0.445, 1 - 411 / 1050, "una «red» de período λ / sen θ  →  frecuencia", fontsize=px(30), color=T2, ha="center", va="center")
fig.text(0.445, 1 - 482 / 1050, r"$k=\frac{\mathrm{sen}\,\theta}{\lambda}$", fontsize=px(58), ha="center", va="center")

# ---- panel 2b: plano de Fourier a escala ----
xl0, xl1, hy = -0.135, 0.29, 0.125
H = 280; W = H * (xl1 - xl0) / (2 * hy)             # misma escala en x e y
a2 = fig.add_axes([0.352, 1 - 828 / 1050, W / 2400, H / 1050]); a2.set_facecolor("white")
a2.set_xlim(xl0, xl1); a2.set_ylim(-hy, hy); a2.set_aspect("equal")
a2.axhline(0, color="#C9C5BA", lw=1.5, zorder=1); a2.axvline(0, color="#C9C5BA", lw=1.5, zorder=1)
a2.add_patch(Circle((0, 0), kp, fc=AZ, alpha=0.16, ec="none")); a2.add_patch(Circle((0, 0), kp, fc="none", ec=AZ, lw=4))
a2.annotate("", xy=(k - 0.014, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>,head_width=0.5,head_length=1.0", color=NJ, lw=4.5), zorder=5)
a2.plot([k], [0], marker="*", ms=36, color=NJ, mec=T1, mew=1.2, zorder=6)
a2.plot([0], [0], "o", ms=8, color=T1, zorder=7)
a2.text(0, 0.070, "pupila", fontsize=px(30), color=AZ, weight="bold", ha="center", va="center")
a2.text(0, 0.036, "radio NA/λ", fontsize=px(30), color=AZ, weight="bold", ha="center", va="center")
a2.text(0, -0.048, "0,111 µm⁻¹", fontsize=px(30), color=AZ, ha="center", va="center")
a2.text(0.284, 0.034, "orden cero", fontsize=px(30), color=NJ, weight="bold", ha="right", va="bottom")
a2.text(k - 0.040, -0.036, "k", fontsize=px(34), color=NJ, style="italic", weight="bold", ha="center", va="center")
tk = [-0.1, 0, 0.1, 0.2]
a2.set_xticks(tk); a2.set_xticklabels([com(t, 1) if t else "0" for t in tk])
a2.set_yticks([-0.1, 0, 0.1]); a2.set_yticklabels(["−0,1", "0", "0,1"])
a2.tick_params(labelsize=px(28), colors=T2, length=6, width=1.5)
a2.set_xlabel("frecuencia espacial (µm⁻¹) — a escala", fontsize=px(30), color=T2, labelpad=4)

fig.text(0.445, 1 - 950 / 1050, r"$k\approx\frac{0{,}119}{0{,}63\ \mathrm{\mu m}}\approx$" + com(k) + " µm⁻¹", fontsize=px(40), ha="center", va="center")

# ---- panel 3: los dos casos ----
def caso(xc, signo, k_led, img, l1, l2, l3, vmax, col):
    fig.text(xc, 0.835, rf"$\mathrm{{sen}}\,\theta{signo}\mathrm{{NA}}$", fontsize=px(46), color=col, ha="center", va="center")
    w = 0.092; h = w * 2400 / 1050
    am = fig.add_axes([xc - w / 2, 0.575, w, h]); am.set_facecolor("white")
    am.set_xlim(-0.23, 0.23); am.set_ylim(-0.23, 0.23); am.set_aspect("equal"); am.set_xticks([]); am.set_yticks([])
    am.axhline(0, color="#C9C5BA", lw=1.2); am.axvline(0, color="#C9C5BA", lw=1.2)
    am.add_patch(Circle((0, 0), kp, fc=AZ, alpha=0.16, ec="none")); am.add_patch(Circle((0, 0), kp, fc="none", ec=AZ, lw=3.5))
    am.annotate("", xy=(k_led * 0.93, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-", color=NJ, lw=3.5))
    am.plot([k_led], [0], marker="*", ms=30, color=NJ, mec=T1, mew=1, zorder=6)
    fig.text(xc, 0.535, l1, fontsize=px(30), color=T1, ha="center", va="center")
    w2 = 0.112; h2 = w2 * 2400 / 1050
    ai = fig.add_axes([xc - w2 / 2, 0.245, w2, h2])
    ai.imshow(img, cmap="gray", vmin=0, vmax=vmax, interpolation="bilinear"); ai.set_xticks([]); ai.set_yticks([])
    for s in ai.spines.values(): s.set_edgecolor(T1); s.set_linewidth(2)
    fig.text(xc, 0.200, l2, fontsize=px(36), color=col, weight="bold", ha="center", va="center")
    fig.text(xc, 0.150, l3, fontsize=px(30), color=T2, ha="center", va="center")

caso(0.688, "<", 0.03 / lam, I_bf, "el orden cero entra", "campo claro", "(fondo brillante)", 1.45, AZ)
caso(0.872, ">", k, I_df, "queda afuera", "campo oscuro", "(solo bordes brillantes)", I_df.max() * 0.55, NJ)
fig.add_artist(plt.Line2D([0.781, 0.781], [0.14, 0.86], color="#C9C5BA", lw=2, transform=fig.transFigure))
fig.text(0.872, 0.090, "ejemplo de 12 mm: 0,119 > 0,07", fontsize=px(30), color="white", weight="bold", ha="center", va="center",
         bbox=dict(boxstyle="round,pad=0.35", fc=NJ, ec="none"))

fig.text(0.5, 0.030, "con estos tres pasos se ubica cada foto en el espectro", fontsize=px(34), color=T1, style="italic", ha="center", va="center")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puente.png")
fig.savefig(out, dpi=DPI, facecolor=BG)
print(out)

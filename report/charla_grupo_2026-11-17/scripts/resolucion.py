"""Figura 'Resolución: la apertura manda' (charla FPM).
Simulación coherente real: I = |F^-1{ P · F{t} }|^2, con t = (1 + w·cos(2πx/p))/2
(red sinusoidal de amplitud, de extensión finita w), λ = 0,63 µm, NA = 0,07.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from idioma import EN, T, salida

LAM, NA = 0.63, 0.07
KC = NA / LAM                      # 0,111 µm^-1
PERIODOS = [20.0, 9.0, 5.0]
N, DX = 2048, 0.25                 # campo simulado 512 µm
L_RED = 300.0                      # extensión de la red (µm)

BG, T1, T2 = "#F6F4EE", "#1B2333", "#3E4756"
AZUL, NAR, NARC, GRIS = "#2F6690", "#A9471A", "#E8925E", "#A7ABB2"

x = (np.arange(N) - N // 2) * DX
X, Y = np.meshgrid(x, x)
f = np.fft.fftfreq(N, DX)
FX, FY = np.meshgrid(f, f)
P = (np.hypot(FX, FY) <= KC).astype(float)          # pupila dura
w = np.exp(-(np.hypot(X, Y) / (L_RED / 2)) ** 8)     # red finita, borde suave


def simular(p):
    t = 0.5 * (1 + w * np.cos(2 * np.pi * X / p))
    cam = np.abs(np.fft.ifft2(P * np.fft.fft2(t))) ** 2
    return np.abs(t) ** 2, cam


W, H, DPI = 2400, 1050, 100
px = lambda n: n * 72 / DPI        # px -> pt
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.unicode_minus": True})
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)


def eje(x0, y0, w_, h_):
    return fig.add_axes([x0 / W, 1 - (y0 + h_) / H, w_ / W, h_ / H])


def txt(xp, yp, s, **kw):
    fig.text(xp / W, 1 - yp / H, s, **kw)


PW, PH, GAP = 560, 250, 22
X0 = [245, 245 + PW + 35, 245 + 2 * (PW + 35)]
Y0 = [92 + i * (PH + GAP) for i in range(3)]
XR = X0[2] + PW + 28
FOVX = 126.0
FOVY = FOVX * PH / PW
KY = 0.125
KX = KY * PW / PH

for xc, s in zip(X0, [T("la muestra", "the sample"), T("su espectro y la pupila", "its spectrum and the pupil"),
                                T("lo que ve la cámara", "what the camera sees")]):
    txt(xc + PW / 2, 50, s, ha="center", va="center", fontsize=px(38),
        color=T1, fontweight="bold")

rot = [(T("pasa", "passes"), None, T1),
       (T("en el límite", "at the limit"), T("pasa medio pico:\nbaja el contraste", "half a peak passes:\ncontrast drops"), NAR),
       (T("se pierde", "lost"), None, T2)]
ext = [-FOVX / 2, FOVX / 2, -FOVY / 2, FOVY / 2]
sel = (np.abs(X) <= FOVX / 2) & (np.abs(Y) <= FOVY / 2)
ny = int(np.sum(np.abs(x) <= FOVY / 2)); nx = int(np.sum(np.abs(x) <= FOVX / 2))

for i, p in enumerate(PERIODOS):
    obj, cam = simular(p)
    y0 = Y0[i]
    txt(225, y0 + PH / 2, T("período\n%s µm", "period\n%s µm") % (("%g" % p) if EN else ("%g" % p).replace(".", ",")),
        ha="right", va="center", fontsize=px(32), color=T1, linespacing=1.25)

    for col, img in ((0, obj), (2, cam)):
        a = eje(X0[col], y0, PW, PH)
        a.imshow(img[sel].reshape(ny, nx), cmap="gray", vmin=0, vmax=1,
                 extent=ext, interpolation="bilinear", aspect="auto")
        a.set_xticks([]); a.set_yticks([])
        for sp in a.spines.values():
            sp.set_color(T2); sp.set_linewidth(1.5)
        if i == 0 and col == 0:
            xb, yb = -FOVX / 2 + 6, -FOVY / 2 + 5
            a.add_patch(plt.Rectangle((xb - 2, yb - 2.5), 24, 16.5, fc=BG, ec="none", zorder=3))
            a.plot([xb, xb + 20], [yb + 1, yb + 1], color=T1, lw=6, solid_capstyle="butt", zorder=4)
            a.text(xb + 10, yb + 4, "20 µm", ha="center", va="bottom",
                   fontsize=px(30), color=T1, zorder=4)

    c = cam[N // 2, (np.abs(x) <= 1.5 * p)]
    print("p = %4.1f µm: I_max %.3f  I_min %.3f  visibilidad %.2f"
          % (p, c.max(), c.min(), (c.max() - c.min()) / (c.max() + c.min())))

    a = eje(X0[1], y0, PW, PH)
    a.set_facecolor("#FCFBF8")
    a.set_xlim(-KX, KX); a.set_ylim(-KY, KY); a.set_aspect("equal")
    a.axhline(0, color=GRIS, lw=1.2, zorder=1); a.axvline(0, color=GRIS, lw=1.2, zorder=1)
    a.add_patch(Circle((0, 0), KC, fc=AZUL, alpha=0.13, ec="none", zorder=2))
    a.add_patch(Circle((0, 0), KC, fc="none", ec=AZUL, lw=4.5, zorder=3))
    ms = px(27)
    a.plot(0, 0, "o", ms=ms, color=NAR, mec=T1, mew=1.5, zorder=5)
    k1 = 1 / p
    for s in (-1, 1):
        if k1 < KC * 0.98:
            a.plot(s * k1, 0, "o", ms=ms, color=NAR, mec=T1, mew=1.5, zorder=5)
        elif k1 > KC * 1.02:
            a.plot(s * k1, 0, "o", ms=ms, color="#D9DADC", mec=GRIS, mew=1.5, zorder=5)
            a.plot(s * k1, 0, "x", ms=ms * 1.25, color=T2, mew=4, zorder=6)
        else:  # justo en el borde: medio pico adentro
            a.plot(s * k1, 0, "o", ms=ms, color=NARC, markerfacecoloralt="#D9DADC",
                   fillstyle="left" if s > 0 else "right", mec=T1, mew=1.5, zorder=5)
    a.text(-KX + 0.008, KY - 0.008, "1/p = " + (("%.3g" % round(k1, 3)) if EN else ("%.3g" % round(k1, 3)).replace(".", ",")),
           ha="left", va="top", fontsize=px(30), color=T1)
    if i == 0:
        a.text(KX - 0.008, KY - 0.008, T("pupila", "pupil"), ha="right", va="top",
               fontsize=px(30), color=AZUL, fontweight="bold")
    a.set_yticks([])
    if i == 2:
        a.set_xticks([-0.2, -0.1, 0, 0.1, 0.2])
        a.set_xticklabels([T("−0,2", "−0.2"), "", "0", "", T("0,2 µm⁻¹", "0.2 µm⁻¹")], fontsize=px(30), color=T2)
        a.tick_params(axis="x", length=8, width=1.5, color=T2, pad=4)
    else:
        a.set_xticks([])
    for sp in a.spines.values():
        sp.set_color(T2); sp.set_linewidth(1.5)

    tit, sub, colr = rot[i]
    if sub:
        txt(XR, y0 + PH / 2 - 52, tit, ha="left", va="center", fontsize=px(38),
            color=colr, fontweight="bold")
        txt(XR, y0 + PH / 2 + 30, sub, ha="left", va="center", fontsize=px(30),
            color=T2, linespacing=1.25)
    else:
        txt(XR, y0 + PH / 2, tit, ha="left", va="center", fontsize=px(38),
            color=colr, fontweight="bold")

txt(W / 2, 995, T("la pupila del objetivo (radio NA/λ) decide qué detalles llegan: "
      "período mínimo ≈ λ/NA (coherente)",
      "the objective pupil (radius NA/λ) decides which details get through: "
      "minimum period ≈ λ/NA (coherent)"),
    ha="center", va="center", fontsize=px(36), color=T1)

out = salida("resolucion.png", os.path.dirname(os.path.abspath(__file__)))
fig.savefig(out, dpi=DPI, facecolor=BG)
print(out)

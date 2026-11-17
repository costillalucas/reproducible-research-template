"""Diapositiva 5: 'Qué es la pticografía: ventanas que se solapan'.
Tres paneles con imágenes simuladas (mismo objeto complejo 256x256).
Uso: python3 ventanas.py  ->  ventanas.png (2400x1050 px) junto al script.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
from idioma import T, salida

FONDO, TXT, TXT2 = "#F6F4EE", "#1B2333", "#3E4756"
AZUL, NAR, NARCL = "#2F6690", "#A9471A", "#E8925E"
W, H, DPI = 2400, 1050, 100
PT = 72 / DPI                      # 1 px real = PT puntos
plt.rcParams["font.family"] = "DejaVu Sans"

# ---------------- objeto ----------------
N = 256
y, x = np.mgrid[0:N, 0:N]
amp = np.ones((N, N))
for x0, w in [(28, 14), (52, 10), (70, 7), (84, 5), (95, 3), (102, 3)]:   # barras
    amp[(x >= x0) & (x < x0 + w) & (y >= 28) & (y < 118)] = 0.25
r = np.hypot(x - 182, y - 74)                                              # círculo
amp[r < 42] = 0.45
amp[r < 20] = 1.0
fuente = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
im = Image.new("L", (N, N), 0)
ImageDraw.Draw(im).text((128, 186), "FPM", font=ImageFont.truetype(fuente, 78), fill=255, anchor="mm")
amp = amp * (1 - 0.8 * np.asarray(im) / 255.0)                             # letras
fx = np.fft.fftfreq(N)
G = np.exp(-2 * (np.pi * 0.7) ** 2 * (fx[None, :] ** 2 + fx[:, None] ** 2))
amp = np.real(np.fft.ifft2(np.fft.fft2(amp) * G))                          # borde suave

def mancha(cx, cy, s):
    return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s ** 2))
fase = (1.7 * mancha(78, 176, 36) - 1.7 * mancha(186, 92, 34)
        + 0.9 * np.sin(2 * np.pi * (x + y) / 32) * mancha(196, 206, 34)
        + 0.9 * np.sin(2 * np.pi * (x - y) / 32) * mancha(56, 52, 30))
psi = amp * np.exp(1j * fase)
I_cam = np.abs(psi) ** 2

# ---------------- espectro y ventanas ----------------
F = np.fft.fftshift(np.fft.fft2(psi))
k = np.arange(N) - N // 2
KX, KY = np.meshgrid(k, k)
R, D = 26, (17, 0)                       # radio de pupila y corrimiento del LED vecino (px de Fourier)
P1 = np.hypot(KX, KY) <= R
P2 = np.hypot(KX - D[0], KY - D[1]) <= R
solape = (P1 & P2).sum() / P1.sum()
foto = lambda P: np.abs(np.fft.ifft2(np.fft.ifftshift(F * P))) ** 2
I1, I2 = foto(P1), foto(P2)
print(f"solapamiento = {100*solape:.1f} % del área de una ventana")
C = 50                                   # semiancho del recorte de espectro mostrado
esp = np.log10(1 + np.abs(F))[N//2 - C:N//2 + C + 1, N//2 - C:N//2 + C + 1]

cmap_fase = LinearSegmentedColormap.from_list(
    "fase", ["#1C4467", AZUL, "#9DBAD1", "#F5F1E8", NARCL, NAR, "#7A3010"])

# ---------------- lienzo (coordenadas en px reales) ----------------
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=FONDO)
ov = fig.add_axes([0, 0, 1, 1]); ov.set_xlim(0, W); ov.set_ylim(0, H); ov.axis("off")
ov.set_zorder(5); ov.patch.set_alpha(0)

def eje(x0, y0, w, h, borde=None, lw=2):
    a = fig.add_axes([x0 / W, y0 / H, w / W, h / H]); a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_edgecolor(borde or TXT2); s.set_linewidth(lw * PT)
    return a

def texto(x0, y0, s, px=31, color=TXT, **kw):
    kw.setdefault("ha", "center"); kw.setdefault("va", "center")
    return ov.text(x0, y0, s, fontsize=px * PT, color=color, **kw)

def flecha(p, q, color=NAR, lw=7, ms=34, ls="-"):
    ov.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms * PT, lw=lw * PT,
                                 color=color, linestyle=ls, shrinkA=0, shrinkB=0))

def titulo(x0, n, s):
    ov.add_patch(Circle((x0 + 30, 992), 30, color=NAR))
    texto(x0 + 30, 990, str(n), px=38, color="white", weight="bold")
    texto(x0 + 76, 1016, s, px=39, weight="bold", ha="left", va="top", linespacing=1.15)

def espectro(a, ventanas, sombra=None):
    a.imshow(esp, cmap="gray", extent=[-C, C, -C, C], origin="lower", vmin=1.2, vmax=esp.max() * 0.95)
    g = np.linspace(-C, C, 800); gx, gy = np.meshgrid(g, g)
    if sombra is not None:               # zona compartida resaltada
        m = (np.hypot(gx, gy) <= R) & (np.hypot(gx - D[0], gy - D[1]) <= R)
        rgba = np.zeros(m.shape + (4,)); rgba[m] = matplotlib.colors.to_rgba(NARCL, 0.72)
        a.imshow(rgba, extent=[-C, C, -C, C], origin="lower")
    for (cx, cy), col in ventanas:
        a.add_patch(Circle((cx, cy), R, fill=False, ec=FONDO, lw=9 * PT))
        a.add_patch(Circle((cx, cy), R, fill=False, ec=col, lw=6 * PT))
    a.set_xlim(-C, C); a.set_ylim(-C, C)

# ---------- panel 1 ----------
X1 = 40
titulo(X1, 1, T("La cámara pierde la fase", "The camera loses the phase"))
texto(X1 + 140, 872, T("amplitud", "amplitude"))
eje(X1, 570, 280, 280).imshow(amp, cmap="gray", vmin=0, vmax=1.05)
texto(X1 + 140, 546, T("fase", "phase"))
eje(X1, 245, 280, 280).imshow(fase, cmap=cmap_fase, vmin=-2, vmax=2)
texto(X1 + 500, 872, T("la cámara mide |ψ|²", "the camera measures |ψ|²"))
eje(X1 + 360, 570, 280, 280).imshow(I_cam, cmap="gray", vmin=0, vmax=1.1)
texto(X1 + 500, 546, T("¿fase?", "phase?"), color=NAR, weight="bold")
ov.add_patch(Rectangle((X1 + 360, 245), 280, 280, fill=True, fc="#ECE8DD", ec=NAR,
                       lw=4 * PT, ls=(0, (5, 4))))
texto(X1 + 500, 380, "?", px=210, color=NAR, weight="bold")
flecha((X1 + 290, 710), (X1 + 350, 710))
flecha((X1 + 290, 385), (X1 + 350, 385), color="#9A9FA8", lw=5, ls=(0, (2.5, 2)))
ov.plot([X1 + 303, X1 + 333], [366, 404], color=NAR, lw=6 * PT, solid_capstyle="round")
ov.plot([X1 + 303, X1 + 333], [404, 366], color=NAR, lw=6 * PT, solid_capstyle="round")
texto(X1 + 320, 150, T("misma foto para infinitas fases", "same photo for infinitely many phases"), px=32, color=TXT2, style="italic")

# ---------- panel 2 ----------
X2 = 800
titulo(X2, 2, T("Cada medida ve por una ventana", "Each photo sees a window"))
texto(X2 + 190, 792, T("espectro del objeto", "object spectrum"))
espectro(eje(X2, 375, 380, 380), [((0, 0), AZUL)])
texto(X2 + 190, 337, T("una ventana (pupila)", "one window (pupil)"), color=AZUL, weight="bold")
flecha((X2 + 390, 565), (X2 + 442, 565), color=AZUL)
texto(X2 + 600, 752, T("su foto", "its photo"))
eje(X2 + 450, 415, 300, 300, AZUL, 6).imshow(I1, cmap="gray", vmin=0, vmax=1.1)
texto(X2 + 600, 377, T("baja resolución", "low resolution"), color=TXT2)

# ---------- panel 3 ----------
X3 = 1670
titulo(X3, 3, T("Ventanas que se solapan\natan la fase", "Overlapping windows\ntie down the phase"))
ys = 385
espectro(eje(X3, ys, 380, 380), [((0, 0), AZUL), (D, NAR)], sombra=True)
esc = 380 / (2 * C)
xl, yl = X3 + 190 + D[0] / 2 * esc, ys + 190
ov.plot([xl, xl], [ys - 22, ys], color=NAR, lw=4 * PT)
ov.plot([xl, xl], [ys, yl - 40], color=FONDO, lw=4 * PT)
ov.add_patch(Circle((xl, yl - 40), 9, color=FONDO))
texto(X3 + 190, ys - 45, T(f"medida dos veces  ≈ {100*solape:.0f} %", f"measured twice  ≈ {100*solape:.0f} %"), color=NAR, weight="bold")
texto(X3 + 570, 878, T("LED central", "central LED"), color=AZUL, weight="bold")
eje(X3 + 440, 598, 260, 260, AZUL, 6).imshow(I1, cmap="gray", vmin=0, vmax=1.1)
texto(X3 + 570, 568, T("LED vecino", "neighbor LED"), color=NAR, weight="bold")
eje(X3 + 440, 288, 260, 260, NAR, 6).imshow(I2, cmap="gray", vmin=0, vmax=1.1)
flecha((X3 + 388, 650), (X3 + 432, 715), color=AZUL, lw=6, ms=30)
flecha((X3 + 388, 500), (X3 + 432, 430), color=NAR, lw=6, ms=30)
texto(X3 + 350, 170, T("las dos fotos tienen que explicarse", "both photos have to be explained"), px=32)
ov.text(X3 + 350, 122, T("con el mismo campo → eso fija la fase", "by the same field → that fixes the phase"), fontsize=32 * PT, color=TXT,
        ha="center", va="center", weight="bold")

# ---------- flechas entre paneles ----------
flecha((700, 565), (782, 565), lw=11, ms=52)
flecha((1570, 565), (1652, 565), lw=11, ms=52)

fig.savefig(salida("ventanas.png", os.path.dirname(os.path.abspath(__file__))),
            dpi=DPI, facecolor=FONDO)

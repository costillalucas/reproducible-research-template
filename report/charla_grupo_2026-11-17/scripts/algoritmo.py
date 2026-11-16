"""Diagrama 'Modelo directo y recuperacion de fase' (FPM) - ciclo de 4 pasos por LED.
Todas las miniaturas salen de una simulacion numpy (objeto 128x128, pupila r=18 px)."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

BG, T1, T2 = "#F6F4EE", "#1B2333", "#3E4756"
ACC, AZ, NAR = "#A9471A", "#2F6690", "#E8925E"
plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans"})
W, H, DPI = 2400, 1000, 100
pt = lambda px: px * 72.0 / DPI

# ---------------- simulacion ----------------
N, R, KJ = 128, 18, (13, -8)          # KJ = (kx, ky) centro de la ventana del LED j
rng = np.random.default_rng(3)
y, x = np.mgrid[:N, :N]
FONT = {"F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"]}
amp = np.ones((N, N))
s = 5
for i, ch in enumerate("FPM"):
    g = np.kron(np.array([[int(c) for c in r] for r in FONT[ch]]), np.ones((s, s)))
    x0 = 18 + i * (5 * s + 8)
    amp[14:14 + 7 * s, x0:x0 + 5 * s] -= 0.65 * g
bars = lambda per, xa, xb: ((x >= xa) & (x < xb) & (y >= 66) & (y < 112) & (((x - xa) % per) < per / 2))
amp[bars(10, 12, 42)] = 0.35          # barras gruesas (se resuelven con el LED central)
amp[bars(5, 46, 66)] = 0.35           # barras finas (no se resuelven con un solo LED)
phase = 1.2 * (((x - 96) ** 2 + (y - 88) ** 2) < 20 ** 2)     # circulo de fase pura
obj = amp * np.exp(1j * phase)

F = lambda a: np.fft.fftshift(np.fft.fft2(a))
Fi = lambda A: np.fft.ifft2(np.fft.ifftshift(A))
ky, kx = np.mgrid[-N // 2:N // 2, -N // 2:N // 2]
P = (kx ** 2 + ky ** 2 <= R ** 2).astype(float)
window = lambda O, k: np.roll(O, (-k[1], -k[0]), axis=(0, 1)) * P      # recorta y centra
unwindow = lambda D, k: np.roll(D, (k[1], k[0]), axis=(0, 1))

def measure(k, photons=3000):
    I = np.abs(Fi(window(F(obj), k))) ** 2
    return rng.poisson(I * photons) / photons

I0, Ij = measure((0, 0)), measure(KJ)

def update(O, k, I):
    psi = Fi(window(O, k))
    psi_new = np.sqrt(I) * np.exp(1j * np.angle(psi))     # conservar fase, reemplazar amplitud
    return O + unwindow(P * (F(psi_new) - F(psi)), k), psi

O_est = F(np.full((N, N), np.sqrt(I0.mean()), complex))   # arranque: objeto plano
O_est, _ = update(O_est, (0, 0), I0)                      # ya se uso el LED central
O_new, psi = update(O_est, KJ, Ij)                        # paso con el LED j (oblicuo)
I_pred = np.abs(psi) ** 2
# para mostrar: se quita la portadora lineal del LED oblicuo (la inclinacion de la onda plana)
dem = psi * np.exp(2j * np.pi * (KJ[0] * x + KJ[1] * y) / N)
ph = np.angle(dem * np.exp(-1j * np.angle(dem.mean())))

# ---------------- figura ----------------
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
ov = fig.add_axes([0, 0, 1, 1]); ov.set_xlim(0, W); ov.set_ylim(H, 0); ov.axis("off")
cm_ph = LinearSegmentedColormap.from_list("azna", ["#17384F", AZ, BG, NAR, ACC])

S, TOP = 340, 122
X = [110, 600, 970, 1460, 1950]       # espectro | fase, predicha | medida | espectro nuevo

def thumb(x0):
    ax = fig.add_axes([x0 / W, 1 - (TOP + S) / H, S / W, S / H])
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(T1); sp.set_linewidth(2)
    return ax

C = 40                                  # medio ancho del recorte del espectro mostrado
def spec(ax, O):
    L = np.log10(np.abs(O) + 1e-9)[N // 2 - C:N // 2 + C, N // 2 - C:N // 2 + C]
    ax.imshow(L, cmap="gray", vmin=vmax_s - 4.2, vmax=vmax_s, extent=[-C, C, C, -C])
    ax.add_patch(Circle(KJ, R, fill=False, ec=ACC, lw=5))
    ax.plot(0, 0, "+", color=AZ, ms=16, mew=3)
vmax_s = np.log10(np.abs(O_new).max())
vI = max(I_pred.max(), Ij.max())

a = thumb(X[0]); spec(a, O_est)
a = thumb(X[1]); a.imshow(ph, cmap=cm_ph, vmin=-1.2, vmax=1.2)
a = thumb(X[2]); a.imshow(I_pred, cmap="gray", vmin=0, vmax=vI)
a = thumb(X[3]); a.imshow(Ij, cmap="gray", vmin=0, vmax=vI)
a = thumb(X[4]); spec(a, O_new)

def title(x0, n, txt):
    ov.add_patch(Circle((x0 + 26, 60), 26, fc=ACC, ec="none"))
    ov.text(x0 + 26, 61, str(n), color="white", fontsize=pt(36), fontweight="bold", ha="center", va="center")
    ov.text(x0 + 66, 60, txt, color=T1, fontsize=pt(35), fontweight="bold", ha="left", va="center", linespacing=1.15)
title(X[0], 1, "Estimación actual\ndel objeto")
title(X[1], 2, "Predecir la foto")
title(X[3], 3, "Comparar con\nla foto medida")
title(X[4], 4, "Corregir solo\nesa ventana")

LY = [496, 537, 578, 619]
def cap(xc, row, txt, color=T2, **kw):
    ov.text(xc, LY[row], txt, color=color, fontsize=pt(30), ha="center", va="center", **kw)
c = lambda i: X[i] + S / 2
cap(c(0), 0, r"espectro $\tilde{O}(\mathbf{k})$,"); cap(c(0), 1, "ventana del LED $j$", color=ACC)
cap(c(1), 0, r"fase de $\psi_j$"); cap(c(2), 0, r"foto predicha $|\psi_j|^2$")
cap((X[1] + X[2] + S) / 2, 1, "recortar la ventana y volver al espacio real")
cap(c(3), 0, r"foto medida $I_j$")
cap(c(3), 1, "conservar la fase,", color=ACC, fontweight="bold")
cap(c(3), 2, "reemplazar la amplitud", color=ACC, fontweight="bold")
cap(c(3), 3, r"por $\sqrt{I_j}$", color=ACC, fontweight="bold")
cap(c(4), 0, "cambia solo lo de"); cap(c(4), 1, "adentro del círculo")

def arrow(p, q, **kw):
    ov.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=42, lw=7, color=ACC,
                                 shrinkA=0, shrinkB=0, joinstyle="miter", capstyle="butt", **kw))
ym = TOP + S / 2
for xa, xb, lab, fs in [(X[0] + S, X[1], r"$\mathcal{F}^{-1}$", 38), (X[2] + S, X[3], "≠", 60),
                        (X[3] + S, X[4], r"$\mathcal{F}$", 38)]:
    arrow((xa + 18, ym), (xb - 18, ym))
    ov.text((xa + xb) / 2, ym - 48, lab, color=ACC, fontsize=pt(fs), ha="center", va="center", fontweight="bold")

# flecha de retorno 4 -> 1
YR = 676
ov.plot([c(4), c(4), c(0), c(0)], [578, YR, YR, 600], color=ACC, lw=7, solid_joinstyle="round", solid_capstyle="butt")
arrow((c(0), 610), (c(0), 566))
ov.text((c(0) + c(3)) / 2 - 120, YR, r"siguiente LED:  $j \rightarrow j+1$", color=ACC, fontsize=pt(32), fontweight="bold",
        ha="center", va="center", bbox=dict(fc=BG, ec="none", pad=10))

# formula y recuadro
ov.text(780, 800, r"$I_j(\mathbf{r}) \;=\; \left|\; \mathcal{F}^{-1}\left\{\, P(\mathbf{k}) \cdot \tilde{O}(\mathbf{k}-\mathbf{k}_j) \,\right\} \;\right|^{2}$",
        color=T1, fontsize=pt(50), ha="center", va="center")
ov.text(780, 905, r"$P$: pupila del objetivo  ·  $\tilde{O}$: espectro del objeto  ·  $\mathbf{k}_j$: inclinación del LED $j$",
        color=T2, fontsize=pt(30), ha="center", va="center")
ov.add_patch(FancyBboxPatch((1560, 762), 730, 170, boxstyle="round,pad=0,rounding_size=18", fc="#FFFFFF", ec=AZ, lw=3))
ov.text(1925, 847, "El error de entrenamiento siempre\nbaja: se corta con LEDs reservados", color=T1,
        fontsize=pt(31), ha="center", va="center", linespacing=1.35)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "algoritmo.png")
fig.savefig(out, dpi=DPI, facecolor=BG)
print(out, "dif. relativa predicha/medida:", round(float(np.abs(I_pred - Ij).sum() / Ij.sum()), 3))

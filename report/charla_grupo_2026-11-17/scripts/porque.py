"""Figura 'Un objetivo barato ve mucho campo, pero poco detalle'.
Mismo objeto simulado (frotis de 'celulas') visto con 2,5x/0,07, 10x/0,25 y la meta de FPM.
Uso: python3 porque.py  -> porque.png (2400x1000 px)
"""
import os
import numpy as np
import scipy.fft as sfft
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, ConnectionPatch

# ---------------- parametros fisicos ----------------
LAM = 0.63            # um
FOV = 1400.0          # um, campo del 2,5x
DX = 0.25             # um/px de la simulacion
N = int(FOV / DX)     # 5600
NA_LO, NA_HI, NA_SYN = 0.07, 0.25, 0.45
FOV_HI = FOV * 2.5 / 10.0          # 350 um, campo del 10x con el mismo sensor
BOX_HI = (300.0, 240.0)            # esquina (x, y) del campo del 10x, um
ZOOM = 48.0                        # um, lado del sub-campo ampliado
ZOOM_XY = (455.0, 400.0)           # esquina (x, y) del sub-campo, um

BG, INK, INK2 = "#F6F4EE", "#1B2333", "#3E4756"
ACC, BLUE, ORANGE = "#A9471A", "#2F6690", "#E8925E"

rng = np.random.default_rng(7)

# ---------------- objeto: transmision de intensidad ----------------
def smooth_noise(n, corr_px, rng):
    f = sfft.rfft2(rng.standard_normal((n, n)).astype(np.float32))
    ky = sfft.fftfreq(n)[:, None]; kx = sfft.rfftfreq(n)[None, :]
    f *= np.exp(-(kx**2 + ky**2) * (np.pi * corr_px) ** 2)
    g = sfft.irfft2(f, s=(n, n))
    return (g - g.min()) / (g.max() - g.min())

# posiciones: densidad modulada + distancia minima
dens = smooth_noise(280, 30, rng)                       # 5 um/px, estructura ~150 um
cand = rng.uniform(8, FOV - 8, size=(26000, 2))
p = 0.25 + 0.75 * dens[(cand[:, 1] / 5).astype(int), (cand[:, 0] / 5).astype(int)]
cand = cand[rng.uniform(size=len(cand)) < p]
keep = np.ones(len(cand), bool)
for i, j in sorted(cKDTree(cand).query_pairs(8.4)):
    if keep[i] and keep[j]:
        keep[j] = False
cells = cand[keep]
ncell = len(cells)
radii = rng.uniform(3.0, 4.0, ncell)                    # diametros 6-8 um
biconc = rng.uniform(size=ncell) < 0.7
infect = rng.uniform(size=ncell) < 0.08
# asegurar detalle fino dentro del sub-campo ampliado
zc = np.array([ZOOM_XY[0] + ZOOM / 2, ZOOM_XY[1] + ZOOM / 2])
d = np.hypot(*(cells - zc).T)
infect[np.argsort(d)[[0, 2, 5]]] = True
biconc[np.argsort(d)[:8]] = True

T = np.ones((N, N), np.float32)

def stamp(cx, cy, half, fun):
    """multiplica T por fun(X, Y) (coordenadas en um relativas al centro)."""
    i0, i1 = int((cy - half) / DX), int((cy + half) / DX) + 1
    j0, j1 = int((cx - half) / DX), int((cx + half) / DX) + 1
    i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1, N), min(j1, N)
    Y = (np.arange(i0, i1)[:, None] + 0.5) * DX - cy
    X = (np.arange(j0, j1)[None, :] + 0.5) * DX - cx
    T[i0:i1, j0:j1] *= fun(X, Y).astype(np.float32)

def disc(r, R, soft=0.2):
    return 0.5 * (1 - np.tanh((r - R) / soft))

for (cx, cy), R, bc, inf in zip(cells, radii, biconc, infect):
    def cell(X, Y, R=R, bc=bc):
        r = np.hypot(X, Y); s = np.clip(r / R, 0, 1)
        if bc:   # perfil biconcavo (Evans-Fung, normalizado)
            h = np.sqrt(1 - s**2) * (0.21 + 2.0 * s**2 - 1.12 * s**4) / 0.62
        else:
            h = np.sqrt(1 - s**2) ** 0.5
        return np.exp(-0.75 * h * disc(r, R)) * (1 - 0.12 * disc(r, R))
    stamp(cx, cy, R + 1.5, cell)
    if inf:      # 1-3 puntos de 1,2-1,8 um ('parasitos')
        ang = rng.uniform(0, 2 * np.pi); rho = rng.uniform(0.2, 0.5) * R
        px, py = cx + rho * np.cos(ang), cy + rho * np.sin(ang)
        for k in range(rng.integers(1, 4)):
            a2 = ang + 2.1 * k + rng.uniform(-0.3, 0.3)
            qx, qy = px + (k > 0) * 2.0 * np.cos(a2), py + (k > 0) * 2.0 * np.sin(a2)
            rd = rng.uniform(0.6, 0.9)
            stamp(qx, qy, 2.0, lambda X, Y, rd=rd: 1 - 0.85 * disc(np.hypot(X, Y), rd, 0.12))

# unos pocos 'globulos blancos': 12 um con nucleo lobulado
for _ in range(45):
    cx, cy = rng.uniform(20, FOV - 20, 2)
    if abs(cx - zc[0]) < 60 and abs(cy - zc[1]) < 60:
        continue
    stamp(cx, cy, 8, lambda X, Y: 1 - 0.25 * disc(np.hypot(X, Y), 6.0, 0.3))
    a0 = rng.uniform(0, 2 * np.pi)
    for k in range(3):
        a = a0 + 2.1 * k
        stamp(cx + 2.1 * np.cos(a), cy + 2.1 * np.sin(a), 4,
              lambda X, Y: 1 - 0.8 * disc(np.hypot(X, Y), rng.uniform(1.7, 2.2), 0.2))

# ---------------- formacion de imagen ----------------
fy = sfft.fftfreq(N, DX)[:, None].astype(np.float32)
fx = sfft.rfftfreq(N, DX)[None, :].astype(np.float32)
RHO = np.sqrt(fx**2 + fy**2)

def incoherente(T, na):
    """intensidad incoherente: OTF de pupila circular, corte 2NA/lambda."""
    s = np.clip(RHO / (2 * na / LAM), 0, 1)
    otf = (2 / np.pi) * (np.arccos(s) - s * np.sqrt(1 - s**2))
    return sfft.irfft2(sfft.rfft2(T, workers=4) * otf, s=T.shape, workers=4)

def coherente(T, na):
    """intensidad coherente: amplitud sqrt(T) filtrada con pupila de corte NA/lambda."""
    A = sfft.irfft2(sfft.rfft2(np.sqrt(T), workers=4) * (RHO <= na / LAM), s=T.shape, workers=4)
    return A**2

I_lo = incoherente(T, NA_LO)
I_hi = incoherente(T, NA_HI)
I_fp = coherente(T, NA_SYN)
print(f"celulas: {ncell}; detalle 2,5x {LAM/(2*NA_LO):.2f} um; 10x {LAM/(2*NA_HI):.2f} um; FPM {LAM/NA_SYN:.2f} um")

def crop(I, xy, side):
    j0, i0, n = int(xy[0] / DX), int(xy[1] / DX), int(side / DX)
    return I[i0:i0 + n, j0:j0 + n]

def binned(I, b):
    n = I.shape[0] // b
    return I[:n * b, :n * b].reshape(n, b, n, b).mean(axis=(1, 3))

# ---------------- figura ----------------
W, H, DPI = 2400, 1000, 100
PX = 72.0 / DPI                      # pt por px
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
plt.rcParams["font.family"] = "DejaVu Sans"
S, GAP, TOP = 740, 50, 96            # lado del panel, separacion, alto del titulo (px)
X0 = (W - 3 * S - 2 * GAP) / 2
IMKW = dict(cmap="gray", vmin=0.0, vmax=1.08)

def panel(k):
    ax = fig.add_axes([(X0 + k * (S + GAP)) / W, 1 - (TOP + S) / H, S / W, S / H])
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(INK2); sp.set_linewidth(1.5)
    return ax

def titulo(ax, txt, color=INK):
    ax.text(0.5, 1.0 + 26 / S, txt, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=40 * PX, fontweight="bold", color=color)

def pie(ax, l1, l2, c2=INK2):
    ax.text(0.5, -22 / S, l1, transform=ax.transAxes, ha="center", va="top",
            fontsize=31 * PX, color=INK)
    ax.text(0.5, -76 / S, l2, transform=ax.transAxes, ha="center", va="top",
            fontsize=31 * PX, color=c2, fontweight="bold")

def barra(ax, side, largo, txt, lw=7, fs=29):
    """barra de escala abajo a la izquierda, sobre placa clara."""
    m = 0.035 * side
    wplaca = max(largo, 0.21 * side * fs / 29) + 2 * m * 0.6
    ax.add_patch(Rectangle((m * 0.5, side - m * 0.5 - 0.125 * side), wplaca, 0.125 * side,
                           fc=BG, ec="none", alpha=0.92, zorder=5))
    y = side - m * 0.5 - 0.028 * side
    ax.plot([m * 1.1, m * 1.1 + largo], [y, y], color=INK, lw=lw, solid_capstyle="butt", zorder=6)
    ax.text(m * 1.1, y - 0.022 * side, txt, ha="left", va="bottom", fontsize=fs * PX,
            color=INK, zorder=6)

def con_zoom(ax, I):
    """panel de campo completo + inset del sub-campo."""
    ax.imshow(binned(I, 4), extent=[0, FOV, FOV, 0], interpolation="lanczos", **IMKW)
    ax.set_xlim(0, FOV); ax.set_ylim(FOV, 0)
    ax.add_patch(Rectangle(ZOOM_XY, ZOOM, ZOOM, fc="none", ec=ACC, lw=3, zorder=7))
    f = 0.50
    axi = ax.inset_axes([1 - f - 0.02, 0.02, f, f])
    axi.imshow(crop(I, ZOOM_XY, ZOOM), extent=[0, ZOOM, ZOOM, 0], interpolation="lanczos", **IMKW)
    axi.set_xticks([]); axi.set_yticks([])
    for sp in axi.spines.values():
        sp.set_color(ACC); sp.set_linewidth(4)
    for (xa, ya), (xb, yb) in [((ZOOM_XY[0] + ZOOM, ZOOM_XY[1]), (0, 0)),
                               ((ZOOM_XY[0], ZOOM_XY[1] + ZOOM), (0, ZOOM))]:
        ax.add_artist(ConnectionPatch((xa, ya), (xb, yb), ax.transData, axi.transData,
                                      color=ACC, lw=2, zorder=7))
    y = ZOOM * 0.93
    axi.add_patch(Rectangle((ZOOM * 0.04, ZOOM * 0.775), ZOOM * 0.30, ZOOM * 0.19,
                            fc=BG, ec="none", alpha=0.92, zorder=5))
    axi.plot([ZOOM * 0.07, ZOOM * 0.07 + 10], [y, y], color=INK, lw=6, solid_capstyle="butt", zorder=6)
    axi.text(ZOOM * 0.07, y - ZOOM * 0.03, "10 µm", ha="left", va="bottom",
             fontsize=28 * PX, color=INK, zorder=6)

# 1) objetivo 2,5x
ax1 = panel(0)
con_zoom(ax1, I_lo)
ax1.add_patch(Rectangle(BOX_HI, FOV_HI, FOV_HI, fc="none", ec=BLUE, lw=4, zorder=7))
ax1.text(BOX_HI[0] + FOV_HI / 2, BOX_HI[1] - 14, "campo del 10×", ha="center", va="bottom",
         fontsize=28 * PX, color=BLUE, fontweight="bold", zorder=8,
         bbox=dict(fc=BG, ec="none", alpha=0.9, pad=3))
barra(ax1, FOV, 200, "200 µm")
titulo(ax1, "Objetivo 2,5× · NA 0,07")
pie(ax1, "campo 1,4 mm · detalle ≈ 4,5 µm", "ve todo, pero borroso")

# 2) objetivo 10x
ax2 = panel(1)
ax2.imshow(binned(crop(I_hi, BOX_HI, FOV_HI), 1), extent=[0, FOV_HI, FOV_HI, 0],
           interpolation="lanczos", **IMKW)
for sp in ax2.spines.values():
    sp.set_color(BLUE); sp.set_linewidth(5)
ax2.add_patch(Rectangle((ZOOM_XY[0] - BOX_HI[0], ZOOM_XY[1] - BOX_HI[1]), ZOOM, ZOOM,
                        fc="none", ec=ACC, lw=3, zorder=7))
barra(ax2, FOV_HI, 50, "50 µm")
titulo(ax2, "Objetivo 10× · NA 0,25")
pie(ax2, "campo 0,35 mm · detalle ≈ 1,3 µm", "nítido, pero 1/16 del área", BLUE)

# 3) FPM (meta)
ax3 = panel(2)
con_zoom(ax3, I_fp)
barra(ax3, FOV, 200, "200 µm")
titulo(ax3, "FPM con el 2,5× (meta)", ACC)
pie(ax3, "campo 1,4 mm · detalle ≈ 1,4 µm", "meta: NA sintética ≈ 0,45 (simulado)", ACC)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "porque.png")
fig.savefig(out, dpi=DPI, facecolor=BG)
print(out)

"""Figura 'El microscopio en el espacio de Fourier' con datos reales (solo lectura).
Captura 2026-11-13.a, rojo, LED (17,16) = vecino del eje (17,15), 18 ms, promedio de 2 frames - dark.
Ajuste: borde del soporte de log|FFT| (suavizado gaussiano 5 px) al nivel medio entre la meseta
interior y el piso exterior, sobre perfiles radiales cada 1 grado (solo el arco que no cae dentro del
circulo gemelo); circulo por minimos cuadrados (Kasa) con recorte 3-sigma, iterado 6 veces.
"""
import glob
import numpy as np, tifffile
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Circle

D = '/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/'
LED = 'fila17_col16'; EXPO = '18ms'
DX = 1.29            # um/px en la muestra (micrometro)
LAM, LAM_MED = 0.63, 0.617
Z, PITCH = 99.5, 6.0  # mm
BG, T1, T2, AZ, NA_ = '#F6F4EE', '#1B2333', '#3E4756', '#2F6690', '#A9471A'
OUT = __file__.replace('fft_real.py', 'fft_real.png')

def coma(x, nd): return f'{x:.{nd}f}'.replace('.', ',')

def cargar():
    im = np.mean([tifffile.imread(f).astype(float) for f in sorted(glob.glob(D + f'2026-11-13.a/{LED}_colorr/{EXPO}/*.tiff'))], 0)
    dk = np.mean([tifffile.imread(f).astype(float) for f in sorted(glob.glob(D + f'2026-11-13.a-dark/fila17_col15_colorr/{EXPO}/*.tiff'))], 0)
    return im - dk

def logfft(im):
    N = im.shape[0]; w = np.hanning(N)
    return np.log10(np.abs(np.fft.fftshift(np.fft.fft2((im - im.mean()) * np.outer(w, w)))) + 1)

def suavizar(L, s):
    f = np.fft.fftfreq(L.shape[0]); G = np.exp(-2 * np.pi**2 * s**2 * (f[:, None]**2 + f[None, :]**2))
    return np.fft.ifft2(np.fft.fft2(L) * G).real

def bilin(A, x, y):
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); dx = x - x0; dy = y - y0
    return A[y0, x0]*(1-dx)*(1-dy) + A[y0, x0+1]*dx*(1-dy) + A[y0+1, x0]*(1-dx)*dy + A[y0+1, x0+1]*dx*dy

def puntos_borde(Ls, c, r0, nang=360, excl=12):
    o = Ls.shape[0] // 2; rr = np.arange(r0 - 45, r0 + 45, 0.5); pts = []
    for th in np.linspace(0, 2*np.pi, nang, endpoint=False):
        u = np.array([np.cos(th), np.sin(th)])
        if np.hypot(*(c + r0*u + c)) < r0 + excl: continue      # ese borde cae dentro del gemelo (-c)
        pr = bilin(Ls, c[0] + rr*u[0] + o, c[1] + rr*u[1] + o)
        lev = 0.5 * (np.median(pr[:40]) + np.median(pr[-40:]))
        idx = np.where((pr[:-1] >= lev) & (pr[1:] < lev))[0]
        if len(idx) == 0: continue
        i = idx[np.argmin(abs(rr[idx] - r0))]
        pts.append(c + (rr[i] + 0.5 * (pr[i] - lev) / (pr[i] - pr[i+1])) * u)
    return np.array(pts)

def kasa(p):
    A = np.c_[2*p[:, 0], 2*p[:, 1], np.ones(len(p))]
    s = np.linalg.lstsq(A, (p**2).sum(1), rcond=None)[0]; c = s[:2]
    return c, np.sqrt(s[2] + c @ c)

def ajustar(Ls, c0, r0):
    c, r = np.array(c0, float), r0
    for _ in range(6):
        p = puntos_borde(Ls, c, r)
        for _ in range(3):
            c, r = kasa(p); res = np.hypot(*(p - c).T) - r
            s = 1.4826 * np.median(abs(res - np.median(res))); k = abs(res) < 3 * max(s, 0.5)
            if k.all(): break
            p = p[k]
    return c, r, p

im = cargar(); N = im.shape[0]
L = logfft(im); c, r, pts = ajustar(suavizar(L, 5), (130, -20), 165)
df = 1 / (N * DX)                       # um^-1 por pixel de FFT
r_f, k_px = r * df, np.hypot(*c); k_f = k_px * df
na, na2 = r_f * LAM, r_f * LAM_MED
st, st2 = k_f * LAM, k_f * LAM_MED
st_esp = PITCH / np.hypot(PITCH, Z)
print(f'N={N} df={df:.3e} centro=({c[0]:.1f},{c[1]:.1f}) px  r={r:.1f} px = {r_f:.4f} um^-1  k={k_px:.1f} px = {k_f:.4f} um^-1')
print(f'NA={na:.4f} (lam .63) / {na2:.4f} (.617); sin={st:.4f} / {st2:.4f}; esperado={st_esp:.4f}; puntos={len(pts)}')

plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': T1, 'axes.labelcolor': T2,
                     'xtick.color': T2, 'ytick.color': T2, 'axes.edgecolor': T2})
FS, FT = 22, 26                          # pt a 100 dpi -> 30,6 px y 36 px
fig = plt.figure(figsize=(24, 10), dpi=100, facecolor=BG)

# --- 1: foto
a1 = fig.add_axes([0.015, 0.06, 0.31, 0.80]); a1.set_title('Foto con un LED de campo claro', fontsize=FT, pad=16, color=T1)
a1.imshow(im, cmap='gray', vmin=np.percentile(im, 0.5), vmax=np.percentile(im, 99.8)); a1.set_xticks([]); a1.set_yticks([])
nb = 200 / DX
a1.add_patch(plt.Rectangle((40, N - 150), nb + 40, 120, color=BG, alpha=0.92))
a1.plot([60, 60 + nb], [N - 55, N - 55], color=T1, lw=7, solid_capstyle='butt')
a1.text(60 + nb/2, N - 75, '200 µm', ha='center', va='bottom', fontsize=FS, color=T1)

# --- 2: FFT
a2 = fig.add_axes([0.385, 0.13, 0.30, 0.73]); a2.set_title('Su transformada de Fourier', fontsize=FT, pad=16, color=T1)
h = 380; o = N // 2; fm = h * df
a2.imshow(L[o-h:o+h, o-h:o+h], cmap='gray', origin='lower', extent=[-fm, fm, -fm, fm],
          vmin=np.percentile(L, 25), vmax=np.percentile(L, 99.9))
cf = c * df
a2.add_patch(Circle(cf, r_f, fill=False, ec='#7FB6DC', lw=4, ls=(0, (5, 3))))
a2.add_patch(Circle(-cf, r_f, fill=False, ec='#7FB6DC', lw=2.5, ls=(0, (5, 3)), alpha=0.75))
ang = np.deg2rad(55); pe = cf + r_f * np.array([np.cos(ang), np.sin(ang)])
a2.annotate('', xy=pe, xytext=cf, arrowprops=dict(arrowstyle='->', color='#7FB6DC', lw=4, mutation_scale=28))
a2.annotate('', xy=cf, xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='#F0A070', lw=4, mutation_scale=28))
a2.plot(0, 0, 'o', color='#F0A070', ms=9)
bb = dict(boxstyle='round,pad=0.3', fc=BG, ec='none', alpha=0.95)
a2.text(0, fm*0.97, f'radio = NA/λ\n{coma(r_f, 3)} µm⁻¹  ({r:.0f} px)', ha='center', va='top', fontsize=FS, color=AZ, bbox=bb, linespacing=1.25)
a2.text(0, -fm*0.97, f'corrimiento = k_LED = sinθ/λ\n{coma(k_f, 3)} µm⁻¹  ({k_px:.0f} px)', ha='center', va='bottom', fontsize=FS, color=NA_, bbox=bb, linespacing=1.25)
fmt = FuncFormatter(lambda v, _: coma(v, 1) if abs(v) > 1e-9 else '0')
for ax_ in (a2.xaxis, a2.yaxis): ax_.set_major_formatter(fmt)
a2.set_xticks([-0.2, 0, 0.2]); a2.set_yticks([-0.2, 0, 0.2]); a2.tick_params(labelsize=FS, length=8, width=2)
a2.set_xlabel('frecuencia espacial (µm⁻¹)', fontsize=FS, labelpad=8)

# --- 3: lo que se lee
a3 = fig.add_axes([0.715, 0.0, 0.285, 1.0]); a3.axis('off'); a3.set_xlim(0, 1); a3.set_ylim(0, 1)
a3.text(0.5, 0.905, 'Lo que se lee', ha='center', fontsize=FT, color=T1)
a3.text(0.06, 0.80, 'NA medida = radio · λ', fontsize=FS, color=T2)
a3.text(0.06, 0.645, coma(na, 3), fontsize=84, color=AZ, fontweight='bold')
a3.text(0.06, 0.575, f'con λ = 0,63 µm (nominal);\ncon λ = 0,617 (medida): {coma(na2, 3)}', fontsize=FS, color=T2, va='top', linespacing=1.3)
a3.text(0.06, 0.415, 'sinθ del LED = corrimiento · λ', fontsize=FS, color=T2)
a3.text(0.06, 0.26, coma(st, 3), fontsize=84, color=NA_, fontweight='bold')
a3.text(0.06, 0.19, f'esperado por geometría: {coma(st_esp, 3)}\n(LED a 6 mm del eje, z ≈ 99,5 mm)', fontsize=FS, color=T2, va='top', linespacing=1.3)
fig.text(0.5, 0.012, 'El algoritmo necesita estos dos números: si están mal, las piezas no encajan.', ha='center', fontsize=FS, color=T1, fontweight='bold')
fig.savefig(OUT, dpi=100, facecolor=BG)

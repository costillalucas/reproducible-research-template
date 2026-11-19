"""red500_espectro.py -- 18/11/2026. ¿Reconstruye el FPM la red de 500 l/mm (T nominal 2,0 µm)?

Pico del espectro (ventana Hann) de la amplitud y la fase reconstruidas, en la banda 0,35–0,75 µm⁻¹, para la
reconstrucción completa y las dos mitades (LEDs disjuntos). Control: la imagen cruda de campo claro (LED del eje)
solo muestrea hasta 0,388 µm⁻¹ (Nyquist con 1,29 µm/px) y su corte coherente es NA/λ = 0,119 µm⁻¹.
C3 (lattice_score) cuenta la energía en picos aislados: una red real lo hace fallar; se recalcula sin sus órdenes.
Uso: python3 red500_espectro.py <carpeta de la reconstrucción>
"""
import sys
import numpy as np
from scipy.ndimage import median_filter

D = sys.argv[1] if len(sys.argv) > 1 else '/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-18/red500/recon'
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.43


def esp(a, dx):
    n = a.shape[0]; w = np.outer(np.hanning(n), np.hanning(n))
    F = np.abs(np.fft.fftshift(np.fft.fft2(w * (a - a.mean()))))
    f = np.fft.fftshift(np.fft.fftfreq(n, dx)); FX, FY = np.meshgrid(f, f)
    return F, FX, FY


def pico(F, FX, FY, lo=0.35, hi=0.75):
    fr = np.hypot(FX, FY); m = (fr > lo) & (fr < hi)
    i = np.argmax(np.where(m, F, 0))
    return F.flat[i] / np.median(F[m]), FX.flat[i], FY.flat[i], fr.flat[i]


for nom in ('objeto_complejo.npy', 'objeto_mitadA.npy', 'objeto_mitadB.npy'):
    o = np.load(f'{D}/{nom}')
    for parte, a in (('amplitud', np.abs(o)), ('fase', np.angle(o))):
        q, x, y, r = pico(*esp(a, DX))
        print(f'{nom:22s} {parte:9s} pico/mediana {q:6.1f}  f=({x:+.3f},{y:+.3f}) |f|={r:.3f} µm⁻¹  T={1 / r:.3f} µm')

o = np.load(f'{D}/objeto_complejo.npy'); A = np.abs(o)
P = np.abs(np.fft.fftshift(np.fft.fft2(A - A.mean()))) ** 2
H = P.shape[0]; yy, xx = np.mgrid[:H, :H] - H // 2; df = 1 / (H * DX)
m = np.hypot(yy, xx) > 0.02 * H
peaks = (P > 20 * median_filter(P, size=9)) & m
_, gx, gy, _ = pico(*esp(A, DX))
cerca = np.zeros_like(m)
for k in (1, 2, 3):
    for s in (1, -1):
        cerca |= np.hypot(xx - s * k * gx / df, yy - s * k * gy / df) < 12 * k
tot = P[m].sum()
print(f'C3 original {P[peaks].sum() / tot:.4f};  sin los órdenes de la red (radio 12k px de Fourier): {P[peaks & ~cerca].sum() / tot:.4f}')

"""red500_mitades.py -- 19/11/2026. ¿Las dos mitades (LEDs disjuntos) reconstruyen las MISMAS líneas de la red de 500 l/mm?

No solo el mismo período (eso lo mide red500_espectro.py), sino la misma posición de las líneas:
  1. correlación de Pearson entre las amplitudes de A y B en el zoom central de 100 µm, y la misma correlación
     después de filtrar alrededor de los órdenes ±1 de la red (anillo de radio 0,5 µm⁻¹, ancho ±0,08);
  2. posición de las líneas: se demodula cada amplitud en la frecuencia de la red (una banda lateral, radio
     0,06 µm⁻¹, señal analítica) y se compara la fase local de A y B en la zona central de 344 µm.
     coherencia = |Σ sA·conj(sB)| / Σ|sA·sB|: 1 = líneas en la misma posición en todo el campo (con un corrimiento
     fijo), ~0 = la posición relativa cambia al azar. Se reporta también la Δφ por bloques de 50 µm.
     (Un único Δφ en un bin de la FFT del zoom no sirve: los picos de A y B caen en bins distintos, 0,501 y 0,521.)
Figura: amplitud de A y B en el zoom de 100 µm, mismo rango de grises (percentiles 1–99 de las dos juntas),
y un perfil promedio perpendicular a las líneas.
Uso: python3 red500_mitades.py <carpeta de la reconstrucción> <png de salida>
"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = sys.argv[1] if len(sys.argv) > 1 else '/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-18/red500/recon'
SAL = sys.argv[2] if len(sys.argv) > 2 else 'red500_mitades.png'
DX = 0.43            # µm por píxel reconstruido (resumen.txt)
ZOOM_UM = 100.0

A = np.abs(np.load(f'{D}/objeto_mitadA.npy'))
B = np.abs(np.load(f'{D}/objeto_mitadB.npy'))
n = A.shape[0]; h = int(round(ZOOM_UM / DX / 2)); c = n // 2
a, b = A[c - h:c + h, c - h:c + h], B[c - h:c + h, c - h:c + h]


def espectro(x):
    m = x.shape[0]; w = np.outer(np.hanning(m), np.hanning(m))
    return np.fft.fft2(w * (x - x.mean())), np.fft.fftfreq(m, DX)


FA, f = espectro(a); FB, _ = espectro(b)
FX, FY = np.meshgrid(f, f); fr = np.hypot(FX, FY)
banda = (fr > 0.35) & (fr < 0.75)
i = np.argmax(np.where(banda, np.abs(FA) + np.abs(FB), 0))
gx, gy = FX.flat[i], FY.flat[i]; g = np.hypot(gx, gy); T = 1 / g
anillo = np.abs(fr - g) < 0.08
abp = np.real(np.fft.ifft2(FA * anillo)); bbp = np.real(np.fft.ifft2(FB * anillo))
r_crudo = np.corrcoef(a.ravel(), b.ravel())[0, 1]
r_red = np.corrcoef(abp.ravel(), bbp.ravel())[0, 1]

# fase local de la red en A y B (zona central de 800 px = 344 µm)
fN = np.fft.fftfreq(n, DX); GX, GY = np.meshgrid(fN, fN)
lado = (np.hypot(GX - gx, GY - gy) < 0.06)
sA = np.fft.ifft2(np.fft.fft2(A - A.mean()) * lado)[200:-200, 200:-200]
sB = np.fft.ifft2(np.fft.fft2(B - B.mean()) * lado)[200:-200, 200:-200]
d = sA * np.conj(sB)
coh = np.abs(d.sum()) / np.abs(d).sum()
blq = 116
bloques = [np.degrees(np.angle(d[i:i + blq, j:j + blq].sum()))
           for i in range(0, d.shape[0] - blq + 1, blq) for j in range(0, d.shape[1] - blq + 1, blq)]

print(f'zoom {2 * h} px = {2 * h * DX:.0f} µm;  vector de la red f=({gx:+.3f},{gy:+.3f}) µm⁻¹, T={T:.3f} µm')
print(f'correlación A-B en el zoom: amplitud {r_crudo:+.3f};  filtrada en la frecuencia de la red {r_red:+.3f}')
print(f'coherencia de la posición de las líneas A-B (344 µm): {coh:.2f};  Δφ por bloques de 50 µm: '
      f'{np.min(bloques):+.0f}° a {np.max(bloques):+.0f}° (sd {np.std(bloques):.0f}°)')

# perfil perpendicular a las líneas: proyectar sobre la dirección del vector de la red
yy, xx = (np.mgrid[:2 * h, :2 * h] - h) * DX
s = (xx * gx + yy * gy) / g
bins = np.arange(-15, 15 + 0.1, 0.2)                   # 30 µm de perfil, cada 0,2 µm
k = np.digitize(s.ravel(), bins)
def perfil(x):
    return np.array([x.ravel()[k == j].mean() for j in range(1, len(bins))])
centros = 0.5 * (bins[1:] + bins[:-1])
pa, pb = perfil(a), perfil(b)

lo, hi = np.percentile(np.concatenate([a.ravel(), b.ravel()]), [1, 99])
fig = plt.figure(figsize=(15, 5.6), dpi=150)
gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.25], wspace=0.18)
ext = [0, 2 * h * DX, 2 * h * DX, 0]
for j, (img, tit) in enumerate(((a, 'Mitad A (LEDs pares)'), (b, 'Mitad B (LEDs impares)'))):
    ax = fig.add_subplot(gs[j]); ax.imshow(img, cmap='gray', vmin=lo, vmax=hi, extent=ext)
    ax.set_title(tit, fontsize=14); ax.set_xlabel('µm'); ax.set_ylabel('µm' if j == 0 else '')
ax = fig.add_subplot(gs[2])
ax.plot(centros, pa / pa.mean(), color='#2F6690', lw=2, label='Mitad A')
ax.plot(centros, pb / pb.mean(), color='#E8925E', lw=2, ls='--', label='Mitad B')
ax.set_xlabel('posición perpendicular a las líneas (µm)'); ax.set_ylabel('amplitud / media')
ax.set_title(f'Perfil perpendicular a las líneas (zoom)', fontsize=14)
ax.legend(frameon=False); ax.grid(alpha=0.3)
fig.savefig(SAL, bbox_inches='tight', facecolor='white')
print('figura:', SAL)

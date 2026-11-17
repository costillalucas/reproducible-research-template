"""forma_pupila.py -- 17/11/2026. ¿La pupila es un círculo, y cambia con la posición en el campo?

Para cada toma roja del 13/11 (13 campos) y para la imagen de campo claro del LED del eje (17,15), 18 ms:
  I = (muestra - oscuro) / (flat - oscuro_flat)      (flat = 2026-11-13.fondo, mismo día)
Se parte el ROI de 1120 px en 3x3 teselas de 373 px. En cada tesela:
  F = log|FFT(ventana Hann · (I/mean - 1))|
  perfil polar de F en 36 sectores de 10°; el borde en cada sector = radio de máxima pendiente negativa
  (perfil suavizado, búsqueda entre 0.6 y 1.4 del radio nominal NA/λ)
  ajuste de círculo (centro libre) a los 36 puntos → centro, radio medio, forma r(φ) - r_medio
Se promedia la forma sobre los 13 campos (la muestra cambia, la pupila no).

Control: lo mismo sobre imágenes simuladas con pupila CIRCULAR perfecta (objeto aleatorio débil, ruido
parecido), para saber qué dispersión de r(φ) da el método solo. Si la forma real supera al control y tiene
un patrón que depende de la tesela (achatamiento orientado respecto del centro del campo), la pupila no es
un círculo fijo.
"""
import glob
import json
import os

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter1d, map_coordinates

I_DIR = '/home/chanoscopio/Documents/AleYLu/imagenes_tomadas'
OUT = os.path.dirname(os.path.abspath(__file__))
CAMPOS = ['2026-11-13', '2026-11-13.a'] + [f'2026-11-13.med{i}' for i in range(1, 12)] + ['2026-11-13.zonarojo']
LED, T = 'fila17_col15_colorr', '18ms'
DX, LAM, NA = 1.29, 0.63, 0.070
NT = 3
NS = 36


def leer(carpeta):
    fs = sorted(glob.glob(f'{carpeta}/{LED}/{T}/*.tif*'))
    return np.mean([tifffile.imread(f).astype(np.float64) for f in fs], axis=0)


def imagen(campo):
    s = leer(f'{I_DIR}/{campo}') - leer(f'{I_DIR}/{campo}-dark')
    f = leer(f'{I_DIR}/2026-11-13.fondo') - leer(f'{I_DIR}/2026-11-13.fondo-dark')
    return s / np.maximum(f, 1.0)


def borde_tesela(t):
    n = t.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    F = np.log(np.abs(np.fft.fftshift(np.fft.fft2(w * (t / t.mean() - 1)))) + 1e-9)
    r0 = NA / LAM * n * DX                       # radio nominal en px de Fourier
    rr = np.arange(0.6 * r0, 1.4 * r0, 0.25)
    c = n // 2
    radios = []
    for k in range(NS):
        phis = np.deg2rad(k * 360 / NS + np.linspace(-4, 4, 9))
        prof = np.mean([map_coordinates(F, [c + rr * np.sin(p), c + rr * np.cos(p)], order=1) for p in phis], axis=0)
        d = np.gradient(gaussian_filter1d(prof, 4))
        radios.append(rr[np.argmin(d)])
    return np.array(radios), r0


def ajustar_circulo(r, phi):
    x, y = r * np.cos(phi), r * np.sin(phi)
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    (a, b, cc), *_ = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)
    R = np.sqrt(cc + a ** 2 + b ** 2)
    rc = np.hypot(x - a, y - b)                  # radio respecto del centro ajustado
    ang = np.arctan2(y - b, x - a)
    o = np.argsort(ang)
    return a, b, R, ang[o], rc[o] - R


def analizar(img):
    n = img.shape[0] // NT
    phi = np.deg2rad(np.arange(NS) * 360 / NS)
    res = {}
    for i in range(NT):
        for j in range(NT):
            r, r0 = borde_tesela(img[i * n:(i + 1) * n, j * n:(j + 1) * n])
            a, b, R, ang, forma = ajustar_circulo(r, phi)
            res[(i, j)] = dict(cx=a, cy=b, R=R, r0=r0, forma=np.interp(phi - np.pi, ang, forma, period=2 * np.pi))
    return res


def simular(semilla, n=1120):
    """Objeto débil aleatorio (fase + amplitud, manchas de ~5 µm), imagen coherente con pupila circular dura."""
    g = np.random.default_rng(semilla)
    k = np.fft.fftfreq(n, DX)
    KX, KY = np.meshgrid(k, k)
    ruido = g.normal(size=(n, n)) + 1j * g.normal(size=(n, n))
    filt = np.exp(-(KX ** 2 + KY ** 2) * (5.0 ** 2))
    o = np.fft.ifft2(np.fft.fft2(ruido) * filt)
    o = 0.3 * o / np.abs(o).std()
    campo = np.exp(1j * o.real) * (1 - 0.3 * np.abs(o.imag))
    P = (np.hypot(KX, KY) <= NA / LAM)
    I = np.abs(np.fft.ifft2(np.fft.fft2(campo) * P)) ** 2
    I = I / I.mean() * 2000
    return g.poisson(np.clip(I, 0, None)).astype(float) / 2000


if __name__ == '__main__':
    reales = {}
    for c in CAMPOS:
        reales[c] = analizar(imagen(c))
        print(c, ' '.join(f"{reales[c][(i, j)]['R']:.1f}" for i in range(NT) for j in range(NT)), flush=True)
    sims = [analizar(simular(s)) for s in range(len(CAMPOS))]
    print('sim', ' '.join(f"{sims[0][(i, j)]['R']:.1f}" for i in range(NT) for j in range(NT)))

    def resumen(lista):
        out = {}
        for i in range(NT):
            for j in range(NT):
                F = np.array([d[(i, j)]['forma'] for d in lista])
                out[f'{i}{j}'] = dict(
                    R=float(np.mean([d[(i, j)]['R'] for d in lista])),
                    R_sd=float(np.std([d[(i, j)]['R'] for d in lista])),
                    cx=float(np.mean([d[(i, j)]['cx'] for d in lista])),
                    cy=float(np.mean([d[(i, j)]['cy'] for d in lista])),
                    forma_media=F.mean(0).tolist(),
                    forma_rms_media=float(np.sqrt((F.mean(0) ** 2).mean())),
                    forma_sem=float(F.std(0).mean() / np.sqrt(len(lista))),
                    r0=float(lista[0][(i, j)]['r0']))
        return out

    R_real, R_sim = resumen(list(reales.values())), resumen(sims)
    json.dump(dict(real=R_real, sim=R_sim, campos=CAMPOS), open(f'{OUT}/forma_pupila.json', 'w'), indent=1)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    phi = np.deg2rad(np.arange(NS) * 360 / NS) - np.pi
    fig, ax = plt.subplots(NT, NT, figsize=(12, 12), subplot_kw=dict(projection='polar'))
    for i in range(NT):
        for j in range(NT):
            a = ax[i, j]
            for d in reales.values():
                f = d[(i, j)]
                a.plot(np.r_[phi, phi[0]], np.r_[f['R'] + f['forma'], f['R'] + f['forma'][0]], color='0.8', lw=0.6)
            m = R_real[f'{i}{j}']
            a.plot(np.r_[phi, phi[0]], np.r_[m['R'] + np.array(m['forma_media']), m['R'] + m['forma_media'][0]], color='C3', lw=2)
            s = R_sim[f'{i}{j}']
            a.plot(np.r_[phi, phi[0]], np.r_[s['R'] + np.array(s['forma_media']), s['R'] + s['forma_media'][0]], color='C0', lw=1.5, ls='--')
            a.set_ylim(m['R'] - 8, m['R'] + 6)
            a.set_yticklabels([])
            a.set_title(f"tesela ({i},{j})  R={m['R']:.1f}±{m['R_sd']:.1f}\nforma rms real {m['forma_rms_media']:.2f} / sim {s['forma_rms_media']:.2f} px", fontsize=9)
    fig.suptitle('Contorno del disco BF (LED eje, 18 ms) por tesela: gris = cada campo, rojo = media real (13), azul = media simulada (pupila circular)')
    fig.savefig(f'{OUT}/forma_pupila.png', dpi=110, bbox_inches='tight')
    print('ok')

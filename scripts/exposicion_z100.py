"""Mapa de exposición por LED para la próxima captura: matriz a 100 mm, 15x15 LEDs (filas 11-25, columnas 8-22),
rojo/verde/azul, a partir de la captura del 2026-09-28 (74 mm, 13x13, foco en verde).

Mismo criterio que el script del laboratorio (calcular_por_led.py): tiempo con el que el percentil 99.9 de la foto
cruda llega a 4000 cuentas; después, el mayor tiempo permitido que no lo supera.
1. De la captura del 28/09, por color y LED: tasa = percentil 99.9 de (foto - oscuro) / t, en cuentas/ms, en función
   de sen(theta) de iluminación (z = 74 mm, eje en fila 17.5, columna 15). Los LEDs con píxeles saturados dan solo
   una cota inferior: se usa max(tasa, (4095 - oscuro)/t) * 1.3.
2. A 100 mm, cada LED tiene otro sen(theta). Al mismo ángulo llega (74/100)^2 de la luz (la distancia LED-muestra es
   z/cos(theta)). La tasa se interpola (en log) en la curva medida, envolvente superior (conservadora).
3. LEDs con sen(theta) < NA + 0.015 (campo claro o su borde): se les asigna la tasa de campo claro medida.
Escribe results/exposicion_2026-09-28_z100/tiempos_exposicion_<color>_z100.csv (Fila, Columna, Tiempo_Optimo_ms,
Tiempo_ms, Tasa_predicha, sen_theta) y un mapa por color.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
import tifffile as T

B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(ROOT, 'results', 'exposicion_2026-09-28_z100')
os.makedirs(OUT, exist_ok=True)
C = slice(360, 760)
PITCH, NA, TARGET = 6.0, 0.07, 4000.0
Z_NUEVO = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0   # mm; medido por Lucas: ~98 +- 2
PERMITIDOS = [4, 8, 16, 32, 64, 128, 250]           # los que usó el programa el 25/09 (máximo 250 ms)
DARK = {t: T.imread(f'{B}/2026-09-25_red_enfocado_dark/organizado/red/{t}ms_recortada_400/fila18_col15.tiff').astype(float)
        for t in (8, 32, 64, 128, 250)}
DARK_LEVEL = float(np.median(DARK[8]))


def sen_theta(r, c, z):
    dx, dy = (c - 15.0) * PITCH, (r - 17.5) * PITCH
    rho = np.hypot(dx, dy)
    return rho / np.hypot(rho, z)


resumen = []
for col, ch in (('red', 'r'), ('green', 'g'), ('blue', 'b')):
    s, rate, bf = [], [], []
    for d in glob.glob(f'{B}/2026-09-28_rgb_enfocado/fila*_col*_color{ch}'):
        r, c = (int(v) for v in os.path.basename(d)[4:].split(f'_color{ch}')[0].split('_col'))
        td = glob.glob(d + '/*ms')[0]; t = int(os.path.basename(td)[:-2])
        a, b = (T.imread(f)[C, C].astype(float) for f in sorted(glob.glob(td + '/imagen_frame_*.tiff')))
        m = (a + b) / 2
        q = (np.percentile(m, 99.9) - np.median(DARK[t])) / t
        if (a >= 4095).any() or (b >= 4095).any():
            q = max(q, (4095 - DARK_LEVEL) / t) * 1.3
        st = sen_theta(r, c, 74.0)
        s.append(st); rate.append(max(q, 1e-4)); bf.append(st < NA)
    s, rate, bf = np.array(s), np.array(rate), np.array(bf)
    tasa_bf = float(rate[bf].max())
    # envolvente superior en bins de sen(theta) (DF), interpolada en log
    edges = np.linspace(NA, s.max() + 1e-6, 14)
    xc, yc = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (s >= lo) & (s < hi) & ~bf
        if k.sum():
            xc.append(s[k].mean()); yc.append(np.log(np.percentile(rate[k], 90)))
    filas = []
    for r in range(11, 26):
        for c in range(8, 23):
            st = sen_theta(r, c, Z_NUEVO)
            if st < NA + 0.015:
                tasa = tasa_bf                      # campo claro o su borde: conservador
            else:
                tasa = float(np.exp(np.interp(st, xc, yc))) * (74.0 / Z_NUEVO) ** 2
            t_opt = (TARGET - DARK_LEVEL) / tasa
            t_sel = max([p for p in PERMITIDOS if p <= t_opt] or [PERMITIDOS[0]])
            filas.append(dict(Fila=r, Columna=c, Tiempo_Optimo_ms=round(t_opt, 2), Tiempo_ms=t_sel,
                              Tasa_predicha=round(tasa, 5), sen_theta=round(st, 4)))
    df = pd.DataFrame(filas)
    df.to_csv(os.path.join(OUT, f'tiempos_exposicion_{col}_z{Z_NUEVO:g}.csv'), index=False)
    cnt = df['Tiempo_ms'].value_counts().sort_index().to_dict()
    lim = int((df['Tiempo_Optimo_ms'] > 250).sum())
    resumen.append((col, cnt, lim, tasa_bf))
    print(f'{col}: LEDs por tiempo {cnt}; {lim} de 225 querrían más de 250 ms; tasa campo claro {tasa_bf:.1f} cuentas/ms')

import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
for a, (col, *_) in zip(ax, resumen):
    df = pd.read_csv(os.path.join(OUT, f'tiempos_exposicion_{col}_z{Z_NUEVO:g}.csv'))
    M = df.pivot(index='Fila', columns='Columna', values='Tiempo_ms')
    im = a.imshow(np.log2(M.values), cmap='viridis', extent=[7.5, 22.5, 25.5, 10.5])
    for (rr, cc), v in np.ndenumerate(M.values):
        a.text(M.columns[cc], M.index[rr], int(v), ha='center', va='center', fontsize=6, color='w')
    a.set_title(f'{col}: tiempo por LED (ms), z = {Z_NUEVO:g} mm'); a.set_xlabel('columna'); a.set_ylabel('fila')
plt.tight_layout(); plt.savefig(os.path.join(OUT, f'mapas_exposicion_z{Z_NUEVO:g}.png'), dpi=90)
print('CSV y mapa en', OUT)

#!/usr/bin/env python3
"""comparar.py -- ¿qué época de una reconstrucción es la mejor? Lee los snapshots que deja ./reconstruir.sh.

Uso (lo llama ./comparar.sh):
    python3 scripts/comparar.py                         la reconstrucción más reciente
    python3 scripts/comparar.py 2026-10-21.d_1655       una (nombre en ~/Documents/AleYLu/reconstrucciones, o ruta)
    python3 scripts/comparar.py A B C                   varias, superpuestas (p. ej. distintos recortes o muestras)

Necesita una reconstrucción corrida con --validar y --guardar-cada N (si no, solo hay el valor final).

Qué mide, por época:
  * C1 = R held-out: cuánto se equivoca el objeto de cada mitad de LEDs al predecir las imágenes de la OTRA mitad
    (anillos < 7). Más bajo = mejor. Es el criterio para elegir la época: el mínimo es la mejor; si después sube,
    hay sobreajuste (el solver empieza a ajustar ruido).
  * acuerdo entre mitades: correlación de la amplitud de las dos mitades (suavizada 1 px). Más alto = mejor: lo que
    aparece en las dos es estructura real; lo que aparece en una sola es ruido.
  * R de ajuste (todos los LEDs usados): siempre baja con más épocas; se muestra para ver que NO sirve para elegir.
Diferencias de C1 menores a 0.005 se consideran empate: entonces conviene la época más corta.
"""
import csv
import glob
import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BASE = os.path.expanduser('~/Documents/AleYLu/reconstrucciones')
EMPATE = 0.005        # diferencias de C1 menores se consideran ruido de la medición
UMBRAL_C1 = 0.895     # C1 pasa si R held-out <= este valor (ver resumen.txt)
# paleta categórica (orden fijo, una por reconstrucción) y tintas
COLORES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
TINTA, TINTA2, GRILLA = '#0b0b0b', '#52514e', '#e4e3df'


def leer_csv(path):
    if not os.path.isfile(path):
        return {}
    with open(path) as f:
        return {int(r['epoca']): r for r in csv.DictReader(f)}


def acuerdo(a, b):
    """Correlación de amplitud entre las dos mitades, suavizada 1 px y sin el 5 % del borde."""
    from scipy import ndimage as ndi
    x, y = (ndi.gaussian_filter(np.abs(np.load(p)).astype(np.float64), 1.0) for p in (a, b))
    m = int(0.05 * x.shape[0])
    x, y = x[m:-m, m:-m].ravel(), y[m:-m, m:-m].ravel()
    x, y = x - x.mean(), y - y.mean()
    return float((x @ y) / np.sqrt((x @ x) * (y @ y)))


def cargar(carpeta):
    snap = os.path.join(carpeta, 'snapshots')
    m0, m1 = leer_csv(os.path.join(snap, 'metricas_mitad0.csv')), leer_csv(os.path.join(snap, 'metricas_mitad1.csv'))
    full = leer_csv(os.path.join(snap, 'metricas_full.csv'))
    eps = sorted(set(m0) & set(m1))
    d = {'nombre': os.path.basename(carpeta.rstrip('/')), 'carpeta': carpeta, 'eps': eps,
         'c1a': np.array([float(m0[e]['R_heldout_C1']) for e in eps]),
         'c1b': np.array([float(m1[e]['R_heldout_C1']) for e in eps]),
         'eps_full': sorted(full), 'r_ajuste': np.array([float(full[e]['R_ajuste']) for e in sorted(full)])}
    d['c1'] = (d['c1a'] + d['c1b']) / 2
    acu = []
    for e in eps:
        a = os.path.join(snap, f'objeto_mitad0_e{e:03d}.npy'); b = os.path.join(snap, f'objeto_mitad1_e{e:03d}.npy')
        acu.append(acuerdo(a, b) if os.path.isfile(a) and os.path.isfile(b) else np.nan)
    d['acuerdo'] = np.array(acu)
    return d


def veredicto(d):
    c1, eps = d['c1'], d['eps']
    i = int(np.argmin(c1)); mejor, emin = float(c1[i]), eps[i]
    j = next(k for k in range(len(eps)) if c1[k] <= mejor + EMPATE)
    ult = float(c1[-1])
    L = [f'== {d["nombre"]}  ({len(eps)} épocas guardadas, de {eps[0]} a {eps[-1]})',
         f'   C1 mínimo: {mejor:.4f} en la época {emin}  (mitades {d["c1a"][i]:.4f} / {d["c1b"][i]:.4f})'
         + ('  -> PASA' if mejor <= UMBRAL_C1 else f'  -> NO PASA (pide <= {UMBRAL_C1})'),
         f'   C1 en la última época ({eps[-1]}): {ult:.4f}']
    if ult - mejor > EMPATE:
        L.append(f'   SOBREAJUSTE: después de la época {emin} el C1 sube {ult - mejor:+.4f}. '
                 f'Usar el objeto de la época {emin} (snapshots/objeto_full_e{emin:03d}.npy).')
    else:
        L.append(f'   Sin sobreajuste: la última época está a menos de {EMPATE} del mínimo.')
    if eps[j] < emin:
        L.append(f'   Desde la época {eps[j]} el C1 ya está a menos de {EMPATE} del mínimo (empate): '
                 f'con ~{eps[j]} épocas alcanza; más épocas no mejoran de forma medible.')
    if np.isfinite(d['acuerdo']).any():
        k = int(np.nanargmax(d['acuerdo']))
        L.append(f'   Acuerdo entre mitades: máximo {d["acuerdo"][k]:.3f} en la época {eps[k]}; '
                 f'en la mejor época por C1, {d["acuerdo"][i]:.3f}.')
    return '\n'.join(L), emin


def ejes(a, titulo, ylabel):
    a.set_title(titulo, fontsize=11, color=TINTA, loc='left')
    a.set_ylabel(ylabel, color=TINTA2, fontsize=9)
    a.grid(True, color=GRILLA, lw=0.8); a.set_axisbelow(True)
    for s in ('top', 'right'):
        a.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        a.spines[s].set_color('#b5b4ad')
    a.tick_params(colors=TINTA2, labelsize=9)


def main():
    args = sys.argv[1:]
    if not args:
        cands = [d for d in sorted(glob.glob(os.path.join(BASE, '*/')), key=os.path.getmtime, reverse=True)
                 if os.path.isdir(os.path.join(d, 'snapshots'))]
        if not cands:
            sys.exit(f'No hay reconstrucciones con snapshots en {BASE}. Correr ./reconstruir.sh con --validar --guardar-cada 10.')
        args = [cands[0]]
    carpetas = [a if os.path.isdir(a) else os.path.join(BASE, a) for a in args]
    datos = []
    for c in carpetas:
        if not os.path.isdir(c):
            print(f'  [AVISO] no existe {c}'); continue
        d = cargar(c)
        if len(d['eps']) < 2:
            print(f'  [AVISO] {d["nombre"]}: no tiene métricas por época de las mitades. '
                  f'Correr con --validar --guardar-cada 10 (o 20).'); continue
        datos.append(d)
    if not datos:
        sys.exit(1)

    fig, ax = plt.subplots(3, 1, figsize=(9, 10.5), sharex=True, gridspec_kw={'height_ratios': [1.4, 1, 1]})
    fig.patch.set_facecolor('#fcfcfb')
    ejes(ax[0], 'C1 (R held-out): más bajo es mejor; el mínimo marca la mejor época', 'R held-out')
    ejes(ax[1], 'Acuerdo entre mitades: más alto es mejor', 'correlación de amplitud')
    if not any(np.isfinite(d['acuerdo']).any() for d in datos):
        ax[1].text(0.5, 0.5, 'sin objetos por época: correr ./reconstruir.sh con --guardar-objetos para ver este panel',
                   transform=ax[1].transAxes, ha='center', va='center', fontsize=9, color=TINTA2)
    ejes(ax[2], 'R de ajuste: siempre baja, no sirve para elegir la época', 'R de ajuste')
    ax[2].set_xlabel('época', color=TINTA2, fontsize=9)
    ax[0].axhline(UMBRAL_C1, color=TINTA2, lw=1, ls='--')
    ax[0].text(0.995, UMBRAL_C1, f'umbral C1 {UMBRAL_C1}', transform=ax[0].get_yaxis_transform(), ha='right',
               va='bottom', fontsize=8, color=TINTA2)
    print()
    for n, d in enumerate(datos):
        col = COLORES[n % len(COLORES)]
        texto, emin = veredicto(d)
        print(texto + '\n')
        eps = np.array(d['eps'])
        ax[0].fill_between(eps, np.minimum(d['c1a'], d['c1b']), np.maximum(d['c1a'], d['c1b']), color=col, alpha=0.15, lw=0)
        ax[0].plot(eps, d['c1'], '-o', color=col, lw=2, ms=4, label=d['nombre'])
        i = d['eps'].index(emin)
        ax[0].plot([emin], [d['c1'][i]], 'o', ms=10, mfc='none', mec=col, mew=2)
        ax[0].annotate(f'mejor: época {emin}\nC1 {d["c1"][i]:.3f}', (emin, d['c1'][i]), xytext=(8, -26),
                       textcoords='offset points', fontsize=8, color=TINTA)
        ax[1].plot(eps, d['acuerdo'], '-o', color=col, lw=2, ms=4)
        if len(d['eps_full']):
            ax[2].plot(d['eps_full'], d['r_ajuste'], '-o', color=col, lw=2, ms=4)
    if len(datos) > 1:
        ax[0].legend(fontsize=8, frameon=False)
    else:
        ax[0].text(0.99, 0.03, 'banda = las dos mitades; línea = su promedio', transform=ax[0].transAxes,
                   fontsize=8, color=TINTA2, va='bottom', ha='right')
    fig.suptitle('Comparación por época: ' + ', '.join(d['nombre'] for d in datos), fontsize=12, color=TINTA, x=0.01, ha='left')
    fig.tight_layout()
    out = (os.path.join(datos[0]['carpeta'], 'comparacion.png') if len(datos) == 1
           else os.path.join(BASE, time.strftime('comparacion_%Y%m%d_%H%M.png')))
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    print(f'  figura: {out}')


if __name__ == '__main__':
    main()

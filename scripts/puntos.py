#!/usr/bin/env python3
"""puntos.py -- ¿los puntos finos de una reconstrucción son reales? Los busca en las dos mitades de LEDs.

Uso (lo llama ./puntos.sh):
    python3 scripts/puntos.py                          la reconstrucción más reciente con mitades
    python3 scripts/puntos.py 2026-10-21.d_1655        una (nombre en ~/Documents/AleYLu/reconstrucciones, o ruta)
    python3 scripts/puntos.py <rec> --epoca 10         usa los snapshots de esa época (si se guardaron)
    python3 scripts/puntos.py <rec> --umbral 4         sensibilidad de la detección (def. 4 desvíos robustos)

Necesita una reconstrucción corrida con --validar (objeto_mitadA.npy y objeto_mitadB.npy, o sus snapshots).

Qué hace, por separado en amplitud y en fase relativa:
  1. Saca el fondo lento (resta un suavizado de ~4 µm) y detecta en la reconstrucción COMPLETA los puntos que se
     apartan del fondo más de --umbral desvíos robustos (MAD), separados al menos 2 µm.
  2. Para cada punto mira las dos mitades (cada una reconstruida con la mitad de los LEDs, sin ver la otra): ¿hay ahí,
     a menos de 0.9 µm, un apartamiento del mismo signo que supere el mismo umbral en esa mitad?
       en las dos mitades -> probablemente real;   en una sola -> dudoso;   en ninguna -> probablemente ruido.
  3. Azar: repite la prueba en posiciones al azar. La fracción de "en las dos" al azar es lo que se espera sin
     estructura real; un punto vale si la fracción medida la supera claramente.
  OJO: "en las dos mitades" descarta el ruido de fotones, pero no lo que es común a las dos (errores del flat, polvo,
  patrón fijo del sensor, artefactos del modelo). Es una condición necesaria para que un punto sea real, no suficiente.
  Tampoco mide su tamaño: el ancho de puntos elegidos por ser máximos sale angosto aunque sean ruido.
Salida: puntos_<amplitud|fase>[_eNNN].png en la carpeta de la reconstrucción y un resumen por pantalla.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from scipy import ndimage as ndi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BASE = os.path.expanduser('~/Documents/AleYLu/reconstrucciones')
FONDO_UM = 4.0       # escala del fondo que se resta
SEP_UM = 2.0         # separación mínima entre puntos
BUSQ_UM = 0.9        # radio de búsqueda en las mitades
AZUL, NARANJA, GRIS = '#2a78d6', '#eb6834', '#9a9890'


def rel_phase(o, sig=20):
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return np.angle(o * np.exp(-1j * np.angle(sm)))


def detalle(img, px):
    """Imagen menos su fondo lento, en unidades de desvío robusto (MAD) y sin el 5 % del borde."""
    d = img - ndi.gaussian_filter(img, FONDO_UM / px)
    m = int(0.05 * d.shape[0])
    core = d[m:-m, m:-m]
    mad = 1.4826 * np.median(np.abs(core - np.median(core)))
    z = (d - np.median(core)) / max(mad, 1e-12)
    z[:m] = z[-m:] = 0; z[:, :m] = z[:, -m:] = 0
    return z


def detectar(z, umbral, px):
    r = max(1, int(round(SEP_UM / px / 2)))
    a = np.abs(z)
    picos = (a == ndi.maximum_filter(a, size=2 * r + 1)) & (a > umbral)
    ys, xs = np.nonzero(picos)
    return np.stack([ys, xs], 1), np.sign(z[ys, xs])


def presente(z, pts, signos, umbral, px):
    """¿Hay en z, cerca de cada punto, un apartamiento del mismo signo mayor que el umbral?"""
    r = max(1, int(round(BUSQ_UM / px)))
    mx, mn = ndi.maximum_filter(z, size=2 * r + 1), ndi.minimum_filter(z, size=2 * r + 1)
    y, x = pts[:, 0], pts[:, 1]
    return np.where(signos > 0, mx[y, x] > umbral, mn[y, x] < -umbral)


def fwhm_promedio(z, pts, signos, px, rad=12):
    """FWHM [µm] del perfil radial promedio de los puntos (cada uno con su signo, normalizado a su pico)."""
    if len(pts) == 0:
        return float('nan')
    acc = np.zeros((2 * rad + 1, 2 * rad + 1)); n = 0
    for (y, x), s in zip(pts, signos):
        if rad <= y < z.shape[0] - rad and rad <= x < z.shape[1] - rad:
            w = s * z[y - rad:y + rad + 1, x - rad:x + rad + 1]
            acc += w / max(w[rad, rad], 1e-12); n += 1
    if n == 0:
        return float('nan')
    acc /= n
    yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    rr = np.hypot(yy, xx).round().astype(int)
    prof = np.array([acc[rr == k].mean() for k in range(rad + 1)])
    prof = (prof - prof[-3:].mean()) / (prof[0] - prof[-3:].mean())
    k = np.argmax(prof < 0.5)
    if k == 0:
        return float('nan')
    r_half = (k - 1) + (prof[k - 1] - 0.5) / (prof[k - 1] - prof[k])
    return float(2 * r_half * px)


def cargar(carpeta, epoca):
    if epoca is None:
        rutas = [os.path.join(carpeta, f) for f in ('objeto_complejo.npy', 'objeto_mitadA.npy', 'objeto_mitadB.npy')]
    else:
        rutas = [os.path.join(carpeta, 'snapshots', f'objeto_{t}_e{epoca:03d}.npy') for t in ('full', 'mitad0', 'mitad1')]
    falta = [r for r in rutas if not os.path.isfile(r)]
    if falta:
        sys.exit('Faltan ' + ', '.join(os.path.basename(f) for f in falta) + '. La reconstrucción tiene que correrse con '
                 '--validar' + ('' if epoca is None else f' y --guardar-cada que incluya la época {epoca}') + '.')
    return [np.load(r) for r in rutas]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rec', nargs='?')
    ap.add_argument('--epoca', type=int, default=None)
    ap.add_argument('--umbral', type=float, default=4.0)
    a = ap.parse_args()
    if a.rec is None:
        cands = [d for d in sorted(glob.glob(os.path.join(BASE, '*/')), key=os.path.getmtime, reverse=True)
                 if os.path.isfile(os.path.join(d, 'objeto_mitadA.npy'))]
        if not cands:
            sys.exit(f'No hay reconstrucciones con mitades en {BASE}: correr ./reconstruir.sh con --validar.')
        a.rec = cands[0]
    carpeta = a.rec if os.path.isdir(a.rec) else os.path.join(BASE, a.rec)
    try:
        px = float(json.load(open(os.path.join(carpeta, 'datos', 'metricas.json')))['hrpx'])
    except (OSError, KeyError, ValueError):
        px = 0.43
    full, ha, hb = cargar(carpeta, a.epoca)
    nombre = os.path.basename(carpeta.rstrip('/')) + ('' if a.epoca is None else f', época {a.epoca}')
    rng = np.random.default_rng(0)
    print(f'\n== Puntos en {nombre}  (píxel {px:.2f} µm, umbral {a.umbral:g} desvíos robustos)')
    for tipo, f in (('amplitud', np.abs), ('fase', rel_phase)):
        z, za, zb = (detalle(f(o).astype(np.float64), px) for o in (full, ha, hb))
        pts, sg = detectar(z, a.umbral, px)
        if len(pts) == 0:
            print(f'   {tipo}: ningún punto supera el umbral.'); continue
        ea, eb = presente(za, pts, sg, a.umbral, px), presente(zb, pts, sg, a.umbral, px)
        dos, una = ea & eb, ea ^ eb
        # azar: mismas pruebas en posiciones al azar dentro del área útil, con signos al azar
        m = int(0.05 * z.shape[0])
        rnd = np.stack([rng.integers(m, z.shape[0] - m, 4000), rng.integers(m, z.shape[1] - m, 4000)], 1)
        rs = rng.choice([-1.0, 1.0], 4000)
        azar = float(np.mean(presente(za, rnd, rs, a.umbral, px) & presente(zb, rnd, rs, a.umbral, px)))
        print(f'   {tipo}: {len(pts)} puntos.  En las dos mitades: {dos.sum()} ({100 * dos.mean():.0f} %, al azar '
              f'{100 * azar:.0f} %);  en una sola: {una.sum()} ({100 * una.mean():.0f} %);  en ninguna: '
              f'{(~ea & ~eb).sum()} ({100 * np.mean(~ea & ~eb):.0f} %).')
        if dos.mean() > 2 * azar and dos.sum() >= 5:
            print('      -> hay estructura reproducible: los puntos "en las dos" superan claramente al azar. Eso descarta el '
                  'ruido de fotones en ellos, no los errores comunes a las dos mitades (flat, polvo, sensor, modelo).')
        else:
            print('      -> los puntos "en las dos" no superan claramente al azar: no se puede afirmar que sean reales.')
        # figura: la imagen con los puntos marcados, entera y zoom de 100 µm al centro
        img = f(full)
        # zoom de 100 µm al centro: a la izquierda la imagen sola, a la derecha con los puntos marcados
        fig, ax = plt.subplots(1, 2, figsize=(16, 9.2))
        fig.patch.set_facecolor('#fcfcfb')
        n = img.shape[0]; zw = int(round(100 / px / 2)); c = n // 2; sl = slice(c - zw, c + zw)
        lo, hi = np.percentile(img[m:-m, m:-m], [1, 99])
        sel = (pts[:, 0] >= sl.start) & (pts[:, 0] < sl.stop) & (pts[:, 1] >= sl.start) & (pts[:, 1] < sl.stop)
        for k in (0, 1):
            ax[k].imshow(img[sl, sl], cmap='gray', vmin=lo, vmax=hi); ax[k].set_xticks([]); ax[k].set_yticks([])
        ax[0].set_title(f'{tipo}, zoom de 100 µm al centro del recorte', fontsize=11, loc='left')
        ax[1].set_title('los mismos puntos, marcados según las mitades', fontsize=11, loc='left')
        for msk, col, mk, lab in ((sel & ~ea & ~eb, GRIS, 'x', 'en ninguna mitad: probablemente ruido'),
                                  (sel & una, NARANJA, 's', 'en una sola mitad: dudoso'),
                                  (sel & dos, AZUL, 'o', 'en las dos mitades: reproducible')):
            ax[1].plot(pts[msk, 1] - sl.start, pts[msk, 0] - sl.start, mk, mfc='none', mec=col, mew=1.6, ms=13, ls='none',
                       label=f'{lab} ({msk.sum()} en el zoom)')
        fig.legend(*ax[1].get_legend_handles_labels(), loc='lower center', ncol=3, fontsize=10, frameon=False)
        fig.suptitle(f'Puntos en {tipo} — {nombre}: {100 * dos.mean():.0f} % en las dos mitades en todo el recorte '
                     f'(al azar {100 * azar:.0f} %)', fontsize=13, x=0.01, ha='left')
        fig.tight_layout(rect=(0, 0.05, 1, 0.95))
        out = os.path.join(carpeta, f'puntos_{tipo}' + ('' if a.epoca is None else f'_e{a.epoca:03d}') + '.png')
        fig.savefig(out, dpi=90, facecolor=fig.get_facecolor()); plt.close(fig)
        print(f'      figura: {out}')
    print()


if __name__ == '__main__':
    main()

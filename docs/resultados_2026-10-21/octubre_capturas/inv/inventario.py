"""inventario.py -- lee un set crudo (fila*_col*_colorX/<t>ms/imagen_frame_{1,2}.tiff) y guarda estadísticas por LED.

Uso: python3 inventario.py NOMBRE_SET
Salida: inv/<set>.npz con keys, t, y por LED: media de los 2 frames (recorte central 400 = [360:760]) submuestreada 4x
(100x100, float32), media/mediana/máx en el recorte, nº saturados (4095) en el frame completo y en el recorte, ruido de
la diferencia de frames (MAD) en el recorte; además el frame completo (1120²) medio de las LEDs de exposición mínima.
"""
import glob
import os
import sys

import numpy as np
import tifffile as T

B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]
d = f'{B}/{name}'
C = slice(360, 760)
dirs = sorted(glob.glob(f'{d}/fila*_col*_color*'))
keys, ts, cols, sm, smean, smed, smax, nsat_full, nsat_c, noise, nfr = [], [], [], [], [], [], [], [], [], [], []
full = {}
for x in dirs:
    b = os.path.basename(x)
    import re
    r, c, col = re.match(r'fila(\d+)_col(\d+)_color(\w+)', b).groups()
    for td in sorted(glob.glob(x + '/*ms')):
        t = int(os.path.basename(td)[:-2])
        fs = sorted(glob.glob(td + '/imagen_frame_*.tiff'))
        fr = [T.imread(f).astype(np.float32) for f in fs]
        m = np.mean(fr, 0)
        mc = m[C, C]
        keys.append((int(r), int(c))); ts.append(t); cols.append(col); nfr.append(len(fr))
        sm.append(mc.reshape(100, 4, 100, 4).mean((1, 3)))
        smean.append(mc.mean()); smed.append(np.median(mc)); smax.append(max(f[C, C].max() for f in fr))
        nsat_full.append(int(sum((f >= 4095).sum() for f in fr))); nsat_c.append(int(sum((f[C, C] >= 4095).sum() for f in fr)))
        if len(fr) == 2:
            dd = fr[0][C, C] - fr[1][C, C]
            noise.append(1.4826 * np.median(np.abs(dd - np.median(dd))) / np.sqrt(2))
        else:
            noise.append(np.nan)
        if (int(r), int(c)) in [(17, 15), (18, 15), (17, 14), (17, 16), (18, 14), (18, 16)]:
            full[f'{r}_{c}_{t}'] = m
np.savez_compressed(f'{HERE}/{name}.npz', keys=np.array(keys), t=np.array(ts), color=np.array(cols), nfr=np.array(nfr),
                    sm=np.array(sm, np.float32), mean=np.array(smean), med=np.array(smed), max=np.array(smax),
                    nsat_full=np.array(nsat_full), nsat_c=np.array(nsat_c), noise=np.array(noise),
                    **{f'full_{k}': v.astype(np.float32) for k, v in full.items()})
print(name, len(keys), 'entradas', flush=True)

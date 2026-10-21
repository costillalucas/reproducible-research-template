"""capas.py -- ¿hay estructura fuera de foco? Mapa de correlación cruzada normalizada entre pasa-altos (σ 10 px) de los BF
(17,15) y (18,15) (Δ 6 mm en filas -> corrimiento de una capa a Δz: Δz·(6/102)/1.29 px a lo largo de filas) y entre (17,14),(17,16)
(Δ 12 mm en columnas). Lista los 4 picos principales (fuera de ±2 px de otro pico) y su Δz equivalente. Escribe capas.json."""
import json, os, sys, numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
import comun as C
out = {}
for ds in ('b_red', 'm2_red', 'a16_red'):
    F, R = C.IR._load(ds); D = F.load_real(); sys.modules.pop('fpm_red', None); o = {}
    for a, b, ax, dl in (((17, 15), (18, 15), 0, 6.0), ((17, 14), (17, 16), 1, 12.0)):
        A = D['I'][a] - gaussian_filter(D['I'][a], 10); B = D['I'][b] - gaussian_filter(D['I'][b], 10)
        A = (A - A.mean()) / A.std(); B = (B - B.mean()) / B.std()
        cc = np.real(np.fft.ifft2(np.fft.fft2(A) * np.conj(np.fft.fft2(B)))) / A.size
        cc = np.fft.fftshift(cc); c0 = 200
        pk = (cc == maximum_filter(cc, 5)); ys, xs = np.nonzero(pk); v = cc[ys, xs]; i = np.argsort(-v)[:4]
        o[f'{a}-{b}'] = [dict(rho=float(v[j]), dy=int(ys[j] - c0), dx=int(xs[j] - c0),
                              dz_um=float(((ys[j] - c0) if ax == 0 else (xs[j] - c0)) * 1.29 / (dl / 102.0))) for j in i]
    out[ds] = o; print(ds, json.dumps(o))
json.dump(out, open(os.path.join(C.HERE, 'capas.json'), 'w'), indent=1)

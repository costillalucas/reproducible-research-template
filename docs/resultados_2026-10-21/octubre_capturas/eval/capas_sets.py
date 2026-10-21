"""capas_sets.py -- = capas.py para todos los sets de muestra de octubre desde inv/<set>.npz (frames completos de las BF, recorte
400 central, (S-188)/(F-188) con el flat del día, sin oscuro por LED: alcanza para la correlación). Escribe capas_sets.json."""
import json, os, numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
H = os.path.dirname(os.path.abspath(__file__)); INV = os.path.join(H, '..', 'inv')
FLAT = {'2026-10-16-muestra2': '2026-10-16-luzsinmuestra', '2026-10-16-a': '2026-10-16-luzsinmuestra', '2026-10-20-muestra': '2026-10-20-luzsinmuestra',
        '2026-10-09-d': '2026-10-09-sinmuestra', '2026-10-09-e': '2026-10-09-sinmuestra', '2026-10-09-muestra': '2026-10-09-sinmuestra',
        '2026-10-02_red_enfocado': '2026-10-02_red_sin_muestra'}
def g(d, k): return [d[n] for n in d.files if n.startswith(f'full_{k[0]}_{k[1]}_')][0][360:760, 360:760].astype(float) - 188.0
out = {}
for s, fl in FLAT.items():
    d = np.load(f'{INV}/{s}.npz'); df = np.load(f'{INV}/{fl}.npz'); o = {}
    for a, b, ax, dl in (((17, 15), (18, 15), 0, 6.0), ((17, 14), (17, 16), 1, 12.0)):
        A, B = g(d, a) / g(df, a), g(d, b) / g(df, b)
        A = A - gaussian_filter(A, 10); B = B - gaussian_filter(B, 10); A = (A - A.mean()) / A.std(); B = (B - B.mean()) / B.std()
        cc = np.fft.fftshift(np.real(np.fft.ifft2(np.fft.fft2(A) * np.conj(np.fft.fft2(B)))) / A.size); c0 = 200
        pk = (cc == maximum_filter(cc, 5)); ys, xs = np.nonzero(pk); v = cc[ys, xs]; i = np.argsort(-v)[:3]
        o[f'{a}-{b}'] = [dict(rho=round(float(v[j]), 3), dy=int(ys[j] - c0), dx=int(xs[j] - c0),
                              dz_um=round(float(((ys[j] - c0) if ax == 0 else (xs[j] - c0)) * 1.29 / (dl / 102.0)))) for j in i]
    out[s] = o; print(s, json.dumps(o))
json.dump(out, open(os.path.join(H, 'capas_sets.json'), 'w'), indent=1)

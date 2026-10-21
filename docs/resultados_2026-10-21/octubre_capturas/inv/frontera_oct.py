"""frontera_oct.py -- ajuste de la frontera |sin|=NA en flats sin muestra (copia de
docs/resultados_2026-10-01/geometria/frontera/ajustar.py, solo rojo, ajuste conjunto de (17,14),(17,16),(18,14),(18,16))
con la geometría de trabajo actual (z 102, NA 0.0669, pixel 1.29 µm). Δy = corrimiento del eje respecto del nominal
(fila 17.5, offset (0,3) mm); el die rojo de 28/09b daba ~+1.06..1.18 mm.
Flats: frames completos de inv/<set>.npz (full_<r>_<c>_<t>), oscuro = mismo LED/exposición del set de oscuros.
Uso: python3 frontera_oct.py   (pares definidos en PARES)"""
import glob, json, os
import numpy as np
import tifffile as T
from scipy.special import fresnel
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
Z, NA, P, PX = 102.0, 0.069 * 1.25 / 1.29, 6.0, 1.29 * 8 / 1000
R0 = Z * np.tan(np.arcsin(NA)); lam = 630e-6
LEDS = [(17, 14), (17, 16), (18, 14), (18, 16)]
PARES = {"28b_flat": None, "2026-10-20-luzsinmuestra": "2026-10-20-muestrasinluz", "2026-10-16-luzsinmuestra": "2026-10-16-muestrasinluz2",
         "2026-10-09-sinmuestra": "2026-10-09-muestrasinluz", "2026-10-02_red_sin_muestra": None,
         # muestras (no flats): la frontera también se ve con muestra rala; control de que el eje no cambió entre flat y muestra
         "2026-10-20-muestra": "2026-10-20-muestrasinluz", "2026-10-16-muestra2": "2026-10-16-muestrasinluz2",
         "2026-10-09-muestra": "2026-10-09-muestrasinluz", "2026-10-09-b": None, "2026-10-09-c": None,
         "2026-10-09-d": "2026-10-09-muestrasinluz", "2026-10-09-e": "2026-10-09-muestrasinluz", "2026-10-16-a": "2026-10-16-muestrasinluz2",
         "2026-10-09": None, "2026-10-02_red_enfocado": None}


def bin8(a):
    return a.reshape(140, 8, 140, 8).mean((1, 3))


def load28():
    FL = f'{B}/2026-09-28.b_rgb_sin_muestra/organizado/red'; DK = f'{B}/2026-09-28.b_dark/fila18_col15_colorb'
    out = {}
    for k in LEDS:
        t, f = max((int(os.path.basename(os.path.dirname(f))[:-2]), f) for f in glob.glob(f'{FL}/*ms/fila{k[0]}_col{k[1]}.tiff'))
        dark = np.mean([T.imread(x).astype(float) for x in sorted(glob.glob(f'{DK}/{t}ms/imagen_frame_*.tiff'))], 0)
        out[k] = bin8((T.imread(f).astype(float) + 0.5 - dark) / t)
    return out


def load(s, dk):
    if s == '28b_flat':
        return load28()
    d = np.load(f'{HERE}/{s}.npz'); out = {}
    dd = np.load(f'{HERE}/{dk}.npz') if dk else None
    for k in LEDS:
        nm = [n for n in d.files if n.startswith(f'full_{k[0]}_{k[1]}_')][0]; t = int(nm.split('_')[-1])
        a = d[nm].astype(float)
        if dd is not None:
            nd = f'full_{k[0]}_{k[1]}_{t}'
            dark = dd[nd].astype(float) if nd in dd.files else 188.0
        else:
            dark = 188.0
        out[k] = bin8((a - dark) / t)
    return out


n = 140; ax_ = (np.arange(n) - n / 2 + 0.5) * PX
Y, X = np.meshgrid(ax_, ax_, indexing='ij')
sg = np.arange(-3, 3, 0.001)


def perfil(d):
    v = sg * np.sqrt(2 / (lam * Z)); S, C = fresnel(v)
    I = ((C + .5) ** 2 + (S + .5) ** 2) / 2
    d = min(d, 1.5)
    if d > 0.002:
        u = np.arange(-d / 2, d / 2 + 1e-9, 0.001); k = np.sqrt(np.clip(1 - (2 * u / d) ** 2, 0, None)); k /= k.sum()
        I = np.convolve(np.pad(I, len(k), mode='edge'), k, mode='same')[len(k):-len(k)]
    return I


def nom(k): return np.array([(k[1] - 15) * P, (k[0] - 17.5) * P])


def res_led(img, L, R, d):
    s = R - np.hypot(X - L[0], Y - L[1]); pr = np.interp(s, sg, perfil(d))
    A = np.stack([pr, pr * X, pr * Y, np.ones_like(X)], -1).reshape(-1, 4)
    y = img.ravel(); c, *_ = np.linalg.lstsq(A, y, rcond=None)
    return (A @ c - y) / img.max(), c


out = {}
for s, dk in PARES.items():
    if s != '28b_flat' and not os.path.exists(f'{HERE}/{s}.npz'):
        continue
    imgs = load(s, dk)
    o = {}
    for tag, freeR in (('R_fijo', False), ('R_libre', True)):
        def f(p):
            R = p[3] if freeR else R0
            return np.concatenate([res_led(imgs[k], nom(k) + p[:2], R, abs(p[2]))[0] for k in LEDS])
        r = min((least_squares(f, [0, dy0, 0.2, R0], loss='soft_l1', f_scale=0.02, diff_step=1e-3) for dy0 in (0.0, 1.0)),
                key=lambda r: r.cost)
        J = r.jac; cov = np.linalg.pinv(J.T @ J) * (r.fun ** 2).mean()
        o[tag] = dict(dx_mm=float(r.x[0]), dy_mm=float(r.x[1]), d_mm=abs(float(r.x[2])), R_mm=float(r.x[3] if freeR else R0),
                      sig=np.sqrt(np.diag(cov)).tolist(), rms=float(np.sqrt((r.fun ** 2).mean())))
    o['media_cuentas_ms'] = {f'{k}': float(v.mean()) for k, v in imgs.items()}
    out[s] = o
    print(s, 'oscuro', dk, {t: 'dx %+.3f dy %+.3f R %.3f d %.3f rms %.3f' % (v['dx_mm'], v['dy_mm'], v['R_mm'], v['d_mm'], v['rms'])
                            for t, v in o.items() if t.startswith('R_')}, flush=True)
json.dump(dict(R0=R0, Z=Z, NA=NA, sets=out), open(f'{HERE}/frontera_oct.json', 'w'), indent=1)

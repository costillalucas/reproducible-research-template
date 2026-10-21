"""desenfoque.py -- desenfoque residual por paralaje entre BF (17,14) y (17,16) (columnas ±1 -> Δx = 12 mm en la placa, z 102 mm):
corrimiento de imagen d = Δz·(tanθ_16 - tanθ_14) ≈ Δz·0.1176 a lo largo de columnas (eje x de la imagen). Recorte 400 central,
correlación de fase subpixel (skimage, upsample 50, normalization=None como auditoria_gb_2026-10-20/desenfoque_bf.py) de S/F (flat suavizado σ 1 px, quita el patrón fijo de polvo), píxel 1.29 µm. El signo es convencional (mismo cálculo para 28/09b, que la
auditoría del 20/10 daba en −8 µm para rojo). Escribe desenfoque.json."""
import glob, json, os, numpy as np
from scipy.ndimage import gaussian_filter
from skimage.registration import phase_cross_correlation as pcc
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, '..', '..'))
PX, Z, P = 1.29, 102.0, 6.0
tg = (2 * P) / Z  # paraxial
def hp(a): a = a.astype(float); return a - gaussian_filter(a, 15)
out = {}
FLAT = {'2026-10-16-muestra2': '2026-10-16-luzsinmuestra', '2026-10-16-a': '2026-10-16-luzsinmuestra', '2026-10-20-muestra': '2026-10-20-luzsinmuestra',
        '2026-10-09-d': '2026-10-09-sinmuestra', '2026-10-09-e': '2026-10-09-sinmuestra', '2026-10-09-muestra': '2026-10-09-sinmuestra',
        '2026-10-02_red_enfocado': '2026-10-02_red_sin_muestra'}
def g(d, k): return [d[n] for n in d.files if n.startswith(f'full_{k[0]}_{k[1]}_')][0][360:760, 360:760].astype(float) - 188.0
for s, fl in FLAT.items():
    d = np.load(f'{HERE}/{s}.npz'); df = np.load(f'{HERE}/{fl}.npz')
    f = lambda k: g(d, k) / gaussian_filter(g(df, k), 1) 
    sh, err, _ = pcc(hp(f((17, 16))), hp(f((17, 14))), upsample_factor=50, normalization=None)
    out[s] = dict(shift_px=[float(x) for x in sh], dz_um=float(sh[1] * PX / tg), err=float(err))
pz = np.load(f'{RES}/captura_2026-09-28b/red/prep.npz'); pk = [tuple(map(int, k)) for k in pz['keys']]
q = lambda k: pz['S'][pk.index(k)] / gaussian_filter(pz['F'][pk.index(k)].astype(float), 1)
sh, err, _ = pcc(hp(q((17, 16))), hp(q((17, 14))), upsample_factor=50, normalization=None)
out['28b_red'] = dict(shift_px=[float(x) for x in sh], dz_um=float(sh[1] * PX / tg), err=float(err))
for k, v in out.items(): print(k, v)
json.dump(out, open(f'{HERE}/desenfoque.json', 'w'), indent=1)

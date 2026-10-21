"""movimiento.py -- ¿se mueve la muestra? Pearson entre los pasa-altos (σ 10 px, recorte 400) de frame 1 y frame 2 de la MISMA LED
(tomados uno detrás del otro) contra el valor esperado si solo hubiera ruido: ρ_esp = var_señal/(var_señal+var_ruido), con
var_ruido de la diferencia de frames. Si ρ ≈ ρ_esp la muestra está quieta entre frames. Además corrimiento subpixel frame2 vs frame1.
Sets: 16/10 muestra2 y a, 20/10 muestra, 09/10 d; 28/09b no tiene frames individuales (solo 'organizado', promedio) -> no.
Escribe movimiento.json."""
import glob, json, os, numpy as np, tifffile as T
from scipy.ndimage import gaussian_filter
from skimage.registration import phase_cross_correlation as pcc
B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas'); HERE = os.path.dirname(os.path.abspath(__file__))
C = slice(360, 760); out = {}
for s in ('2026-10-16-muestra2', '2026-10-16-a', '2026-10-20-muestra', '2026-10-09-d'):
    o = {}
    for k in ((17, 15), (18, 15), (20, 15), (21, 17)):
        d = glob.glob(f'{B}/{s}/fila{k[0]}_col{k[1]}_colorr/*ms')[0]
        f1, f2 = (T.imread(f).astype(float)[C, C] for f in sorted(glob.glob(d + '/imagen_frame_*.tiff')))
        h1, h2 = f1 - gaussian_filter(f1, 10), f2 - gaussian_filter(f2, 10)
        vn = np.var(h1 - h2) / 2; vs = max(np.cov(h1.ravel(), h2.ravel())[0, 1], 1e-9)
        rho = float(np.corrcoef(h1.ravel(), h2.ravel())[0, 1])
        hs1, hs2 = gaussian_filter(h1, 1.5), gaussian_filter(h2, 1.5)
        sh = pcc(hs1, hs2, upsample_factor=50, normalization=None)[0]
        o[str(k)] = dict(t=os.path.basename(d), rho=rho, rho_si_quieta=float(vs / (vs + vn)), shift_px=[float(x) for x in sh])
    out[s] = o; print(s, json.dumps(o))
json.dump(out, open(f'{HERE}/movimiento.json', 'w'), indent=1)

"""survey_contraste.py -- contraste rms de S/F (LED (17,15)) en recortes de 400 px candidatos, para elegir recortes comparables."""
import sys, os, json
sys.dont_write_bytecode = True
import numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, '/home/chanoscopio/Documents/LucasC/reproducible-research-template/scripts')
import reconstruir as RC
B = '/home/chanoscopio/Documents/AleYLu/imagenes_tomadas'
CAPS = {'0311': ('2026-11-03-red', '2026-11-03-red-sinmuestra', '2026-11-03-red-dark', '2026-11-03-red-sinmuestra-dark'),
        'redc': ('2026-10-30-red-c', '2026-10-30-red-c-sinmuestra', '2026-10-30-red-c-dark', '2026-10-30-red-c-sinmuestra-dark'),
        'red': ('2026-10-30-red', '2026-10-30-red-b-sinmuestra', '2026-10-30-red-dark', '2026-10-30-red-b-sinmuestra-dark'),
        'redb': ('2026-10-30-red-b', '2026-10-30-red-b-sinmuestra', '2026-10-30-red-b-dark', '2026-10-30-red-b-sinmuestra-dark')}
out = {}
for et, (c, f, d, dfl) in CAPS.items():
    SM, FL = RC.indexar(f'{B}/{c}', 'r'), RC.indexar(f'{B}/{f}', 'r')
    om, of = RC.Oscuros([f'{B}/{d}', f'{B}/{dfl}'], None), RC.Oscuros([f'{B}/{dfl}', f'{B}/{d}'], None)
    k = (17, 15); t = RC.elegir_t(SM[k], None); tf = RC.elegir_t(FL[k], None)
    s, *_ = RC.promediar(SM[k][t], om, t, None, 'm', []); fl, *_ = RC.promediar(FL[k][tf], of, tf, None, 'f', [])
    q = s / np.maximum(gaussian_filter(fl, 2), 1e-6)
    hp = q - gaussian_filter(q, 20)   # contraste de partículas (quita viñeteo lento)
    res = {}
    for f0 in range(0, 721, 120):
        for c0 in range(0, 721, 120):
            qq = q[f0:f0 + 400, c0:c0 + 400]; m = np.median(qq)
            res[f'{f0},{c0}'] = dict(rms_hp=float(np.std(hp[f0:f0 + 400, c0:c0 + 400]) / m), oscuro=float(np.mean(qq / m < 0.5)))
    out[et] = res
    top = sorted(res.items(), key=lambda x: -x[1]['rms_hp'])
    print(et, '360,80:', res.get('360,80'), '| min', top[-1], '| max', top[0], flush=True)
json.dump(out, open('../resultados/survey_contraste.json', 'w'), indent=1)

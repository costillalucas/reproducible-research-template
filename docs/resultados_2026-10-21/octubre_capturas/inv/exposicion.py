"""exposicion.py -- exposición efectiva t_ef = t_nominal + t0 medida con el MISMO campo a varias exposiciones:
2026-10-09 (BF 16 / borde 32 ms), -b (8/18), -c (4/10), -d (5/10) son el mismo campo (correlación BF 0.89-0.99, corrimiento 0).
Para cada LED con exposición distinta entre sets: media del recorte (bin 4) sobre oscuro, sin LEDs con saturados en el recorte;
ajuste I_k(set) = r_k (t_set + t0) con t0 común (y deriva por set libre como control). Oscuro: 10-09-muestrasinluz (mismo LED/t
si existe; si no, media por t interpolada -- el oscuro es ~plano en t: 192 cuentas). Escribe exposicion.json."""
import json, os, numpy as np
from scipy.optimize import least_squares
HERE = os.path.dirname(os.path.abspath(__file__))
SETS = ['2026-10-09', '2026-10-09-b', '2026-10-09-c', '2026-10-09-d']
dk = np.load(f'{HERE}/2026-10-09-muestrasinluz.npz'); dkk = [tuple(k) for k in dk['keys']]
dper = {(k, int(t)): m for k, t, m in zip(dkk, dk['t'], dk['mean'])}
byt = {}
for (k, t), m in dper.items(): byt.setdefault(t, []).append(m)
ts = np.array(sorted(byt)); vs = np.array([np.mean(byt[t]) for t in ts])
rows = []
for si, s in enumerate(SETS):
    d = np.load(f'{HERE}/{s}.npz'); keys = [tuple(k) for k in d['keys']]
    for i, k in enumerate(keys):
        t = int(d['t'][i])
        if t > 40: continue
        dm = dper.get((k, t), float(np.interp(t, ts, vs)))
        rows.append(dict(set=s, si=si, k=tuple(map(int, k)), t=t, I=float(d['mean'][i] - dm), satc=int(d['nsat_c'][i]), satf=int(d['nsat_full'][i])))
ok = [r for r in rows if r['satc'] == 0]
leds = sorted({r['k'] for r in ok})
def fit(drift):
    def f(p):
        t0 = p[0]; rk = dict(zip(leds, p[1:1 + len(leds)])); g = np.r_[1.0, p[1 + len(leds):]] if drift else np.ones(4)
        return np.array([(r['I'] - g[r['si']] * rk[r['k']] * (r['t'] + t0)) / r['I'] for r in ok])
    p0 = [0.0] + [np.mean([r['I'] / r['t'] for r in ok if r['k'] == k]) for k in leds] + ([1, 1, 1] if drift else [])
    res = least_squares(f, p0); J = res.jac; cov = np.linalg.pinv(J.T @ J) * np.mean(res.fun ** 2)
    return dict(t0_ms=float(res.x[0]), sig_t0=float(np.sqrt(cov[0, 0])), rms_rel=float(np.sqrt(np.mean(res.fun ** 2))),
                deriva=(res.x[1 + len(leds):].tolist() if drift else None))
out = dict(filas=[{**r, 'k': list(r['k'])} for r in rows], sin_deriva=fit(False))
# deriva solo identificable si hay LEDs con la misma t en dos sets: (18,14),(18,16) a 10 ms en -c y -d
out['con_deriva'] = fit(True)
# por LED: pendiente/ordenada de I vs t
per = {}
for k in leds:
    rr = [r for r in ok if r['k'] == k]
    if len({r['t'] for r in rr}) >= 2:
        A = np.c_[[r['t'] for r in rr], np.ones(len(rr))]; c, *_ = np.linalg.lstsq(A, [r['I'] for r in rr], rcond=None)
        per[str(k)] = dict(t=[r['t'] for r in rr], I=[round(r['I'], 1) for r in rr], t0=float(c[1] / c[0]))
out['por_led'] = per
for r in rows: print(r['set'], r['k'], r['t'], round(r['I'], 1), 'c/ms %.1f' % (r['I'] / r['t']), 'satc', r['satc'])
print('sin deriva', out['sin_deriva']); print('con deriva', out['con_deriva']); print(json.dumps(per))
json.dump(out, open(f'{HERE}/exposicion.json', 'w'), indent=1, default=int)

"""calibra.py -- calibra el fantoma y la caída de brillo contra la captura real 28/09b rojo (z≈98-102, 15x15, 400 px).
Real: prep.npz (S = (muestra-oscuro)/t, F = campo plano sin muestra) por anillo de LEDs (centro (17.5,15)).
Sim: misma grilla, fantoma de densidad rho, intensidad normalizada (campo claro pleno = 1).
Compara por anillo: media(S-F)/118 real vs media sim (DF); p99.9 real vs sim; y media BF S/F."""
import json, sys, time
import numpy as np
sys.path.insert(0, '.')
import sim as S
R = dict(np.load('../captura_2026-09-28b/red/prep.npz')); keys = [tuple(map(int, k)) for k in R['keys']]
z = 102.0
real = {}
for i, k in enumerate(keys):
    r = int(round(np.hypot(k[0] - 17.5, k[1] - 15)))
    s, f = R['S'][i], R['F'][i]
    real.setdefault(r, []).append((float((s - f).mean()) / S.B0, float(np.percentile(s, 99.9)) / S.B0,
                                   float(f.mean()) / S.B0, float(s.mean() / f.mean())))
n = 160
pos = S.led_set(z, 'entre', square=True); fxy = S.fxy_of(pos, z)
out = {'real': {r: np.median(np.array(v), 0).tolist() for r, v in sorted(real.items())}}
for rho in [float(a) for a in sys.argv[1:]] or [1e-3]:
    acc = {}
    for seed in (0, 1):
        sph, L = S.phantom(n, seed=seed, rho=rho)
        o = S.truth_object(sph, L, n)
        I = S.predict(o, fxy, list(pos), n)
        for k in pos:
            r = int(round(np.hypot(k[0] - 0.5, k[1])))
            acc.setdefault(r, []).append((float(I[k].mean()), float(np.percentile(I[k], 99.9))))
    out[f'sim_rho{rho:g}'] = {r: np.median(np.array(v), 0).tolist() for r, v in sorted(acc.items())}
    out[f'nsph_rho{rho:g}'] = len(sph)
print('anillo  NA   real(S-F)/B  real p99.9/B  stray F/B  BF S/F | sim mean, p99.9 por rho')
for r in sorted(out['real']):
    na = r * 6 / np.hypot(r * 6, z)
    rr = out['real'][r]
    s = '  '.join('%.2e %.2e' % tuple(out[kk][r]) for kk in out if kk.startswith('sim') and r in out[kk])
    print(f'{r:3d} {na:.3f}  {rr[0]:.2e}  {rr[1]:.2e}  {rr[2]:.2e}  {rr[3]:.3f} | {s}')
json.dump(out, open('calibra.json', 'w'), indent=1)

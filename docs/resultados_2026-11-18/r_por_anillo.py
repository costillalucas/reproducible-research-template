"""r_por_anillo.py -- 18/11/2026. R held-out por anillo (TODOS los anillos, no solo < 7 como C1) para el 2x2.

Para cada corrida: objeto de la mitad h, LEDs no vistos = paridad != h (todos los anillos). R = residuo afín de
reconstruir.r_leds (0 perfecto, 1 nada). Se agrupa por anillo = round(ring(k)) desde el eje (17,15).
Referencias por anillo: 'sin FPM' (objeto inicial fourier_avg de los BF) y 'piso' (ruido; 2º valor de affine_residual).
"""
import importlib.util, json, os, sys
import numpy as np
REPO = '/home/chanoscopio/Documents/LucasC/reproducible-research-template'
sys.path.insert(0, os.path.join(REPO, 'scripts')); sys.argv = ['x']
spec = importlib.util.spec_from_file_location('rec', os.path.join(REPO, 'scripts', 'reconstruir.py'))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
AQUI = os.path.dirname(os.path.abspath(__file__))
EJE, NL, Z = (17, 15), 21, 143.5
out = {}
for run in sys.argv_runs if hasattr(sys, 'argv_runs') else sorted(d for d in os.listdir(AQUI) if d.startswith(('1025ms', '2048ms'))):
    d = os.path.join(AQUI, run)
    if not os.path.isfile(os.path.join(d, 'objeto_mitadB.npy')):
        print(run, 'sin terminar'); continue
    m = json.load(open(os.path.join(d, 'datos', 'metricas.json')))
    na = float('0.' + run.split('_na')[1])
    F, IR = R.cargar_solver('red', 3, NL, EJE, na)
    n = m['recorte'][2]
    geo = F.geometry(Z, offset_mm=tuple(m['offset_mm']), crop=n)
    F.BF = [tuple(k) for k in m['bf']]
    Dd = F.load_real(os.path.join(d, 'datos', 'prep.npz'))
    keys = sorted(Dd['I'])
    per = {}
    for h, nom in ((0, 'A'), (1, 'B')):
        o = np.load(os.path.join(d, f'objeto_mitad{nom}.npy'))
        ho = [k for k in keys if (k[0] + k[1]) % 2 != h]
        for k, v in R.r_leds(F, o, ho, geo, Dd, n).items():
            per[k] = (float(v[0]), float(v[1]))
    o0 = F.initial_object(Dd['I'], geo['factor'], 'fourier_avg')
    sin = {k: float(v[0]) for k, v in R.r_leds(F, o0, keys, geo, Dd, n).items()}
    anillos = {}
    for k in keys:
        a = int(round(F.ring(k)))
        anillos.setdefault(a, []).append((per[k][0], per[k][1], sin[k]))
    out[run] = {a: dict(R=float(np.mean([x[0] for x in v])), piso=float(np.mean([x[1] for x in v])),
                        sin_fpm=float(np.mean([x[2] for x in v])), n=len(v)) for a, v in sorted(anillos.items())}
    out[run + '_porled'] = {f'{k[0]},{k[1]}': per[k] for k in per}
    print(run, 'listo', flush=True)
json.dump(out, open(os.path.join(AQUI, 'r_por_anillo.json'), 'w'), indent=1)
runs = [r for r in out if not r.endswith('_porled')]
print('\nR held-out por anillo (menor = mejor); entre paréntesis piso de ruido')
print('anillo  n  ' + '  '.join(f'{r:>20s}' for r in runs) + '   sin FPM(1ra)')
for a in sorted(out[runs[0]]):
    row = '  '.join(f"{out[r][a]['R']:.3f} ({out[r][a]['piso']:.3f})".rjust(20) for r in runs)
    print(f'{a:5d} {out[runs[0]][a]["n"]:3d}  {row}   {out[runs[0]][a]["sin_fpm"]:.3f}')

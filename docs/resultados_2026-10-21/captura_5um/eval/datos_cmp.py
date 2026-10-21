"""datos_cmp.py -- calidad de datos comparada (r21_red vs m2_red vs 28/09b rojo), en el objetivo que ve el solver (fpm_red.load_real):
por anillo de iluminación (distancia al eje real en pasos: r21 eje (17,15); m2/28b eje ~ (17.32,15)), mediana sobre LEDs de
contraste std(I_k), ruido sqrt(V_k) y piso = sqrt(V)/std(I) (lo que el ruido solo dejaría en el R held-out). Escribe datos_cmp.json."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import runner_2110 as RN
IR = RN.IR
AX = {'r21_red': (17.0, 15.0), 'm2_red': (17.32, 15.0), 'b_red': (17.32, 15.0)}
out = {}
for ds in ('r21_red', 'm2_red', 'b_red'):
    F, R = IR._load(ds); D = F.load_real()
    rows = {}
    for k in D['keys']:
        if k in F.BF:
            continue
        rg = np.hypot(k[0] - AX[ds][0], k[1] - AX[ds][1]); I = D['I'][k]; sd = float(I[D['mask'][k]].std()); nz = float(np.sqrt(D['V'][k]))
        rows.setdefault(int(round(rg)), []).append((sd, nz, nz / sd))
    out[ds] = {str(q): dict(n=len(v), contraste=float(np.median([x[0] for x in v])), ruido=float(np.median([x[1] for x in v])),
                            piso=float(np.median([x[2] for x in v]))) for q, v in sorted(rows.items())}
    allp = [x[2] for v in rows.values() for x in v]
    out[ds]['piso_mediana_anillo_lt7'] = float(np.median([x[2] for q, v in rows.items() if q < 7 for x in v]))
    sys.modules.pop('fpm_red', None); sys.path.remove(IR.DATASETS[ds][0])
    print(ds, {q: (round(v['contraste'], 3), round(v['piso'], 3)) for q, v in out[ds].items() if q.isdigit()}, 'piso<7', round(out[ds]['piso_mediana_anillo_lt7'], 3))
json.dump(out, open(os.path.join(HERE, 'datos_cmp.json'), 'w'), indent=1)

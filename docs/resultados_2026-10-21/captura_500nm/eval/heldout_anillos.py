"""COPIA 21/10 tarde: agrega r500_red rojo_500 (este set).
heldout_anillos.py -- R held-out por anillo de iluminación (folds, LEDs no entrenados, sin los excluidos a horcajadas de cada set),
con el piso de ruido de cada LED (sqrt(V)/std(I), columna 2 de per_led) y el exceso de modelo sqrt(max(R²-piso²,0)), para:
r21_red rojo_centrado (este dir), m2_red rojo_final (octubre + folds completados aquí), 28/09b rojo_final (offset_color_2026-10-02),
y las variantes de offset de r21 (control de centrado). Anillo = distancia al eje real en pasos (r21 (17,15); m2/28b (17.32,15)).
Uso: python3 heldout_anillos.py [EPOCA ...]  -> heldout_anillos.json"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, '..', '..'))
CD = os.path.join(RES, 'captura_2026-10-21'); OC = os.path.join(RES, 'octubre_capturas_2026-10-21'); OF = os.path.join(RES, 'offset_color_2026-10-02')
EX = {'r500_red': set(), 'r21_red': set(), 'm2_red': {'18,14', '18,16'}, 'b_red': {'18,14', '18,16'}}
AX = {'r500_red': (17.0, 15.0), 'r21_red': (17.0, 15.0), 'm2_red': (17.32, 15.0), 'b_red': (17.32, 15.0)}
RUNS = {'r500 (tarde)': ('r500_red', 'rojo_500', [os.path.join(RES, 'captura_2026-10-21_500')]), 'r21 centrado': ('r21_red', 'rojo_centrado', [CD]), 'm2 (16/10)': ('m2_red', 'rojo_final', [CD, OC]), '28/09b': ('b_red', 'rojo_final', [OF]),
        'r21 off -0.6': ('r21_red', 'rc_om060', [CD]), 'r21 off +0.6': ('r21_red', 'rc_op060', [CD]), 'r21 off +1.06': ('r21_red', 'rc_op106', [CD])}
eps = [int(e) for e in sys.argv[1:]] or [40, 160]


def fold_rows(ds, var, roots, f, ep):
    for r in roots:
        p = os.path.join(r, 'out', var, ds, f'real_A+init_z98.0_f{f}', 'metrics.jsonl')
        if os.path.exists(p):
            for l in open(p):
                x = json.loads(l)
                if x['epoch'] == ep:
                    return x['per_led']
    return None


out = {}
for name, (ds, var, roots) in RUNS.items():
    for ep in eps:
        per = [fold_rows(ds, var, roots, f, ep) for f in range(5)]
        if any(p is None for p in per):
            continue
        rows = []; fm = []
        for p in per:
            v = [(k, x[0], x[1]) for k, x in p.items() if not x[3] and x[2] < 7 and k not in EX[ds]]
            fm.append(np.mean([a[1] for a in v])); rows += v
        rb = {}
        for k, R, fl in rows:
            r, c = map(int, k.split(',')); q = int(round(np.hypot(r - AX[ds][0], c - AX[ds][1])))
            rb.setdefault(q, []).append((R, fl))
        out[f'{name} e{ep}'] = dict(C1_media=float(np.mean(fm)), C1_sd=float(np.std(fm)), piso_media=float(np.mean([a[2] for a in rows])),
                                    exceso_media=float(np.mean([np.sqrt(max(a[1] ** 2 - a[2] ** 2, 0)) for a in rows])), n=len(rows),
                                    anillos={str(q): dict(n=len(v), R=float(np.median([a[0] for a in v])), piso=float(np.median([a[1] for a in v])),
                                                          exceso=float(np.median([np.sqrt(max(a[0] ** 2 - a[1] ** 2, 0)) for a in v])))
                                             for q, v in sorted(rb.items())})
        o = out[f'{name} e{ep}']
        print(f'{name:14s} e{ep:3d}  C1 {o["C1_media"]:.4f}±{o["C1_sd"]:.4f}  piso {o["piso_media"]:.3f}  exceso {o["exceso_media"]:.3f}  n {o["n"]}  ',
              ' '.join(f'r{q}:{v["R"]:.2f}/{v["piso"]:.2f}' for q, v in o['anillos'].items()))
json.dump(out, open(os.path.join(HERE, 'heldout_anillos.json'), 'w'), indent=1)

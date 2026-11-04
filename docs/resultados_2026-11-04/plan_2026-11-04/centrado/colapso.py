"""colapso.py -- chequeo NO paramétrico del eje: monotonía del perfil radial (sin escalón logístico, sin A_k libre).

Hipótesis mínimas: (1) borde BF circular e isótropo, con perfil f(d) decreciente en la distancia d al centro del círculo;
(2) mismo brillo para todos los LEDs del anillo 1 (cociente normalizado por A_ref); (3) corrimiento no telecéntrico puro:
d_k(p) = |k - eje - p/s| en pasos, s = 3538 px/paso (p = píxel respecto del centro del ROI; filas crecientes = abajo).
Puntos: bloques de 160 x 160 px (7 x 7 por vecino) con la mediana del cociente. Para cada eje candidato se cuentan los pares
de bloques "discordantes" (el más cercano al centro de su círculo es el más oscuro) entre pares con |Δcociente| > 0.05.
  viol_todos  : todos los pares (8 vecinos);
  viol_cd     : solo pares cruz-diagonal (las diagonales juzgadas contra la cruz; no intervienen pares diag-diag).
Lee mapas_<captura>.npz y tabla.json (de centrado.py). Escribe colapso.json.  Uso: python3 colapso.py
"""
import json
import os
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
S = 3538.0
NB = 7
c = ((np.arange(NB) + 0.5) * 160 - 560) / S
PY, PX = np.meshgrid(c, c, indexing='ij')
CRUZ = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
VEC = CRUZ + DIAG
UMBRAL = 0.05


def bloques(z):
    q, es_d = [], []
    for d in VEC:
        m = z[f'q_{d[0]}_{d[1]}'][:70, :70].reshape(NB, 10, NB, 10).transpose(0, 2, 1, 3).reshape(NB, NB, 100)
        q.append(np.median(m, -1).ravel()); es_d.append(np.full(NB * NB, d in DIAG))
    return np.concatenate(q), np.concatenate(es_d)


def dist(ar, ac):
    return np.concatenate([np.hypot(d[0] - ar - PY, d[1] - ac - PX).ravel() for d in VEC])


def violaciones(q, es_d, ar, ac):
    d = dist(ar, ac)
    dq = q[:, None] - q[None, :]; dd = d[:, None] - d[None, :]
    sel = np.triu(np.abs(dq) > UMBRAL, 1)
    disc = sel & (dq * dd > 0)        # más brillante y más lejos
    cd = sel & (es_d[:, None] != es_d[None, :])
    return float(disc.sum() / sel.sum()), float((disc & cd).sum() / max(cd.sum(), 1)), int(cd.sum())


def main():
    tab = json.load(open(os.path.join(OUT, 'tabla.json')))
    out = {}
    ars = np.round(np.arange(-0.40, 0.4001, 0.005), 3); acs = np.round(np.arange(-0.10, 0.1001, 0.005), 3)
    for r in tab:
        f = os.path.join(OUT, f'mapas_{r["nombre"]}.npz')
        if not os.path.exists(f):
            continue
        q, es_d = bloques(np.load(f))
        V = np.array([[violaciones(q, es_d, a, b)[:2] for b in acs] for a in ars])
        res = {}
        for k, idx in (('todos', 0), ('cd', 1)):
            i, j = np.unravel_index(np.argmin(V[..., idx]), V.shape[:2])
            vmin = V[i, j, idx]
            # región "casi óptima": violaciones <= mínimo + 0.01
            ok = V[..., idx] <= vmin + 0.01
            res[k] = dict(mejor=[float(ars[i]), float(acs[j])], vmin=float(vmin),
                          fila_rango=[float(ars[ok.any(1)].min()), float(ars[ok.any(1)].max())],
                          col_rango=[float(acs[ok.any(0)].min()), float(acs[ok.any(0)].max())])
        cand = {'a': r['a']['eje'], 'b': r['b']['eje'], 'a_cruz': r['a_cruz']['eje']}
        if r.get('b_diag'):
            cand['b_diag'] = r['b_diag']
        res['candidatos'] = {k: dict(zip(('viol_todos', 'viol_cd', 'n_pares_cd'), violaciones(q, es_d, *v))) for k, v in cand.items()}
        jb = int(np.argmin(np.abs(acs - res['cd']['mejor'][1])))
        res['curva_fila'] = dict(ars=ars.tolist(), viol_todos=V[:, jb, 0].tolist(), viol_cd=V[:, jb, 1].tolist())
        out[r['nombre']] = res
        print(r['nombre'], 'todos:', res['todos']['mejor'], round(res['todos']['vmin'], 3), res['todos']['fila_rango'],
              '| cruz-diag:', res['cd']['mejor'], round(res['cd']['vmin'], 3), res['cd']['fila_rango'],
              {k: (round(v['viol_todos'], 3), round(v['viol_cd'], 3)) for k, v in res['candidatos'].items()}, flush=True)
    json.dump(out, open(os.path.join(OUT, 'colapso.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

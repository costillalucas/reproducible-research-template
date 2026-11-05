"""real_rb0.py -- misma prueba que diag_rb0 ('original' vs 'etapa1_radio') sobre los datos REALES 03/11
(prep.npz de 2026-11-03-red_1311, recorte 360:760, 80:480, división por flat como paso_espectral_0311). Solo lectura."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import sys
sys.dont_write_bytecode = True
import json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_borde as S  # noqa: E402
import diag_rb0 as D  # noqa: E402

P = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-03-red_1311/datos/prep.npz"
d = np.load(P); keys = [tuple(int(v) for v in k) for k in d["keys"]]
imgs = {}
for dd in S.BF5:
    i = keys.index((17 + dd[0], 15 + dd[1])); f = d["F"][i].astype(float)
    imgs[dd] = d["S"][i].astype(float) / f * f.mean()
print('forma', imgs[(0, 0)].shape)
out = {}
for modo in ('original', 'etapa1_radio'):
    r = D.espectral_var(imgs, modo, None); out[modo] = r
    print(f"REAL 03/11 {modo:12s}: NA·z {r['NAz_fila']:.3f}/{r['NAz_col']:.3f} rb {r['rb']:.2f} s {r['s_row']:.2f}/{r['s_col']:.2f}", flush=True)
json.dump(out, open(os.path.join(D.RES, 'real_rb0_0311.json'), 'w'), indent=1)

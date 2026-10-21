"""bf_consistencia.py -- consistencia entre fotos de campo claro: FRC (ventana Tukey 0.2) entre pares de BF (I del modelo, S/F·<F>)
para m2_red, a16_red y 28/09b rojo; correlación de Pearson de los mapas pasa-altos (σ 10 px); corrimiento relativo (sin normalizar).
Si la muestra no cambia, (17,15) vs (18,15) solo difieren por la inclinación. Escribe bf_consistencia.json."""
import json, os, sys, numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal.windows import tukey
from skimage.registration import phase_cross_correlation as pcc
import comun as C
H = C.HERE
W = np.outer(tukey(400, .2), tukey(400, .2))
def load(ds):
    if ds == 'b_red':
        F, R = C.IR._load('b_red'); return F.load_real()
    os.environ['DS'] = ds; F, R = C.IR._load(ds); return F.load_real()
out = {}
for ds in ('b_red', 'm2_red', 'a16_red'):
    D = load(ds); o = {}
    for a, b in (((17, 15), (18, 15)), ((17, 14), (17, 16)), ((17, 15), (17, 14)), ((17, 15), (17, 16))):
        A, B = D['I'][a], D['I'][b]
        fr = C.frc((A - A.mean()) * W, (B - B.mean()) * W, 1.29, 40, 1 / (2 * 1.29))
        hpA, hpB = A - gaussian_filter(A, 10), B - gaussian_filter(B, 10)
        sh = pcc(hpA, hpB, upsample_factor=20, normalization=None)[0]
        k17 = next((float(k) for k, y, n in fr if y < 1 / 7 and k > 0.02), None)
        o[f'{a}-{b}'] = dict(pearson_hp=float(np.corrcoef(hpA.ravel(), hpB.ravel())[0, 1]), shift_px=[float(x) for x in sh],
                             k_primer_cruce_1_7=k17, periodo_um=(1 / k17 if k17 else None),
                             frc_bandas={'[0.02,0.1]': float(np.mean(fr[(fr[:, 0] > .02) & (fr[:, 0] < .1), 1])),
                                         '[0.1,0.2]': float(np.mean(fr[(fr[:, 0] > .1) & (fr[:, 0] < .2), 1]))})
    out[ds] = o; print(ds, json.dumps(o))
    for m in ('fpm_red',): sys.modules.pop(m, None)
json.dump(out, open(f'{H}/bf_consistencia.json', 'w'), indent=1)

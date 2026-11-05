"""diag_espectral.py -- ¿de dónde sale el sesgo del método espectral con pupila DURA? (diagnóstico, onda plana, recorte 400)

Compara la misma cadena (espectral() de sim_borde, sin cambios) sobre objetos con distinta envolvente espectral:
  esferas      : el objeto de la simulación principal (fase ~2 rad, espectro que cae con |f|)
  esferas_debil: mismas esferas con fase x0.1 (objeto débil, misma envolvente)
  blanco_debil : fase aleatoria blanca 0.1 rad rms en la grilla fina (espectro ~plano dentro de la pupila)
  blanco_amp   : AMPLITUD aleatoria blanca 10 % rms (control: un objeto de amplitud no anula la transferencia donde
                 se solapan los dos círculos ±k; uno de fase débil sí, P(f+k) - P(f-k) ~ 0 en la lente común)
Pupila dura, verdades A (NA 0.070) y B (NA 0.0744), z 99.5, semillas 0-1. Sin ruido y con ruido. Reporta sesgo de centros (bins) y NA·z.
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import sys
sys.dont_write_bytecode = True
import json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_borde as S  # noqa: E402

Z = 99.5
out = []
for seed in (0, 1):
    obj, _ = S.objeto(seed, S.NROI)
    phi = np.angle(obj)
    rng = np.random.default_rng(seed + 40)
    objs = dict(esferas=obj, esferas_debil=np.exp(0.1j * phi).astype(np.complex64),
                blanco_debil=np.exp(0.1j * rng.standard_normal(obj.shape)).astype(np.complex64),
                blanco_amp=(1 + 0.1 * rng.standard_normal(obj.shape)).astype(np.complex64))
    for nom, o in objs.items():
        for NA, w in ((0.070, 0.0), (0.0744, 0.0)):
            pw = S.recorte_onda_plana(o, S.BF5, NA, w, Z)
            esc = S.PICO / float(np.percentile(pw[(0, 0)], 99.9))
            for etq, imgs in (('sin_ruido', pw), ('ruido', {d: S.ruido(pw[d] * esc, rng) for d in S.BF5})):
                r = S.espectral(imgs)
                pr, pc = S.CR0 + S.NCR / 2 - S.NROI / 2, S.CC0 + S.NCR / 2 - S.NROI / 2
                sesgo = []
                for l in r['leds']:
                    d = (l['led'][0] - 17, l['led'][1] - 15)
                    ky, kx, _ = S.k_local(d, pr, pc, Z)
                    sesgo.append([l['c0'] - ky * S.N * S.PX, l['c1'] - kx * S.N * S.PX])
                fila = dict(seed=seed, obj=nom, NA=NA, w=w, datos=etq, NAz_fila=r['NAz_fila'], NAz_col=r['NAz_col'],
                            rb=r['rb_bins'], s_row=r['s_row'], s_col=r['s_col'], sesgo_centros=sesgo)
                out.append(fila)
                print(f"s{seed} {nom:13s} NA {NA:.4f} {etq:9s}: NA·z {r['NAz_fila']:.3f}/{r['NAz_col']:.3f} rb {r['rb_bins']:.2f} "
                      f"s {r['s_row']:.2f}/{r['s_col']:.2f} (verdad rb {NA / S.LAM * S.N * S.PX:.2f}, s ~50.3)", flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados', 'diag_espectral.json'), 'w'), indent=1)

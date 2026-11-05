"""diag_rb0.py -- hipótesis: el sesgo del método espectral viene de la búsqueda, no de la física.
La etapa 1 de paso_espectral_0311 busca el CENTRO con el radio fijo en rb0 = 0.0669/0.63/df (54.8 bins); si el radio verdadero
es mayor, el centro se corre hacia afuera para que el arco lejano (el único que sobrevive a 'keep') quede tangente por dentro,
y la etapa 2 solo deja mover el centro ±3 bins. Prueba sobre los recortes con ruido de la semilla 0 (imgs_*_s0.npz):
  original     : espectral() sin cambios
  rb0_verdad   : igual pero con rb0 = radio verdadero (oráculo, solo diagnóstico)
  etapa1_radio : etapa 1 con radio libre en 7 valores 0.92-1.20·rb0 y etapa 2 en 0.88-1.25·rb0 (no usa la verdad)
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import sys
sys.dont_write_bytecode = True
import glob
import json
import numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_borde as S  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados')


def espectral_var(imgs, modo, rb_verdad):
    rb0 = 0.0669 / S.lam / S.df
    if modo == 'rb0_verdad':
        rb0 = rb_verdad
    rows = []
    for dd in S.BF5:
        k = (17 + dd[0], 15 + dd[1])
        I = imgs[dd].astype(float); I = (I - I.mean()) * S.win
        L = gaussian_filter(np.log(np.abs(np.fft.fftshift(np.fft.fft2(I))) + 1e-6), 2.0)
        n0 = (k[0] - 17) * S.PITCH / 102 / S.lam / S.df; n1 = ((k[1] - 15) * S.PITCH + 0.529) / 102 / S.lam / S.df
        r1 = [rb0] if modo != 'etapa1_radio' else list(rb0 * np.linspace(0.92, 1.20, 7))
        c0, c1, rb = S.grid(L, n0, n1, r1, half=round(0.45 * rb0), step=1.0)
        c0, c1, rb = S.grid(L, c0, c1, rb0 * (np.linspace(0.90, 1.15, 26) if modo != 'etapa1_radio' else np.linspace(0.88, 1.25, 38)), half=3, step=0.5)
        c0, c1, rb = S.grid(L, c0, c1, rb + np.arange(-0.6, 0.61, 0.15), half=0.75, step=0.125)
        if (c0 - n0) ** 2 + (c1 - n1) ** 2 > (c0 + n0) ** 2 + (c1 + n1) ** 2: c0, c1 = -c0, -c1
        rows.append(dict(led=list(k), c0=float(c0), c1=float(c1), rb=float(rb)))
    g = {tuple(r["led"]): r for r in rows}
    s_col = (g[(17, 16)]["c1"] - g[(17, 14)]["c1"]) / 2; s_row = (g[(18, 15)]["c0"] - g[(16, 15)]["c0"]) / 2
    rb = float(np.mean([r["rb"] for r in rows]))
    return dict(rb=rb, s_row=float(s_row), s_col=float(s_col), NAz_fila=rb / s_row * S.PITCH, NAz_col=rb / s_col * S.PITCH)


def main():
    caso = sys.argv[1]
    NA = 0.070 if caso.startswith('A') else 0.0744
    d = np.load(os.path.join(RES, f'imgs_{caso}_s0.npz'))
    imgs = {dd: d[f'n_{dd[0]}_{dd[1]}'][S.CR0:S.CR0 + S.NCR, S.CC0:S.CC0 + S.NCR] for dd in S.BF5}
    rbv = NA / S.LAM * S.N * S.PX
    out = dict(caso=caso, NAz_verdad=NA * 99.5, rb_verdad=rbv)
    for modo in ('original', 'rb0_verdad', 'etapa1_radio'):
        out[modo] = espectral_var(imgs, modo, rbv)
        r = out[modo]
        print(f"{caso} {modo:12s}: NA·z {r['NAz_fila']:.3f}/{r['NAz_col']:.3f} rb {r['rb']:.2f} (verdad {rbv:.2f}) "
              f"s {r['s_row']:.2f}/{r['s_col']:.2f} | verdad NA·z {NA * 99.5:.3f}", flush=True)
    json.dump(out, open(os.path.join(RES, f'diag_rb0_{caso}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

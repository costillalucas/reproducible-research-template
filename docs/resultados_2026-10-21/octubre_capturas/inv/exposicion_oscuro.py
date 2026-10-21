"""exposicion_oscuro.py -- linealidad del tiempo de integración del sensor con píxeles calientes de los oscuros:
2026-10-02_red_oscura (16/32/64/128/256 ms, mismo LED apagado) y 2026-10-16-muestrasinluz2 / 2026-10-20-muestrasinluz
(5/10/128/257 ms, distintas carpetas de LED). Señal caliente = píxel - mediana del frame; píxeles = top 0.05 % a la t máxima
(sin saturar); ajuste s(t) = a (t + t0) por mínimos cuadrados sobre la mediana de los píxeles calientes. Escribe exposicion_oscuro.json."""
import glob, json, os, numpy as np, tifffile as T
B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas'); HERE = os.path.dirname(os.path.abspath(__file__))
def frm(d):
    fs = sorted(glob.glob(d + '/imagen_frame_*.tiff')); return np.mean([T.imread(f).astype(float) for f in fs], 0)
cases = {'2026-10-02_red_oscura': {t: f'{B}/2026-10-02_red_oscura/fila18_col15_colorr/{t}ms' for t in (16, 32, 64, 128, 256)}}
for s in ('2026-10-16-muestrasinluz2', '2026-10-20-muestrasinluz', '2026-10-09-muestrasinluz'):
    cases[s] = {5: f'{B}/{s}/fila17_col15_colorr/5ms', 10: f'{B}/{s}/fila18_col14_colorr/10ms',
                128: f'{B}/{s}/fila16_col15_colorr/128ms', 257: f'{B}/{s}/fila20_col15_colorr/257ms'}
out = {}
for s, c in cases.items():
    F = {t: frm(d) for t, d in c.items()}; tm = max(F)
    h = {t: f - np.median(f) for t, f in F.items()}
    thr = np.quantile(h[tm], 0.9995); m = (h[tm] > thr) & (F[tm] < 4000)
    ts = np.array(sorted(F)); v = np.array([np.median(h[t][m]) for t in ts])
    A = np.c_[ts, np.ones(len(ts))]; cf, *_ = np.linalg.lstsq(A, v, rcond=None)
    out[s] = dict(t=ts.tolist(), señal_caliente=v.tolist(), n_px=int(m.sum()), pendiente=float(cf[0]), t0_ms=float(cf[1] / cf[0]),
                  mediana_frame={int(t): float(np.median(F[t])) for t in ts},
                  cociente_tmax_tmin_medido=float(v[-1] / v[0]), cociente_nominal=float(ts[-1] / ts[0]))
    print(s, out[s])
json.dump(out, open(f'{HERE}/exposicion_oscuro.json', 'w'), indent=1)

"""qc.py -- QC de la captura roja 21/10 desde inv.npz (inventario.py).
Completitud, exposiciones, oscuro (por exposición; el oscuro de cada LED se toma de la carpeta con la MISMA exposición: hay oscuros
de 5/128/257 ms, que son las únicas exposiciones usadas), señal sobre oscuro por LED y por anillo (cuentas y cuentas/ms), SNR por
píxel (σ de UN frame), saturación, flat (forma, viñeteo, BF/DF) y centrado del eje con los arcos de frontera BF/DF de los 4 vecinos de
(17,15) en el flat (y en la muestra, control). Escribe qc.json y figs/qc_*.png."""
import json, os
import numpy as np
from scipy.ndimage import gaussian_filter1d, gaussian_filter
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
d = np.load(os.path.join(HERE, 'inv.npz'))
PXSTEP = 3538.0 / 4   # px (binneado 4) por paso de LED en el plano imagen (visionpoint 21/10, sistema no telecéntrico)


def tab(tag):
    return {tuple(map(int, k)): i for i, k in enumerate(d[f'{tag}_k'])}


Ts, Tf, Td = tab('muestra'), tab('flat'), tab('oscuro')
out = {}
ALL = {(r, c) for r in range(10, 25) for c in range(8, 23)}
out['completitud'] = dict(muestra=len(Ts), flat=len(Tf), faltan_muestra=sorted(ALL - set(Ts)), faltan_flat=sorted(ALL - set(Tf)),
                          frames=sorted(set(d['muestra_nfr'].tolist()) | set(d['flat_nfr'].tolist())),
                          misma_exposicion_muestra_flat=bool(all(d['muestra_t'][Ts[k]] == d['flat_t'][Tf[k]] for k in Ts)))
exps = {}
for k, i in Ts.items():
    exps.setdefault(int(d['muestra_t'][i]), []).append(k)
out['exposiciones'] = {str(t): (sorted(v) if len(v) < 20 else len(v)) for t, v in sorted(exps.items())}
# oscuros
dk = {int(d['oscuro_t'][i]): dict(media=float(d['oscuro_mean'][i]), media_recorte=float(d['oscuro_mean_c'][i]), sigma=float(d['oscuro_sig'][i]),
                                  max=float(d['oscuro_max'][i]), led=list(k)) for k, i in Td.items()}
out['oscuros'] = dk
dsm = {int(d['oscuro_t'][i]): d['oscuro_sm'][i].astype(float) for k, i in Td.items()}


def ring(k):
    return float(np.hypot(k[0] - 17, k[1] - 15))


per = {}
for k, i in Ts.items():
    t = int(d['muestra_t'][i]); j = Tf[k]; dm = dk[t]['media_recorte']
    s_c = d['muestra_mean_c'][i] - dm; f_c = d['flat_mean_c'][j] - dm
    per[k] = dict(t=t, ring=ring(k), S_cuentas=float(s_c), S_cms=float(s_c / t), F_cms=float(f_c / t), snr=float(s_c / d['muestra_sig_c'][i]),
                  max_muestra=float(d['muestra_max'][i]), max_flat=float(d['flat_max'][j]), sat_muestra=int(d['muestra_nsat'][i]), sat_flat=int(d['flat_nsat'][j]),
                  sig_frame=float(d['muestra_sig_c'][i]), frac_rango=float(d['muestra_max'][i] / 4095))
# BF/DF: fracción del frame del flat con señal > 50 % del máximo del BF central (en cuentas/ms)
f0 = (d['flat_sm'][Tf[(17, 15)]] - dsm[int(d['flat_t'][Tf[(17, 15)]])]) / d['flat_t'][Tf[(17, 15)]]
lvl = np.median(f0)
for k, p in per.items():
    j = Tf[k]; t = int(d['flat_t'][j]); fk = (d['flat_sm'][j] - dsm[t]) / t
    p['frac_BF_frame'] = float((fk > 0.5 * lvl).mean()); p['frac_BF_recorte'] = float((fk[90:190, 90:190] > 0.5 * lvl).mean())
    p['clase'] = 'BF' if p['frac_BF_recorte'] > 0.99 else ('DF' if p['frac_BF_frame'] < 0.01 else 'mixto')
out['por_led'] = {f'{k[0]},{k[1]}': v for k, v in per.items()}
out['clases'] = {c: sorted([list(k) for k, v in per.items() if v['clase'] == c]) for c in ('BF', 'mixto')}
out['clases']['n_DF'] = sum(v['clase'] == 'DF' for v in per.values())
rb = {}
for k, v in per.items():
    rb.setdefault(int(round(v['ring'])), []).append(v)
out['anillos'] = {str(q): dict(n=len(v), t=sorted({x['t'] for x in v}), S_cuentas_med=float(np.median([x['S_cuentas'] for x in v])),
                               S_cms_med=float(np.median([x['S_cms'] for x in v])), F_cms_med=float(np.median([x['F_cms'] for x in v])),
                               snr_med=float(np.median([x['snr'] for x in v])), frac_rango_max=float(max(x['frac_rango'] for x in v)))
                  for q, v in sorted(rb.items())}
out['saturacion'] = dict(leds_muestra=[list(k) for k, v in per.items() if v['sat_muestra']], leds_flat=[list(k) for k, v in per.items() if v['sat_flat']],
                         max_crudo_muestra=float(d['muestra_max'].max()), max_crudo_flat=float(d['flat_max'].max()))
bf5 = [k for k in per if per[k]['t'] == 5]
out['BF_5ms'] = {f'{k[0]},{k[1]}': dict(max=per[k]['max_muestra'], frac_rango=per[k]['frac_rango'], media_sobre_oscuro=per[k]['S_cuentas'],
                                        frac_rango_media=(per[k]['S_cuentas'] + dk[5]['media_recorte']) / 4095) for k in bf5}
# forma del flat (17,15): viñeteo
H = f0.shape[0]; yy, xx = np.mgrid[:H, :H]; w = f0.sum(); cy, cx = (f0 * yy).sum() / w, (f0 * xx).sum() / w
fs = gaussian_filter(f0, 6)
out['flat_17_15'] = dict(cms_centro=float(fs[130:150, 130:150].mean()), esquinas_sobre_centro=[float(fs[a:a + 20, b:b + 20].mean() / fs[130:150, 130:150].mean())
                         for a, b in ((5, 5), (5, 255), (255, 5), (255, 255))], recorte400_minmax_sobre_media=[float(fs[90:190, 90:190].min() / fs[90:190, 90:190].mean()),
                         float(fs[90:190, 90:190].max() / fs[90:190, 90:190].mean())], centroide_px_full=[float(cy * 4 + 1.5), float(cx * 4 + 1.5)])


# centrado del eje: arcos de frontera de los 4 vecinos BF de (17,15). Perfil por el centro (banda de 40 px binneados) a lo largo del
# eje del LED; frontera = cruce del 50 % entre plateau BF y nivel DF. Con eje centrado los arcos opuestos son simétricos.
def cruce(prof):
    p = gaussian_filter1d(prof, 1.5); hi = np.percentile(p, 90); lo = np.percentile(p, 3); h = 0.5 * (hi + lo)
    i = np.where(np.diff(np.sign(p - h)) != 0)[0]
    return [float(x + (h - p[x]) / (p[x + 1] - p[x])) for x in i]


def arcos(tag):
    T = tab(tag); res = {}
    for k in ((16, 15), (18, 15), (17, 14), (17, 16)):
        j = T[k]; t = int(d[f'{tag}_t'][j]); im = (d[f'{tag}_sm'][j] - dsm[t]) / t
        prof = im[:, 120:160].mean(1) if k[1] == 15 else im[120:160, :].mean(0)
        c = cruce(prof); res[f'{k[0]},{k[1]}'] = c
    def sel(c, lado):   # cruce más cercano al centro del lado esperado
        c = [x for x in c if (x < 140) == (lado < 0)]
        return min(c, key=lambda x: abs(x - 140)) if c else None
    # (18,15) es BF en +y (abajo) -> su frontera está ARRIBA (y<140); (16,15) abajo; (17,16) BF a la derecha -> frontera a la izquierda
    y18, y16 = sel(res['18,15'], -1), sel(res['16,15'], +1); x16, x14 = sel(res['17,16'], -1), sel(res['17,14'], +1)
    o = dict(cruces=res, y_18_15=y18, y_16_15=y16, x_17_16=x16, x_17_14=x14)
    if y18 and y16:
        o['eje_dy_px_bin4'] = (y18 + y16) / 2 - 139.5; o['eje_dfila_pasos'] = o['eje_dy_px_bin4'] / PXSTEP
        o['semiancho_y_px_full'] = (y16 - y18) / 2 * 4
    if x16 and x14:
        o['eje_dx_px_bin4'] = (x16 + x14) / 2 - 139.5; o['eje_dcol_pasos'] = o['eje_dx_px_bin4'] / PXSTEP
        o['semiancho_x_px_full'] = (x14 - x16) / 2 * 4
    return o


out['eje'] = {'flat': arcos('flat'), 'muestra': arcos('muestra')}
json.dump(out, open(os.path.join(HERE, 'qc.json'), 'w'), indent=1)
for s in ('completitud', 'exposiciones', 'oscuros', 'clases', 'saturacion', 'BF_5ms', 'flat_17_15', 'eje'):
    print(s, json.dumps(out[s]))
for q, v in out['anillos'].items():
    print('anillo', q, v)

# figuras
fig, ax = plt.subplots(1, 3, figsize=(16, 5))
M = np.full((15, 15), np.nan); Mf = M.copy(); Mn = M.copy()
for k, v in per.items():
    M[k[0] - 10, k[1] - 8] = v['S_cms']; Mf[k[0] - 10, k[1] - 8] = v['F_cms']; Mn[k[0] - 10, k[1] - 8] = v['snr']
for a, A, tt in ((ax[0], M, 'muestra: cuentas/ms sobre oscuro (recorte 400)'), (ax[1], Mf, 'flat: cuentas/ms sobre oscuro'), (ax[2], Mn, 'SNR por píxel (muestra, 1 frame)')):
    im = a.imshow(np.log10(np.clip(A, 1e-3, None)), extent=(7.5, 22.5, 24.5, 9.5), cmap='viridis'); plt.colorbar(im, ax=a, label='log10')
    a.set_title(tt, fontsize=10); a.set_xlabel('columna'); a.set_ylabel('fila'); a.plot(15, 17, 'r+', ms=12)
    for k, v in per.items():
        if v['clase'] == 'BF':
            a.plot(k[1], k[0], 'wo', mfc='none', ms=9)
plt.tight_layout(); plt.savefig(os.path.join(HERE, 'figs', 'qc_mapas.png'), dpi=110); plt.close()
fig, ax = plt.subplots(1, 5, figsize=(20, 4.4))
for a, k in zip(ax, ((17, 15), (16, 15), (18, 15), (17, 14), (17, 16))):
    j = Tf[k]; t = int(d['flat_t'][j]); im = (d['flat_sm'][j] - dsm[t]) / t
    a.imshow(im, cmap='gray'); a.set_title(f'flat {k} {t} ms'); a.axhline(139.5, color='r', lw=.5); a.axvline(139.5, color='r', lw=.5)
    a.add_patch(plt.Rectangle((90, 77.5), 100, 100, fill=False, color='y'))
    a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig(os.path.join(HERE, 'figs', 'qc_flat_bf.png'), dpi=90); plt.close()

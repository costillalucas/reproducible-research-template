"""qc.py -- QC de los sets de octubre a partir de inv/<set>.npz (inventario.py) y referencia 28/09b (prep.npz / prep_stats.json).

Por set: tipo inferido (oscuro / flat / muestra) desde el nivel y el contraste de alta frecuencia del BF (17,15);
mapa de exposiciones; saturación; LED más brillante; por anillo (int(hypot(r-17.5, c-15))): mediana sobre LEDs de
(media del recorte - oscuro) en cuentas y en cuentas/ms, SNR por píxel = (media - oscuro)/σ_pix (σ de la media de los 2
frames, de la diferencia de frames); para muestras con flat, también la señal propia de la muestra (S - F) por anillo.
Campo: correlación normalizada (fase) del BF (17,15) de cada muestra contra cada otra y contra 28/09b. Escribe qc.json."""
import json, os, glob
import numpy as np
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, '..', '..'))
SETS = sorted(os.path.basename(p)[:-4] for p in glob.glob(f'{HERE}/2026-*.npz'))


def L(s):
    d = np.load(f'{HERE}/{s}.npz')
    keys = [tuple(k) for k in d['keys']]
    return d, keys


def ring(k):
    return float(np.hypot(k[0] - 17.5, k[1] - 15))


def hp_contrast(im):
    im = im.astype(float); lp = gaussian_filter(im, 8)
    return float(np.std(im - lp) / max(np.mean(im), 1e-9))


info = {}
for s in SETS:
    d, keys = L(s)
    t = d['t']; mean = d['mean']
    i0 = [i for i, k in enumerate(keys) if k == (17, 15)]
    bf = d['sm'][i0[0]] if i0 else d['sm'][0]
    exps = {}
    for k, tt in zip(keys, t):
        exps.setdefault(int(tt), []).append(list(map(int, k)))
    ib = int(np.argmax(mean / t))
    info[s] = dict(n=len(keys), colores=sorted(set(d['color'].tolist())), nfr=sorted(set(d['nfr'].tolist())),
                   exposiciones={str(a): (len(b) if len(b) > 8 else b) for a, b in sorted(exps.items())},
                   media_global=float(np.median(mean)), bf_17_15_media=float(mean[i0[0]]) if i0 else None,
                   bf_hp_contraste=hp_contrast(bf), led_mas_brillante=list(map(int, keys[ib])), max_cuentas_ms=float((mean / t)[ib]),
                   leds_con_saturados_full=[list(map(int, k)) for k, n in zip(keys, d['nsat_full']) if n > 0],
                   leds_con_saturados_recorte=int((d['nsat_c'] > 0).sum()), max_crudo=float(d['max'].max()))

# tipo
for s, v in info.items():
    v['tipo'] = 'oscuro' if v['media_global'] < 200 and (v['bf_17_15_media'] or 0) < 200 else (
        'flat?' if v['bf_hp_contraste'] < 0.01 else 'muestra?')

# pares (muestra, oscuro, flat) por fecha: oscuro/flat = los únicos de la fecha
PAIR = {
    '2026-10-02_red_enfocado': ('2026-10-02_red_oscura', '2026-10-02_red_sin_muestra'),
    '2026-10-09': ('2026-10-09-muestrasinluz', '2026-10-09-sinmuestra'),
    '2026-10-09-b': ('2026-10-09-muestrasinluz', '2026-10-09-sinmuestra'),
    '2026-10-09-c': ('2026-10-09-muestrasinluz', '2026-10-09-sinmuestra'),
    '2026-10-09-d': ('2026-10-09-muestrasinluz', '2026-10-09-sinmuestra'),
    '2026-10-09-e': ('2026-10-09-muestrasinluz', '2026-10-09-sinmuestra'),
    '2026-10-09-muestra': ('2026-10-09-muestrasinluz', '2026-10-09-sinmuestra'),
    '2026-10-16-a': ('2026-10-16-muestrasinluz2', '2026-10-16-luzsinmuestra'),
    '2026-10-16-muestra2': ('2026-10-16-muestrasinluz2', '2026-10-16-luzsinmuestra'),
    '2026-10-20-muestra': ('2026-10-20-muestrasinluz', '2026-10-20-luzsinmuestra'),
}


def darkmap(s):
    """{(k,t): media del recorte} y {t: media} de un set de oscuros."""
    d, keys = L(s)
    per = {(k, int(tt)): float(m) for k, tt, m in zip(keys, d['t'], d['mean'])}
    byt = {}
    for (k, tt), m in per.items():
        byt.setdefault(tt, []).append(m)
    return per, {tt: float(np.mean(v)) for tt, v in byt.items()}


def dark_for(per, byt, k, t):
    if (k, t) in per:
        return per[(k, t)], 'mismo LED/t'
    if t in byt:
        return byt[t], 'misma t'
    ts = np.array(sorted(byt)); vs = np.array([byt[x] for x in ts])
    return float(np.interp(t, ts, vs)), 'interpolado en t'


rings = {}
for s, (dk, fl) in PAIR.items():
    if s not in info or dk not in info:
        continue
    d, keys = L(s); per, byt = darkmap(dk)
    df_, fk = L(fl) if fl in info else (None, None)
    fidx = {k: i for i, k in enumerate(fk)} if fk else {}
    fper, fbyt = darkmap(dk)
    rows = []
    how = set()
    for i, k in enumerate(keys):
        tt = int(d['t'][i]); dm, h = dark_for(per, byt, k, tt); how.add(h)
        sig = float(d['mean'][i] - dm); sp = float(d['noise'][i] / np.sqrt(2))
        r = dict(k=k, t=tt, sobre_oscuro=sig, cms=sig / tt, snr=sig / sp, ring=ring(k))
        if k in fidx:
            j = fidx[k]; tf = int(df_['t'][j]); dmf, _ = dark_for(fper, fbyt, k, tf)
            F = (df_['sm'][j] - dmf) / tf; S = (d['sm'][i] - dm) / tt
            r['flat_cms'] = float(F.mean()); r['t_flat'] = tf
            r['muestra_menos_flat_cms'] = float(np.mean(S - gaussian_filter(F, 2)))   # sm = bin 4 -> sigma 8 px = 2
            r['muestra_menos_flat_abs_cms'] = float(np.mean(np.abs(S - gaussian_filter(F, 2))))
        rows.append(r)
    info[s]['oscuro_usado'] = dk; info[s]['flat_usado'] = fl; info[s]['oscuro_como'] = sorted(how)
    info[s]['exposicion_flat_igual'] = bool(all(r.get('t_flat', r['t']) == r['t'] for r in rows))
    rb = {}
    for r in rows:
        rb.setdefault(int(r['ring']), []).append(r)
    rings[s] = {str(q): dict(n=len(v), t=sorted({x['t'] for x in v}), sobre_oscuro=float(np.median([x['sobre_oscuro'] for x in v])),
                             cms=float(np.median([x['cms'] for x in v])), snr=float(np.median([x['snr'] for x in v])),
                             muestra_menos_flat_abs_cms=(float(np.median([x['muestra_menos_flat_abs_cms'] for x in v]))
                                                         if 'muestra_menos_flat_abs_cms' in v[0] else None))
                for q, v in sorted(rb.items())}

# 28/09b rojo: prep_stats (crop mean over dark, counts/ms) y ruido de prep.npz
p28 = os.path.join(RES, 'captura_2026-09-28b', 'red')
ps = json.load(open(f'{p28}/prep_stats.json'))['per_led']; pz = np.load(f'{p28}/prep.npz')
pk = [tuple(map(int, k)) for k in pz['keys']]
rb = {}
for i, k in enumerate(pk):
    v = ps[f'{k[0]},{k[1]}']; t = v['t']; sp = np.sqrt(float(pz['V'][i])) * t
    S = pz['S'][i].astype(float); F = pz['F'][i].astype(float)
    rb.setdefault(int(ring(k)), []).append(dict(t=t, sobre_oscuro=v['counts_over_dark'], cms=v['S_mean'], snr=v['counts_over_dark'] / sp,
                                               mfa=float(np.mean(np.abs(S - gaussian_filter(F, 8))))))
rings['28b_red'] = {str(q): dict(n=len(v), t=sorted({x['t'] for x in v}), sobre_oscuro=float(np.median([x['sobre_oscuro'] for x in v])),
                                 cms=float(np.median([x['cms'] for x in v])), snr=float(np.median([x['snr'] for x in v])),
                                 muestra_menos_flat_abs_cms=float(np.median([x['mfa'] for x in v])))
                    for q, v in sorted(rb.items())}

# correlación de campo (BF (17,15), recorte 400 binneado 4 -> 100²; 28/09b: S de prep.npz binneado igual)
def pc(a, b):
    a = (a - gaussian_filter(a, 6)); b = (b - gaussian_filter(b, 6))
    A = np.fft.fft2(a); Bf = np.fft.fft2(b); Rr = np.real(np.fft.ifft2(A * np.conj(Bf)))
    Rr /= np.sqrt((a ** 2).sum() * (b ** 2).sum())
    i = np.unravel_index(np.argmax(Rr), Rr.shape); sh = [(x if x < 50 else x - 100) for x in i]
    return float(Rr.max()), sh


def full_bf(s):
    d = np.load(f'{HERE}/{s}.npz'); nm = [n for n in d.files if n.startswith('full_17_15_')][0]
    return d[nm].reshape(280, 4, 280, 4).mean((1, 3)).astype(float)


muestras = [s for s in PAIR if s in info]
bfs = {s: L(s)[0]['sm'][L(s)[1].index((17, 15))].astype(float) for s in muestras}
bfs['28b_red'] = pz['S'][pk.index((17, 15))].astype(float).reshape(100, 4, 100, 4).mean((1, 3))
corr = {}
for a in bfs:
    for b in bfs:
        if a < b:
            corr[f'{a}|{b}'] = pc(bfs[a], bfs[b])
# frames completos (1120 -> 280) entre muestras de octubre: detecta corrimientos > recorte
fullc = {}
fb = {s: full_bf(s) for s in muestras}
for a in fb:
    for b in fb:
        if a < b:
            A = fb[a] - gaussian_filter(fb[a], 6); Bb = fb[b] - gaussian_filter(fb[b], 6)
            Rr = np.real(np.fft.ifft2(np.fft.fft2(A) * np.conj(np.fft.fft2(Bb)))) / np.sqrt((A ** 2).sum() * (Bb ** 2).sum())
            i = np.unravel_index(np.argmax(Rr), Rr.shape)
            fullc[f'{a}|{b}'] = [float(Rr.max()), [int(x if x < 140 else x - 280) for x in i]]

json.dump(dict(sets=info, anillos=rings, corr_bf_recorte_bin4=corr, corr_bf_full_bin4=fullc), open(f'{HERE}/qc.json', 'w'), indent=1,
          default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
for s, v in info.items():
    print(s, v['tipo'], 'n', v['n'], 'exp', v['exposiciones'], 'med %.0f' % v['media_global'], 'BF %s' % v['bf_17_15_media'],
          'hp %.3f' % v['bf_hp_contraste'], 'brillante', v['led_mas_brillante'], '%.1f c/ms' % v['max_cuentas_ms'],
          'sat', v['leds_con_saturados_full'], 'max', v['max_crudo'], v.get('oscuro_como'), v.get('exposicion_flat_igual'))
for s, r in rings.items():
    print(s, ' '.join(f"r{q}:{x['sobre_oscuro']:.1f}c/{x['snr']:.1f}snr/{x['muestra_menos_flat_abs_cms'] or 0:.3f}" for q, x in r.items()))
for k, v in corr.items():
    print('corr', k, v)
for k, v in fullc.items():
    print('full', k, v)

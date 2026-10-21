"""prep_oct.py -- preprocesado de un set rojo de octubre; = results/captura_2026-09-28b/prep_color.py (mismo prep.npz) con:
  * oscuro POR LED Y EXPOSICIÓN, pixel a pixel (cada carpeta fila*_col*/<t>ms del/los set(s) de oscuros; si hay dos sets de
    oscuros, promedio de los 4 frames); la muestra y el flat usan el mismo oscuro del mismo LED/t.
  * exposición efectiva t_ef = t + T0 (T0 medido en inv/exposicion.json con el mismo campo a 4/5/8/16 ms; por defecto -0.20 ms).
  * cada LED tiene UNA exposición en estos sets (BF 5 ms, (18,14),(18,16) 10 ms, (16,15),(19,15) 128 ms, resto 257 ms); el flat
    tiene las mismas.
  S_k = (mean(f1,f2) - dark_k,t) / t_ef;  F_k = (mean flat - dark_k,tf) / tf_ef;  V_k, SAT_k como en prep_color.py.
Uso: python3 prep_oct.py SET_MUESTRA SET_FLAT SET_OSCURO[,SET_OSCURO2] SALIDA [T0]"""
import glob, json, os, sys
import numpy as np
import tifffile as T

SMn, FLn, DKn, OUTn = sys.argv[1:5]
T0 = float(sys.argv[5]) if len(sys.argv) > 5 else -0.20
B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
SM, FL, DKS = f'{B}/{SMn}', f'{B}/{FLn}', [f'{B}/{x}' for x in DKn.split(',')]
C = slice(360, 760)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTn); os.makedirs(OUT, exist_ok=True)


def frames(d):
    fs = sorted(glob.glob(f'{d}/imagen_frame_*.tiff')); assert len(fs) == 2, (d, fs)
    return [T.imread(f)[C, C].astype(float) for f in fs]


def tdir(d):
    ts = [int(os.path.basename(x)[:-2]) for x in glob.glob(d + '/*ms')]; assert len(ts) == 1, (d, ts); return ts[0]


def dkdir(D, nm):
    """carpeta de oscuro del LED; si el set de oscuros tiene una sola carpeta (2026-10-02_red_oscura: fila18_col15 a 16..256 ms),
    se usa esa para todos los LEDs (el oscuro no depende del LED)."""
    if os.path.isdir(f'{D}/{nm}'):
        return f'{D}/{nm}'
    ds = glob.glob(f'{D}/fila*_col*_color*'); assert len(ds) == 1, (D, nm); return ds[0]


keys = sorted(tuple(int(v) for v in os.path.basename(f)[4:].split('_colorr')[0].split('_col')) for f in glob.glob(f'{SM}/fila*_col*_colorr'))
assert len(keys) == 225 and set(keys) == {(r, c) for r in range(11, 26) for c in range(8, 23)}
S, F, V, VF, SAT, TT, info = [], [], [], [], [], [], {}
for k in keys:
    nm = f'fila{k[0]}_col{k[1]}_colorr'
    t = tdir(f'{SM}/{nm}'); tf = tdir(f'{FL}/{nm}')
    dk = {tt: np.mean([f for D in DKS for f in frames(f'{dkdir(D, nm)}/{tt}ms')], 0) for tt in {t, tf}}
    s1, s2 = frames(f'{SM}/{nm}/{t}ms'); f1, f2 = frames(f'{FL}/{nm}/{tf}ms')
    te, tfe = t + T0, tf + T0
    S.append(((s1 + s2) / 2 - dk[t]) / te); F.append(((f1 + f2) / 2 - dk[tf]) / tfe)
    SAT.append((s1 >= 4095) | (s2 >= 4095)); TT.append(t)
    for dd, L, tt in ((s1 - s2, V, te), (f1 - f2, VF, tfe)):
        L.append((1.4826 * np.median(np.abs(dd - np.median(dd)))) ** 2 / 4 / tt ** 2)
    info[f'{k[0]},{k[1]}'] = dict(t=t, t_flat=tf, t_ef=te, S_mean=float(S[-1].mean()), F_mean=float(F[-1].mean()),
                                 sat=int(SAT[-1].sum()), counts_over_dark=float(S[-1].mean() * te), dark_mean=float(dk[t].mean()))
k0 = (17, 15); i0 = keys.index(k0); t0 = TT[i0]
s1, s2 = frames(f'{SM}/fila17_col15_colorr/{t0}ms'); dk0 = np.mean([f for D in DKS for f in frames(f'{dkdir(D, "fila17_col15_colorr")}/{t0}ms')], 0)
m = (s1 + s2) / 2 - dk0; d = s1 - s2
bins = np.quantile(m, np.linspace(0.02, 0.98, 12))
pts = np.array([(m[(m >= a) & (m < b)].mean(), d[(m >= a) & (m < b)].var() / 2) for a, b in zip(bins[:-1], bins[1:])])
g, r2 = np.polyfit(pts[:, 0], pts[:, 1], 1)
np.savez_compressed(os.path.join(OUT, 'prep.npz'), keys=np.array(keys), S=np.array(S, np.float32), F=np.array(F, np.float32),
                    V=np.array(V), VF=np.array(VF), SAT=np.array(SAT), t=np.array(TT), gain=g, read_var=r2)
json.dump(dict(per_led=info, gain=g, read_var=r2, T0=T0, muestra=SMn, flat=FLn, oscuros=DKn), open(os.path.join(OUT, 'prep_stats.json'), 'w'), indent=1)
bright = sorted(keys, key=lambda k: -info[f'{k[0]},{k[1]}']['S_mean'])[:8]
print(OUTn, '| 8 LEDs más brillantes (cuentas/ms):', [(k, round(info[f'{k[0]},{k[1]}']['S_mean'], 1)) for k in bright])
print(OUTn, '| LEDs con saturados:', sum(1 for s in SAT if s.any()), '| DF mediana sobre oscuro a la t máxima: %.1f cuentas' %
      np.median([v['counts_over_dark'] for v in info.values() if v['t'] == max(TT)]), '| ganancia %.3f e-/cuenta^-1, var lectura %.1f' % (g, r2))

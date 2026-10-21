"""prep_500.py (21/10 tarde) -- COPIA de ../captura_2026-10-21/prep_2110.py para la muestra nueva 2026-10-21.500 (esferas 500 nm),
misma geometría/flat/oscuros de la mañana. Cambios: carpeta de muestra, recorte filas 140:540, columnas 560:960 (arriba a la derecha:
evita la aguja, las partículas grandes y el arco), BF de la muestra a 8 ms (flat a 5 ms; cada uno normalizado por su t_ef y oscuro propio).

Original: prep_2110.py -- preprocesado de la captura roja 21/10 = results/octubre_capturas_2026-10-21/prep_oct.py con:
  * filas 10-24 (eje sobre el LED (17,15), centro de la grilla), una exposición por LED (BF 5 ms, anillo de 8 a 128 ms, resto 257 ms);
    las carpetas 10ms/64ms de organizado están vacías: no hay HDR que mezclar (igual que los sets de octubre).
  * oscuro POR EXPOSICIÓN, píxel a píxel: 2026-10-21-dark tiene una carpeta por exposición (5, 128, 257 ms; un LED cualquiera, el
    oscuro no depende del LED) -> se usa la de la misma t (no hace falta interpolar: 10 y 64 ms no se usan). Mismo oscuro para el flat.
  * recorte 400: filas 310:710, columnas 360:760 (50 px arriba del centro del ROI: deja fuera el grupo de esferas de abajo al centro;
    el eje local se corre 50/3538 = 0.014 pasos -> offset +0.085 mm en filas, ver runner_2110.py).
  * máscara de POLVO: la mancha negra nítida fija en el sensor (en flat Y muestra, misma posición para todos los LEDs, ~(600,572) px)
    cae dentro del recorte; píxeles con F(17,15)/gauss(F,15) < 0.8, dilatados 4 px, se enmascaran en TODOS los LEDs (como saturados).
  S_k = (mean(f1,f2) - dark_t) / t_ef;  F_k igual con el flat;  t_ef = t + T0 (T0 = -0.20 ms, inv/exposicion.json de octubre).
Uso: python3 prep_2110.py [T0]"""
import glob, json, os, sys
import numpy as np
import tifffile as T
from scipy.ndimage import gaussian_filter, binary_dilation

T0 = float(sys.argv[1]) if len(sys.argv) > 1 else -0.20
B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
SM, FL, DK = f'{B}/2026-10-21.500', f'{B}/2026-10-21-sinmuestra', f'{B}/2026-10-21-dark'
CY, CX = slice(140, 540), slice(560, 960)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r500_red'); os.makedirs(OUT, exist_ok=True)


def frames(d, full=False):
    fs = sorted(glob.glob(f'{d}/imagen_frame_*.tiff')); assert len(fs) == 2, (d, fs)
    return [T.imread(f).astype(float) if full else T.imread(f)[CY, CX].astype(float) for f in fs]


def tdir(d):
    ts = [int(os.path.basename(x)[:-2]) for x in glob.glob(d + '/*ms')]; assert len(ts) == 1, (d, ts); return ts[0]


DARK = {}
for d in glob.glob(f'{DK}/fila*_col*_colorr/*ms'):
    DARK[int(os.path.basename(d)[:-2])] = np.mean(frames(d), 0)
print('oscuros:', {t: round(float(v.mean()), 2) for t, v in sorted(DARK.items())})

keys = sorted(tuple(int(v) for v in os.path.basename(f)[4:].split('_colorr')[0].split('_col')) for f in glob.glob(f'{SM}/fila*_col*_colorr'))
assert len(keys) == 225 and set(keys) == {(r, c) for r in range(10, 25) for c in range(8, 23)}
# máscara de polvo desde el flat (17,15)
f1, f2 = frames(f'{FL}/fila17_col15_colorr/5ms'); f0 = (f1 + f2) / 2 - DARK[5]
DUST = binary_dilation(f0 / gaussian_filter(f0, 15) < 0.8, iterations=4)
print('polvo: %d px enmascarados (%.2f %%)' % (DUST.sum(), 100 * DUST.mean()))
S, F, V, VF, SAT, TT, info = [], [], [], [], [], [], {}
for k in keys:
    nm = f'fila{k[0]}_col{k[1]}_colorr'
    t = tdir(f'{SM}/{nm}'); tf = tdir(f'{FL}/{nm}')
    s1, s2 = frames(f'{SM}/{nm}/{t}ms'); f1, f2 = frames(f'{FL}/{nm}/{tf}ms')
    te, tfe = t + T0, tf + T0
    S.append(((s1 + s2) / 2 - DARK[t]) / te); F.append(((f1 + f2) / 2 - DARK[tf]) / tfe)
    SAT.append((s1 >= 4095) | (s2 >= 4095) | DUST); TT.append(t)
    for dd, L, tt in ((s1 - s2, V, te), (f1 - f2, VF, tfe)):
        L.append((1.4826 * np.median(np.abs(dd - np.median(dd)))) ** 2 / 4 / tt ** 2)
    info[f'{k[0]},{k[1]}'] = dict(t=t, t_flat=tf, t_ef=te, S_mean=float(S[-1].mean()), F_mean=float(F[-1].mean()),
                                 sat=int(((s1 >= 4095) | (s2 >= 4095)).sum()), counts_over_dark=float(S[-1].mean() * te), dark_mean=float(DARK[t].mean()))
s1, s2 = frames(f'{SM}/fila17_col15_colorr/8ms')
m = (s1 + s2) / 2 - DARK[8]; dd = s1 - s2
bins = np.quantile(m, np.linspace(0.02, 0.98, 12))
pts = np.array([(m[(m >= a) & (m < b)].mean(), dd[(m >= a) & (m < b)].var() / 2) for a, b in zip(bins[:-1], bins[1:])])
g, r2 = np.polyfit(pts[:, 0], pts[:, 1], 1)
np.savez_compressed(os.path.join(OUT, 'prep.npz'), keys=np.array(keys), S=np.array(S, np.float32), F=np.array(F, np.float32),
                    V=np.array(V), VF=np.array(VF), SAT=np.array(SAT), t=np.array(TT), gain=g, read_var=r2, DUST=DUST)
json.dump(dict(per_led=info, gain=g, read_var=r2, T0=T0, muestra=SM, flat=FL, oscuros=DK, recorte=[[140, 540], [560, 960]], polvo_px=int(DUST.sum())),
          open(os.path.join(OUT, 'prep_stats.json'), 'w'), indent=1)
bright = sorted(keys, key=lambda k: -info[f'{k[0]},{k[1]}']['S_mean'])[:8]
print('8 LEDs más brillantes (cuentas/ms):', [(k, round(info[f'{k[0]},{k[1]}']['S_mean'], 1)) for k in bright])
print('LEDs con saturados:', sum(1 for v in info.values() if v['sat']), '| DF mediana sobre oscuro a 257 ms: %.1f cuentas' %
      np.median([v['counts_over_dark'] for v in info.values() if v['t'] == 257]), '| ganancia %.3f, var lectura %.1f' % (g, r2))

"""informe.py -- tabla.md y fig_centrado.png a partir de tabla.json (centrado.py) y colapso.json (colapso.py)."""
import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
tab = json.load(open(os.path.join(OUT, 'tabla.json')))
col = json.load(open(os.path.join(OUT, 'colapso.json')))
VEC = ['(-1, -1)', '(-1, 0)', '(-1, 1)', '(0, -1)', '(0, 1)', '(1, -1)', '(1, 0)', '(1, 1)']
DIAG = ['(-1, -1)', '(-1, 1)', '(1, -1)', '(1, 1)']
ESQ = ['arr-izq', 'arr-der', 'abj-izq', 'abj-der']


def f3(x):
    return 'n/a' if x is None else f'{x:+.3f}'


L = ['# Centrado del eje: (a) modelo de borde vs (b) simetría de pares\n',
     'Generado por `centrado.py`, `colapso.py`, `informe.py` (esta carpeta). Desvíos en pasos de LED (fila, col) respecto de '
     '(17,15); filas crecientes = ABAJO en la imagen. s = 3538 px/paso (corrimiento no telecéntrico 0.001696 mm/px).\n',
     '## 1. Estimaciones por captura\n',
     '| captura | color | ROI | (a) eje | R (a) | w (a) px | (b) eje | R (b) | w (b) | (a) solo cruz | LOO fila min..max | (a) s libre: s, eje | (b) diagonales |',
     '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for r in tab:
    lo = np.array([v['eje'] for v in r['loo'].values()])
    L.append(f"| {r['nombre']} | {r['color']} | {r['roi'][0]},{r['roi'][1]} | ({f3(r['a']['eje'][0])}, {f3(r['a']['eje'][1])}) | "
             f"{r['a']['R_pasos']:.3f} | {r['a']['w_px']:.0f} | ({f3(r['b']['eje'][0])}, {f3(r['b']['eje'][1])})"
             f"{'' if r['b_aplica'] else ' *fila de (a)*'} | {r['b']['R_pasos']:.3f} | {r['b']['w_px']:.0f} | "
             f"({f3(r['a_cruz']['eje'][0])}, {f3(r['a_cruz']['eje'][1])}) R {r['a_cruz']['R_pasos']:.3f} | "
             f"{lo[:, 0].min():+.3f}..{lo[:, 0].max():+.3f} | {r['s_libre']['s']:.0f}, ({f3(r['s_libre']['eje'][0])}, {f3(r['s_libre']['eje'][1])}) | "
             f"{'n/a' if not r['b_diag'] else '(' + f3(r['b_diag'][0]) + ', ' + f3(r['b_diag'][1]) + ')'} |")
L += ['\n## 2. Amplitudes A_k del ajuste (a) (previa 1 ± 0.15; la cruz debería dar ~1 si los LEDs brillan igual)\n',
      '| captura | ' + ' | '.join(VEC) + ' |', '|---|' + '---|' * 8]
for r in tab:
    L.append(f"| {r['nombre']} | " + ' | '.join(f"{r['a_A'][k]:.2f}" for k in VEC) + ' |')
L += ['\n## 3. Diagonales: cociente observado en las esquinas (mediana de bloques 192 px, normalizado por A_ref) vs '
      'escalón predicho T (A = 1) bajo (a), (b) y (a) solo cruz\n',
      'Formato por esquina: obs / T(a) / T(b) / T(a cruz). Clase predicha con el borde duro (d < R) y, entre corchetes, con R ± w.\n',
      '| captura | LED | clase obs (f>0.5) | (a) | (b) | (a cruz) | arr-izq | arr-der | abj-izq | abj-der | margen |k-eje|-R (a / b) | margen en el ROI (a / b) |',
      '|---|---|---|---|---|---|---|---|---|---|---|---|']
for r in tab:
    for k in DIAG:
        o, pa, pb, px = r['obs'][k], r['pred']['a'][k], r['pred']['b'][k], r['pred']['a_cruz'][k]
        esq = ' | '.join(f"{o['reg'][e]:.2f} / {pa['reg'][e]:.2f} / {pb['reg'][e]:.2f} / {px['reg'][e]:.2f}" for e in ESQ)
        L.append(f"| {r['nombre']} | {k} | {o['clase']} | {pa['clase']} [{pa['clase_tol']}] | {pb['clase']} [{pb['clase_tol']}] | "
                 f"{px['clase']} [{px['clase_tol']}] | {esq} | {pa['marg_centro']:+.3f} / {pb['marg_centro']:+.3f} | "
                 f"{pa['marg_roi']:+.3f} / {pb['marg_roi']:+.3f} |")
L += ['\n## 4. Puntajes\n',
      'err_esq_diag = media |T(A=1) - obs| en las 16 esquinas de las diagonales (sin A_k libre); clases = acuerdo BF/mixto/DF '
      '(umbral 0.5·A_ref, ver caveat); LOO = cada vecino predicho por el ajuste (a) de los otros 7; a_cruz/b_cruz = ajuste '
      'solo con la cruz, puntuado solo en las diagonales. Monotonía (colapso.py): fracción de pares de bloques discordantes '
      '(más cerca del centro del círculo pero más oscuro) para el eje dado; "mejor" = eje que la minimiza.\n',
      '| captura | clases a / b / LOO | err_esq_diag a / b / LOO / a_cruz / b_cruz | monotonía (todos) a / b / a_cruz | '
      'mejor eje monotonía (rango fila ≤ mín+0.01) | monotonía cruz-diag a / b |', '|---|---|---|---|---|---|']
for r in tab:
    s = r['score']; c = col.get(r['nombre'])
    if c:
        cc = c['candidatos']
        mono = f"{cc['a']['viol_todos']:.3f} / {cc['b']['viol_todos']:.3f} / {cc['a_cruz']['viol_todos']:.3f}"
        best = f"({c['todos']['mejor'][0]:+.3f}, {c['todos']['mejor'][1]:+.3f}) fila {c['todos']['fila_rango'][0]:+.3f}..{c['todos']['fila_rango'][1]:+.3f}"
        cd = f"{cc['a']['viol_cd']:.3f} / {cc['b']['viol_cd']:.3f}"
    else:
        mono = best = cd = 'n/a'
    L.append(f"| {r['nombre']} | {s['a']['clases_ok']}/8 / {s['b']['clases_ok']}/8 / {s['loo']['clases_ok']}/8 | "
             f"{s['a']['err_esq_diag']:.3f} / {s['b']['err_esq_diag']:.3f} / {s['loo']['err_esq_diag']:.3f} / "
             f"{s['a_cruz']['err_esq_diag']:.3f} / {s['b_cruz']['err_esq_diag']:.3f} | {mono} | {best} | {cd} |")
open(os.path.join(OUT, 'tabla.md'), 'w').write('\n'.join(L) + '\n')

# figura: (izq) 3x3 de 2026-11-03-red con círculos (a), (b), (a cruz); (der arriba) ejes por captura; (der abajo) monotonía vs fila
r = next((x for x in tab if x['nombre'] == '2026-11-03-red'), tab[-1])
z = np.load(os.path.join(OUT, f"mapas_{r['nombre']}.npz"))
fig = plt.figure(figsize=(15, 8.5))
gs = fig.add_gridspec(3, 6)
th = np.linspace(0, 2 * np.pi, 800); S = 3538.0
for k in VEC:
    d = eval(k)
    a = fig.add_subplot(gs[d[0] + 1, d[1] + 1])
    a.imshow(z[f'q_{d[0]}_{d[1]}'], extent=(-560, 560, 560, -560), cmap='gray', vmin=0, vmax=1.1 if k not in DIAG else 0.35)
    for nm, cl in (('a', 'tab:red'), ('b', 'tab:cyan'), ('a_cruz', 'tab:orange')):
        p = r[nm]; R = p['R_pasos'] * S
        cy, cx = S * (d[0] - p['eje'][0]), S * (d[1] - p['eje'][1])
        a.plot(cx + R * np.cos(th), cy + R * np.sin(th), '-', color=cl, lw=1.2)
    a.set_xlim(-700, 700); a.set_ylim(700, -700); a.set_xticks([]); a.set_yticks([])
    a.plot([-560, 560, 560, -560, -560], [-560, -560, 560, 560, -560], 'y-', lw=.6)
    a.set_title(f"{(17 + d[0], 15 + d[1])}  esq: " + ' '.join(f"{r['obs'][k]['reg'][e]:.2f}" for e in ESQ), fontsize=7)
a = fig.add_subplot(gs[1, 1]); a.axis('off')
a.text(0.5, 0.5, f"{r['nombre']}\ncociente / A_ref\n(diagonales: escala 0-0.35)\nrojo (a), cian (b),\nnaranja (a) solo cruz\n"
       "esq: arr-izq arr-der\nabj-izq abj-der", ha='center', va='center', fontsize=8)
a = fig.add_subplot(gs[:2, 4:])
for i, x in enumerate(tab):
    y = i
    a.plot(x['a']['eje'][0], y, 'o', color='tab:red', label='(a) 8 vecinos' if i == 0 else None)
    a.plot(x['b']['eje'][0], y, 's', color='tab:cyan', label='(b) pares cruz' if i == 0 else None)
    a.plot(x['a_cruz']['eje'][0], y, '^', color='tab:orange', label='(a) solo cruz' if i == 0 else None)
    lo = [v['eje'][0] for v in x['loo'].values()]
    a.plot([min(lo), max(lo)], [y, y], '-', color='tab:red', alpha=.4, lw=4, label='(a) LOO rango' if i == 0 else None)
    if x['b_diag']:
        a.plot(x['b_diag'][0], y, 'x', color='k', label='simetría diagonales' if i == 0 else None)
    c = col.get(x['nombre'])
    if c:
        a.plot(c['todos']['fila_rango'], [y + 0.25] * 2, '-', color='tab:green', lw=2, label='monotonía ≤ mín+0.01' if i == 0 else None)
a.set_yticks(range(len(tab))); a.set_yticklabels([f"{x['nombre']} ({x['color']})" for x in tab], fontsize=8)
a.axvline(0, color='0.7', lw=.8); a.set_xlabel('desvío del eje en FILA (pasos de LED)'); a.legend(fontsize=7, loc='lower right')
a.set_xlim(-0.45, 0.45); a.invert_yaxis(); a.set_title('fila del eje según cada método', fontsize=10)
a = fig.add_subplot(gs[2, 4:])
for x in tab:
    c = col.get(x['nombre'])
    if c and x['nombre'] in ('2026-11-03-red', '2026-10-30-red-c', '2026-10-22', '2026-10-29-blue'):
        a.plot(c['curva_fila']['ars'], c['curva_fila']['viol_todos'], label=x['nombre'])
a.set_xlabel('fila del eje (pasos)'); a.set_ylabel('pares discordantes'); a.set_xlim(-0.2, 0.3); a.set_ylim(0, 0.15)
a.legend(fontsize=7); a.set_title('monotonía del perfil radial (sin modelo logístico, brillo igual)', fontsize=9)

fig.suptitle('Centrado: (a) modelo de borde vs (b) simetría de pares; corrimiento no telecéntrico incluido (s = 3538 px/paso)', fontsize=11)
fig.subplots_adjust(left=0.01, right=0.98, top=0.9, bottom=0.07, wspace=0.08, hspace=0.3); fig.savefig(os.path.join(OUT, 'fig_centrado.png'), dpi=90)
print('ok')

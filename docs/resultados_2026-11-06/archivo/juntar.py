"""Junta runs/*/zonas.json (+ resultados/2026-11-06 de zonas_3x3) en tabla.md/tabla.csv, correlaciones y fig_archivo.png."""
import json, os, glob, datetime
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
A = os.path.dirname(os.path.abspath(__file__))
meta = json.load(open(os.path.join(A, 'meta.json')))
jobs = {l.split('|')[0]: l.strip().split('|') for l in open(os.path.join(A, 'jobs.txt'))}
ROI_SIN_JSON = {'2026-10-21': '(4000,1942)*', '2026-10-21.500': '?*', '2026-10-21.c': '?*', '2026-10-21.d': '?*',
                '2026-10-02-viejo': '(4032,3040)?*', '2026-10-09-muestra': '(4032,3040)?*', '2026-10-16-muestra2': '(4032,3040)?*',
                '2026-10-16-a': '(4032,3040)?*', '2026-10-20-muestra': '(4032,3040)?*'}
filas = []
fuentes = glob.glob(os.path.join(A, 'runs', '*', 'zonas.json')) + \
    [os.path.join(A, '..', 'zonas_3x3', 'resultados', '2026-11-06', 'zonas.json')]
for fj in fuentes:
    for z in json.load(open(fj))['zonas']:
        n = z['etiqueta']; m = meta.get(n, {})
        b = z['borde']; a, sl = b['s_fijo'], b['s_libre']
        self_flat = jobs.get(n, ['', '', ''])[2] == 'SELF'
        esA, esB = (z['espectral']['A'], z['espectral']['B']) if z['espectral'] else (None, None)
        roi = m.get('roi')
        fecha = m.get('fecha')
        if not fecha:
            mt = os.path.getmtime(os.path.join('/home/chanoscopio/Documents/AleYLu/imagenes_tomadas', m.get('captura', n)))
            fecha = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M') + ' (mtime)'
        tipo = 'flat-prueba' if self_flat else ('prueba' if '-p1' in n else ('viejo' if n < '2026-10-21' else 'captura'))
        filas.append(dict(n=n, captura=m.get('captura', n), fecha=fecha, tipo=tipo, esp_motivo='n/a (sin flat)' if self_flat else 'n/a (espectral falla)',
                          roi=f'({roi[0]},{roi[1]})' if roi else ROI_SIN_JSON.get(n, 'sin json'), roi_y=roi[1] if roi else None,
                          t_bf=b['t_central'], eje_f=a['eje'][0], eje_c=a['eje'][1], w=a['w_px'], naz_fijo=a['NAz'],
                          naz_libre=sl['NAz'], s_libre=sl['s'],
                          esp=None if (self_flat or z['espectral'] is None) else (esA['NAz_fila'], esA['NAz_col'], esA['rb_sd_rel'], esB['NAz_fila'], esB['NAz_col'], esB['rb_sd_rel']),
                          flat=m.get('flat')))
filas.sort(key=lambda r: (r['fecha'][:16], r['n']))
L = ['| captura | fecha/hora | tipo | ROI (x,y) | t BF (ms) | eje (a) fila, col (pasos) | w (px) | NA·z borde s fijo | NA·z borde s libre (s) | espectral A filas/cols (sd) | espectral B filas/cols (sd) |',
     '|---|---|---|---|---|---|---|---|---|---|---|']
for r in filas:
    e = r['esp']
    eA = r['esp_motivo'] if e is None else f'{e[0]:.2f}/{e[1]:.2f} ({100*e[2]:.0f} %)'
    eB = r['esp_motivo'] if e is None else f'{e[3]:.2f}/{e[4]:.2f} ({100*e[5]:.0f} %)'
    L.append(f'| {r["n"]} | {r["fecha"]} | {r["tipo"]} | {r["roi"]} | {r["t_bf"]:g} | {r["eje_f"]:+.3f}, {r["eje_c"]:+.3f} | {r["w"]:.0f} | '
             f'{r["naz_fijo"]:.3f} | {r["naz_libre"]:.3f} ({r["s_libre"]:.0f}) | {eA} | {eB} |')
open(os.path.join(A, 'tabla.md'), 'w').write('\n'.join(L) + '\n')
json.dump(filas, open(os.path.join(A, 'tabla.json'), 'w'), indent=1)
print('\n'.join(L))
# correlaciones
def corr(sel, nombre):
    out = [f'\n### {nombre} (n={len(sel)})']
    if len(sel) < 3: return out
    y = np.array([r['naz_fijo'] for r in sel]); yl = np.array([r['naz_libre'] for r in sel])
    xs = {'eje fila': [r['eje_f'] for r in sel], '|eje|': [np.hypot(r['eje_f'], r['eje_c']) for r in sel],
          'eje col': [r['eje_c'] for r in sel], 'w': [r['w'] for r in sel], 't BF': [r['t_bf'] for r in sel],
          'ROI y': [r['roi_y'] for r in sel],
          'día (desde 21/10)': [(datetime.date.fromisoformat(r['fecha'][:10]) - datetime.date(2026, 10, 21)).days for r in sel]}
    for k, x in xs.items():
        if any(v is None for v in x): out.append(f'- {k}: sin dato en alguna captura'); continue
        x = np.array(x, float)
        if x.std() == 0: out.append(f'- {k}: constante'); continue
        r1 = np.corrcoef(x, y)[0, 1]; r2 = np.corrcoef(x, yl)[0, 1]; p = np.polyfit(x, y, 1)
        out.append(f'- {k}: r(s fijo) = {r1:+.2f}, r(s libre) = {r2:+.2f}, pendiente s fijo = {p[0]:+.4g} mm/unidad')
    return out
nuevos = [r for r in filas if r['tipo'] != 'viejo']
conm = [r for r in nuevos if r['tipo'] != 'flat-prueba']
dias = {}
for r in conm: dias.setdefault(r['fecha'][:10], []).append(r)
C = corr(conm, 'Rojo ≥ 21/10, con muestra (capturas + pruebas)') + corr(nuevos, 'Rojo ≥ 21/10, incluye pruebas sin muestra') + \
    corr([r for r in conm if r['roi_y'] is not None], 'Rojo ≥ 21/10 con muestra y ROI de captura.json (sin 21/10)')
C += ['\n### Por día (con muestra, s fijo)', '', '| día | n | NA·z media | sd | eje fila media |', '|---|---|---|---|---|']
for d, rs in sorted(dias.items()):
    v = np.array([r['naz_fijo'] for r in rs]); e = np.array([r['eje_f'] for r in rs])
    C.append(f'| {d} | {len(v)} | {v.mean():.3f} | {v.std(ddof=1) if len(v) > 1 else float("nan"):.3f} | {e.mean():+.3f} |')
# un punto por (día, ROI): evita que las 7 zonas del 06/11 pesen 7 veces
grupos = {}
for r in conm: grupos.setdefault((r['fecha'][:10], r['roi']), []).append(r)
G = []
for (d, roi), rs in sorted(grupos.items()):
    G.append(dict(n=f'{d} {roi}', fecha=d, roi=roi, roi_y=rs[0]['roi_y'], tipo='grupo',
                  **{k: float(np.mean([r[k] for r in rs])) for k in ('eje_f', 'eje_c', 'w', 'naz_fijo', 'naz_libre', 't_bf')}))
C += ['', '### Por (día, ROI) con muestra', '', '| día | ROI | n | NA·z s fijo | NA·z s libre | eje fila | eje col | w | t BF usado por borde (ms) |', '|---|---|---|---|---|---|---|---|---|']
for g, ((d, roi), rs) in zip(G, sorted(grupos.items())):
    C.append(f"| {d} | {roi} | {len(rs)} | {g['naz_fijo']:.3f} | {g['naz_libre']:.3f} | {g['eje_f']:+.3f} | {g['eje_c']:+.3f} | {g['w']:.0f} | {g['t_bf']:.1f} |")
C += corr(G, 'Correlaciones con un punto por (día, ROI)')
open(os.path.join(A, 'correlaciones.md'), 'w').write('\n'.join(C) + '\n'); print('\n'.join(C))
# figura
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
estilos = {'captura': ('o', 'C0'), 'prueba': ('s', 'C1'), 'flat-prueba': ('^', 'C2'), 'viejo': ('x', 'C3')}
paneles = [('eje_f', 'naz_fijo', 'eje (a) fila (pasos)', 'NA·z s fijo vs eje fila'),
           ('eje_c', 'naz_fijo', 'eje (a) col (pasos)', 'NA·z s fijo vs eje col'),
           ('eje_f', 'naz_libre', 'eje (a) fila (pasos)', 'NA·z s libre vs eje fila')]
for i, (kx, ky, xl, tt) in enumerate(paneles):
    for tipo, (mk, c) in estilos.items():
        rs = [r for r in filas if r['tipo'] == tipo]
        if rs: ax[i].scatter([r[kx] for r in rs], [r[ky] for r in rs], marker=mk, c=c, label=tipo, s=28)
    for r in filas:
        if r['tipo'] in ('captura', 'viejo') and not r['n'].startswith('2026-11-06-') or r['n'] == '2026-11-06-a.1':
            ax[i].annotate(r['n'].replace('2026-', '').replace('-viejo', ''), (r[kx], r[ky]), fontsize=6, xytext=(3, 2), textcoords='offset points')
    ax[i].set_xlabel(xl); ax[i].set_title(tt, fontsize=10); ax[i].grid(alpha=.3)
ax[0].set_ylabel('NA·z borde (a) (mm)'); ax[0].legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(A, 'fig_archivo.png'), dpi=140)

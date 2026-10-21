"""inventario.py -- lee TODOS los frames crudos de la captura roja 21/10 (muestra, flat sin muestra, oscuros) y guarda un resumen
compacto en inv.npz: por LED y set, exposición, media (frame completo y recorte central 400), máx, n saturados (>=4095, cualquier
frame), σ frame-a-frame (MAD de f1-f2, /√2 -> ruido de UN frame), y la imagen media de los 2 frames binneada 4 (280²).
También compara organizado/red/<t>ms/filaR_colC.tiff con los frames crudos."""
import glob, os, json
import numpy as np
import tifffile as T

B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
HERE = os.path.dirname(os.path.abspath(__file__))
SETS = {'muestra': '2026-10-21', 'flat': '2026-10-21-sinmuestra', 'oscuro': '2026-10-21-dark'}
C = slice(360, 760)
out = {}
for tag, s in SETS.items():
    rows = []
    for d in sorted(glob.glob(f'{B}/{s}/fila*_col*_colorr')):
        nm = os.path.basename(d); r, c = (int(v) for v in nm[4:].split('_colorr')[0].split('_col'))
        for td in sorted(glob.glob(f'{d}/*ms')):
            t = int(os.path.basename(td)[:-2]); fs = sorted(glob.glob(f'{td}/imagen_frame_*.tiff'))
            fr = [T.imread(f).astype(float) for f in fs]
            m = np.mean(fr, 0); dd = fr[0] - fr[1] if len(fr) == 2 else np.zeros_like(m)
            sig = 1.4826 * np.median(np.abs(dd - np.median(dd))) / np.sqrt(2)
            rows.append(dict(k=(r, c), t=t, nfr=len(fr), mean=m.mean(), mean_c=m[C, C].mean(), max=max(f.max() for f in fr),
                             nsat=int(sum((f >= 4095).sum() for f in fr)), sig=sig, sig_c=1.4826 * np.median(np.abs(dd[C, C] - np.median(dd[C, C]))) / np.sqrt(2),
                             sm=m.reshape(280, 4, 280, 4).mean((1, 3)).astype(np.float32)))
    out[tag] = rows
    print(tag, len(rows), flush=True)
np.savez_compressed(os.path.join(HERE, 'inv.npz'), **{f'{tag}_{f}': np.array([r[f] for r in rows]) for tag, rows in out.items()
                                                     for f in ('k', 't', 'nfr', 'mean', 'mean_c', 'max', 'nsat', 'sig', 'sig_c', 'sm')})
# organizado vs crudos
chk = {}
for p in sorted(glob.glob(f'{B}/2026-10-21/organizado/red/*ms/*.tiff'))[::20]:
    t = os.path.basename(os.path.dirname(p)); nm = os.path.basename(p)[:-5]
    o = T.imread(p).astype(float); f = [T.imread(x).astype(float) for x in sorted(glob.glob(f'{B}/2026-10-21/{nm}_colorr/{t}/imagen_frame_*.tiff'))]
    chk[f'{nm}/{t}'] = dict(dtype=str(T.imread(p).dtype), max_vs_f1=float(np.abs(o - f[0]).max()), max_vs_f2=float(np.abs(o - f[1]).max()),
                           max_vs_media=float(np.abs(o - (f[0] + f[1]) / 2).max()), media_menos_org=float(((f[0] + f[1]) / 2 - o).mean()))
json.dump(chk, open(os.path.join(HERE, 'organizado_chk.json'), 'w'), indent=1)
print(chk)

"""resumen.py -- junta espectral_*.json y borde_*.json en resultados/resumen.json."""
import json, glob, os
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados')
out = {'espectral': {}, 'borde': {}}
for f in sorted(glob.glob(f'{R}/espectral_*.json')):
    d = json.load(open(f)); e = d['etapa1_radio']; o = d['original']
    out['espectral'][d['etiqueta']] = dict(captura=d['captura'], recorte=d['recorte'][:2],
        NAz_fila=e['NAz_fila'], NAz_col=e['NAz_col'], rb=e['rb'], rb_sd_rel=e['rb_sd_rel'], s_fila=e['s_row'], s_col=e['s_col'],
        NAz_por_led=e['NAz_por_led'], original_fila=o['NAz_fila'], original_col=o['NAz_col'])
for f in sorted(glob.glob(f'{R}/borde_*.json')):
    d = json.load(open(f))
    loo = [v * 6 for v in d['loo'].values()]
    out['borde'][d['nombre']] = dict(s_fijo=d['s_fijo'], s_libre=d['s_libre'], loo_NAz_min=min(loo), loo_NAz_max=max(loo))
json.dump(out, open(f'{R}/resumen.json', 'w'), indent=1)
for k, v in out['espectral'].items():
    print(k, v['recorte'], '%.3f/%.3f sd %.1f%%' % (v['NAz_fila'], v['NAz_col'], 100 * v['rb_sd_rel']))

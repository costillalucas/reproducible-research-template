"""borde_zonas.py -- estimación (a) de centrado.py (copia sin cambios, importada) sobre las 4 capturas rojas.
Solo cambia el directorio de salida (OUT) y agrega 2026-10-30-red (oscuros 2026-10-30-red-dark). Sin flat (como el original).
NA·z = R_pasos·6 mm (convención de los informes) y corregido tan->sin: z·sin(atan(R·6/z)) con z 99.5."""
import os, sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import centrado as C  # noqa: E402
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados')
C.OUT = RES
LISTA = {'2026-11-03-red': '2026-11-03-red-dark', '2026-10-30-red-c': '2026-10-30-red-c-dark',
         '2026-10-30-red': '2026-10-30-red-dark', '2026-10-30-red-b': '2026-10-30-red-b-dark'}
Z = 99.5
def naz(R):
    return dict(NAz_R6=R * 6.0, NAz_sin=Z * math.sin(math.atan(R * 6.0 / Z)))
sel = sys.argv[1:] or list(LISTA)
for nom in sel:
    r = C.analizar(nom, LISTA[nom], None)
    a, sl = r['a'], r['s_libre']
    R_px_fijo = a['R_pasos'] * 3538.0; R_px_lib = sl['R_pasos'] * 3538.0
    out = dict(nombre=nom, roi=r['roi'], t_central=r['t_central'],
               s_fijo=dict(eje=a['eje'], R_px=R_px_fijo, R_pasos=a['R_pasos'], w_px=a['w_px'], s=a['s'], **naz(a['R_pasos'])),
               s_libre=dict(eje=sl['eje'], R_px=R_px_lib, s=sl['s'], w_px=sl['w_px'],
                            R_pasos_sobre_s_libre=R_px_lib / sl['s'], R_pasos_sobre_3538=R_px_lib / 3538.0,
                            **naz(R_px_lib / sl['s'])),
               b_eje=r['b']['eje'], loo={k: v['R_pasos'] for k, v in r['loo'].items()}, score_a=r['score']['a'])
    json.dump(out, open(os.path.join(RES, f'borde_{nom}.json'), 'w'), indent=1)
    print(nom, json.dumps({k: out[k] for k in ('s_fijo', 's_libre')}), flush=True)

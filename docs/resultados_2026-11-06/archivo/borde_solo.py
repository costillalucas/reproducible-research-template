"""Solo borde (a) para capturas donde el espectral de analizar_zonas.py se cae (grid() devuelve None).
Importa analizar_zonas.py sin cambios y repite TEXTUALMENTE su bloque de borde (centrado.analizar, s fijo / s libre).
uso: python3 borde_solo.py NOMBRE CAPTURA_ABS DARK_ABS OUT_DIR"""
import os, sys, json, math, tempfile, shutil
sys.path.insert(0, '/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/zonas_3x3')
import analizar_zonas as Z
C, S_NOM, ZZ = Z.C, Z.S_NOM, Z.Z
n, cap, dark, out = sys.argv[1:5]
Z.exigir(cap, 'r', Z.LEDS_3x3, 'borde (a)')
tmp = tempfile.mkdtemp(prefix='mapas_', dir=os.path.dirname(os.path.abspath(__file__)))
try:
    C.BASE, C.OUT = os.path.dirname(cap), tmp
    r = C.analizar(os.path.basename(cap), dark, None)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
a, sl = r['a'], r['s_libre']
R_px_lib = sl['R_pasos'] * S_NOM
borde = dict(
    t_central=r['t_central'],
    s_fijo=dict(eje=a['eje'], R_px=a['R_pasos'] * S_NOM, R_pasos=a['R_pasos'], w_px=a['w_px'], s=a['s'],
                NAz=a['R_pasos'] * 6.0, NAz_sin=ZZ * math.sin(math.atan(a['R_pasos'] * 6.0 / ZZ))),
    s_libre=dict(eje=sl['eje'], R_px=R_px_lib, s=sl['s'], w_px=sl['w_px'], R_pasos=R_px_lib / sl['s'],
                 NAz=R_px_lib / sl['s'] * 6.0),
    loo_NAz={k: v['R_pasos'] * 6.0 for k, v in r['loo'].items()}, b_eje=r['b']['eje'], score_a=r['score']['a'])
od = os.path.join(out, n); os.makedirs(od, exist_ok=True)
json.dump(dict(meta=dict(nota='solo borde (espectral falló)', dark=dark), zonas=[dict(etiqueta=n, captura=cap, roi=Z.roi_de(cap),
          espectral=None, borde=borde)]), open(os.path.join(od, 'zonas.json'), 'w'), indent=1)
print(n, borde['s_fijo']['NAz'], borde['s_fijo']['eje'], borde['s_fijo']['w_px'], borde['s_libre']['NAz'])

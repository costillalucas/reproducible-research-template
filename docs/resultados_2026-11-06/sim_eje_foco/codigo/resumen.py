"""resumen.py -- tabla markdown + json de ../resultados/res_*.json (sim_eje_foco)."""
import glob, json, os, math
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados')
filas = []
for f in sorted(glob.glob(os.path.join(R, 'res_*.json'))):
    d = json.load(open(f)); r, s0 = d['ruido'], d['sin_ruido']
    NA, z = d['NA'], d['z']
    filas.append(dict(nombre=d['nombre'], seed=d['seed'], verdad=d['NAz_verdad'], verdad_tan=z * math.tan(math.asin(NA)),
                      eje=d['eje'], dz=d['dz'], a=r['borde']['a']['NAz'], a_sr=s0['borde']['a']['NAz'],
                      a_eje=r['borde']['a']['eje'], w=r['borde']['a']['w_px'], b=r['borde']['b']['NAz'],
                      ef=r['esp_nt']['NAz_fila'], ec=r['esp_nt']['NAz_col'], rb=r['esp_nt']['rb_bins'],
                      rb_sd=r['esp_nt']['rb_sd'], seg=d['seg']))
json.dump(filas, open(os.path.join(R, 'resumen.json'), 'w'), indent=1)
L = ['| caso | verdad NA·z (z·tanθ) | eje filas, cols | dz µm | borde (a) NA·z ruido / sin ruido | eje (a) ajustado | w px | borde (b) | espectral filas / cols | rb (sd) bins |',
     '|---|---|---|---|---|---|---|---|---|---|']
for x in filas:
    L.append(f"| {x['nombre']} s{x['seed']} | {x['verdad']:.3f} ({x['verdad_tan']:.3f}) | {x['eje'][0]:+.3f}, {x['eje'][1]:+.3f} | {x['dz']:+.0f} | "
             f"{x['a']:.3f} / {x['a_sr']:.3f} | {x['a_eje'][0]:+.3f}, {x['a_eje'][1]:+.3f} | {x['w']:.1f} | {x['b']:.3f} | "
             f"{x['ef']:.2f} / {x['ec']:.2f} | {x['rb']:.1f} ({x['rb_sd']:.1f}) |")
open(os.path.join(R, 'tabla_resumen.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))

"""analizar_zonas.py -- espectral (etapa 1 radio libre) + borde (a) de centrado.py, zona por zona, para la captura 3x3
de 06/11 (mismo ROI, sin reenfocar, N posiciones XY de la platina = N zonas, cada una con solo los 9 LEDs centrales).

NO reescribe los métodos: importa sin cambios
  ../zonas/codigo/espectral_zonas.py  (cargar + espectral, modo 'etapa1_radio'; score/grid textuales de paso_espectral_0311)
  ../zonas/codigo/centrado.py         (analizar: (a) con s fijo 3538 y con s libre, LOO)
Lo único nuevo: CLI, chequeo de LEDs, contraste de partículas (= survey_contraste.py) y las tablas / resumen.

LEDs que se necesitan (falla con ERROR si falta alguno):
  espectral: los 5 BF (17,15) (16,15) (17,14) (17,16) (18,15), en la muestra Y en el flat;
  borde (a): los 9 del 3x3 centrado en (17,15), en la muestra (sin flat, como el original).
LEDs de más (p. ej. la grilla 15x15 completa) se ignoran.

Uso:
  python3 analizar_zonas.py CAPTURA [CAPTURA ...] --flat F --dark D --dark-flat DF [--repeticion A B] [--nombre N]
CAPTURA = carpeta o glob (relativo a imagenes_tomadas o absoluto). Ver README.md.
Modo prueba: --auto  -> por captura C usa C-sinmuestra, C-dark, C-sinmuestra-dark.
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
import glob
import json
import math
import re
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
CODIGO = os.path.join(os.path.dirname(AQUI), 'zonas', 'codigo')
sys.path.insert(0, CODIGO)
import numpy as np  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402
import espectral_zonas as E  # noqa: E402  (importa scripts/reconstruir.py del repo, solo lectura)
import centrado as C  # noqa: E402        (importa scripts/precaptura.py del repo, solo lectura)

RC = E.RC
BASE = '/home/chanoscopio/Documents/AleYLu/imagenes_tomadas'
RECORTES = {'A': (360, 80), 'B': (360, 480)}     # filas 360:760; cols 80:480 / 480:880 (INFORME 06/11)
EJE = (17, 15)
LEDS_BF = list(E.BF)
LEDS_3x3 = [(EJE[0] + dr, EJE[1] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
S_NOM = 3538.0
Z = 99.5   # solo para la variante tan->sin que ya informaba borde_zonas.py


def ruta(p):
    p = os.path.expanduser(p)
    return os.path.abspath(p if os.path.isabs(p) else os.path.join(BASE, p))


def orden_natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def leds_presentes(carpeta, color):
    return set(RC.indexar(carpeta, color))


def exigir(carpeta, color, leds, para):
    if not os.path.isdir(carpeta):
        raise SystemExit(f'ERROR: no existe la carpeta {carpeta} ({para})')
    falta = sorted(set(leds) - leds_presentes(carpeta, color))
    if falta:
        raise SystemExit(f'ERROR: {carpeta} no tiene los LEDs {falta} (color {color}), necesarios para {para}. '
                         'Revisar nombres fila{r}_col{c}_color{x}/<t>ms/imagen_frame_*.tiff')


def roi_de(carpeta):
    cj = os.path.join(carpeta, 'captura.json')
    if os.path.exists(cj):
        with open(cj) as f:
            j = json.load(f)
        return [j['roi']['offset_x'], j['roi']['offset_y']]
    return None


# ------------------------------------------------------------------- contraste de partículas (= survey_contraste.py)
def contraste(cap, flat, dark, darkf, color):
    """rms del pasa-altos de S/F del LED (17,15), sobre la mediana del recorte; misma cuenta que survey_contraste.py."""
    SM, FL = RC.indexar(cap, color), RC.indexar(flat, color)
    om, of = RC.Oscuros([dark, darkf], None), RC.Oscuros([darkf, dark], None)
    k = EJE; t = RC.elegir_t(SM[k], None); tf = RC.elegir_t(FL[k], None)
    s, *_ = RC.promediar(SM[k][t], om, t, None, 'm', []); fl, *_ = RC.promediar(FL[k][tf], of, tf, None, 'f', [])
    q = s / np.maximum(gaussian_filter(fl, 2), 1e-6)
    hp = q - gaussian_filter(q, 20)
    out = {}
    for nom, (f0, c0) in RECORTES.items():
        qq = q[f0:f0 + 400, c0:c0 + 400]; m = np.median(qq)
        out[nom] = dict(rms_hp=float(np.std(hp[f0:f0 + 400, c0:c0 + 400]) / m), oscuro=float(np.mean(qq / m < 0.5)))
    return out


# ------------------------------------------------------------------------------------------------- por zona
def zona(arg):
    et, cap, flat, dark, darkf, color, tmp = arg
    t0 = time.time()
    res = dict(etiqueta=et, captura=cap, flat=flat, dark=dark, dark_flat=darkf, roi=roi_de(cap), espectral={})
    # espectral, recortes A y B
    for nom, (f0, c0) in RECORTES.items():
        imgs, info, desc = E.cargar(cap, flat, dark, darkf, f0, c0)
        r = E.espectral(imgs, 'etapa1_radio')
        res['espectral'][nom] = dict(recorte=[f0, c0, E.N], info=info, descartes=desc, **r)
    res['contraste'] = contraste(cap, flat, dark, darkf, color)
    # borde (a): centrado.analizar sin cambios. BASE = carpeta madre, nombre = basename; oscuro con ruta absoluta.
    C.BASE, C.OUT = os.path.dirname(cap), tmp
    r = C.analizar(os.path.basename(cap), dark, None)
    a, sl = r['a'], r['s_libre']
    R_px_lib = sl['R_pasos'] * S_NOM
    res['borde'] = dict(
        t_central=r['t_central'],
        s_fijo=dict(eje=a['eje'], R_px=a['R_pasos'] * S_NOM, R_pasos=a['R_pasos'], w_px=a['w_px'], s=a['s'],
                    NAz=a['R_pasos'] * 6.0, NAz_sin=Z * math.sin(math.atan(a['R_pasos'] * 6.0 / Z))),
        s_libre=dict(eje=sl['eje'], R_px=R_px_lib, s=sl['s'], w_px=sl['w_px'], R_pasos=R_px_lib / sl['s'],
                     NAz=R_px_lib / sl['s'] * 6.0),
        loo_NAz={k: v['R_pasos'] * 6.0 for k, v in r['loo'].items()}, b_eje=r['b']['eje'], score_a=r['score']['a'])
    res['seg'] = round(time.time() - t0, 1)
    print(f'  {et}: listo en {res["seg"]} s', flush=True)
    return res


# ------------------------------------------------------------------------------------------------- tablas
METRICAS = [  # (clave, extractor) -> estadística entre zonas
    ('espectral_A_fila', lambda z: z['espectral']['A']['NAz_fila']),
    ('espectral_A_col', lambda z: z['espectral']['A']['NAz_col']),
    ('espectral_B_fila', lambda z: z['espectral']['B']['NAz_fila']),
    ('espectral_B_col', lambda z: z['espectral']['B']['NAz_col']),
    ('espectral_A_sd_rel', lambda z: z['espectral']['A']['rb_sd_rel']),
    ('espectral_B_sd_rel', lambda z: z['espectral']['B']['rb_sd_rel']),
    ('borde_sfijo_NAz', lambda z: z['borde']['s_fijo']['NAz']),
    ('borde_sfijo_R_pasos', lambda z: z['borde']['s_fijo']['R_pasos']),
    ('borde_sfijo_w_px', lambda z: z['borde']['s_fijo']['w_px']),
    ('borde_slibre_NAz', lambda z: z['borde']['s_libre']['NAz']),
    ('borde_slibre_s', lambda z: z['borde']['s_libre']['s']),
    ('eje_a_fila', lambda z: z['borde']['s_fijo']['eje'][0]),
    ('eje_a_col', lambda z: z['borde']['s_fijo']['eje'][1]),
    ('contraste_A', lambda z: z['contraste']['A']['rms_hp']),
    ('contraste_B', lambda z: z['contraste']['B']['rms_hp']),
]


def resumen(zonas, rep):
    out = {}
    for k, f in METRICAS:
        v = np.array([f(z) for z in zonas], float)
        out[k] = dict(n=len(v), media=float(v.mean()), sd=float(v.std(ddof=1)) if len(v) > 1 else None,
                      sd_rel=float(v.std(ddof=1) / abs(v.mean())) if len(v) > 1 else None,
                      min=float(v.min()), max=float(v.max()))
    rd = None
    if rep:
        za, zb = (next(z for z in zonas if z['etiqueta'] == e) for e in rep)
        rd = dict(a=rep[0], b=rep[1], dif={k: float(f(zb) - f(za)) for k, f in METRICAS},
                  dif_rel={k: float((f(zb) - f(za)) / abs(f(za))) if f(za) else None for k, f in METRICAS})
    return out, rd


def markdown(zonas, est, rd, meta):
    L = [f'# Zonas 3x3 -- {meta["nombre"]}', '',
         f'Flat `{meta["flat"]}`, oscuros `{meta["dark"]}` / `{meta["dark_flat"]}`, color `{meta["color"]}`. '
         'NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` '
         '(NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.', '',
         '## Espectral', '',
         '| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |',
         '|---|---|---|---|---|---|---|---|---|']
    for z in zonas:
        for nom in RECORTES:
            e = z['espectral'][nom]
            L.append(f'| {z["etiqueta"]} | {z["roi"]} | {nom} | {e["NAz_fila"]:.3f} | {e["NAz_col"]:.3f} | '
                     f'{100 * e["rb_sd_rel"]:.1f} % | {" ".join(f"{v:.2f}" for v in e["NAz_por_led"])} | '
                     f'{e["s_row"]:.2f}/{e["s_col"]:.2f} | {z["contraste"][nom]["rms_hp"]:.3f} |')
    L += ['', '## Borde (a)', '',
          '| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for z in zonas:
        b = z['borde']; a, s = b['s_fijo'], b['s_libre']; loo = list(b['loo_NAz'].values())
        L.append(f'| {z["etiqueta"]} | ({a["eje"][0]:+.3f}, {a["eje"][1]:+.3f}) | {a["R_px"]:.0f} | {a["R_pasos"]:.4f} | '
                 f'{a["w_px"]:.0f} | {a["NAz"]:.3f} | {s["s"]:.0f} | {s["R_px"]:.0f} | {s["R_pasos"]:.4f} | {s["NAz"]:.3f} | '
                 f'{min(loo):.2f}–{max(loo):.2f} |')
    L += ['', '## Resumen entre zonas', '', '| métrica | n | media | sd | sd rel | min | max |', '|---|---|---|---|---|---|---|']
    for k, v in est.items():
        sd = '—' if v['sd'] is None else f'{v["sd"]:.4f}'
        sr = '—' if v['sd_rel'] is None else f'{100 * v["sd_rel"]:.2f} %'
        L.append(f'| {k} | {v["n"]} | {v["media"]:.4f} | {sd} | {sr} | {v["min"]:.4f} | {v["max"]:.4f} |')
    if rd:
        L += ['', f'## Repetición: {rd["b"]} − {rd["a"]}', '', '| métrica | diferencia | dif rel |', '|---|---|---|']
        for k in rd['dif']:
            r = rd['dif_rel'][k]
            L.append(f'| {k} | {rd["dif"][k]:+.4f} | {"—" if r is None else f"{100 * r:+.2f} %"} |')
    L += ['', f'Generado {meta["fecha"]} por `{meta["comando"]}`.', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('capturas', nargs='+', help='carpetas o globs (relativos a imagenes_tomadas o absolutos)')
    ap.add_argument('--flat'); ap.add_argument('--dark'); ap.add_argument('--dark-flat')
    ap.add_argument('--auto', action='store_true', help='prueba: flat/oscuros = C-sinmuestra, C-dark, C-sinmuestra-dark')
    ap.add_argument('--color', default='r')
    ap.add_argument('--repeticion', nargs=2, metavar=('A', 'B'), help='nombres (basename) de las 2 tomas de zona 1')
    ap.add_argument('--nombre', default=None, help='nombre de la corrida (carpeta de salida en resultados/)')
    ap.add_argument('--out', default=os.path.join(AQUI, 'resultados'))
    ap.add_argument('--procs', type=int, default=3)
    a = ap.parse_args()
    if not a.auto and not (a.flat and a.dark and a.dark_flat):
        ap.error('hacen falta --flat, --dark y --dark-flat (o --auto)')
    fijos = {ruta(x) for x in (a.flat, a.dark, a.dark_flat) if x}
    caps = []
    for pat in a.capturas:
        m = sorted(glob.glob(ruta(pat))) if any(ch in pat for ch in '*?[') else [ruta(pat)]
        if not m:
            raise SystemExit(f'ERROR: el patrón {pat} no encontró nada')
        for c in m:
            b = os.path.basename(c)
            if c in fijos or b.endswith('-dark') or 'sinmuestra' in b or 'prueba' in b:
                print(f'  [salteo] {b} (oscuro / flat / prueba)'); continue
            if os.path.isdir(c) and c not in caps:
                caps.append(c)
    caps.sort(key=lambda c: orden_natural(os.path.basename(c)))
    if not caps:
        raise SystemExit('ERROR: ninguna carpeta de captura')
    etqs = [os.path.basename(c) for c in caps]
    if len(set(etqs)) != len(etqs):
        raise SystemExit(f'ERROR: nombres de carpeta repetidos {etqs}')
    if a.repeticion:
        for e in a.repeticion:
            if e not in etqs:
                raise SystemExit(f'ERROR: --repeticion {e} no está entre las capturas {etqs}')
    trabajos = []
    for c in caps:
        if a.auto:
            fl, dk, dkf = c + '-sinmuestra', c + '-dark', c + '-sinmuestra-dark'
        else:
            fl, dk, dkf = ruta(a.flat), ruta(a.dark), ruta(a.dark_flat)
        exigir(c, a.color, LEDS_3x3, 'borde (a) [3x3] y espectral [5 BF]')
        exigir(fl, a.color, LEDS_BF, 'flat del espectral [5 BF]')
        for d in (dk, dkf):
            if not os.path.isdir(d):
                raise SystemExit(f'ERROR: no existe la carpeta de oscuros {d}')
        trabajos.append([os.path.basename(c), c, fl, dk, dkf, a.color, None])
    rois = {tuple(roi_de(c) or ()) for c in caps}
    print(f'{len(caps)} capturas: {etqs}  ROI(s): {sorted(rois)}', flush=True)
    if len(rois) > 1:
        print('  [AVISO] las capturas no tienen todas el mismo ROI', flush=True)
    tmp = tempfile.mkdtemp(prefix='mapas_', dir=AQUI)   # centrado.analizar escribe mapas_*.npz: se borran al final
    for tr in trabajos:
        tr[-1] = tmp
    t0 = time.time()
    try:
        with ProcessPoolExecutor(max_workers=max(1, min(a.procs, len(trabajos)))) as ex:
            zonas = list(ex.map(zona, trabajos))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    est, rd = resumen(zonas, a.repeticion)
    nombre = a.nombre or time.strftime('corrida_%Y-%m-%d_%H%M')
    od = os.path.join(a.out, nombre); os.makedirs(od, exist_ok=True)
    meta = dict(nombre=nombre, fecha=time.strftime('%Y-%m-%d %H:%M'), comando=' '.join(sys.argv), color=a.color,
                flat='auto' if a.auto else ruta(a.flat), dark='auto' if a.auto else ruta(a.dark),
                dark_flat='auto' if a.auto else ruta(a.dark_flat), codigo=CODIGO, seg=round(time.time() - t0, 1))
    with open(os.path.join(od, 'zonas.json'), 'w') as f:
        json.dump(dict(meta=meta, zonas=zonas, resumen=est, repeticion=rd), f, indent=1)
    md = markdown(zonas, est, rd, meta)
    with open(os.path.join(od, 'zonas.md'), 'w') as f:
        f.write(md)
    print(md)
    print(f'\nSalida: {od}/zonas.json, zonas.md  ({meta["seg"]} s)')


if __name__ == '__main__':
    main()

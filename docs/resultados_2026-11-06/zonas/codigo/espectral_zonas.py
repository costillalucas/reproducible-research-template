"""espectral_zonas.py -- método espectral (paso_espectral_0311.py, score/grid VERBATIM) con la etapa 1 de radio libre
(como diag_rb0.espectral_var modo 'etapa1_radio'), aplicado a otras capturas / recortes.

Preprocesado: el de scripts/reconstruir.py (repo, importado SOLO LECTURA, sin __pycache__): por LED, exposición más larga
sin saturar en el recorte, promedio de frames con descarte, oscuro de la misma t restado, /t_ef. Muestra y flat cada uno con
sus oscuros. Imagen = S/F·<F> (igual que paso_espectral_0311). Solo los 5 LEDs BF de la cruz.

Uso: python3 espectral_zonas.py <etiqueta> <captura> <flat> <dark> <dark_flat> F0,C0 [prep.npz para validar]
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import sys
sys.dont_write_bytecode = True
import json
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
sys.path.insert(0, '/home/chanoscopio/Documents/LucasC/reproducible-research-template/scripts')
import reconstruir as RC  # noqa: E402

BASE = '/home/chanoscopio/Documents/AleYLu/imagenes_tomadas'
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados')
# ---- constantes y funciones copiadas textualmente de paso_espectral_0311.py
PX, N, PITCH, lam = 1.29, 400, 6.0, 0.63
df = 1.0 / (N * PX); win = np.outer(np.hanning(N), np.hanning(N))
TH = np.linspace(0, 2 * np.pi, 360, endpoint=False); DD = 3.0
def score(L, c0, c1, rb, d=DD):
    s = []
    for sg in (1, -1):
        p0, p1 = sg * c0 + rb * np.sin(TH), sg * c1 + rb * np.cos(TH)
        keep = np.hypot(p0 + sg * c0, p1 + sg * c1) > rb + d
        if keep.sum() < 20: return -1e9
        inn = map_coordinates(L, [N // 2 + sg * c0 + (rb - d) * np.sin(TH[keep]), N // 2 + sg * c1 + (rb - d) * np.cos(TH[keep])], order=1)
        out = map_coordinates(L, [N // 2 + sg * c0 + (rb + d) * np.sin(TH[keep]), N // 2 + sg * c1 + (rb + d) * np.cos(TH[keep])], order=1)
        s.append(inn - out)
    return float(np.mean(np.concatenate(s)))
def grid(L, g0, g1, rbs, half, step):
    a = np.arange(-half, half + 1e-9, step); best = (-1e18, None)
    for rb in rbs:
        for u in a:
            for v in a:
                sc = score(L, g0 + u, g1 + v, rb)
                if sc > best[0]: best = (sc, (g0 + u, g1 + v, rb))
    return best[1]
BF = [(17, 15), (16, 15), (17, 14), (17, 16), (18, 15)]


def espectral(imgs, modo):
    """= diag_rb0.espectral_var (modos 'original' y 'etapa1_radio'), con guess nominal sin cambios (z 102, +0.529 mm)."""
    rb0 = 0.0669 / lam / df
    rows = []
    for k in BF:
        I = imgs[k].astype(float); I = (I - I.mean()) * win
        L = gaussian_filter(np.log(np.abs(np.fft.fftshift(np.fft.fft2(I))) + 1e-6), 2.0)
        n0 = (k[0] - 17) * PITCH / 102 / lam / df; n1 = ((k[1] - 15) * PITCH + 0.529) / 102 / lam / df
        r1 = [rb0] if modo != 'etapa1_radio' else list(rb0 * np.linspace(0.92, 1.20, 7))
        c0, c1, rb = grid(L, n0, n1, r1, half=round(0.45 * rb0), step=1.0)
        c0, c1, rb = grid(L, c0, c1, rb0 * (np.linspace(0.90, 1.15, 26) if modo != 'etapa1_radio' else np.linspace(0.88, 1.25, 38)), half=3, step=0.5)
        c0, c1, rb = grid(L, c0, c1, rb + np.arange(-0.6, 0.61, 0.15), half=0.75, step=0.125)
        if (c0 - n0) ** 2 + (c1 - n1) ** 2 > (c0 + n0) ** 2 + (c1 + n1) ** 2: c0, c1 = -c0, -c1
        rows.append(dict(led=list(k), c0=float(c0), c1=float(c1), rb=float(rb)))
    g = {tuple(r["led"]): r for r in rows}
    s_col = (g[(17, 16)]["c1"] - g[(17, 14)]["c1"]) / 2; s_row = (g[(18, 15)]["c0"] - g[(16, 15)]["c0"]) / 2
    rbl = np.array([r["rb"] for r in rows]); rb = float(rbl.mean())
    # NA·z por LED (radio de cada LED / paso medio de su eje) para ver la dispersión entre LEDs
    s_med = 0.5 * (s_row + s_col)
    return dict(leds=rows, rb=rb, rb_sd=float(rbl.std(ddof=1)), rb_sd_rel=float(rbl.std(ddof=1) / rb),
                s_row=float(s_row), s_col=float(s_col),
                NAz_fila=rb / s_row * PITCH, NAz_col=rb / s_col * PITCH,
                NAz_por_led=[float(r / s_med * PITCH) for r in rbl])


def cargar(cap, flat, dark, darkf, f0, c0):
    rec = RC.Recorte(f0, c0, N)
    SM, FL = RC.indexar(os.path.join(BASE, cap), 'r'), RC.indexar(os.path.join(BASE, flat), 'r')
    oscm = RC.Oscuros([os.path.join(BASE, dark), os.path.join(BASE, darkf)], rec)
    oscf = RC.Oscuros([os.path.join(BASE, darkf), os.path.join(BASE, dark)], rec)
    imgs, info, desc = {}, {}, []
    for k in BF:
        t = RC.elegir_t(SM[k], rec); tf = RC.elegir_t(FL[k], rec) if len(FL[k]) > 1 else next(iter(FL[k]))
        s, _, sat, nf = RC.promediar(SM[k][t], oscm, t, rec, f'muestra {k}', desc)
        f, _, _, _ = RC.promediar(FL[k][tf], oscf, tf, rec, f'flat {k}', desc)
        imgs[k] = s / f * f.mean()
        q = s / np.maximum(gaussian_filter(f, 2), 1e-6); q = q / np.median(q)
        info[str(k)] = dict(t=t, tf=tf, frames=nf, sat_px=int(sat.sum()), contraste_rms=float(np.std(q)),
                            oscuro_frac=float(np.mean(q < 0.5)))
    return imgs, info, desc


def main():
    et, cap, flat, dark, darkf, fc = sys.argv[1:7]
    f0, c0 = (int(v) for v in fc.split(','))
    imgs, info, desc = cargar(cap, flat, dark, darkf, f0, c0)
    out = dict(etiqueta=et, captura=cap, flat=flat, dark=dark, dark_flat=darkf, recorte=[f0, c0, N], info=info,
               descartes=desc)
    for modo in ('original', 'etapa1_radio'):
        r = espectral(imgs, modo); out[modo] = r
        print(f"{et} {modo:12s}: NA·z {r['NAz_fila']:.3f}/{r['NAz_col']:.3f} rb {r['rb']:.2f}±{r['rb_sd']:.2f} "
              f"({100 * r['rb_sd_rel']:.1f} %) s {r['s_row']:.2f}/{r['s_col']:.2f}  porLED {np.round(r['NAz_por_led'], 2)}",
              flush=True)
    if len(sys.argv) > 7:   # validación: mismo cálculo desde el prep.npz de la reconstrucción
        d = np.load(sys.argv[7]); keys = [tuple(int(v) for v in k) for k in d['keys']]
        im2 = {}
        for k in BF:
            i = keys.index(k); f = d['F'][i].astype(float); im2[k] = d['S'][i].astype(float) / f * f.mean()
        out['max_dif_vs_prep'] = float(max(np.abs(im2[k] - imgs[k]).max() / np.abs(im2[k]).mean() for k in BF))
        r = espectral(im2, 'etapa1_radio'); out['prep_etapa1_radio'] = r
        print(f"{et} desde prep.npz etapa1_radio: NA·z {r['NAz_fila']:.3f}/{r['NAz_col']:.3f}; "
              f"dif rel máx imágenes {out['max_dif_vs_prep']:.2e}", flush=True)
    json.dump(out, open(os.path.join(RES, f'espectral_{et}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()

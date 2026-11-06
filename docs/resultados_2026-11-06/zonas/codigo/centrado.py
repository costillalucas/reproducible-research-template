"""centrado.py -- (a) modelo de borde vs (b) simetría de pares: ¿cuál predice qué vecinos del anillo 1 son BF / mixtos / DF?

Uso:  python3 centrado.py            (todas las capturas de LISTA; escribe tabla.json, tabla.md, fig_centrado.png aquí)

Reproduce el núcleo de `precaptura.py centro` (repo, solo lectura: se importa sin escribir __pycache__) y agrega:
  * (b)+R,w: eje fijo en la estimación (b), R y w reajustados (para que (b) tenga su mejor borde, no el de (a));
  * predicción por vecino: fracción del ROI con |p - s(k - eje)| < R (modelo NO telecéntrico: el centro del círculo BF del
    vecino k está en s·(k - eje) px de ROI, s = 3538 px/paso = 6 mm / 0.001696 mm/px), banda ±w, esquinas/bordes iluminados;
  * observación: cociente vecino/central (oscuro restado, por ms, bineado 16, misma máscara que el chequeo), píxel "claro" si
    cociente > 0.5·A_ref (A_ref = mediana del percentil 90 de los 4 vecinos en cruz);
  * chequeos menos circulares: (a) ajustado SOLO a la cruz -> predice las diagonales (igual información que usa (b));
    leave-one-out sobre los 8 vecinos; (b) "diagonal": simetría de pares de las diagonales (LEDs distintos de los de (b)).
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1'); os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import sys
import json
import math
import time
sys.dont_write_bytecode = True
REPO = '/home/chanoscopio/Documents/LucasC/reproducible-research-template'
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import numpy as np  # noqa: E402
import precaptura as P  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BASE = '/home/chanoscopio/Documents/AleYLu/imagenes_tomadas'
OUT = os.path.dirname(os.path.abspath(__file__))
EJE0 = (17, 15)
B = 16
S = P.PASO_PX
# nombre -> (carpeta de oscuros, ROI si no hay captura.json)
LISTA = {
    '2026-10-20-muestra': ('2026-10-20-muestrasinluz', (4000, 1942)),
    '2026-10-21.500': ('2026-10-21-dark', (4000, 1942)),
    '2026-10-21.c': ('2026-10-21.c-dark', (4000, 1942)),
    '2026-10-21.d': ('2026-10-21.d-dark', (4000, 1942)),
    '2026-10-22': ('2026-10-22-dark', None),
    '2026-10-23': ('2026-10-23-dark', None),
    '2026-10-27-blue-b-prueba-1727': ('2026-10-27-blue-b-prueba-1727-dark', None),
    '2026-10-29-blue': ('2026-10-29-blue-dark', None),
    '2026-10-30-red-b': ('2026-10-30-red-b-dark', None),
    '2026-10-30-red-c': ('2026-10-30-red-c-dark', None),
    '2026-11-03-red': ('2026-11-03-red-dark', None),
}
VEC = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
CRUZ = [d for d in VEC if abs(d[0]) + abs(d[1]) == 1]
DIAG = [d for d in VEC if abs(d[0]) + abs(d[1]) == 2]
REG = 12  # bins (192 px) de los bloques de esquina / borde


def regiones(n):
    """Máscaras (n x n bins) de 4 esquinas y 4 bordes medios. Filas crecientes = ABAJO en la imagen."""
    r = {}
    a, z, m = slice(0, REG), slice(n - REG, n), slice(n // 2 - REG // 2, n // 2 + REG // 2)
    for nom, (sy, sx) in {'arr-izq': (a, a), 'arr-der': (a, z), 'abj-izq': (z, a), 'abj-der': (z, z),
                          'arriba': (a, m), 'abajo': (z, m), 'izq': (m, a), 'der': (m, z)}.items():
        mk = np.zeros((n, n), bool); mk[sy, sx] = True; r[nom] = mk
    return r


def ajustar(Q, M, dks, Y, X, p0=None, libres=(0, 1, 2, 3), eje_fijo=None):
    fit = P.AjusteBorde([q.ravel() for q in Q], dks, Y, X, [m.ravel() for m in M])
    libres = np.array(libres)
    base = np.array([0.0, 0.0, P.RADIO_PX / 1000, math.log(100.0), S / 1000]) if p0 is None else p0.copy()
    if eje_fijo is not None:
        base[:2] = eje_fijo; starts = [base]
    else:
        starts = []
        for ar in np.arange(-0.5, 0.51, 0.25):
            for ac in np.arange(-0.5, 0.51, 0.25):
                pp = base.copy(); pp[:2] = ar, ac; starts.append(pp)
    best = None
    for pp in starts:
        r = fit.resid(pp[libres], libres, pp); c = r @ r
        if best is None or c < best[0]:
            best = (c, pp)
    p, _ = fit.ajustar(best[1], libres)
    amp = fit.amplitudes(p)
    return p, [float(a[0]) for a in amp]


def prediccion(p, d, Y, X, mk, regs):
    ar, ac, R, w, s = p[0], p[1], p[2] * 1000, math.exp(p[3]), p[4] * 1000
    dist = np.hypot(Y - s * (d[0] - ar), X - s * (d[1] - ac))
    f = float(np.mean(dist[mk] < R)); fmin = float(np.mean(dist[mk] < R - w)); fmax = float(np.mean(dist[mk] < R + w))
    T = P.sigm((R - dist) / w)
    # margen del círculo respecto del LED sin corrimiento de campo (como la cuenta a mano) y con el píxel más cercano
    marg_centro = math.hypot(d[0] - ar, d[1] - ac) - R / s
    marg_roi = float(dist[mk].min() - R) / s
    return dict(f=f, fmin=fmin, fmax=fmax, clase=clase(f), clase_tol=clase_tol(fmin, fmax),
                reg={k: float(T[v & mk].mean()) for k, v in regs.items()},
                marg_centro=marg_centro, marg_roi=marg_roi), T


def clase(f):
    return 'BF' if f > 0.98 else ('DF' if f < 0.02 else 'mixto')


def clase_tol(fmin, fmax):
    a, b = clase(fmin), clase(fmax)
    return a if a == b else f'{a}/{b}'


def analizar(nombre, dark, roi_def):
    t_ini = time.time()
    carpeta = os.path.join(BASE, nombre)
    cj = os.path.join(carpeta, 'captura.json')
    roi = roi_def
    if os.path.exists(cj):
        with open(cj) as f:
            j = json.load(f)
        roi = (j['roi']['offset_x'], j['roi']['offset_y'])
    col = [d for d in os.listdir(carpeta) if d.startswith('fila17_col15_color')][0][-1]
    idx = P.indexar(carpeta, col)
    osc = P.Oscuro(os.path.join(BASE, dark))
    t0, c_img = P.elegir_t(idx[EJE0])
    C = (c_img - osc.en(t0)) / (t0 + P.T0_MS)
    Cb = P.binear(C, B); H, W = C.shape
    yy, xx = np.mgrid[:Cb.shape[0], :Cb.shape[1]]
    Y = ((yy + 0.5) * B - H / 2).ravel(); X = ((xx + 0.5) * B - W / 2).ravel()
    mC = Cb > 0.2 * np.median(Cb); mCf = C > 0.2 * np.median(C)
    Q, M, Qfull = {}, {}, {}
    for d in VEC:
        k = (EJE0[0] + d[0], EJE0[1] + d[1])
        t, im = P.elegir_t(idx[k])
        Nf = (im - osc.en(t)) / (t + P.T0_MS)
        Q[d] = np.where(mC, P.binear(Nf, B) / np.maximum(Cb, 1e-6), 0.0); M[d] = mC.copy()
        Qfull[d] = np.where(mCf, Nf / np.maximum(C, 1e-6), np.nan)
    n = Cb.shape[0]; regs = {k: v.ravel() for k, v in regiones(n).items()}; mk = mC.ravel()

    # (a) completo
    pa, Aa = ajustar([Q[d] for d in VEC], [M[d] for d in VEC], VEC, Y, X)
    # (a) con s libre (¿la escala no telecéntrica 3538 px/paso es la de los datos?)
    ps, _ = ajustar([Q[d] for d in VEC], [M[d] for d in VEC], VEC, Y, X, p0=pa, libres=(0, 1, 2, 3, 4), eje_fijo=pa[:2])
    # (b) simetría de pares de la cruz (idéntico a precaptura) y de las diagonales
    Yf, Xf = P.coords(C.shape)

    def sim(dp, e):
        dm = (-dp[0], -dp[1])
        ms = [P.espejo(Qfull[dp], Qfull[dm], e, Yf, Xf, banda) for banda in ((-450, 450), (-450, 0), (0, 450))]
        return ms
    fino = {}
    for comp, d in ((0, (1, 0)), (1, (0, 1))):
        ms = sim(d, d)
        fino[comp] = None if (ms[0] is None or abs(pa[comp]) >= 0.12) else -ms[0] / S
    eje_b = (fino[0] if fino[0] is not None else pa[0], fino[1] if fino[1] is not None else pa[1])
    b_aplica = fino[0] is not None and fino[1] is not None
    # diagonales: proyección del eje sobre (1,1)/√2 y (1,-1)/√2 (solo si los espejos se solapan)
    diag = {}
    for d in ((1, 1), (1, -1)):
        e = np.array(d, float) / math.sqrt(2)
        ms = sim(d, e)
        diag[d] = None if ms[0] is None else -ms[0] / S
    eje_bd = None
    if diag[(1, 1)] is not None and diag[(1, -1)] is not None:
        u, v = diag[(1, 1)], diag[(1, -1)]
        eje_bd = ((u + v) / math.sqrt(2), (u - v) / math.sqrt(2))
    # (b) con R, w propios
    pb, Ab = ajustar([Q[d] for d in VEC], [M[d] for d in VEC], VEC, Y, X, p0=pa, libres=(2, 3), eje_fijo=eje_b)
    # solo cruz: (a') libre, (b') eje fijo -> predicen diagonales
    pax, _ = ajustar([Q[d] for d in CRUZ], [M[d] for d in CRUZ], CRUZ, Y, X)
    pbx, _ = ajustar([Q[d] for d in CRUZ], [M[d] for d in CRUZ], CRUZ, Y, X, p0=pa, libres=(2, 3), eje_fijo=eje_b)
    # leave-one-out
    loo = {}
    for d in VEC:
        resto = [e for e in VEC if e != d]
        loo[d], _ = ajustar([Q[e] for e in resto], [M[e] for e in resto], resto, Y, X)

    # observación
    qn = {d: Q[d].ravel() for d in VEC}
    Aref = float(np.median([np.percentile(qn[d][mk], 90) for d in CRUZ]))
    obs = {}
    for d in VEC:
        q = qn[d] / Aref
        obs[d] = dict(f=float(np.mean(q[mk] > 0.5)), clase=clase(float(np.mean(q[mk] > 0.5))),
                      reg={k: float(np.median(q[v & mk])) for k, v in regs.items()},
                      p90=float(np.percentile(q[mk], 90)))
    modelos = {'a': pa, 'b': pb, 'a_cruz': pax, 'b_cruz': pbx}
    pred = {m: {} for m in modelos}; pred['loo'] = {}
    for m, p in modelos.items():
        for d in VEC:
            pred[m][d], _ = prediccion(p, d, Y, X, mk, regs)
    for d in VEC:
        pred['loo'][d], _ = prediccion(loo[d], d, Y, X, mk, regs)

    def par(p):
        return dict(eje=[float(p[0]), float(p[1])], R_pasos=float(p[2] * 1000 / S), w_px=float(math.exp(p[3])),
                    s=float(p[4] * 1000))
    res = dict(nombre=nombre, color=col, roi=list(roi), t_central=t0, Aref=Aref,
               a=par(pa), a_A=dict(zip(map(str, VEC), Aa)), b=par(pb), b_A=dict(zip(map(str, VEC), Ab)),
               b_aplica=b_aplica, b_fino=[fino[0], fino[1]], s_libre=par(ps),
               b_diag=None if eje_bd is None else [float(eje_bd[0]), float(eje_bd[1])],
               b_diag_proy={str(k): v for k, v in diag.items()},
               a_cruz=par(pax), b_cruz=par(pbx), loo={str(d): par(loo[d]) for d in VEC},
               obs={str(d): obs[d] for d in VEC},
               pred={m: {str(d): v for d, v in pm.items()} for m, pm in pred.items()},
               seg=round(time.time() - t_ini, 1))
    # puntajes: error de fracción clara y acuerdo de clase (todos los vecinos; diagonales para los modelos de cruz)
    sc = {}
    for m in ('a', 'b', 'loo', 'a_cruz', 'b_cruz'):
        ds = DIAG if m.endswith('cruz') else VEC
        err = [abs(pred[m][d]['f'] - obs[d]['f']) for d in ds]
        ok = [pred[m][d]['clase'] == obs[d]['clase'] for d in ds]
        rerr = [np.mean([abs(pred[m][d]['reg'][k] - obs[d]['reg'][k]) for k in regs]) for d in ds]
        esq = ('arr-izq', 'arr-der', 'abj-izq', 'abj-der')
        ediag = [abs(pred[m][d]['reg'][k] - obs[d]['reg'][k]) for d in DIAG for k in esq]
        sc[m] = dict(err_f=float(np.mean(err)), clases_ok=int(sum(ok)), n=len(ds), err_reg=float(np.mean(rerr)),
                     err_esq_diag=float(np.mean(ediag)))
    res['score'] = sc
    np.savez_compressed(os.path.join(OUT, f'mapas_{nombre}.npz'), **{f'q_{d[0]}_{d[1]}': Q[d] / Aref for d in VEC},
                        mask=mC)
    print(f'{nombre}: {res["seg"]} s  a={res["a"]["eje"]} b={res["b"]["eje"]} '
          + ' '.join(f'{m}:{v["clases_ok"]}/{v["n"]},{v["err_f"]:.3f}' for m, v in sc.items()), flush=True)
    return res


def main():
    sel = sys.argv[1:] or list(LISTA)
    out = []
    jp = os.path.join(OUT, 'tabla.json')
    for nom in sel:
        dark, roi = LISTA[nom]
        out.append(analizar(nom, dark, roi))
        with open(jp, 'w') as f:
            json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()

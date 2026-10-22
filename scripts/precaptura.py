#!/usr/bin/env python3
"""precaptura.py -- chequeos rápidos en el microscopio ANTES (y justo después) de una captura FPM 15x15.

Solo numpy + PIL + matplotlib. Cada subcomando imprime un veredicto corto por chequeo (OK / CORREGIR + qué hacer)
y guarda UNA figura PNG de resumen (por defecto en el directorio actual, ver --png).

Estructura de imágenes que escribe el programa de captura:
    <carpeta>/fila{R}_col{C}_color{r|g|b}/{t}ms/imagen_frame_{n}.tiff     (Mono12, 0-4095, uint16, ROI 1120x1120)
Se promedian los frames. Las carpetas que no siguen el patrón (p. ej. 'organizado') se ignoran.

Subcomandos
-----------
1) centro <carpeta> [--led 17,15] [--offset 4000,1942] [--dark <carpeta_oscuro>]
   Imágenes del LED objetivo, sus 4 vecinos en cruz y, mejor, las 4 diagonales; SIN muestra (flat) o con muestra rala.
   Trabaja con el cociente vecino / LED central (cuentas/ms sobre oscuro) y s = px de ROI por paso de LED (3538 px,
   calibración 21/10, rojo, z 102 mm, 2.5x; sistema NO telecéntrico en objeto: cambiar --paso-px si cambia z).
   (a) grueso: modelo común de borde campo claro/oscuro, cociente = A_k*escalón((R - |p - s*(k - eje)|)/w) + b_k,
       R = radio BF (libre; calibración 4132 px = 1.168 pasos). Sirve cuando el eje está corrido y los arcos caen
       dentro del ROI. Con el eje centrado los arcos quedan ~35 px FUERA del ROI y este ajuste no es fiable.
   (b) fino (si |desvío| < ~0.12 paso): simetría de los pares opuestos de la cruz. El cociente de (f+1,c) es el espejo
       del de (f-1,c) respecto de y = -s*desvío_fila (ídem columnas), sea cual sea la forma real del borde (tiene una
       banda brillante junto al borde que el escalón no modela). Se informa también la mitad izquierda vs derecha.
   OK si |desvío| < 0.05 paso; si no, da el cambio de OffsetX/OffsetY del ROI (filas -> +y, columnas -> +x):
   Offset_nuevo = Offset_actual - desvío_pasos * 3538 px  (o la matriz se movió desvío * 6 mm).
   Ejemplo:  python3 scripts/precaptura.py centro ~/Documents/AleYLu/imagenes_tomadas/2026-10-21-sinmuestra
             python3 scripts/precaptura.py centro .../2026-10-20-luzsinmuestra --offset 4032,3040

2) exposicion <carpeta> --dark <carpeta_oscuro> [--led 17,15]
   Fotos de prueba de algunos LEDs por anillo (anillo = round(distancia radial al LED del eje), igual que
   results/captura_2026-10-21/qc.py). Por LED: señal sobre oscuro en cuentas/ms (mediana y percentil 99.9) y
   fracción saturada. Recomienda: exposición de campo claro (BF) con p99.9 crudo ~ 80 % del rango (3276 cuentas);
   exposición de campo oscuro (DF) por anillo, tope T_MAX = 1025 ms, con p99.9 crudo < 3500; y número de frames N por anillo
   para mediana de SNR >= 3. Modelo de ruido por frame: var = g*S + var_oscuro [cuentas^2]; g y var_oscuro se
   ajustan con las diferencias entre frames de los propios datos (si hay >= 2 frames), si no se usan los valores
   por defecto medidos el 21/10 (g 0.297, var 7.1; ver nota en DEFAULT_GAIN). Escribe además un CSV
   (Fila, Columna, Tiempo_ms, N_frames) para la grilla 15x15 junto a la figura.
   Ejemplo:  python3 scripts/precaptura.py exposicion .../2026-10-21 --dark .../2026-10-21-dark

3) qc <carpeta> [--flat <carpeta_flat>] [--dark <carpeta_oscuro>] [--led 17,15]
   Post-captura: completitud de la grilla 15x15, frames por LED, exposiciones, oscuros para cada exposición usada,
   saturación, y tabla de señal y SNR por anillo.
   Ejemplo:  python3 scripts/precaptura.py qc .../2026-10-21 --flat .../2026-10-21-sinmuestra --dark .../2026-10-21-dark

Opciones comunes: --color r|g|b (si la carpeta tiene más de un color), --png <ruta.png>.
"""
import argparse
import json
import glob
import math
import os
import re
import sys
import time

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

RANGO = 4095                 # Mono12
PASO_PX = 3538.0             # px de ROI por paso de LED (visionpoint 21/10, rojo, z 102 mm, 2.5x)
RADIO_PX = 4132.0            # radio del círculo de campo claro en px de ROI (= 1.168 pasos)
PITCH_MM = 6.0               # paso de la matriz de LEDs
OFFSET_REF = (4000, 1942)    # ROI bueno 21/10: eje sobre el LED (17,15)
T0_MS = -0.20                # exposición efectiva = t + T0 (results/octubre_capturas_2026-10-21, prep_2110.py)
NIVEL_OSCURO = 188.0         # cuentas, oscuro medio 21/10 (si no se da --dark)
# Modelo de ruido por frame var = g*S + v0 [cuentas^2]. prep.log del 21/10 dice "ganancia 0.189, var lectura 71.3", pero ese
# ajuste (pendiente/ordenada de var vs media en UNA imagen BF de 5 ms) no reproduce las diferencias de frames: los oscuros
# dan var 7.1 por frame (5/128/257 ms) y los BF a 5 y 8 ms dan pendiente 0.297 (175 y 311 cuentas^2 a S = 565 y 1026).
DEFAULT_GAIN, DEFAULT_VAR0 = 0.297, 7.1
BF_OBJ = 0.80 * RANGO        # p99.9 crudo objetivo en BF
DF_MAX = 3500.0              # p99.9 crudo máximo en DF
T_MAX = 1025.0               # ms, máximo del programa de captura (line time 1000 + frame 1150 ms, desde el 22/10; antes 257)
SNR_OBJ = 3.0

RX_LED = re.compile(r'^fila(\d+)_col(\d+)_color([rgb])$')
RX_T = re.compile(r'^(\d+(?:\.\d+)?)ms$')


# ----------------------------------------------------------------------------------------------- utilidades de E/S
def tstr(t):
    return f'{t:g}'


def indexar(carpeta, color=None, solo_color=True):
    """{(fila, col): {t_ms: [archivos]}} de una carpeta de captura."""
    carpeta = os.path.expanduser(carpeta)
    if not os.path.isdir(carpeta):
        sys.exit(f'ERROR: no existe la carpeta {carpeta}')
    out, colores = {}, set()
    for d in sorted(os.listdir(carpeta)):
        m = RX_LED.match(d)
        if not m:
            continue
        colores.add(m.group(3))
        if color and solo_color and m.group(3) != color:
            continue
        k = (int(m.group(1)), int(m.group(2)))
        ent = out.setdefault(k, {})
        for e in os.listdir(os.path.join(carpeta, d)):
            mt = RX_T.match(e)
            if mt:
                fs = sorted(glob.glob(os.path.join(carpeta, d, e, 'imagen_frame_*.tif*')))
                ent.setdefault(float(mt.group(1)), []).extend(fs)
    if solo_color and color is None and len(colores) > 1:
        sys.exit(f'ERROR: {carpeta} tiene colores {sorted(colores)}: elegir uno con --color')
    return out


def leer(fs, maxf=None):
    """Promedio (float), diferencia de los 2 primeros frames (float32, o None), n saturados (algún frame)."""
    fs = fs[:maxf] if maxf else fs
    acc, sat, prim = None, None, []
    for f in fs:
        a = np.asarray(Image.open(f))
        s = a >= RANGO
        sat = s if sat is None else (sat | s)
        acc = a.astype(np.float64) if acc is None else acc + a
        if len(prim) < 2:
            prim.append(a)
    m = acc / len(fs)
    dif = prim[0].astype(np.float32) - prim[1].astype(np.float32) if len(prim) == 2 else None
    return m, dif, int(sat.sum())


class Oscuro:
    """Oscuro por exposición (imagen media por t); interpola linealmente en t entre las disponibles."""

    def __init__(self, carpeta=None, nivel=NIVEL_OSCURO):
        self.img, self.var, self.nfr, self.nivel = {}, {}, {}, nivel
        if carpeta:
            idx = indexar(carpeta, solo_color=False)
            por_t = {}
            for k, ts in idx.items():
                for t, fs in ts.items():
                    if fs:
                        por_t.setdefault(t, []).append(fs)
            for t, lst in por_t.items():
                lst = lst[:2]            # el oscuro no depende del LED: con 2 carpetas por exposición alcanza (rapidez)
                ms, vs = [], []
                for fs in lst:
                    m, dif, _ = leer(fs)
                    ms.append(m); vs.append(float(np.var(dif) / 2) if dif is not None else None)
                self.img[t] = np.mean(ms, 0)
                vs = [x for x in vs if x is not None]
                self.var[t] = float(np.mean(vs)) if vs else None
                self.nfr[t] = sum(len(fs) for fs in lst)

    def tiempos(self):
        return sorted(self.img)

    def en(self, t):
        if not self.img:
            return self.nivel
        ts = self.tiempos()
        if t in self.img:
            return self.img[t]
        if t <= ts[0]:
            return self.img[ts[0]]
        if t >= ts[-1]:
            return self.img[ts[-1]]
        j = int(np.searchsorted(ts, t)); a, b = ts[j - 1], ts[j]; f = (t - a) / (b - a)
        return (1 - f) * self.img[a] + f * self.img[b]

    def media(self, t):
        x = self.en(t)
        return float(np.mean(x)) if np.ndim(x) else float(x)

    def var0(self):
        v = [x for x in self.var.values() if x is not None]
        return float(np.mean(v)) if v else None


def anillo(k, eje):
    """Anillo como en results/captura_2026-10-21/qc.py: round(distancia radial al LED del eje)."""
    return int(round(math.hypot(k[0] - eje[0], k[1] - eje[1])))


def par_int(s):
    a, b = s.split(','); return (int(a), int(b))


def ruta_png(args, sub, carpeta):
    if args.png:
        return args.png
    return os.path.abspath(f'precaptura_{sub}_{os.path.basename(os.path.normpath(carpeta))}.png')


def veredicto(ok, texto):
    print(('  [OK]       ' if ok else '  [CORREGIR] ') + texto)


# ------------------------------------------------------------------------------------------------------- centro
def sigm(u):
    return 0.5 * (1.0 + np.tanh(0.5 * u))


def elegir_t(ts):
    """La exposición más larga sin saturación apreciable (< 1e-4 de los píxeles); si todas saturan, la más corta."""
    best = None
    for t in sorted(ts, reverse=True):
        fs = ts[t]
        if not fs:
            continue
        m, _, ns = leer(fs)
        if ns < 1e-4 * m.size:
            return t, m
        best = (t, m)
    return best


def binear(a, b):
    H, W = a.shape; H2, W2 = H // b * b, W // b * b
    return a[:H2, :W2].reshape(H2 // b, b, W2 // b, b).mean((1, 3))


class AjusteBorde:
    """Ajuste conjunto de los bordes BF/DF de los vecinos: parámetros no lineales p = (eje_f, eje_c, R/1000, log w, s/1000);
    A_k, b_k lineales (eliminados por mínimos cuadrados en cada evaluación, con previa A~1+-0.15, b~0+-0.05)."""

    def __init__(self, Q, dks, Y, X, M, s=PASO_PX):
        self.Q, self.dks, self.Y, self.X, self.M = Q, dks, Y, X, M
        self.W = [m.astype(float) for m in M]
        self.sig = [0.02] * len(Q)
        self.s = s

    def perfiles(self, p):
        ar, ac, R, lw, s = p[0], p[1], p[2] * 1000, p[3], p[4] * 1000
        w = math.exp(lw)
        out = []
        for dr, dc in self.dks:
            d = np.hypot(self.Y - s * (dr - ar), self.X - s * (dc - ac))
            out.append(sigm((R - d) / w))
        return out

    def lineal(self, T, q, wt, sg):
        sw = np.sqrt(wt) / sg
        A = np.vstack([np.r_[T * sw, 1 / 0.15, 0], np.r_[sw, 0, 1 / 0.05]]).T
        y = np.r_[q * sw, 1 / 0.15, 0]
        return np.linalg.lstsq(A, y, rcond=None)[0]

    def resid(self, p, libres, p_full):
        pf = p_full.copy(); pf[libres] = p
        rs = []
        for T, q, wt, sg in zip(self.perfiles(pf), self.Q, self.W, self.sig):
            A, b = self.lineal(T, q, wt, sg)
            rs.append((q - A * T - b) * np.sqrt(wt) / sg)
            rs.append(np.array([(A - 1) / 0.15, b / 0.05]))
        return np.concatenate(rs)

    def lm(self, p_full, libres, nit=40):
        p = p_full[libres].copy(); lam = 1e-2
        r = self.resid(p, libres, p_full); c = r @ r
        for _ in range(nit):
            J = np.empty((r.size, p.size)); h = 1e-4
            for j in range(p.size):
                pp = p.copy(); pp[j] += h
                J[:, j] = (self.resid(pp, libres, p_full) - r) / h
            H = J.T @ J; g = J.T @ r
            mejora = False
            for _ in range(8):
                dp = -np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-12), g)
                rn = self.resid(p + dp, libres, p_full); cn = rn @ rn
                if cn < c:
                    p, r, c, lam, mejora = p + dp, rn, cn, max(lam / 3, 1e-6), True
                    break
                lam *= 4
            if not mejora or np.max(np.abs(dp)) < 1e-6:
                break
        out = p_full.copy(); out[libres] = p
        try:
            cov = np.linalg.inv(J.T @ J) * (c / max(r.size - p.size, 1))
        except np.linalg.LinAlgError:
            cov = np.full((p.size, p.size), np.nan)
        return out, cov

    def ajustar(self, p0, libres, nrob=3):
        p = p0.copy(); cov = None
        for _ in range(nrob):
            p, cov = self.lm(p, libres)
            for i, (T, q) in enumerate(zip(self.perfiles(p), self.Q)):
                A, b = self.lineal(T, q, self.W[i], self.sig[i])
                e = (q - A * T - b)[self.M[i]]
                sg = 1.4826 * np.median(np.abs(e - np.median(e))) + 1e-6
                self.sig[i] = sg
                u = (q - A * T - b) / (4.685 * sg)
                self.W[i] = np.where(np.abs(u) < 1, (1 - u ** 2) ** 2, 0.0) * self.M[i]
        return p, cov

    def amplitudes(self, p):
        return [self.lineal(T, q, wt, sg) for T, q, wt, sg in zip(self.perfiles(p), self.Q, self.W, self.sig)]


def coords(shape):
    H, W = shape
    yy, xx = np.mgrid[:H, :W]
    return yy - H / 2 + 0.5, xx - W / 2 + 0.5


def perfil(q, e, Y, X, banda):
    """Perfil (mediana) de q a lo largo de la dirección e (px, bins de 8), con |coord. perpendicular| en banda."""
    e = np.asarray(e, float); e = e / np.linalg.norm(e)
    u = Y * e[0] + X * e[1]; v = -Y * e[1] + X * e[0]
    ok = np.isfinite(q) & (v >= banda[0]) & (v <= banda[1])
    ub = np.round(u[ok] / 8).astype(int); qs = q[ok]
    o = np.argsort(ub, kind='stable'); ub, qs = ub[o], qs[o]
    lo, hi = ub[0], ub[-1]; cuts = np.searchsorted(ub, np.arange(lo, hi + 2))
    P = np.array([np.median(qs[cuts[i]:cuts[i + 1]]) if cuts[i + 1] - cuts[i] >= 20 else np.nan for i in range(hi - lo + 1)])
    return np.arange(lo, hi + 1) * 8.0, P


def espejo(qp, qm, e, Y, X, banda):
    """Punto m (px a lo largo de e) tal que perfil_{+d}(u) = a * perfil_{-d}(2m - u); a = cociente de mesetas centrales."""
    up, Pp = perfil(qp, e, Y, X, banda); um, Pm = perfil(qm, e, Y, X, banda)
    g = np.isfinite(Pm)
    if g.sum() < 30:
        return None
    a = np.nanmedian(Pp[np.abs(up) < 150]) / np.nanmedian(Pm[np.abs(um) < 150])
    ms = np.arange(-500, 501, 2.0); cst = np.full(ms.size, np.inf)
    for i, m in enumerate(ms):
        x = 2 * m - up; ok = np.isfinite(Pp) & (x >= um[g][0]) & (x <= um[g][-1])
        if ok.sum() >= 25:
            cst[i] = np.mean((Pp[ok] - a * np.interp(x[ok], um[g], Pm[g])) ** 2)
    i = int(np.argmin(cst))
    if not np.isfinite(cst[i]) or i in (0, ms.size - 1):
        return None
    y0, y1, y2 = cst[i - 1:i + 2]; den = y0 - 2 * y1 + y2
    return float(ms[i] + (0.5 * (y0 - y2) / den * 2 if den > 0 else 0))


def cmd_centro(args):
    t_ini = time.time()
    eje0 = par_int(args.led); off = par_int(args.offset)
    idx = indexar(args.carpeta, args.color)
    osc = Oscuro(args.dark)
    print(f'== precaptura centro: {args.carpeta}\n   LED objetivo {eje0}, ROI actual OffsetX {off[0]}, OffsetY {off[1]}, '
          f'paso {args.paso_px:g} px/LED, oscuro: {"carpeta" if args.dark else f"nivel fijo {NIVEL_OSCURO:g}"}')
    if eje0 not in idx or not any(idx[eje0].values()):
        print(f'  [CORREGIR] falta la imagen del LED objetivo {eje0}: tomarla (sin muestra o con muestra rala).'); return 2
    t0, c_img = elegir_t(idx[eje0])
    C = (c_img - osc.en(t0)) / (t0 + T0_MS)
    vec = [(eje0[0] + dr, eje0[1] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
    pres = [k for k in vec if k in idx and any(idx[k].values())]
    falt = [k for k in vec if k not in pres]
    cruz = [k for k in pres if abs(k[0] - eje0[0]) + abs(k[1] - eje0[1]) == 1]
    if len(cruz) < 4:
        print(f'  [CORREGIR] faltan vecinos en cruz {sorted(set(vec) - set(pres))}: hacen falta los 4 (y mejor también las diagonales).')
        if len(pres) < 3:
            return 2
    elif falt:
        print(f'  (sin diagonales {falt}: el ajuste usa solo la cruz; con diagonales es más robusto)')
    b = 16
    Cb = binear(C, b); H, W = C.shape
    yy, xx = np.mgrid[:Cb.shape[0], :Cb.shape[1]]
    Y = (yy + 0.5) * b - H / 2; X = (xx + 0.5) * b - W / 2
    mC = Cb > 0.2 * np.median(Cb); mCf = C > 0.2 * np.median(C)
    Q, M, dks, tk, Qfull = [], [], [], {}, {}
    for k in pres:
        t, im = elegir_t(idx[k]); tk[k] = t
        Nfull = (im - osc.en(t)) / (t + T0_MS); Nk = binear(Nfull, b)
        Q.append(np.where(mC, Nk / np.maximum(Cb, 1e-6), 0.0)); M.append(mC.copy())
        d = (k[0] - eje0[0], k[1] - eje0[1]); dks.append(d)
        Qfull[d] = np.where(mCf, Nfull / np.maximum(C, 1e-6), np.nan)
    # (a) GRUESO: modelo de borde (escalón logístico) ajustado a todos los vecinos; sirve con el eje corrido (arcos dentro del ROI)
    Y, X = Y.ravel(), X.ravel()
    Qf = [q.ravel() for q in Q]; Mf = [m.ravel() for m in M]
    fit = AjusteBorde(Qf, dks, Y, X, Mf)
    p0 = np.array([0.0, 0.0, args.radio_px / 1000, math.log(100.0), args.paso_px / 1000])
    libres = np.array([0, 1, 2, 3] + ([4] if args.ajustar_paso else []))
    best = None
    for ar in np.arange(-0.5, 0.51, 0.25):
        for ac in np.arange(-0.5, 0.51, 0.25):
            pp = p0.copy(); pp[:2] = ar, ac
            r = fit.resid(pp[libres], libres, pp); c = r @ r
            if best is None or c < best[0]:
                best = (c, pp)
    p, cov = fit.ajustar(best[1], libres)
    R, w, s = p[2] * 1000, math.exp(p[3]), p[4] * 1000
    gr, gc = p[0], p[1]
    # (b) FINO: simetría de los pares opuestos de la cruz. Con el eje en -s*eje (px), el cociente del vecino +d es el espejo del
    # de -d respecto de ese punto, sea cual sea la forma del borde (incluida la banda brillante junto al borde). Necesita que los
    # espejos se solapen en el ROI (|desvío| <~ 0.12 paso). Amplitud relativa del par = cociente de sus mesetas centrales.
    fino, unc = {}, {}
    for comp, d in ((0, (1, 0)), (1, (0, 1))):
        dm = (-d[0], -d[1])
        if d in Qfull and dm in Qfull and abs(p[comp]) < 0.12:
            ms = [espejo(Qfull[d], Qfull[dm], d, Yf, Xf, banda) for banda in ((-450, 450), (-450, 0), (0, 450))
                  for Yf, Xf in [coords(C.shape)]]
            if ms[0] is not None:
                fino[comp] = -ms[0] / s
                h = [m for m in ms[1:] if m is not None]
                unc[comp] = abs(h[0] - h[1]) / 2 / s if len(h) == 2 else float('nan')
    dr = fino.get(0, gr); dc = fino.get(1, gc)
    sd = np.sqrt(np.abs(np.diag(cov)))[:2] * b
    print(f'  imágenes: central {tstr(t0)} ms; vecinos ' + ', '.join(f'{k}:{tstr(tk[k])}ms' for k in pres))
    print(f'  (a) modelo de borde, todos los vecinos: desvío (fila, col) = ({gr:+.3f}, {gc:+.3f}) pasos; R = {R:.0f} px = {R / s:.3f} pasos '
          f'(calibración {RADIO_PX / PASO_PX:.3f}), ancho w = {w:.0f} px' + (f', s = {s:.0f} px/paso' if args.ajustar_paso else ''))
    if fino:
        print('  (b) simetría de pares de la cruz: ' + ', '.join(f'{"fila" if c == 0 else "col"} {v:+.3f} (+-{unc[c]:.3f} mitades)'
                                                             for c, v in sorted(fino.items())))
    else:
        print('  (b) simetría de pares: no aplicable (eje lejos o falta un par de la cruz) -> se usa (a); repetir tras corregir')
    print(f'  EJE ÓPTICO en LED fila {eje0[0] + dr:.3f}, columna {eje0[1] + dc:.3f}  ->  desvío ({dr:+.3f}, {dc:+.3f}) pasos'
          f' = ({dr * s:+.0f}, {dc * s:+.0f}) px de ROI  [fuente: fila {"(b)" if 0 in fino else "(a)"}, col {"(b)" if 1 in fino else "(a)"}]')
    mod = math.hypot(dr, dc)
    if abs(R / s - RADIO_PX / PASO_PX) > 0.08:
        veredicto(False, f'radio BF {R / s:.3f} pasos lejos de 1.168: ¿cambió z, el objetivo o el color? Rehacer la calibración de '
                         f'arcos (visionpoint) antes de confiar en px/paso.')
    disc = max([abs(fino[c] - p[c]) for c in fino] + [0.0])
    if disc > 0.06:
        print(f'             (a) y (b) difieren {disc:.3f} pasos: normal con el eje centrado (los arcos caen fuera del ROI y (a) '
              f'es poco fiable); vale (b).')
    sugerido = None
    if mod < 0.05:
        veredicto(True, f'eje centrado sobre {eje0} (|desvío| = {mod:.3f} < 0.05 paso). No tocar el ROI.')
        ok = True
    else:
        # la cámara acepta OffsetX en múltiplos de 32 y OffsetY en múltiplos de 2 (driver_imperx.py)
        nx, ny = 32 * round((off[0] - dc * s) / 32), 2 * round((off[1] - dr * s) / 2)
        sugerido = [nx, ny]
        veredicto(False, f'eje corrido {mod:.3f} pasos de {eje0}. Mover el ROI: OffsetX {off[0]} -> {nx} ({nx - off[0]:+d} px), '
                         f'OffsetY {off[1]} -> {ny} ({ny - off[1]:+d} px), ya redondeados al incremento de la cámara; '
                         f'luego repetir este chequeo' + ('' if len(fino) == 2 else ' (la estimación fina (b) recién vale cerca del centro)') + '.')
        if off == OFFSET_REF:
            print(f'             El ROI ya es el bueno del 21/10 ({OFFSET_REF[0]},{OFFSET_REF[1]}): si no se cambió a propósito, '
                  f'la matriz (o la cámara) se movió ~({dr * PITCH_MM:+.2f}, {dc * PITCH_MM:+.2f}) mm en (filas, columnas); '
                  f'alternativa: volver a ponerla en su lugar.')
        ok = False
    # figura
    fig = plt.figure(figsize=(15, 11))
    gs = fig.add_gridspec(3, 4)
    amp = fit.amplitudes(p); perf = fit.perfiles(p)
    ext = (-W / 2, W / 2, H / 2, -H / 2); L = 1000
    for i, (d, q) in enumerate(zip(dks, Q)):
        a = fig.add_subplot(gs[d[0] + 1, d[1] + 1])
        a.imshow(q / max(amp[i][0], 0.05), extent=ext, cmap='gray', vmin=0, vmax=1.2)
        cy, cx = s * (d[0] - dr), s * (d[1] - dc); th = np.linspace(0, 2 * np.pi, 2000)
        a.plot(cx + R * np.cos(th), cy + R * np.sin(th), 'r-', lw=1)
        a.plot([-W / 2, W / 2, W / 2, -W / 2, -W / 2], [-H / 2, -H / 2, H / 2, H / 2, -H / 2], 'y-', lw=.8)
        a.set_xlim(-L, L); a.set_ylim(L, -L); a.set_xticks([]); a.set_yticks([])
        a.set_title(f'{pres[i]} {tstr(tk[pres[i]])} ms  A={amp[i][0]:.2f}', fontsize=9)
    a = fig.add_subplot(gs[1, 1]); a.imshow(C, extent=ext, cmap='gray'); a.set_xlim(-L, L); a.set_ylim(L, -L)
    a.set_title(f'central {eje0} {tstr(t0)} ms (cuentas/ms)', fontsize=9); a.set_xticks([]); a.set_yticks([])
    a = fig.add_subplot(gs[:, 3])
    for rr in range(eje0[0] - 2, eje0[0] + 3):
        for cc in range(eje0[1] - 2, eje0[1] + 3):
            a.plot(cc, rr, 'o', color='0.6' if (rr, cc) not in idx else 'k', ms=6)
    th = np.linspace(0, 2 * np.pi, 400)
    a.plot(eje0[1] + dc + R / s * np.cos(th), eje0[0] + dr + R / s * np.sin(th), 'r-', lw=1, label='campo claro (radio ajustado)')
    a.plot(eje0[1] + dc, eje0[0] + dr, 'r+', ms=16, mew=2, label='eje óptico (ajuste)')
    a.plot(eje0[1], eje0[0], 'bs', mfc='none', ms=14, label='LED objetivo')
    a.add_patch(plt.Circle((eje0[1], eje0[0]), 0.05, color='g', alpha=.3, label='tolerancia 0.05'))
    a.set_aspect('equal'); a.invert_yaxis(); a.set_xlabel('columna'); a.set_ylabel('fila'); a.legend(fontsize=8, loc='lower center')
    a.set_title(('OK' if ok else 'CORREGIR') + f': desvío ({dr:+.3f}, {dc:+.3f}) pasos\n= ({dr * s:+.0f}, {dc * s:+.0f}) px ROI', fontsize=11)
    fig.suptitle(f'precaptura centro  {args.carpeta}\ncociente vecino/central (normalizado por A); rojo = borde ajustado; '
                 f'amarillo = ROI', fontsize=10)
    fig.tight_layout(); png = ruta_png(args, 'centro', args.carpeta); fig.savefig(png, dpi=80); plt.close(fig)
    # resultado legible por el script de captura (lo copia ./chequeo.sh a chequeos/centro_actual.json)
    with open(os.path.splitext(png)[0] + '.json', 'w') as f:
        json.dump({'ok': ok, 'fecha': time.strftime('%Y-%m-%d %H:%M'), 'carpeta': os.path.abspath(args.carpeta),
                   'led': list(eje0), 'desvio_pasos': [round(dr, 4), round(dc, 4)],
                   'offset_roi': list(off), 'offset_sugerido': sugerido}, f, indent=1)
    print(f'  figura: {png}   ({time.time() - t_ini:.1f} s)')
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------------------- exposición
def stats_led(ts, osc, todas=False):
    """Estadísticos de un LED: usa la exposición más larga sin saturación (o todas). Devuelve lista de dicts."""
    out = []
    for t in sorted(ts, reverse=True):
        fs = ts[t]
        if not fs:
            continue
        m, dif, ns = leer(fs)
        dk = osc.en(t); dm = osc.media(t); te = t + T0_MS
        S = m - dk
        sub = m[::2, ::2]
        med = float(np.median(binear(S, 4)))          # mediana de bloques 4x4: no queda cuantizada en 0.5 cuenta
        v = vmed = None
        if dif is not None:
            v = float(np.var(dif) / 2)                 # var por frame, toda la imagen (para el ajuste del modelo, con la media)
            q1, q3 = np.percentile(S[::2, ::2], [25, 75])
            sel = (S >= q1) & (S <= q3)
            vmed = float(np.var(dif[sel]) / 2)         # var por frame de los píxeles de nivel ~ mediana (SNR medido)
        r = dict(t=t, nfr=len(fs), med=med, media=float(S.mean()), p999=float(np.percentile(sub, 99.9)),
                 sat=ns / m.size, var1=v, var1_med=vmed, dark=dm)
        r['cms_med'] = r['med'] / te; r['cms_p999'] = (r['p999'] - dm) / te
        out.append(r)
        if not todas and ns < 1e-4 * m.size:
            break
    return out


def ajustar_ruido(puntos, var_osc):
    """var1 = g*S + v0 por mínimos cuadrados (S = media sobre oscuro); incluye el oscuro (S=0) si hay."""
    P = [(s, v) for s, v in puntos if v is not None]
    if var_osc is not None:
        P += [(0.0, var_osc)] * 3
    P = np.array(P)
    if len(P) < 4 or np.ptp(P[:, 0]) < 50:
        return DEFAULT_GAIN, DEFAULT_VAR0, False
    w = 1 / (P[:, 1] + 1)            # pesos relativos ~ 1/var (los BF no dominan)
    A = np.vstack([P[:, 0], np.ones(len(P))]).T * w[:, None]
    g, v0 = np.linalg.lstsq(A, P[:, 1] * w, rcond=None)[0]
    if g <= 0 or v0 <= 0:
        return DEFAULT_GAIN, DEFAULT_VAR0, False
    return float(g), float(v0), True


def elegir_muestra(keys, eje, maxn):
    """Hasta maxn LEDs por anillo, repartidos en ángulo."""
    por = {}
    for k in keys:
        por.setdefault(anillo(k, eje), []).append(k)
    out = []
    for q, ks in sorted(por.items()):
        ks = sorted(ks, key=lambda k: math.atan2(k[0] - eje[0], k[1] - eje[1]))
        if maxn and len(ks) > maxn:
            ks = [ks[int(i * len(ks) / maxn)] for i in range(maxn)]
        out += ks
    return out


def cmd_exposicion(args):
    t_ini = time.time()
    eje = par_int(args.led)
    idx = indexar(args.carpeta, args.color)
    if not args.dark:
        print('  [CORREGIR] falta --dark: sin oscuro por exposición la señal DF (pocas cuentas) no es medible. Tomar oscuros '
              'con las exposiciones a usar (p. ej. 5, 128, 257 ms).'); return 2
    osc = Oscuro(args.dark)
    print(f'== precaptura exposicion: {args.carpeta}\n   eje {eje}; oscuros: '
          + ', '.join(f'{tstr(t)} ms ({osc.media(t):.1f} cuentas, var/frame {osc.var[t] if osc.var[t] is None else round(osc.var[t], 1)})'
                      for t in osc.tiempos()))
    keys = elegir_muestra([k for k in idx if any(idx[k].values())], eje, args.max_por_anillo)
    # BF: LEDs dentro del círculo de campo claro siempre se miden todos
    keys = sorted(set(keys) | {k for k in idx if math.hypot(k[0] - eje[0], k[1] - eje[1]) < RADIO_PX / PASO_PX and any(idx[k].values())})
    filas = {}
    for k in keys:
        filas[k] = stats_led(idx[k], osc, todas=True)
    # noise model
    pts = [(r['media'], r['var1']) for v in filas.values() for r in v]
    g, v0, medido = ajustar_ruido(pts, osc.var0())
    print(f'  modelo de ruido por frame: var = {g:.3f}*S + {v0:.1f} cuentas^2 ' + ('(ajustado con diferencias de frames de estos datos)'
                                                                                    if medido else '(valores por defecto 21/10)'))
    # una fila por LED: la exposición más larga sin saturar
    sel = {}
    for k, v in filas.items():
        ok = [r for r in v if r['sat'] < 1e-4]
        sel[k] = max(ok, key=lambda r: r['t']) if ok else min(v, key=lambda r: r['t'])
    cmax = max(r['cms_med'] for r in sel.values())
    for k, r in sel.items():
        r['ring'] = anillo(k, eje); r['dist'] = math.hypot(k[0] - eje[0], k[1] - eje[1])
        r['clase'] = 'BF' if r['cms_med'] > 0.25 * cmax else ('mixto' if r['cms_p999'] > 0.25 * cmax else 'DF')
        S = r['med']; r['snr1'] = S / math.sqrt(max(g * S, 0) + v0)
        r['snr1_emp'] = S / math.sqrt(r['var1_med']) if r['var1_med'] else None
    print('\n  LED       anillo clase  t[ms] fr  med[c/ms]  p99.9[c/ms]  sat[%]   SNR/frame(modelo|medido)')
    for k in sorted(sel, key=lambda k: (sel[k]['dist'], k)):
        r = sel[k]
        print(f'  {str(k):9s} {r["ring"]:4d}   {r["clase"]:5s} {tstr(r["t"]):>5s} {r["nfr"]:2d} {r["cms_med"]:10.3f} {r["cms_p999"]:11.3f}'
              f'  {100 * r["sat"]:6.3f}   {r["snr1"]:6.2f} | ' + (f'{r["snr1_emp"]:.2f}' if r['snr1_emp'] else '-'))
    print()
    # BF
    bf = [k for k in sel if sel[k]['clase'] == 'BF']
    dm = osc.media(T_MAX)
    rec = {}
    if bf:
        kb = max(bf, key=lambda k: sel[k]['cms_p999'])
        tb = (BF_OBJ - osc.media(sel[kb]['t'])) / sel[kb]['cms_p999'] - T0_MS
        tb_ent = max(1, int(math.floor(tb)))
        S = np.median([sel[k]['cms_med'] for k in bf]) * (tb_ent + T0_MS); snr = S / math.sqrt(g * S + v0)
        t_us = sorted({sel[k]['t'] for k in bf})
        ok = all(abs(t - tb_ent) / tb_ent < 0.25 for t in t_us) and all(sel[k]['sat'] < 1e-4 for k in bf)
        veredicto(ok, f'BF ({len(bf)} LEDs, limita {kb}): exposición recomendada {tb_ent} ms (p99.9 crudo -> ~{BF_OBJ:.0f}); '
                      f'probado a {", ".join(tstr(t) for t in t_us)} ms; SNR/frame mediana a {tb_ent} ms = {snr:.0f}')
        rec['BF'] = dict(t=tb_ent, N=1, snr1=snr)
    else:
        veredicto(False, 'no hay LEDs de campo claro entre las fotos de prueba: incluir el LED del eje y la cruz.')
    # DF por anillo
    por = {}
    for k in sel:
        if sel[k]['clase'] != 'BF':
            por.setdefault(sel[k]['ring'], []).append(k)
    print('\n  anillo  nLED  t_rec[ms]  limita    med[c/ms]  SNR/frame@t_rec  N(SNR>=3)  SNR/frame medido@t_prueba')
    for q, ks in sorted(por.items()):
        kl = max(ks, key=lambda k: sel[k]['cms_p999'])
        rp = max(sel[kl]['cms_p999'], 1e-3)
        tr = min(T_MAX, (DF_MAX - dm) / rp - T0_MS)
        tr = max(1, int(math.floor(tr))) if tr < T_MAX else int(T_MAX)
        cm = float(np.median([sel[k]['cms_med'] for k in ks]))
        S = cm * (tr + T0_MS); snr = S / math.sqrt(max(g * S, 0) + v0)
        N = int(math.ceil((SNR_OBJ / max(snr, 1e-3)) ** 2))
        emp = [sel[k]['snr1_emp'] for k in ks if sel[k]['snr1_emp'] is not None]
        tpr = sorted({tstr(sel[k]['t']) for k in ks})
        rec[q] = dict(t=tr, N=N, snr1=snr, limita=kl)
        print(f'  {q:5d}  {len(ks):4d}  {tr:9d}  {str(kl):9s} {cm:9.3f}  {snr:15.2f}  {N:9d}   '
              + (f'{np.median(emp):.2f} @ {"/".join(tpr)} ms' if emp else '-'))
    print()
    for q, r in sorted((q, r) for q, r in rec.items() if q != 'BF'):
        if r['N'] <= 1:
            veredicto(True, f'anillo {q}: {r["t"]} ms, 1 frame alcanza (SNR/frame {r["snr1"]:.1f}).')
        else:
            veredicto(False, f'anillo {q}: {r["t"]} ms con SNR/frame {r["snr1"]:.2f} < 3 -> promediar N = {r["N"]} frames '
                             + ('(muy caro: considerar agrupar LEDs / aceptar menos SNR en este anillo)' if r['N'] > 30 else ''))
    # CSV 15x15
    csv = os.path.splitext(ruta_png(args, 'exposicion', args.carpeta))[0] + '.csv'
    grilla = {}
    with open(csv, 'w') as f:
        f.write('Fila,Columna,Tiempo_ms,N_frames,anillo\n')
        for rr in range(eje[0] - 7, eje[0] + 8):
            for cc in range(eje[1] - 7, eje[1] + 8):
                q = anillo((rr, cc), eje)
                if math.hypot(rr - eje[0], cc - eje[1]) < RADIO_PX / PASO_PX and 'BF' in rec:
                    r = rec['BF']
                else:
                    r = rec.get(q) or rec.get(min((x for x in rec if x != 'BF'), key=lambda x: abs(x - q), default='BF'))
                if r:
                    f.write(f'{rr},{cc},{r["t"]},{r["N"]},{q}\n')
                    grilla[(rr, cc)] = r
    # la misma tabla como grilla 15x15 en la terminal: tiempo [ms] / frames por LED
    print('\n  plan para la próxima toma, por LED: tiempo [ms] / frames a promediar')
    cs = range(eje[1] - 7, eje[1] + 8)
    print('  fila\\col ' + ' '.join(f'{cc:>6}' for cc in cs))
    for rr in range(eje[0] - 7, eje[0] + 8):
        print(f'  {rr:>8} ' + ' '.join(f'{grilla[(rr, cc)]["t"]:>4}/{grilla[(rr, cc)]["N"]}' if (rr, cc) in grilla
                                       else '     -' for cc in cs))
    print()
    # figura
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    col = {'BF': 'C0', 'mixto': 'C2', 'DF': 'C3'}
    for k, r in sel.items():
        ax[0].semilogy(r['dist'], max(r['cms_med'], 1e-3), 'o', color=col[r['clase']], ms=5)
        ax[0].semilogy(r['dist'], max(r['cms_p999'], 1e-3), '^', color=col[r['clase']], ms=4, alpha=.5)
        ax[1].semilogy(r['dist'], max(r['snr1'], 1e-3), 'o', color=col[r['clase']], ms=5)
    for c, nm in col.items():
        ax[0].plot([], [], 'o', color=nm, label=c)
    ax[0].plot([], [], 'k^', alpha=.5, label='p99.9'); ax[0].legend(fontsize=8)
    ax[0].set_xlabel('distancia al eje [pasos de LED]'); ax[0].set_ylabel('cuentas/ms sobre oscuro (o = mediana)')
    ax[0].set_title('señal por LED de prueba')
    ax[1].axhline(1, color='k', lw=.5); ax[1].axhline(SNR_OBJ, color='g', lw=.8, ls='--', label='objetivo 3')
    ax[1].set_xlabel('distancia al eje [pasos]'); ax[1].set_ylabel('SNR por frame (mediana, a la t probada)'); ax[1].legend(fontsize=8)
    ax[1].set_title(f'ruido: var = {g:.3f} S + {v0:.1f}')
    qs = [q for q in rec if q != 'BF']
    if qs:
        ax[2].bar(np.array(qs) - 0.2, [rec[q]['t'] for q in qs], 0.4, color='C1', label='t DF [ms]')
        a2 = ax[2].twinx(); a2.bar(np.array(qs) + 0.2, [rec[q]['N'] for q in qs], 0.4, color='C4', label='N frames')
        a2.set_ylabel('N frames para SNR>=3', color='C4')
    ax[2].set_xlabel('anillo'); ax[2].set_ylabel('t recomendado [ms]', color='C1')
    ax[2].set_title(f'recomendado: BF {rec["BF"]["t"] if "BF" in rec else "-"} ms; DF por anillo (tope {T_MAX:g} ms)')
    fig.suptitle(f'precaptura exposicion  {args.carpeta}', fontsize=10)
    fig.tight_layout(); png = ruta_png(args, 'exposicion', args.carpeta); fig.savefig(png, dpi=90); plt.close(fig)
    print(f'  figura: {png}\n  tabla 15x15: {csv}   ({time.time() - t_ini:.1f} s)')
    return 0


# ------------------------------------------------------------------------------------------------------------- qc
def cmd_qc(args):
    t_ini = time.time()
    eje = par_int(args.led)
    idx = indexar(args.carpeta, args.color)
    grilla = {(r, c) for r in range(eje[0] - 7, eje[0] + 8) for c in range(eje[1] - 7, eje[1] + 8)}
    print(f'== precaptura qc: {args.carpeta}\n   grilla esperada 15x15: filas {eje[0] - 7}-{eje[0] + 7}, columnas {eje[1] - 7}-{eje[1] + 7}')
    falt = sorted(grilla - {k for k in idx if any(idx[k].values())}); extra = sorted(set(idx) - grilla)
    veredicto(not falt, f'{len(grilla) - len(falt)}/225 LEDs con imágenes' + (f'; FALTAN {falt[:12]}{"..." if len(falt) > 12 else ""}: recapturarlos' if falt else ''))
    if extra:
        print(f'             ({len(extra)} LEDs fuera de la grilla: {extra[:6]}{"..." if len(extra) > 6 else ""})')
    nfr = {}; tus = {}; multi = []
    for k, ts in idx.items():
        tt = [t for t, fs in ts.items() if fs]
        if len(tt) > 1:
            multi.append((k, sorted(tt)))
        for t in tt:
            nfr.setdefault(len(ts[t]), []).append((k, t)); tus.setdefault(t, []).append(k)
        for t, fs in ts.items():
            if not fs:
                nfr.setdefault(0, []).append((k, t))
    moda = max(nfr, key=lambda n: len(nfr[n]))
    raros = sorted(x for n, v in nfr.items() if n != moda for x in v)
    veredicto(not raros, f'frames por LED y exposición: {moda} en {len(nfr[moda])} carpetas'
              + (f'; distinto en {[(k, tstr(t), n) for n, v in nfr.items() if n != moda for k, t in v][:8]}: revisar/recapturar' if raros else ''))
    print('  exposiciones usadas: ' + ', '.join(f'{tstr(t)} ms x {len(v)} LEDs' for t, v in sorted(tus.items())))
    if multi:
        print(f'  LEDs con más de una exposición ({len(multi)}): ' + ', '.join(f'{k}:{"/".join(tstr(t) for t in ts)}' for k, ts in multi[:10]))
    osc = Oscuro(args.dark) if args.dark else None
    if osc:
        sin = [t for t in tus if t not in osc.img]
        veredicto(not sin, 'oscuros: ' + ', '.join(f'{tstr(t)} ms ({osc.nfr[t]} fr)' for t in osc.tiempos())
                  + (f'; FALTAN oscuros a {", ".join(tstr(t) for t in sorted(sin))} ms: tomarlos (o se interpola en t)' if sin else ' -> cubren todas las exposiciones'))
    else:
        veredicto(False, 'sin --dark: no se verifica que haya oscuro por exposición (se usa nivel fijo 188 para la señal).')
        osc = Oscuro(None)
    fl = None
    if args.flat:
        fl = indexar(args.flat, args.color)
        ff = sorted(grilla - {k for k in fl if any(fl[k].values())})
        dif = sorted(k for k in grilla & set(fl) & set(idx) if {t for t, f in fl[k].items() if f} != {t for t, f in idx[k].items() if f})
        veredicto(not ff and not dif, f'flat: {225 - len(ff)}/225 LEDs' + (f'; faltan {ff[:8]}' if ff else '')
                  + (f'; exposición distinta a la muestra en {len(dif)} LEDs (p. ej. {dif[:5]}): normalizar por t' if dif else ''))
    # señal, saturación, SNR
    g, v0 = DEFAULT_GAIN, DEFAULT_VAR0
    per = {}
    for k in sorted(grilla & set(idx)):
        st = stats_led(idx[k], osc)
        if not st:
            continue
        r = st[0]; r['ring'] = anillo(k, eje)
        r['snr1'] = r['med'] / math.sqrt(r['var1_med']) if r['var1_med'] else r['med'] / math.sqrt(g * max(r['med'], 0) + v0)
        per[k] = r
    satk = sorted(k for k, r in per.items() if r['sat'] > 0)
    veredicto(not satk, f'saturación: ' + ('ningún LED con píxeles en 4095' if not satk else
              f'{len(satk)} LEDs con píxeles saturados (peor {max(satk, key=lambda k: per[k]["sat"])}: '
              f'{100 * max(per[k]["sat"] for k in satk):.3f} %): bajar su exposición'))
    if fl is not None:
        fsat = []
        for k in sorted(grilla & set(fl)):
            ts = {t: f for t, f in fl[k].items() if f}
            if ts:
                t = min(ts)
                for f in ts[t]:
                    if np.asarray(Image.open(f)).max() >= RANGO:
                        fsat.append(k); break
        veredicto(not fsat, 'flat: ' + ('sin saturación' if not fsat else f'{len(fsat)} LEDs saturados {fsat[:6]}'))
    print('\n  anillo  nLED  t[ms]          med[c/ms]   med[cuentas]  p99.9 crudo max  SNR/frame med  frames  N p/SNR>=3')
    rings = {}
    for k, r in per.items():
        rings.setdefault(r['ring'], []).append(r)
    malos = []
    for q, v in sorted(rings.items()):
        snr = float(np.median([x['snr1'] for x in v])); nf = int(np.median([x['nfr'] for x in v]))
        Nn = int(math.ceil((SNR_OBJ / max(snr, 1e-3)) ** 2))
        if snr * math.sqrt(nf) < SNR_OBJ:
            malos.append((q, snr * math.sqrt(nf), Nn))
        print(f'  {q:5d}  {len(v):4d}  {"/".join(tstr(t) for t in sorted({x["t"] for x in v})):13s} {np.median([x["cms_med"] for x in v]):10.3f}'
              f'  {np.median([x["med"] for x in v]):12.1f}  {max(x["p999"] for x in v):15.0f}  {snr:13.2f}  {nf:6d}  {Nn:9d}')
    veredicto(not malos, 'SNR por anillo (promedio de los frames tomados): ' + ('>= 3 en todos' if not malos else
              '; '.join(f'anillo {q}: {s:.2f} (harían falta ~{n} frames)' for q, s, n in malos)))
    # figura
    fig, ax = plt.subplots(1, 4, figsize=(20, 4.8))
    mats = [np.full((15, 15), np.nan) for _ in range(4)]
    for k, r in per.items():
        i, j = k[0] - eje[0] + 7, k[1] - eje[1] + 7
        mats[0][i, j] = r['t']; mats[1][i, j] = np.log10(max(r['cms_med'], 1e-3))
        mats[2][i, j] = r['snr1'] * math.sqrt(r['nfr']); mats[3][i, j] = 100 * r['sat']
    ext = (eje[1] - 7.5, eje[1] + 7.5, eje[0] + 7.5, eje[0] - 7.5)
    tit = ['exposición [ms]', 'log10 cuentas/ms sobre oscuro (mediana)', 'SNR mediana (frames promediados)', '% píxeles saturados']
    cms = ['viridis', 'magma', 'RdYlGn', 'Reds']
    for a, Mx, tt, cm in zip(ax, mats, tit, cms):
        kw = dict(vmin=0, vmax=6) if cm == 'RdYlGn' else (dict(vmin=0, vmax=max(1e-3, np.nanmax(Mx))) if cm == 'Reds' else {})
        im = a.imshow(Mx, extent=ext, cmap=cm, **kw); plt.colorbar(im, ax=a, fraction=.046)
        a.set_title(tt, fontsize=10); a.set_xlabel('columna'); a.set_ylabel('fila'); a.plot(eje[1], eje[0], 'c+', ms=12)
        for k in falt:
            a.plot(k[1], k[0], 'kx', ms=8)
    fig.suptitle(f'precaptura qc  {args.carpeta}   (x = falta)', fontsize=10)
    fig.tight_layout(); png = ruta_png(args, 'qc', args.carpeta); fig.savefig(png, dpi=80); plt.close(fig)
    print(f'  figura: {png}   ({time.time() - t_ini:.1f} s)')
    return 0 if not falt and not raros and not satk else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description='Chequeos rápidos antes/después de una captura FPM 15x15 (ver docstring).')
    sp = ap.add_subparsers(dest='cmd', required=True)
    for nombre, f in (('centro', cmd_centro), ('exposicion', cmd_exposicion), ('qc', cmd_qc)):
        p = sp.add_parser(nombre); p.set_defaults(func=f)
        p.add_argument('carpeta')
        p.add_argument('--led', default='17,15', help='LED del eje objetivo "fila,col" (def. 17,15)')
        p.add_argument('--color', choices=('r', 'g', 'b'), default=None)
        p.add_argument('--dark', default=None, help='carpeta de oscuros (misma estructura, una carpeta por exposición)')
        p.add_argument('--png', default=None, help='ruta de la figura (def. ./precaptura_<sub>_<carpeta>.png)')
        if nombre == 'centro':
            p.add_argument('--offset', default=f'{OFFSET_REF[0]},{OFFSET_REF[1]}', help='OffsetX,OffsetY actuales del ROI')
            p.add_argument('--paso-px', type=float, default=PASO_PX, help='px de ROI por paso de LED (def. 3538, z 102 mm)')
            p.add_argument('--radio-px', type=float, default=RADIO_PX, help='radio BF inicial en px (def. 4132)')
            p.add_argument('--ajustar-paso', action='store_true', help='ajustar también px/paso (necesita diagonales)')
        if nombre == 'exposicion':
            p.add_argument('--max-por-anillo', type=int, default=8, help='LEDs por anillo a leer (0 = todos)')
        if nombre == 'qc':
            p.add_argument('--flat', default=None)
    a = ap.parse_args(argv)
    a.carpeta = os.path.expanduser(a.carpeta)
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main())

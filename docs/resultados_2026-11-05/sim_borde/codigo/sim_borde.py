"""sim_borde.py -- ¿un borde de pupila BLANDO explica que el método espectral (log|FFT|) y el método de borde (espacio imagen,
no telecéntrico) den NA·z distintos en la captura roja 03/11 (6.97 vs 7.40-7.47 mm)?

Simula, con verdad conocida, las imágenes que usa cada método y les aplica el código REAL sin cambios:
  * espectral: funciones score/grid y el preprocesado de docs/resultados_2026-11-04/plan_2026-11-04/auditoria/paso_espectral_0311.py
    (copiadas textualmente abajo; solo cambia la fuente de imágenes), recorte 400x400 filas 360:760, cols 80:480 del ROI.
  * borde: centrado.ajustar (estimación (a), importada del repo) y la estimación (b) (simetría de pares + R,w con eje fijo),
    replicada línea a línea de centrado.analizar.

Modelo directo (objeto delgado, coherente, intensidad):
  E(p) = IFFT[ P(f + k) · FFT(o) ](p),  k = sinθ/λ de la iluminación LOCAL relativa a la pupila.
  Se corre la PUPILA (evaluada analíticamente en f + k) en lugar de inclinar el objeto: la componente DC del objeto pasa con
  amplitud exacta P(k), sin fuga espectral por k no entero.
  No telecéntrico: u(p) = (d - eje)·pitch - p·0.001696 mm (p = px de ROI desde el centro), sinθ = u/sqrt(|u|^2 + z^2).
  El campo se tesela en bloques de 80 px de cámara (margen 40 px) con su k local; en los bloques donde el borde BF/DF de un
  LED cae cerca (|‖u‖ - R| < banda), se subdivide en sub-bloques de 16 px para que el borde en espacio imagen no quede
  escalonado (paso de k entre sub-bloques: 0.027 mm en el plano de LEDs = 16 px de borde).
  Grilla fina x3 (0.43 µm), intensidad bineada 3x3 a píxeles de cámara de 1.29 µm.

Uso: python3 sim_borde.py [n_procesos]   (escribe ../resultados/*.json)
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import math
import time
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates, zoom
from scipy.special import erfc

REPO = '/home/chanoscopio/Documents/LucasC/reproducible-research-template'
sys.path.insert(0, os.path.join(REPO, 'scripts'))
sys.path.insert(0, os.path.join(REPO, 'docs/resultados_2026-11-04/plan_2026-11-04/centrado'))
import precaptura as P  # noqa: E402  (solo lectura)
import centrado as CE  # noqa: E402  (solo lectura; ajustar = estimación (a))

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(AQUI), 'resultados')

# ------------------------------------------------------------------ geometría (real 03/11)
PX = 1.29            # µm por px de cámara en la muestra
UP = 3               # sobremuestreo de la grilla fina
FPX = PX / UP
NROI = 1120
MARG = 40            # px de cámara de margen alrededor de cada bloque (PSF coherente ~0.7 % a 52 µm)
TC, TS = 80, 16      # núcleo de bloque grueso / sub-bloque (px de cámara)
PITCH = 6.0          # mm
CMM = 0.001696       # mm del plano de LEDs por px de ROI (no telecéntrico)
S_PX = PITCH / CMM   # 3538 px por paso
EJE = (0.073, -0.028)  # desvío del eje (pasos) = estimación (a) 03/11
LAM = 0.617
VEC = CE.VEC         # 8 vecinos del anillo 1 (mismo orden que centrado)
BF5 = [(0, 0), (-1, 0), (0, -1), (0, 1), (1, 0)]
G_ADU, VAR0 = 0.297, 7.1   # ruido: var = g·S + var0 (cuentas)
SAT_NETO = 4095 - 188      # tope Mono12 menos el oscuro medio
PICO = 3000.0              # p99.9 objetivo del BF central (cuentas netas)


def pupila(r_na, NA, w):
    """r_na = |f|·λ (unidades de NA). w = 0: borde duro; si no, 0.5·erfc((r - NA)/w) (= _pupila_blanda)."""
    if w <= 0:
        return (r_na < NA).astype(np.float32)
    return (0.5 * erfc((r_na - NA) / w)).astype(np.float32)


def k_local(d, p_row, p_col, z):
    """k (ciclos/µm) de la iluminación del vecino d en el punto de campo p (px de ROI desde el centro)."""
    uy = (d[0] - EJE[0]) * PITCH - p_row * CMM
    ux = (d[1] - EJE[1]) * PITCH - p_col * CMM
    n = math.sqrt(uy * uy + ux * ux + z * z)
    return uy / n / LAM, ux / n / LAM, math.hypot(uy, ux)


# ------------------------------------------------------------------ objeto
def objeto(seed, nlado_cam):
    """Fase delgada: esferas polidispersas (d 3-7 µm, mediana 4.5) Δn 0.046 + fondo suave. Devuelve exp(iφ) en grilla fina
    de (nlado_cam + 2·MARG)·UP px de lado (índice fino 0 = px de cámara -MARG)."""
    rng = np.random.default_rng(1000 + seed)
    nc = nlado_cam + 2 * MARG
    nf = nc * UP
    phi = np.zeros((nf, nf), np.float32)
    nesf = int(round(60 * (nc / 400) ** 2))
    dn = 0.046
    for _ in range(nesf):
        dia = float(np.clip(4.5 * np.exp(0.2 * rng.standard_normal()), 3.0, 7.0))
        r = dia / 2
        cy, cx = rng.uniform(0, nf * FPX, 2)
        i0, i1 = int((cy - r) / FPX) - 1, int((cy + r) / FPX) + 2
        j0, j1 = int((cx - r) / FPX) - 1, int((cx + r) / FPX) + 2
        i0, j0 = max(i0, 0), max(j0, 0); i1, j1 = min(i1, nf), min(j1, nf)
        if i1 <= i0 or j1 <= j0:
            continue
        yy = (np.arange(i0, i1) + 0.5) * FPX - cy; xx = (np.arange(j0, j1) + 0.5) * FPX - cx
        rho2 = yy[:, None] ** 2 + xx[None, :] ** 2
        t = 2 * np.sqrt(np.clip(r * r - rho2, 0, None))
        phi[i0:i1, j0:j1] += (2 * np.pi * dn * t / LAM).astype(np.float32)
    # fondo suave débil: ~0.1 rad rms, correlación ~30 µm
    b = gaussian_filter(rng.standard_normal((nc, nc)), 30 / PX)
    b *= 0.1 / (b.std() + 1e-12)
    phi += zoom(b, UP, order=1).astype(np.float32)[:nf, :nf]
    return np.exp(1j * phi).astype(np.complex64), nesf


# ------------------------------------------------------------------ render
_FG = {}


def frecs(n):
    if n not in _FG:
        f = np.fft.fftfreq(n, d=FPX).astype(np.float32)
        _FG[n] = (f[:, None], f[None, :])
    return _FG[n]


def render_bloque(Ospec, n, k, NA, w):
    fy, fx = frecs(n)
    r = np.hypot(fy + np.float32(k[0]), fx + np.float32(k[1])) * np.float32(LAM)
    E = np.fft.ifft2(Ospec * pupila(r, NA, w))
    return (E.real ** 2 + E.imag ** 2).astype(np.float32)


def binear_cam(I):
    n = I.shape[0] // UP
    return I.reshape(n, UP, -1, UP).mean((1, 3))


def campo_completo(obj, leds, NA, w, z, refinar=True):
    """Imágenes (px de cámara, NROI x NROI) de cada LED con k local por bloque (no telecéntrico)."""
    out = {d: np.zeros((NROI, NROI), np.float32) for d in leds}
    Rmm = z * NA / math.sqrt(1 - NA * NA)
    banda = 3 * w * z + 0.12 + TC * CMM * 0.75   # mm
    nsub = 0
    for r0 in range(0, NROI, TC):
        for c0 in range(0, NROI, TC):
            tile = obj[r0 * UP:(r0 + TC + 2 * MARG) * UP, c0 * UP:(c0 + TC + 2 * MARG) * UP]
            n = tile.shape[0]
            Os = np.fft.fft2(tile)
            sub_cache = {}
            pr, pc = r0 + TC / 2 - NROI / 2, c0 + TC / 2 - NROI / 2
            for d in leds:
                ky, kx, umm = k_local(d, pr, pc, z)
                if refinar and abs(umm - Rmm) < banda:
                    for a0 in range(0, TC, TS):
                        for b0 in range(0, TC, TS):
                            key = (a0, b0)
                            if key not in sub_cache:
                                st = obj[(r0 + a0) * UP:(r0 + a0 + TS + 2 * MARG) * UP,
                                         (c0 + b0) * UP:(c0 + b0 + TS + 2 * MARG) * UP]
                                sub_cache[key] = np.fft.fft2(st)
                            kk = k_local(d, r0 + a0 + TS / 2 - NROI / 2, c0 + b0 + TS / 2 - NROI / 2, z)
                            I = render_bloque(sub_cache[key], (TS + 2 * MARG) * UP, kk, NA, w)
                            core = I[MARG * UP:(MARG + TS) * UP, MARG * UP:(MARG + TS) * UP]
                            out[d][r0 + a0:r0 + a0 + TS, c0 + b0:c0 + b0 + TS] = binear_cam(core)
                            nsub += 1
                else:
                    I = render_bloque(Os, n, (ky, kx), NA, w)
                    core = I[MARG * UP:(MARG + TC) * UP, MARG * UP:(MARG + TC) * UP]
                    out[d][r0:r0 + TC, c0:c0 + TC] = binear_cam(core)
    return out, nsub


# recorte del método espectral (mismo que paso_espectral_0311: filas 360:760, cols 80:480)
CR0, CC0, NCR = 360, 80, 400


def recorte_onda_plana(obj, leds, NA, w, z):
    """Recorte 400x400 con UNA onda plana por LED (k del centro del recorte), sin variación de campo."""
    tile = obj[CR0 * UP:(CR0 + NCR + 2 * MARG) * UP, CC0 * UP:(CC0 + NCR + 2 * MARG) * UP]
    n = tile.shape[0]
    Os = np.fft.fft2(tile)
    pr, pc = CR0 + NCR / 2 - NROI / 2, CC0 + NCR / 2 - NROI / 2
    out = {}
    for d in leds:
        ky, kx, _ = k_local(d, pr, pc, z)
        I = render_bloque(Os, n, (ky, kx), NA, w)
        out[d] = binear_cam(I[MARG * UP:(MARG + NCR) * UP, MARG * UP:(MARG + NCR) * UP])
    return out


def ruido(I_cuentas, rng):
    s = np.clip(I_cuentas, 0, None)
    x = s + rng.standard_normal(s.shape) * np.sqrt(G_ADU * s + VAR0)
    return np.minimum(np.round(x), SAT_NETO)


# ------------------------------------------------------------------ método espectral (copia TEXTUAL de paso_espectral_0311.py)
N = NCR
lam = 0.63
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


def espectral(imgs, rango=(0.90, 1.15)):
    """imgs: dict d(relativo a (17,15)) -> recorte 400x400 (cuentas netas; flat = 1). rango: búsqueda del radio relativa a
    rb0 (el script real usa 0.90-1.15; 'ancho' = 0.85-1.35 se corre aparte para ver si el original toca el borde)."""
    rb0 = 0.0669 / lam / df; rows = []
    for dd in BF5:
        k = (17 + dd[0], 15 + dd[1])
        I = imgs[dd].astype(float)
        I = (I - I.mean()) * win
        L = gaussian_filter(np.log(np.abs(np.fft.fftshift(np.fft.fft2(I))) + 1e-6), 2.0)
        n0 = (k[0] - 17) * PITCH / 102 / lam / df; n1 = ((k[1] - 15) * PITCH + 0.529) / 102 / lam / df
        c0, c1, rb = grid(L, n0, n1, [rb0], half=round(0.45 * rb0), step=1.0)
        c0, c1, rb = grid(L, c0, c1, rb0 * np.linspace(rango[0], rango[1], 26), half=3, step=0.5)
        c0, c1, rb = grid(L, c0, c1, rb + np.arange(-0.6, 0.61, 0.15), half=0.75, step=0.125)
        if (c0 - n0) ** 2 + (c1 - n1) ** 2 > (c0 + n0) ** 2 + (c1 + n1) ** 2: c0, c1 = -c0, -c1
        rows.append(dict(led=list(k), c0=float(c0), c1=float(c1), rb=float(rb)))
    g = {tuple(r["led"]): r for r in rows}
    s_col = (g[(17, 16)]["c1"] - g[(17, 14)]["c1"]) / 2; s_row = (g[(18, 15)]["c0"] - g[(16, 15)]["c0"]) / 2
    rb = np.mean([r["rb"] for r in rows]); rbs = np.std([r["rb"] for r in rows], ddof=1)
    rbmax = rb0 * rango[1] + 0.6
    return dict(rb_bins=float(rb), rb_sd=float(rbs), s_row=float(s_row), s_col=float(s_col),
                NAz_fila=float(rb / s_row * PITCH), NAz_col=float(rb / s_col * PITCH),
                NAz_media=float(rb / (0.5 * (s_row + s_col)) * PITCH),
                NA_radio=float(rb * LAM / (N * PX)), toca_borde=bool(max(r["rb"] for r in rows) > rbmax - 0.8),
                leds=rows)


# ------------------------------------------------------------------ método de borde (centrado.py)
B = 16


def borde(imgs):
    """imgs: dict d -> imagen completa 1120x1120 (cuentas netas por unidad de exposición; misma exposición para todos).
    Replica centrado.analizar: (a) = CE.ajustar con eje, R, w libres; (b) eje por simetría de pares + R, w con eje fijo."""
    S = CE.S
    C = imgs[(0, 0)].astype(float)
    Cb = P.binear(C, B); H, W = C.shape
    yy, xx = np.mgrid[:Cb.shape[0], :Cb.shape[1]]
    Y = ((yy + 0.5) * B - H / 2).ravel(); X = ((xx + 0.5) * B - W / 2).ravel()
    mC = Cb > 0.2 * np.median(Cb); mCf = C > 0.2 * np.median(C)
    Q, M, Qfull = {}, {}, {}
    for d in VEC:
        Nf = imgs[d].astype(float)
        Q[d] = np.where(mC, P.binear(Nf, B) / np.maximum(Cb, 1e-6), 0.0); M[d] = mC.copy()
        Qfull[d] = np.where(mCf, Nf / np.maximum(C, 1e-6), np.nan)
    pa, Aa = CE.ajustar([Q[d] for d in VEC], [M[d] for d in VEC], VEC, Y, X)
    Yf, Xf = P.coords(C.shape)

    def sim(dp, e):
        dm = (-dp[0], -dp[1])
        return [P.espejo(Qfull[dp], Qfull[dm], e, Yf, Xf, banda) for banda in ((-450, 450), (-450, 0), (0, 450))]
    fino = {}
    for comp, d in ((0, (1, 0)), (1, (0, 1))):
        ms = sim(d, d)
        fino[comp] = None if (ms[0] is None or abs(pa[comp]) >= 0.12) else -ms[0] / S
    eje_b = (fino[0] if fino[0] is not None else pa[0], fino[1] if fino[1] is not None else pa[1])
    pb, Ab = CE.ajustar([Q[d] for d in VEC], [M[d] for d in VEC], VEC, Y, X, p0=pa, libres=(2, 3), eje_fijo=eje_b)

    def par(p):
        return dict(eje=[float(p[0]), float(p[1])], R_pasos=float(p[2] * 1000 / S), w_px=float(math.exp(p[3])),
                    NAz=float(p[2] * 1000 / S * PITCH))
    return dict(a=par(pa), a_A=[float(v) for v in Aa], b=par(pb), b_fino=[fino[0], fino[1]])


# ------------------------------------------------------------------ un trabajo = (verdad, w, semilla)
def trabajo(args):
    nombre, NA, z, w, seed = args
    t0 = time.time()
    obj, nesf = objeto(seed, NROI)
    leds = [(0, 0)] + VEC
    full, nsub = campo_completo(obj, leds, NA, w, z)
    pw = recorte_onda_plana(obj, BF5, NA, w, z)
    # escala de cuentas: p99.9 del BF central = PICO (misma exposición para los 9 LEDs, como una captura BF)
    esc = PICO / float(np.percentile(full[(0, 0)], 99.9))
    rng = np.random.default_rng(50000 + seed * 97 + int(w * 1e4) * 7 + int(NA * 1e4))
    full_n = {d: ruido(full[d] * esc, rng) for d in leds}
    pw_n = {d: ruido(pw[d] * esc, rng) for d in BF5}
    crop = lambda im: im[CR0:CR0 + NCR, CC0:CC0 + NCR]  # noqa: E731
    res = dict(nombre=nombre, NA=NA, z=z, w=w, seed=seed, NAz_verdad=NA * z, nesf=nesf, nsub=nsub, escala=esc,
               frac_sat=float(np.mean(full_n[(0, 0)] >= SAT_NETO)))
    for etq, F, PWi in (('sin_ruido', full, pw), ('ruido', full_n, pw_n)):
        r = {}
        r['esp_nt'] = espectral({d: crop(F[d]) for d in BF5})
        r['esp_pw'] = espectral(PWi)
        r['esp_nt_ancho'] = espectral({d: crop(F[d]) for d in BF5}, rango=(0.85, 1.35))
        r['borde'] = borde(F)
        res[etq] = r
    res['seg'] = round(time.time() - t0, 1)
    if seed == 0:
        np.savez_compressed(os.path.join(OUT, f'imgs_{nombre}_s0.npz'),
                            **{f'n_{d[0]}_{d[1]}': full_n[d].astype(np.float32) for d in leds})
    with open(os.path.join(OUT, f'res_{nombre}_s{seed}.json'), 'w') as f:
        json.dump(res, f, indent=1)
    rr = res['ruido']
    print(f"{nombre} s{seed}: {res['seg']} s nsub {nsub} | esp_nt {rr['esp_nt']['NAz_fila']:.3f}/{rr['esp_nt']['NAz_col']:.3f} "
          f"esp_pw {rr['esp_pw']['NAz_fila']:.3f}/{rr['esp_pw']['NAz_col']:.3f} | borde a {rr['borde']['a']['NAz']:.3f} "
          f"w {rr['borde']['a']['w_px']:.0f} b {rr['borde']['b']['NAz']:.3f} | verdad {NA * z:.3f}", flush=True)
    return res


CASOS = []
for (tag, NA, z) in (('A', 0.070, 99.5), ('B', 0.0744, 99.5)):
    for w in (0.0, 0.002, 0.004, 0.008):
        CASOS.append((f'{tag}_w{w:.3f}', NA, z, w))


def main():
    os.makedirs(OUT, exist_ok=True)
    nproc = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    semillas = [int(s) for s in sys.argv[2].split(',')] if len(sys.argv) > 2 else [0, 1, 2]
    sel = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    jobs = [(n, NA, z, w, s) for (n, NA, z, w) in CASOS for s in semillas if (sel is None or n in sel)
            and not os.path.exists(os.path.join(OUT, f'res_{n}_s{s}.json'))]
    print(f'{len(jobs)} trabajos', flush=True)
    if nproc <= 1:
        for j in jobs:
            trabajo(j)
    else:
        from multiprocessing import Pool
        with Pool(nproc) as pool:
            for _ in pool.imap_unordered(trabajo, jobs):
                pass


if __name__ == '__main__':
    main()

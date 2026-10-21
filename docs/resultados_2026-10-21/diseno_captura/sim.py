"""sim.py -- estudio de diseño de captura (2026-10-21). Simulación FPM de ranking, no resultado final.

Geometría base = la medida (docs/resultado_rojo_2026-10.md): λ 0.63 µm, pixel en muestra 1.29 µm, NA 0.067,
pitch 6 mm. Modelo directo = el de fpm_red.predict (results/captura_2026-09-28b/red/fpm_red.py): recorte del
espectro HR con spectral_ops.led_crop_window + pupila circular, intensidad. Solver = copia del lazo A+init de
fpm_red.reconstruct (init 'fourier_avg', paso 0.3 con rampa 1-exp(-0.3 it), sin pesos/s,b/EPRY, máscara de
saturados), con orden por |f| de iluminación (en vez del anillo de la grilla 28/09b) y LEDs de campo claro
definidas por geometría. Objeto delgado (sim_grueso_2026-10-20 mostró BPM ≈ delgado para estas esferas).

Ruido calibrado (results/captura_2026-09-28b/red/prep.npz y prep_stats.json; ver calibra.py):
  ganancia 0.2845 cuentas/e-, lectura σ 4.4 cuentas/cuadro, oscuro 188, saturación 4095 (cuadro crudo),
  brillo de LED (cuentas/ms equivalentes a campo claro pleno) B(θ) = 118·(102/z)²·cos^M θ, luz parásita en DF
  (campo plano sin muestra) = fracción del brillo, interpolada en NA de iluminación desde los datos reales.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
from ptyco_full_simulator.optics import circular_pupil  # noqa: E402
from ptyco_full_simulator.spectral_ops import led_crop_window  # noqa: E402

LAM, LRPX, NA, PITCH = 0.63, 1.29, 0.067, 6.0
FACTOR = 3
GAIN, SIG_R, DARK, SAT = 0.2845, 4.4, 188.0, 4095.0
B0, Z0 = 118.0, 102.0           # cuentas/ms, campo claro sin muestra, LED casi axial a z = 102 (prep_stats F_mean)
NM, DN = 1.48, 0.05
OVERHEAD_S = 0.10                # s por cuadro (cambio de LED + lectura + guardado): SUPUESTO, no medido
# calibra.py / calibra.json (28/09b rojo, z 102, anillos 2..10 -> NA de iluminación):
RING_NA = np.array([0.117, 0.174, 0.229, 0.282, 0.333, 0.381, 0.426, 0.468, 0.507])
# luz parásita sin muestra en DF / B0 (mediana por anillo de F_mean / 118)
STRAY_FR = np.array([6.61e-4, 3.03e-4, 1.53e-4, 9.72e-5, 7.50e-5, 5.99e-5, 4.57e-5, 3.89e-5, 2.08e-5])
# ganancia efectiva DF: media real (S-F)/B0 / media sim (fantoma rho 1e-3, sin caída) por anillo. Absorbe la caída
# de brillo con el ángulo y el exceso de luz DF de la muestra real (~3x más que esferas lisas a NA > 0.2).
G_DF = np.array([1.03, 2.14, 3.53, 3.39, 3.10, 2.73, 3.09, 2.95, 3.93])


# ---------------------------------------------------------------- geometría
def led_set(z, a=0.5, na_max=0.42, square=None):
    """LEDs como offsets enteros (i fila, j col); eje corrido a pasos a lo largo de filas (0 = sobre una LED,
    0.5 = mitad de paso, 0.677 = mitad + dado rojo 1.06 mm). square = n -> cuadrado n×n de LEDs alrededor del eje
    (15 -> filas -6..8 como 28/09b y 20/10); si no, disco NA_ill <= na_max. Devuelve k -> (X, Y) mm al eje."""
    out = {}
    R = 30
    for i in range(-R, R + 1):
        for j in range(-R, R + 1):
            Y, X = (i - a) * PITCH, j * PITCH
            if square is not None:
                h = square // 2
                lo = -h + (1 if (square == 15 and a > 0.25) else 0)
                hi = lo + square - 1
                if not (lo <= i <= hi and -h <= j <= -h + square - 1):
                    continue
            elif np.hypot(X, Y) / np.sqrt(X * X + Y * Y + z * z) > na_max:
                continue
            out[(i, j)] = (X, Y)
    return out


def aberrated_pupil(n_lr, na, astig=0.0, defocus=0.0, vig=0.0):
    """Pupila verdadera fuera de eje: astigmatismo y desenfoque (ondas P-V en el borde: astig·ρ²cos2θ,
    defocus·ρ²) y viñeteo = intersección con un círculo igual corrido vig·R a lo largo de filas."""
    P = circular_pupil((n_lr, n_lr), LRPX, na, LAM).astype(complex)
    f = np.fft.fftshift(np.fft.fftfreq(n_lr, d=LRPX))
    FX, FY = np.meshgrid(f, f)
    R = na / LAM
    rho2 = (FX ** 2 + FY ** 2) / R ** 2
    c2 = np.where(rho2 > 0, (FX ** 2 - FY ** 2) / np.maximum(FX ** 2 + FY ** 2, 1e-30), 0)
    P = P * np.exp(2j * np.pi * (astig * rho2 * c2 + defocus * rho2))
    if vig:
        P = P * ((FX ** 2 + (FY - vig * R) ** 2) <= R ** 2)
    return P


def fxy_of(pos, z, kscale=1.0):
    f = {}
    for k, (X, Y) in pos.items():
        r = np.sqrt(X * X + Y * Y + z * z)
        f[k] = (kscale * X / r / LAM, kscale * Y / r / LAM)
    return f


def na_ill(fxy):
    return {k: float(np.hypot(*v) * LAM) for k, v in fxy.items()}


def brightness(nas, z):
    """B_eff (cuentas/ms por unidad de intensidad normalizada): B0·(102/z)²·G(NA); G = 1 en campo claro."""
    return {k: B0 * (Z0 / z) ** 2 * (1.0 if na < NA else float(np.interp(na, RING_NA, G_DF))) for k, na in nas.items()}


def stray(na, z):
    """luz parásita (cuentas/ms) de una LED DF: fracción calibrada × B0·(102/z)²; 0 en campo claro (ya en el plano)."""
    return 0.0 if na < NA else float(np.interp(na, RING_NA, STRAY_FR)) * B0 * (Z0 / z) ** 2


# ---------------------------------------------------------------- fantoma
def phantom(n_lr, seed=0, rho=1.0e-3, n_small=8):
    """Esferas polidispersas (lognormal, mediana 3.5 µm, σ_ln 0.57, recorte 1–20 µm: distribución real de
    docs/resultado_rojo_2026-10.md) sin solaparse lateralmente, densidad rho /µm², + n_small dispersores de 1.2 µm
    aislados. Devuelve lista (cy, cx, d) en µm y el lado L."""
    rng = np.random.default_rng(seed)
    L = n_lr * LRPX
    n = rng.poisson(rho * L * L)
    d = np.clip(np.exp(np.log(3.5) + 0.57 * rng.standard_normal(n)), 1.0, 20.0)
    d = np.sort(d)[::-1]
    sph = []
    for di in list(d) + [1.2] * n_small:
        gap = 0.5 if di > 1.3 else 8.0       # los chicos, bien aislados
        for _ in range(4000):
            cy, cx = rng.uniform(di / 2 + 4, L - di / 2 - 4, 2)
            if all(np.hypot(cy - a, cx - b) > (di + e) / 2 + gap for a, b, e in sph):
                sph.append((cy, cx, di)); break
    return sph, L


def thickness(sph, L, N):
    px = L / N
    yy, xx = (np.mgrid[:N, :N] + 0.5) * px
    t = np.zeros((N, N))
    for cy, cx, d in sph:
        r = int(np.ceil(d / 2 / px)) + 2
        iy, ix = int(cy / px), int(cx / px)
        sl = (slice(max(iy - r, 0), iy + r), slice(max(ix - r, 0), ix + r))
        r2 = (d / 2) ** 2 - (yy[sl] - cy) ** 2 - (xx[sl] - cx) ** 2
        t[sl] += 2 * np.sqrt(np.clip(r2, 0, None))
    return t


def to_grid(a, n):
    N = a.shape[0]
    S = np.fft.fftshift(np.fft.fft2(a)); o = (N - n) // 2
    return np.fft.ifft2(np.fft.ifftshift(S[o:o + n, o:o + n])) * (n / N) ** 2


def truth_object(sph, L, n_lr, sup=2):
    H = n_lr * FACTOR
    t = thickness(sph, L, H * sup)
    o = to_grid(np.exp(1j * 2 * np.pi * DN * t / LAM), H)
    return o / FACTOR ** 2          # escala de fpm_red.predict: campo claro ≈ 1


def hrpx(n_lr):
    return LRPX / FACTOR


# ---------------------------------------------------------------- modelo directo y solver
def predict(obj, fxy, keys, n_lr, na=NA, pupil=None):
    spec = np.fft.fftshift(np.fft.fft2(obj))
    P = circular_pupil((n_lr, n_lr), LRPX, na, LAM) if pupil is None else pupil
    out = {}
    for k in keys:
        ys, xs = led_crop_window(obj.shape, hrpx(n_lr), (n_lr, n_lr), *fxy[k])
        out[k] = np.abs(np.fft.ifft2(np.fft.ifftshift(spec[ys, xs] * P))) ** 2
    return out


def fourier_upsample(a, f):
    n = a.shape[0]
    A = np.fft.fftshift(np.fft.fft2(a)); H = n * f
    out = np.zeros((H, H), complex); o = (H - n) // 2
    out[o:o + n, o:o + n] = A
    return np.fft.ifft2(np.fft.ifftshift(out)) * f * f


def reconstruct(I, keys, fxy, n_lr, bf, iterations=80, step=0.3, mask=None, snaps=()):
    """Copia del lazo A+init de fpm_red.reconstruct (sin opciones)."""
    P = circular_pupil((n_lr, n_lr), LRPX, NA, LAM).astype(complex)
    bfk = [k for k in bf if k in I]
    amp = np.sqrt(np.clip(np.mean([I[k] for k in bfk], 0), 0, None))
    o0 = np.real(fourier_upsample(amp, FACTOR)).astype(complex) / FACTOR ** 2
    spec = np.fft.fftshift(np.fft.fft2(o0))
    win = {k: led_crop_window(o0.shape, hrpx(n_lr), (n_lr, n_lr), *fxy[k]) for k in keys}
    order = sorted(keys, key=lambda k: (np.hypot(*fxy[k]), k))
    tg = {k: np.sqrt(np.clip(I[k], 0, None)) for k in keys}
    hist, snap = [], {}
    for it in range(iterations):
        mu = step * (1.0 - np.exp(-0.3 * it))
        err = 0.0
        for k in order:
            ys, xs = win[k]
            ps = spec[ys, xs]
            A = np.fft.ifft2(np.fft.ifftshift(ps * P))
            a = np.abs(A)
            t = tg[k] if mask is None else np.where(mask[k], tg[k], a)
            err += float(np.mean((a - t) ** 2))
            D = np.fft.fftshift(np.fft.fft2(t * A / np.maximum(a, 1e-12) - A))
            spec[ys, xs] = ps + mu * P * D
        hist.append(err / len(keys))
        if it + 1 in snaps:
            snap[it + 1] = np.fft.ifft2(np.fft.ifftshift(spec)).astype(np.complex64)
    return np.fft.ifft2(np.fft.ifftshift(spec)), hist, snap


# ---------------------------------------------------------------- métricas (mismas definiciones que fpm_red)
def frc(a, b, px_um, nb=60, kmax=None):
    Fa = np.fft.fftshift(np.fft.fft2(a - a.mean()))
    Fb = np.fft.fftshift(np.fft.fft2(b - b.mean()))
    H = a.shape[0]
    fy, fx = np.mgrid[:H, :H] - H // 2
    kr = np.hypot(fx, fy) / (H * px_um)
    kmax = kmax or kr.max()
    edges = np.linspace(0, kmax, nb + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (kr >= lo) & (kr < hi)
        num = np.abs(np.sum(Fa[m] * np.conj(Fb[m])))
        den = np.sqrt(np.sum(np.abs(Fa[m]) ** 2) * np.sum(np.abs(Fb[m]) ** 2)) + 1e-30
        out.append((0.5 * (lo + hi), num / den, int(m.sum())))
    return np.array(out)


def frc_period(fr, thr=1 / 7):
    """Período (µm) del primer cruce por debajo de thr (interpolado), desde la frecuencia del objetivo hacia afuera."""
    f, v = fr[:, 0], fr[:, 1]
    for i in range(1, len(f)):
        if f[i] > 0.05 and v[i] < thr:
            f0 = f[i - 1] + (f[i] - f[i - 1]) * (v[i - 1] - thr) / max(v[i - 1] - v[i], 1e-12)
            return float(1 / f0)
    return float(1 / f[-1])


def band_mean(fr, lo, hi):
    m = (fr[:, 0] >= lo) & (fr[:, 0] < hi)
    return float(np.mean(fr[m, 1]))


def affine_residual(pred, meas, var, mask=None):
    m = mask if mask is not None else np.ones(meas.shape, bool)
    x, y = pred[m].ravel(), meas[m].ravel()
    X = np.stack([x, np.ones_like(x)], 1)
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    if c[0] < 0:
        c = np.array([0.0, y.mean()])
    r = y - X @ c
    sd = y.std()
    return float(np.sqrt(np.mean(r ** 2)) / sd), float(np.sqrt(var) / sd)


def predict_heights(sph, L, n_lr, fxy, keys, pupil=None, na=NA, zf=3.0, dzbin=1.0):
    """Esferas apoyadas en el fondo (centro a altura d/2), plano de foco a zf µm: aproximación de muestra rala —
    cada grupo de alturas (bins de dzbin) dispersa como objeto delgado en su plano y su campo dispersado se propaga
    (espectro angular en DMSO, n 1.48) hasta el plano de foco; el término no dispersado no se propaga. Por LED:
    espectro = δ + Σ_g S_g(ventana) · exp(2πi Δz_g (kz(p) - kz(f_ill))), p = frecuencia local de la ventana."""
    H = n_lr * FACTOR
    hs = np.array([d / 2 for _, _, d in sph])
    groups = {}
    for s, h in zip(sph, hs):
        groups.setdefault(round(h / dzbin) * dzbin, []).append(s)
    one = np.fft.fftshift(np.fft.fft2(np.ones((H, H)) / FACTOR ** 2))
    Sg = {h: np.fft.fftshift(np.fft.fft2(truth_object(g, L, n_lr))) - one for h, g in groups.items()}
    P = circular_pupil((n_lr, n_lr), LRPX, na, LAM) if pupil is None else pupil
    f = np.fft.fftshift(np.fft.fftfreq(n_lr, d=LRPX))
    FX, FY = np.meshgrid(f, f)
    k0 = NM / LAM
    kz = np.sqrt(np.clip(k0 ** 2 - FX ** 2 - FY ** 2, 0, None))
    out = {}
    for k in keys:
        ys, xs = led_crop_window((H, H), LRPX / FACTOR, (n_lr, n_lr), *fxy[k])
        kz0 = np.sqrt(k0 ** 2 - fxy[k][0] ** 2 - fxy[k][1] ** 2)
        sp = one[ys, xs].copy()
        for h, S_ in Sg.items():
            sp = sp + S_[ys, xs] * np.exp(2j * np.pi * (h - zf) * (kz - kz0))
        out[k] = np.abs(np.fft.ifft2(np.fft.ifftshift(sp * P))) ** 2
    return out


def predict_spherical(obj, pos, z, keys, n_lr, fxy, s=2.5, pupil=None, na=NA):
    """Iluminación de onda esférica exacta desde cada LED (puntual) en vez de onda plana. Se quita, por LED, la parte
    que el modelo de onda plana ya representa (constante + lineal en el centro del campo) y la cuadrática paraxial
    común a todas las LEDs k|x|²/2z (se absorbe en el objeto, como la no-telecentricidad: ver INFORME). Queda el
    residuo no paraxial dependiente de la LED (~ k|x|²(1-cos³θ)/2z). s escala el campo: el error es el de un punto
    a s·x, para emular teselas más grandes que el recorte simulado (s = 2.5 -> tesela de 400 px)."""
    H = obj.shape[0]
    px = LRPX / FACTOR
    c = (np.arange(H) - H / 2 + 0.5) * px * 1e-3 * s       # mm, centrado
    yy, xx = np.meshgrid(c, c, indexing="ij")
    k = 2 * np.pi / (LAM * 1e-3)                            # 1/mm
    out = {}
    P = circular_pupil((n_lr, n_lr), LRPX, na, LAM) if pupil is None else pupil
    for kk in keys:
        X, Y = pos[kk]
        r0 = np.sqrt(X * X + Y * Y + z * z)
        r = np.sqrt((X - xx) ** 2 + (Y - yy) ** 2 + z * z)
        lin = -(X * xx + Y * yy) / r0
        d = k * (r - r0 - lin) - k * (xx ** 2 + yy ** 2) / (2 * z)
        spec = np.fft.fftshift(np.fft.fft2(obj * np.exp(1j * d)))
        ys, xs = led_crop_window(obj.shape, px, (n_lr, n_lr), *fxy[kk])
        out[kk] = np.abs(np.fft.ifft2(np.fft.ifftshift(spec[ys, xs] * P))) ** 2
    return out

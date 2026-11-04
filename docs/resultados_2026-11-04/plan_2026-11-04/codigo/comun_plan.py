"""comun_plan.py -- funciones compartidas del plan 2026-11-03 (FRC, C2, remuestreo, geometría). Solo lee."""
import os, sys
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np
from scipy import ndimage as ndi

R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones"
P = os.path.join(R, "plan_2026-11-03")
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
LAM = {"red": 0.63, "blue": 0.47}
NA0 = 0.069 * 1.25 / 1.29   # 0.0669


def frc(a, b, px, nb=60, kmax=None):
    """= results/captura_2026-10-21/eval/comun.frc (anillos de ancho kmax/nb, kmax = esquina por defecto, sin ventana).
    columnas: k [1/µm], FRC, n_px."""
    Fa = np.fft.fftshift(np.fft.fft2(a - a.mean())); Fb = np.fft.fftshift(np.fft.fft2(b - b.mean()))
    H = a.shape[0]; fy, fx = np.mgrid[:H, :H] - H // 2
    kr = np.hypot(fx, fy) / (H * px); kmax = kmax or kr.max()
    e = np.linspace(0, kmax, nb + 1); out = []
    idx = np.digitize(kr.ravel(), e) - 1
    ok = (idx >= 0) & (idx < nb)
    prod = (Fa * np.conj(Fb)).ravel()
    num = np.abs(np.bincount(idx[ok], prod.real[ok], nb) + 1j * np.bincount(idx[ok], prod.imag[ok], nb))
    pa = np.bincount(idx[ok], (np.abs(Fa) ** 2).ravel()[ok], nb); pb = np.bincount(idx[ok], (np.abs(Fb) ** 2).ravel()[ok], nb)
    n = np.bincount(idx[ok], None, nb)
    return np.stack([0.5 * (e[:-1] + e[1:]), num / (np.sqrt(pa * pb) + 1e-30), n], 1)


def band_mean(fr, lo, hi):
    m = (fr[:, 0] >= lo) & (fr[:, 0] < hi)
    return float(np.mean(fr[m, 1]))


def c2(h0, h1, px, na, lam, hi=0.45):
    """C2 = media del FRC complejo SIN ventana (60 anillos hasta la esquina) en [2NA/λ, 0.45] 1/µm
    (= results/captura_2026-10-21/eval/resolucion.py, = criterios_b.py)."""
    return band_mean(frc(h0, h1, px), 2 * na / lam, hi)


def hann2(n):
    w = np.hanning(n); return np.outer(w, w)


def frc_fino(a, b, px, ancho=0.012, ventana=True):
    """FRC con anillos de ancho fijo ~0.012 1/µm hasta Nyquist del grid (como resolucion.py), con ventana Hann opcional
    (para comparar imágenes NO periódicas entre sí: rojo vs azul, crudo vs crudo)."""
    a = a - a.mean(); b = b - b.mean()
    if ventana:
        W = hann2(a.shape[0]); a = a * W; b = b * W
    kmax = 1 / (2 * px); nb = int(round(kmax / ancho))
    return frc(a, b, px, nb, kmax)


def cruce(fr, thr=1 / 7, k0=0.02, nsm=3):
    """primera k > k0 donde el FRC (media móvil de nsm anillos) cae por debajo de thr (interpolado). None si no cae."""
    k, y = fr[:, 0], np.convolve(fr[:, 1], np.ones(nsm) / nsm, mode="same")
    for i in range(1, len(k)):
        if k[i] > k0 and y[i] < thr and y[i - 1] >= thr:
            return float(k[i - 1] + (thr - y[i - 1]) * (k[i] - k[i - 1]) / (y[i] - y[i - 1]))
        if k[i] > k0 and y[i] < thr and k[i - 1] <= k0:
            return float(k[i])
    return None


def rel_phase(o, sig=20):
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return np.angle(o * np.exp(-1j * np.angle(sm)))


def rel_complex(o, sig=20):
    """objeto complejo sin la fase de baja frecuencia (para comparar colores: la rampa/fondo de fase no es muestra)."""
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return o * np.exp(-1j * np.angle(sm))


def fourier_resample(x, n):
    """remuestreo por recorte/relleno del espectro centrado (conserva el campo físico, cambia el píxel)."""
    N = x.shape[0]
    X = np.fft.fftshift(np.fft.fft2(x))
    Y = np.zeros((n, n), complex)
    m = min(N, n); a0 = (N - m) // 2; b0 = (n - m) // 2
    Y[b0:b0 + m, b0:b0 + m] = X[a0:a0 + m, a0:a0 + m]
    y = np.fft.ifft2(np.fft.ifftshift(Y)) * (n / N) ** 2
    return y if np.iscomplexobj(x) else y.real


def k_sint(color, offset_mm, factor, na=NA0):
    """NA/λ del objetivo y corte sintético NA/λ + max|f_LED| (sobre los 225 LEDs de la grilla) con la geometría del script."""
    sys.path.insert(0, os.path.join(P, "codigo"))
    import reconstruir_plan as RP
    RP.NA_OBJ = na
    F, IR = RP.cargar_solver(color, factor)
    geo = F.geometry(102.0, offset_mm=offset_mm, crop=400)
    keys = [(r, c) for r in range(10, 25) for c in range(8, 23)]
    fm = max(np.hypot(*geo["fxy"][k]) for k in keys)
    return dict(lam=geo["lam"], k_obj=geo["na"] / geo["lam"], k_sint=geo["na"] / geo["lam"] + fm, hrpx=geo["hrpx"],
                k_nyq_hr=1 / (2 * geo["hrpx"]), NA_sint=geo["na"] + geo["lam"] * fm)

"""COPIA 21/10 tarde (captura_2026-10-21_500): DS por defecto r500_red, runner = ../runner_500.py (envuelve runner_2110), VAR rojo_500.
comun.py -- COPIA (21/10, captura_2026-10-21) de octubre_capturas_2026-10-21/eval/comun.py: DS por defecto r21_red, runner =
../runner_2110.py, variante por env VAR (por defecto rojo_centrado; m2_red -> rojo_final), EXCL según el set (r21_red: ninguna).

comun.py (COPIA 21/10 de rojo_resolucion_2026-10-20/comun.py; dataset = env DS, por defecto m2_red; runner = ../runner_oct.py) -- carga de geometría/datos/objetos para el análisis de resolución del rojo (20/10).

Geometría de rojo_final (= z102_p129) armada con los mismos hooks que offset_color_2026-10-02/runner.py
(aumento -> lrpx 1.29, NA objetivo 0.069·1.25/1.29, z 102, offset por color, factor 3); no modifica nada.
Funciones de FRC/bandas/rel_phase/blobs = las de fpm_red.py y captura_2026-09-25_red/analyze.py (C2/C4)."""
import os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, "..", ".."))   # results/
OC = os.path.abspath(os.path.join(HERE, ".."))   # carpeta de runner_2110.py y out/
OCO = os.path.join(RES, "octubre_capturas_2026-10-21")   # corridas de octubre (m2_red)
DS = os.environ.get("DS", "r500_red")
VAR = os.environ.get("VAR", {"r500_red": "rojo_500", "r21_red": "rojo_centrado"}.get(DS, "rojo_final"))
B28 = os.path.join(RES, "captura_2026-09-28b", "red")
sys.path.insert(0, OC)
import runner_500 as RN  # noqa: E402  (solo lectura: VARIANTS, IR)

IR = RN.IR
LAM = 0.63
EXCL = [] if DS in ("r21_red", "r500_red") else [(18, 14), (18, 16)]   # fuera del entrenamiento en rojo_final (a horcajadas del borde de pupila)


def load(var=None):
    var = var or VAR
    """(F, geo, D) con la geometría de la variante (por defecto rojo_final)."""
    F, R = IR._load(DS)
    V = RN.VARIANTS[var]
    if "_mag" in V or "_naobj" in V:
        from dataclasses import replace as _rep
        s0f = F.setup
        def _setup(*a, **kw):
            s0 = s0f(*a, **kw)
            return _rep(s0, objective=_rep(s0.objective, magnification=V.get("_mag", s0.objective.magnification),
                                            na=V.get("_naobj", s0.objective.na)))
        F.setup = _setup
    if "_factor" in V:
        from ptyco_full_simulator import optics as _opt
        fz = V["_factor"]["red"]
        F.cc.factor_for = lambda s0, fz=fz: max(fz, _opt.canvas_upsampling_factor(s0))
    geo = F.geometry(V.get("_z", 98.0), offset_mm=(0.0, 3.0 + V["red"]), na=V.get("_na"))
    return F, geo, F.load_real()


def load_old():
    """Geometría vieja de 28/09b (z 98, lrpx 1.28, NA 0.07, offset nominal)."""
    F, R = IR._load("b_red")
    return F, F.geometry(98.0), F.load_real()


def frc(a, b, px, nb=60, kmax=None):
    """= fpm_red.frc (anillos de ancho kmax/nb); columnas k, FRC, n_px."""
    Fa = np.fft.fftshift(np.fft.fft2(a - a.mean())); Fb = np.fft.fftshift(np.fft.fft2(b - b.mean()))
    H = a.shape[0]; fy, fx = np.mgrid[:H, :H] - H // 2
    kr = np.hypot(fx, fy) / (H * px); kmax = kmax or kr.max()
    e = np.linspace(0, kmax, nb + 1); out = []
    for lo, hi in zip(e[:-1], e[1:]):
        m = (kr >= lo) & (kr < hi)
        num = np.abs(np.sum(Fa[m] * np.conj(Fb[m])))
        den = np.sqrt(np.sum(np.abs(Fa[m]) ** 2) * np.sum(np.abs(Fb[m]) ** 2)) + 1e-30
        out.append((0.5 * (lo + hi), num / den, int(m.sum())))
    return np.array(out)


def band_mean(fr, lo, hi):
    m = (fr[:, 0] >= lo) & (fr[:, 0] < hi)
    return float(np.mean(fr[m, 1]))


def radial(P, px, nb=120, kmax=None):
    """Promedio radial de un mapa (fftshift) de potencia/espectro cruzado."""
    H = P.shape[0]; fy, fx = np.mgrid[:H, :H] - H // 2
    kr = np.hypot(fx, fy) / (H * px); kmax = kmax or kr.max()
    e = np.linspace(0, kmax, nb + 1); idx = np.digitize(kr.ravel(), e) - 1
    ok = (idx >= 0) & (idx < nb)
    s = np.bincount(idx[ok], P.ravel()[ok], nb); n = np.bincount(idx[ok], None, nb)
    return 0.5 * (e[:-1] + e[1:]), s / np.maximum(n, 1), n


def rel_phase(o, sig=20):
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return np.angle(o * np.exp(-1j * np.angle(sm)))


def blobs(img, px, sigmas=(1, 1.5, 2, 3, 4, 5), k=5.0):
    """= analyze.blobs (C4) con el píxel HR como parámetro."""
    img = img - ndi.gaussian_filter(img, 30)
    st = np.stack([np.abs(s * s * ndi.gaussian_laplace(img, s)) for s in sigmas])
    thr = np.array([k * 1.4826 * np.median(np.abs(x - np.median(x))) + np.median(x) for x in st])
    mx = ndi.maximum_filter(st, size=(3, 7, 7))
    pk = (st == mx) & (st > thr[:, None, None])
    si, y, x = np.nonzero(pk)
    r_um = np.array(sigmas)[si] * np.sqrt(2) * px
    return np.stack([y * px, x * px, r_um], 1) if len(y) else np.zeros((0, 3))


def near(a, b, d):
    if len(a) == 0 or len(b) == 0:
        return np.zeros(len(a), bool)
    from scipy.spatial import cKDTree
    return cKDTree(b[:, :2]).query(a[:, :2], k=1)[0] < d


def c4(full, h0, h1, raw_bf, px, F):
    """= analyze.c4: nuevas (r <= 2 µm, sin detección cruda a < 3 µm) confirmadas (< 2 µm) en las DOS mitades."""
    rec = blobs(rel_phase(full), px)
    raw = blobs(np.real(F.fourier_upsample(np.sqrt(np.clip(raw_bf, 0, None)), full.shape[0] // raw_bf.shape[0])), px)
    new = rec[(rec[:, 2] <= 2.0) & ~near(rec, raw, 3.0)]
    b0, b1 = blobs(rel_phase(h0), px), blobs(rel_phase(h1), px)
    both = near(new, b0, 2.0) & near(new, b1, 2.0)
    return dict(n_rec=len(rec), n_raw=len(raw), n_new=len(new), n_new_both_halves=int(both.sum()),
                frac=float(both.mean()) if len(new) else 0.0)

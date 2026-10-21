"""fpm_red.py -- COPIA (21/10) de results/octubre_capturas_2026-10-21/m2_red/fpm_red.py (= 28/09b) para la captura roja 21/10
(eje sobre el LED (17,15)): filas 10-24 (row_index_base 10), BF = cruz de 5 LEDs con (17,15) primero, CENTER (17,15), offset nominal
(0,0) (el runner lo fija). Nada más cambia.

Original: fpm_red.py -- standalone FPM solver + metrics for the 2026-09-25 red capture (set 3).

Does NOT modify src/. It reuses the repo's geometry (config/led_array via
results/captura_2026-09-24/j3/common/cv_common.py), `optics.circular_pupil`,
`spectral_ops.led_crop_window` and `cv_common.lattice_score`, and re-implements
the ePIE/WF update of `reconstruction.reconstruct` (step_relative form: a unit
step is the ePIE projection) with the options the J3 brief forbade:

  weights   per-LED step multiplier w_k ('none' | 'noise' | 'bfdown')
  fit_sb    per-LED intensity model  I_k ~ s_k |A_k|^2 + b_k, (s_k, b_k) refit by
            least squares every epoch (s of the brightest BF LED pinned to 1)
  init      'kron17' (J3: nearest-neighbour upsample of LED (17,15)) |
            'fourier_avg' (Fourier-interpolated sqrt of the mean of both BF LEDs)
  epry      EPRY pupil branch (ou2014), same relative step

Data model (prep.npz from prep.py): S_k = (sample-dark)/t, counts/ms.
Target intensity I_k:
  BF LEDs (17,15),(18,15): S_k / F_k * mean(F_k)  (flat-field division)
  DF LEDs:                 S_k - gaussian(F_k, 8 px)   (no-sample stray light removed)
  saturated pixels (either raw frame at 4095) are masked out of every update/metric.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "results", "captura_2026-09-24", "j3", "common"))

import cv_common as cc  # noqa: E402
from ptyco_full_simulator import config, led_array, optics  # noqa: E402
from ptyco_full_simulator.optics import circular_pupil  # noqa: E402
from ptyco_full_simulator.spectral_ops import led_crop_window  # noqa: E402

BF = [(17, 15), (16, 15), (17, 14), (17, 16), (18, 15)]  # 21/10: eje sobre (17,15) -> cruz de 5 LEDs de campo claro
CENTER = (17.0, 15.0)
LAM, NA, LRPX = 0.63, 0.07, 1.28


def ring(k):
    return float(np.hypot(k[0] - CENTER[0], k[1] - CENTER[1]))


def setup(z_mm=98.0, offset_mm=(0.0, 0.0), crop=400):
    # 28/09 (b): 15x15 LEDs, filas 11-25, columnas 8-22 (centro nominal (18, 15); offset (0, 3) mm -> eje en fila 17.5)
    return config.default_setup("red", 15, objective=cc.OBJECTIVE, resolution_px=(crop, crop), row_index_base=10,
                                col_index_base=8, z_distance_mm=z_mm, led_center_offset_mm=offset_mm)


# 21/10 tarde (muestra .500): el recorte está corrido +200 px en columnas respecto del centro del ROI (560); con la misma convención que
# las filas de la mañana (-50 px en filas -> +0.085 mm, 0.0017 mm/px; los arcos del flat dan la misma orientación en filas y columnas)
# el eje local se corre -0.340 mm en x. Se SUMA aquí porque runner_2110.run_task fija offset_x = 0. La componente y va en la variante.
CROP_OFFSET_X_MM = float(os.environ.get("R500_XOFF", "-0.340"))   # env solo para el control de signo (run_xoff.sh)


def geometry(z_mm=98.0, offset_mm=(0.0, 0.0), crop=400, na=None):
    s = setup(z_mm, (offset_mm[0] + CROP_OFFSET_X_MM, offset_mm[1]), crop)
    f = cc.factor_for(s)
    grid = led_array.build_led_grid(s.led_array, s.wavelength_um)
    return dict(factor=f, hrpx=optics.actual_hr_pixel_size_um(s, f), lrpx=s.lr_pixel_size_um,
                lam=s.wavelength_um, na=na or s.objective.na,
                fxy={(e["row"], e["col"]): (e["fx"], e["fy"]) for e in grid})


def load_real(path=os.path.join(HERE, "prep.npz"), df_sigma=8.0):
    d = dict(np.load(path))  # decompress each array once (npz access re-decompresses)
    keys = [tuple(int(v) for v in k) for k in d["keys"]]
    I, V, M = {}, {}, {}
    for i, k in enumerate(keys):
        s, f = d["S"][i].astype(float), d["F"][i].astype(float)
        if k in BF:
            I[k] = s / f * f.mean()
            V[k] = float(d["V"][i]) * float(np.mean((f.mean() / f) ** 2))
        else:
            I[k] = s - gaussian_filter(f, df_sigma)
            V[k] = float(d["V"][i])
        M[k] = ~d["SAT"][i]
    return dict(I=I, V=V, mask=M, keys=keys, gain=float(d["gain"]), read_var=float(d["read_var"]),
                t={k: float(t) for k, t in zip(keys, d["t"])})


def noise_weights(I, V, sigma0=0.1):
    """Projection-form noise weight: relative amplitude noise of LED k is
    sigma_rel = sqrt(V)/(2 <I>); w = 1/(1+(sigma_rel/sigma0)^2)."""
    w = {}
    for k in I:
        m = max(float(np.mean(I[k])), 1e-9)
        sr = np.sqrt(V[k]) / (2 * m)
        w[k] = 1.0 / (1.0 + (sr / sigma0) ** 2)
    return w


def fourier_upsample(a, f):
    n = a.shape[0]
    A = np.fft.fftshift(np.fft.fft2(a))
    H = n * f
    out = np.zeros((H, H), complex)
    o = (H - n) // 2
    out[o:o + n, o:o + n] = A
    return np.fft.ifft2(np.fft.ifftshift(out)) * f * f  # keeps pixel values


def initial_object(I, factor, kind):
    bf = [k for k in BF if k in I]  # a split half holds only one of the two BF LEDs
    if kind == "kron17":
        amp = np.sqrt(np.clip(I[bf[0]], 0, None))
        return np.kron(amp, np.ones((factor, factor))).astype(complex) / factor ** 2
    if kind == "fourier_avg":
        amp = np.sqrt(np.clip(np.mean([I[k] for k in bf], 0), 0, None))
        return np.real(fourier_upsample(amp, factor)).astype(complex) / factor ** 2
    raise ValueError(kind)


def _order(keys):
    return sorted(keys, key=lambda k: (ring(k), k))


def reconstruct(I, keys, geo, iterations=40, step=0.3, weights=None, fit_sb=False,
                init="kron17", epry=False, mask=None, obj0=None, seed_sb=None, sb_start=10, s_max=4.0):
    lr_shape = I[keys[0]].shape
    n = lr_shape[0] * lr_shape[1]
    Pm = circular_pupil(lr_shape, geo["lrpx"], geo["na"], geo["lam"])
    P = Pm.astype(complex)
    f = geo["factor"]
    o0 = obj0 if obj0 is not None else initial_object(I, f, init)
    hr = o0.shape
    spec = np.fft.fftshift(np.fft.fft2(o0))
    win = {k: led_crop_window(hr, geo["hrpx"], lr_shape, *geo["fxy"][k]) for k in keys}
    order = _order(keys)
    w = weights or {k: 1.0 for k in keys}
    s = {k: 1.0 for k in keys}
    b = {k: 0.0 for k in keys}
    if seed_sb:
        s.update(seed_sb[0]); b.update(seed_sb[1])
    p5 = {k: float(np.percentile(I[k], 5)) for k in keys}
    hist = []
    for it in range(iterations):
        mu = step * (1.0 - np.exp(-0.3 * it)) if not epry else step
        acc = {}
        err = 0.0
        for k in order:
            ys, xs = win[k]
            ps = spec[ys, xs]
            A = np.fft.ifft2(np.fft.ifftshift(ps * P))
            amp = np.abs(A)
            tgt = np.sqrt(np.clip((I[k] - b[k]) / s[k], 0, None))
            if mask is not None:
                tgt = np.where(mask[k], tgt, amp)
            if fit_sb:
                x = amp ** 2
                mk = mask[k] if mask is not None else slice(None)
                xv, yv = x[mk], I[k][mk]
                acc[k] = (xv.sum(), yv.sum(), (xv * xv).sum(), (xv * yv).sum(), xv.size)
            err += float(np.mean((amp - tgt) ** 2))
            corr = tgt * A / np.maximum(amp, 1e-12)
            D = np.fft.fftshift(np.fft.fft2(corr - A))
            if epry:
                pm = max(float(np.max(np.abs(P) ** 2)), 1e-12)
                sm = max(float(np.max(np.abs(ps) ** 2)), 1e-12)
                spec[ys, xs] = ps + mu * w[k] * np.conj(P) / pm * D
                P = (P + mu * w[k] * np.conj(ps) / sm * D) * Pm
            else:
                spec[ys, xs] = ps + mu * w[k] * P * D
        if fit_sb and it >= sb_start:
            # s free for a dim LED would trap the solver (early prediction ~0 -> s huge ->
            # target ~0 -> HF never grows), so: start after `sb_start` epochs, s in
            # [0.25, 4], b in [0, p5(I_k)] (the background cannot exceed the darkest pixels).
            for k, (sx, sy, sxx, sxy, m) in acc.items():
                den = m * sxx - sx * sx
                if den <= 0:
                    continue
                sk = float(np.clip((m * sxy - sx * sy) / den, 0.25, s_max))
                bk = float(np.clip((sy - sk * sx) / m, 0.0, max(p5[k], 0.0)))
                s[k], b[k] = sk, bk
            ref = next((s[k] for k in BF if k in s), 1.0)
            for k in s:
                s[k] = float(np.clip(s[k] / ref, 0.25, s_max))
        hist.append(err / len(keys))
    obj = np.fft.ifft2(np.fft.ifftshift(spec))
    return dict(object=obj, pupil=P, s=s, b=b, hist=hist)


def predict(obj, keys, geo, lr_shape=(400, 400), pupil=None):
    spec = np.fft.fftshift(np.fft.fft2(obj))
    P = pupil if pupil is not None else circular_pupil(lr_shape, geo["lrpx"], geo["na"], geo["lam"])
    out = {}
    for k in keys:
        ys, xs = led_crop_window(obj.shape, geo["hrpx"], lr_shape, *geo["fxy"][k])
        out[k] = np.abs(np.fft.ifft2(np.fft.ifftshift(spec[ys, xs] * P))) ** 2
    return out


def affine_residual(pred, meas, var, mask=None):
    """Held-out metric: best 2-parameter fit meas ~ s*pred + b (s>=0), then
    R = ||meas - fit|| / ||meas - mean(meas)||  (1 == no better than a constant),
    floor = sqrt(var) / std(meas)  (what pure noise would leave)."""
    m = mask if mask is not None else np.ones(meas.shape, bool)
    x, y = pred[m].ravel(), meas[m].ravel()
    X = np.stack([x, np.ones_like(x)], 1)
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    if c[0] < 0:
        c = np.array([0.0, y.mean()])
    r = y - X @ c
    sd = y.std()
    return float(np.sqrt(np.mean(r ** 2)) / sd), float(np.sqrt(var) / sd)


def folds(keys, K=5):
    """Stratified by ring: sort non-BF LEDs by (ring, key) and deal round-robin.
    BF LEDs are never held out."""
    ks = [k for k in _order(keys) if k not in BF]
    return [set(ks[i::K]) for i in range(K)]


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


def band_mean(fr, lo, hi):
    m = (fr[:, 0] >= lo) & (fr[:, 0] < hi)
    return float(np.mean(fr[m, 1]))


def remove_phase_ramp_and_offset(o):
    """Align a complex reconstruction for comparison: remove global phase."""
    return o * np.exp(-1j * np.angle(np.sum(o)))


lattice_score = cc.lattice_score

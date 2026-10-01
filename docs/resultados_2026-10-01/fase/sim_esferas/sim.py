"""Curva de calibración de fase: esferas de fase pura (1-10 µm) en la geometría 28/09 (b), verde.

Reusa results/sim_multiespectral_2026-09-29/sim.py (mismo modelo directo fpm_red.predict, brillo por LED igualado al
medido y ruido gaussiano con la varianza medida por LED) y el solver A+init (fpm_red.reconstruct, init fourier_avg,
paso 0.3). Campo 128 µm (100 px LR). dn = 0.045 + 0.0015/lam^2 (sim_multiespectral sim.py:30, 'del orden de poliamida
en DMSO') -> 0.0503 a 530 nm.
python3 sim.py run   -> out/obj_<ruido>_<epocas>.npy
"""
import importlib.util, json, os, sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAM = 0.53
DN = 0.045 + 0.0015 / LAM ** 2
FOV, CROP = 128.0, 100
DIAM = [1, 2, 3, 5, 7, 10]
CENT = [(32, 21), (32, 64), (32, 107), (96, 21), (96, 64), (96, 107)]  # (y, x) µm


def mod():
    s = importlib.util.spec_from_file_location("Fg", os.path.join(REPO, "results/captura_2026-09-28b/green/fpm_red.py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def truth(n):
    px = FOV / n
    yy, xx = (np.mgrid[:n, :n] + 0.5) * px
    t = np.zeros((n, n))
    for d, (cy, cx) in zip(DIAM, CENT):
        r = d / 2; d2 = (yy - cy) ** 2 + (xx - cx) ** 2; m = d2 < r * r
        t[m] += 2 * np.sqrt(r * r - d2[m])
    return t


def to_grid(a, n):
    N = a.shape[0]; S = np.fft.fftshift(np.fft.fft2(a)); o = (N - n) // 2
    return np.fft.ifft2(np.fft.ifftshift(S[o:o + n, o:o + n])) * (n / N) ** 2


def data(F, g, R, noisy):
    H = CROP * g["factor"]
    t = truth(4 * H)
    obj = to_grid(np.exp(1j * 2 * np.pi * DN * t / LAM), H) / g["factor"] ** 2
    clean = F.predict(obj, R["keys"], g, lr_shape=(CROP, CROP))
    rng = np.random.default_rng(1); I = {}
    for k in R["keys"]:
        s = max(float(np.mean(R["I"][k])), 1e-6) / max(float(clean[k].mean()), 1e-12)
        I[k] = s * clean[k] + (rng.standard_normal(clean[k].shape) * np.sqrt(R["V"][k]) if noisy else 0)
    return I


def task(tk):
    noisy, its = tk
    out = os.path.join(HERE, "out", f"obj_{'ruido' if noisy else 'limpio'}_{its}.npy")
    if os.path.exists(out):
        return
    F = mod(); g = F.geometry(98.0, crop=CROP); R = F.load_real()
    I = data(F, g, R, noisy)
    res = F.reconstruct(I, R["keys"], g, iterations=its, init="fourier_avg")
    np.save(out, res["object"].astype(np.complex64))
    print("listo", out, g["factor"], g["hrpx"], flush=True)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    T = [(True, 400), (False, 400), (True, 40), (False, 40)]
    with mp.get_context("fork").Pool(4) as p:
        p.map(task, T, chunksize=1)

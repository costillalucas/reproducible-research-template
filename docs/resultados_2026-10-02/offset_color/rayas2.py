"""rayas2.py -- rayas a lo largo de y (filas LED), versión general: cualquier variante/dataset/época, período del pico
refinado con FFT con relleno de ceros (x16). Fondo lento quitado demodulando con el campo suavizado (sigma 60 µm).
Uso: python3 rayas2.py VAR:DS:EP [VAR:DS:EP ...]   (VAR = base -> iteraciones_2026-09-30)"""
import json, os, sys
import numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
T = "real_A+init_z98.0_full"


def path(var, ds, e):
    root = os.path.join(HERE, "..", "iteraciones_2026-09-30", "out") if var == "base" else os.path.join(HERE, "out", var)
    return os.path.join(root, ds, T, f"obj_e{e:03d}.npy")


def rayas(o):
    o = o.astype(complex); N = o.shape[0]; hr = 512 / N; mg = int(round(17 / hr))
    u = o / np.maximum(abs(o), 1e-6); s = 60 / hr
    bg = ndi.gaussian_filter(u.real, s) + 1j * ndi.gaussian_filter(u.imag, s)
    w = np.angle(o * np.conj(bg))[mg:-mg, mg:-mg]
    prof = np.median(w, axis=1); prof -= prof.mean()
    n = len(prof); S = np.abs(np.fft.rfft(prof * np.hanning(n), 16 * n)) ** 2; f = np.fft.rfftfreq(16 * n, hr)
    m = (f > 1 / 200) & (f < 1 / 20); k = np.argmax(np.where(m, S, 0))
    return dict(rms_perfil_rad=float(prof.std()), periodo_um=float(1 / f[k]), bins_512=float(f[k] * 512),
                mad_fondo_rad=float(1.4826 * np.median(np.abs(w - np.median(w)))))


if __name__ == "__main__":
    out = {}
    for a in sys.argv[1:]:
        var, ds, e = a.split(":"); p = path(var, ds, int(e))
        if not os.path.exists(p): print(a, "falta"); continue
        out[a] = rayas(np.load(p)); print(a, {k: round(v, 3) for k, v in out[a].items()}, flush=True)
    f = os.path.join(HERE, "rayas2.json"); old = json.load(open(f)) if os.path.exists(f) else {}
    old.update(out); json.dump(old, open(f, "w"), indent=1)

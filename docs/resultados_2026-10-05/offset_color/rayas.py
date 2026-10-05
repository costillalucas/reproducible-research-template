"""rayas.py -- cuantifica las rayas horizontales (modulación a lo largo de y = filas LED) en la fase roja, base vs die.
Perfil: mediana en x de la fase desenrollada sin rampa lineal; espectro 1D del perfil; potencia en el pico."""
import json, os, sys
import numpy as np
from skimage.restoration import unwrap_phase
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
T = "real_A+init_z98.0_full"
P = {"base": os.path.join(HERE, "..", "iteraciones_2026-09-30", "out", "b_red", T), "die": os.path.join(HERE, "out", "die", "b_red", T)}
HR = 512 / 1200; out = {}
for tag, p in P.items():
    M = {r["epoch"]: r for r in map(json.loads, open(os.path.join(p, "metrics.jsonl")))}
    for e in (5, 40, 160):
        o = np.load(os.path.join(p, f"obj_e{e:03d}.npy")).astype(complex)
        # demodular con el campo suavizado elimina rampa/fondo lento (sigma 60 µm) sin desenrollar global
        u = o / np.maximum(abs(o), 1e-6); s = 60 / HR
        bg = ndi.gaussian_filter(u.real, s) + 1j * ndi.gaussian_filter(u.imag, s)
        w = np.angle(o * np.conj(bg))[40:-40, 40:-40]
        prof = np.median(w, axis=1); prof -= prof.mean()
        S = np.abs(np.fft.rfft(prof * np.hanning(len(prof)))) ** 2; f = np.fft.rfftfreq(len(prof), HR)
        m = f > 1 / 200; k = np.argmax(S * m)
        out[f"{tag}_e{e}"] = dict(perfil_rms_rad=float(prof.std()), periodo_pico_um=float(1 / f[k]), lattice=M[e]["lattice"],
                                  fondo_mad_rad=float(1.4826 * np.median(np.abs(w - np.median(w)))))
        print(tag, e, {k2: round(v, 4) for k2, v in out[f"{tag}_e{e}"].items()})
json.dump(out, open(os.path.join(HERE, "rayas.json"), "w"), indent=1)

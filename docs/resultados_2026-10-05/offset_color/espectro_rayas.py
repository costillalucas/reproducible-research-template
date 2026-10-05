"""espectro_rayas.py -- dónde está la raya en el espectro del objeto (fase): mapa |FFT(fase demodulada)| cerca del eje fy,
bins de la grilla HR (dk = 1/512 µm^-1). Busca el pico con |fx| <= 2 bins, 3 <= |fy| <= 30 bins.
Uso: python3 espectro_rayas.py VAR:EP ..."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rayas2 import path
from scipy import ndimage as ndi
out = {}
for a in sys.argv[1:]:
    var, e = a.split(":"); o = np.load(path(var, "b_red", int(e))).astype(complex); N = o.shape[0]; hr = 512 / N
    u = o / np.maximum(abs(o), 1e-6); s = 60 / hr
    bg = ndi.gaussian_filter(u.real, s) + 1j * ndi.gaussian_filter(u.imag, s)
    w = np.angle(o * np.conj(bg)); S = np.abs(np.fft.fftshift(np.fft.fft2(w)))
    c = N // 2; win = S[c - 30:c + 31, c - 2:c + 3].max(1); fy = np.arange(-30, 31)
    m = np.abs(fy) >= 3; top = np.argsort(np.where(m, win, 0))[::-1][:4]
    out[a] = [(int(fy[i]), float(win[i] / np.median(S))) for i in top]
    print(a, out[a], flush=True)

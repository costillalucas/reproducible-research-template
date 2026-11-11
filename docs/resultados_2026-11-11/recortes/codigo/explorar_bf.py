"""Mapa BF (LED 17,15 / flat) del ROI entero de red-c y detección preliminar de partículas (solo para elegir el recorte de 200 px)."""
import sys, numpy as np, glob, tifffile
from scipy import ndimage as ndi
B = "/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/"
def med(c, t):
    fs = sorted(glob.glob(f"{B}{c}/fila17_col15_colorr/{t}/imagen_frame_*.tif*"))
    return np.mean([tifffile.imread(f).astype(float) for f in fs], 0)
import os
ts = os.listdir(B + "2026-10-30-red-c/fila17_col15_colorr"); tf = os.listdir(B + "2026-10-30-red-c-sinmuestra/fila17_col15_colorr")
print(ts, tf)
t = sorted(ts, key=lambda s: float(s[:-2]))[0]; t2 = sorted(tf, key=lambda s: float(s[:-2]))[0]
s = med("2026-10-30-red-c", t); f = med("2026-10-30-red-c-sinmuestra", t2)
print("max raw", s.max())
q = (s - 188) / np.maximum(ndi.gaussian_filter(f - 188, 2), 1)
q /= np.median(q)
np.save(sys.argv[1], q.astype(np.float32))
hp = q - ndi.gaussian_filter(q, 6)
print("hp std", hp.std(), "q pct", np.percentile(q, [1, 50, 99]))

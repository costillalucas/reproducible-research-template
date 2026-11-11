"""Detección de partículas en el mapa BF (LED central / flat) para elegir el recorte de 200 px.
Partícula = mínimo local de q suavizado (sigma 1 px) con profundidad > umbral respecto del fondo (mediana 31 px)."""
import sys, numpy as np
from scipy import ndimage as ndi
q = np.load(sys.argv[1]).astype(float)
bg = ndi.median_filter(q, 31)
d = bg - ndi.gaussian_filter(q, 1.0)          # profundidad (oscuro = positivo)
mx = (d == ndi.maximum_filter(d, 7)) & (d > 0.12)
ys, xs = np.nonzero(mx)
# "objetos" = cualquier cosa con contraste (para medir aislamiento también contra manchas grandes/brillantes)
obj = np.abs(q - bg) > 0.08
lab, n = ndi.label(obj)
P = np.stack([ys, xs], 1)
np.save(sys.argv[2], dict(P=P, depth=d[ys, xs], lab=lab, q=q, bg=bg), allow_pickle=True)
print(len(P), "candidatos")

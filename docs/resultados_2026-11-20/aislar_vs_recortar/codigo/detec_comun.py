"""detec_comun.py -- detección de partículas por desvío complejo respecto del fondo (sirve aunque la fase no se pueda
desenvolver: en esta toma las partículas reconstruyen con amplitud ~0 en el centro y vórtices de fase).
D = |o / fondo − 1| suavizado (σ 1 µm), fondo = gaussiana compleja de 12 µm (como octubre). Umbral max(0.15, med + 6·MAD).
Grupos = componentes dilatadas 3 µm (centro + anillos de la misma partícula = un grupo)."""
import numpy as np
from scipy import ndimage as ndi


def mapa_D(o, hr):
    o = o.astype(complex)
    bgc = ndi.gaussian_filter(o.real, 12 / hr) + 1j * ndi.gaussian_filter(o.imag, 12 / hr)
    return ndi.gaussian_filter(np.abs(o / bgc - 1), 1 / hr)


def grupos(o, hr, margen_um=16.0):
    D = mapa_D(o, hr)
    med = np.median(D); noise = 1.4826 * np.median(np.abs(D - med)); thr = max(0.15, med + 6 * noise)
    m = D > thr
    g, n = ndi.label(ndi.binary_dilation(m, iterations=int(round(3 / hr))))
    gl = g * m
    out = []
    mg = int(round(margen_um / hr))
    for k, sl in enumerate(ndi.find_objects(gl), 1):
        if sl is None: continue
        mk = gl == k
        yy, xx = np.nonzero(mk)
        w = D[mk]
        cy, cx = (w * yy).sum() / w.sum(), (w * xx).sum() / w.sum()
        ext_y = (yy.max() - yy.min() + 1) * hr; ext_x = (xx.max() - xx.min() + 1) * hr
        cov = np.cov(np.stack([yy, xx])) if len(yy) > 2 else np.eye(2); ev = np.sort(np.linalg.eigvalsh(cov))
        sub, nsub = ndi.label(mk[sl])
        out.append(dict(k=k, cy=float(cy), cx=float(cx), ext=float(max(ext_y, ext_x)), d_eq=float(2 * np.sqrt(mk.sum() * hr * hr / np.pi)),
                        elong=float(np.sqrt(ev[1] / max(ev[0], 1e-9))), Dmax=float(w.max()), n_comp=int(nsub),
                        borde=bool(cy < mg or cx < mg or cy > o.shape[0] - mg or cx > o.shape[1] - mg)))
    return out, dict(thr=float(thr), med=float(med), noise=float(noise)), D, gl

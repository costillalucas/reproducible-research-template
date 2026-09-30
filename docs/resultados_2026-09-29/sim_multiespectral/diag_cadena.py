"""Diagnóstico de la cadena multiespectral (multispectral.couple_rgb_channels) SIN reconstrucción: fases verdaderas.
Espesor verdadero generado directo en la grilla común (1200 px, 0.427 µm; sin remuestreo ni filtrado), tres muestras:
  delgada   : radios 0.5-1.5 µm, sin superposición
  gruesa    : radios 0.5-5 µm, sin superposición
  superpuesta: radios 0.5-5 µm con superposición (como sim.py)
y ruido de fase gaussiano 0 / 0.05 / 0.2 rad por color. Separa las dos etapas de la cadena:
  1. desenvolvimiento: error del camino óptico (OPL = dn t) desenvuelto contra el verdadero, por color
  2. ajuste de Cauchy libre (C + D/lambda^2, t = C/A): espesor final de la cadena
y lo compara con usar la dispersión CONOCIDA sobre el mismo OPL desenvuelto (t = promedio de OPL_c / dn_c).
Escribe diag_cadena.json."""
import json
import os
import sys

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))
from ptyco_full_simulator import multispectral as ms  # noqa: E402

LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}
A_DN, B_DN = 0.045, 0.0015
N, FOV = 1200, 512.0
PX = FOV / N


def dn(lam):
    return A_DN + B_DN / lam ** 2


def muestra(rmin, rmax, n, solapar, seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:N, :N] * PX
    t = np.zeros((N, N)); inside = np.zeros((N, N), bool)
    for r in np.exp(rng.uniform(np.log(rmin), np.log(rmax), n)):
        cy, cx = rng.uniform(r + 30, FOV - r - 30, 2)
        y0, y1 = int((cy - r) / PX) - 1, int((cy + r) / PX) + 2
        x0, x1 = int((cx - r) / PX) - 1, int((cx + r) / PX) + 2
        d2 = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        m = d2 < r * r
        if not solapar and ndi.binary_dilation(inside[y0:y1, x0:x1], iterations=2)[m].any():
            continue
        t[y0:y1, x0:x1][m] += 2 * np.sqrt(r * r - d2[m]); inside[y0:y1, x0:x1] |= m
    return t, inside


def corr(a, b, m):
    a, b = a[m] - a[m].mean(), b[m] - b[m].mean()
    return float(np.sum(a * b) / np.sqrt(np.sum(a * a) * np.sum(b * b)))


CASOS = {"delgada": (0.5, 1.5, 4000, False), "gruesa": (0.5, 5.0, 1500, False), "superpuesta": (0.5, 5.0, 1500, True)}
out = {}
for nombre, (rmin, rmax, n, sol) in CASOS.items():
    t, inside = muestra(rmin, rmax, n, sol)
    bg = ndi.binary_erosion(~inside, iterations=3)
    m = np.zeros((N, N), bool); m[40:-40, 40:-40] = True
    mp = m & inside                                     # métricas de espesor sobre las partículas
    for sig in (0.0, 0.05, 0.2):
        rng = np.random.default_rng(1)
        ph = {c: np.angle(np.exp(1j * (2 * np.pi * dn(l) * t / l + rng.standard_normal((N, N)) * sig))) for c, l in LAM.items()}
        cp = ms.couple_rgb_channels(ph, LAM, bg, baseline_index_A=A_DN)
        opl_err = {c: float(np.median(np.abs(cp["opl"][c] - dn(l) * t)[mp])) for c, l in LAM.items()}
        salto = {c: float(np.mean(np.abs(cp["opl"][c] - dn(l) * t)[mp] > l / 4)) for c, l in LAM.items()}   # vuelta de fase mal elegida
        t_cad = cp["resolved"]["thickness_um"]
        t_con = np.mean([cp["opl"][c] / dn(l) for c, l in LAM.items()], axis=0)
        r = dict(t_max_um=float(t.max()), fase_max_azul_rad=float(2 * np.pi * dn(0.47) * t.max() / 0.47),
                 opl_err_mediana_um=opl_err, frac_vuelta_equivocada=salto,
                 cadena_corr=corr(t_cad, t, m), cadena_rmse_um=float(np.sqrt(np.mean((t_cad - t)[mp] ** 2))),
                 dispersion_conocida_corr=corr(t_con, t, m), dispersion_conocida_rmse_um=float(np.sqrt(np.mean((t_con - t)[mp] ** 2))))
        out[f"{nombre}_ruido{sig}"] = r
        print(nombre, sig, {k: (round(v, 3) if isinstance(v, float) else {a: round(b, 3) for a, b in v.items()}) for k, v in r.items()}, flush=True)
json.dump(out, open(os.path.join(HERE, "diag_cadena.json"), "w"), indent=1)

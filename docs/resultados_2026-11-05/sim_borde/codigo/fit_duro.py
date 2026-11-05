"""fit_duro.py -- Entregable 2: si la pupila real es blanda (erf, ancho w), ¿qué NA de una pupila DURA ajusta mejor las imágenes?

Modelo directo simple (NO es una reconstrucción): objeto VERDADERO conocido (semilla 0 de sim_borde), recorte 400x400 con onda
plana por LED (mismo recorte que el método espectral), pupila dura con borde antialiasado de 1 bin de frecuencia
(clip((NA - r)/δ + 0.5, 0, 1), δ = λ/(lado del bloque) ≈ 0.001 NA, para que el desajuste sea continuo en NA).
Para cada NA_duro: escala libre por imagen (mínimos cuadrados) y desajuste relativo Σ‖I_obs - a·I_mod‖² / Σ‖I_obs‖².
Conjuntos: 5 LEDs BF; 5 BF + 4 diagonales (DF, el borde de la pupila entra más). Datos: sin ruido y con ruido (semilla 0).
También se reporta el desajuste en amplitud (sqrt de la intensidad), más parecido a la pérdida típica de un solver FPM.
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
import sys
sys.dont_write_bytecode = True
import json
import math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_borde as S  # noqa: E402

DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
LEDS = S.BF5 + DIAG


def pupila_dura_aa(r, NA, delta):
    return np.clip((NA - r) / delta + 0.5, 0, 1).astype(np.float32)


def preparar(obj, z):
    tile = obj[S.CR0 * S.UP:(S.CR0 + S.NCR + 2 * S.MARG) * S.UP, S.CC0 * S.UP:(S.CC0 + S.NCR + 2 * S.MARG) * S.UP]
    n = tile.shape[0]
    Os = np.fft.fft2(tile)
    fy, fx = S.frecs(n)
    pr, pc = S.CR0 + S.NCR / 2 - S.NROI / 2, S.CC0 + S.NCR / 2 - S.NROI / 2
    R = {}
    for d in LEDS:
        ky, kx, _ = S.k_local(d, pr, pc, z)
        R[d] = np.hypot(fy + np.float32(ky), fx + np.float32(kx)) * np.float32(S.LAM)
    return Os, R, S.LAM / (n * S.FPX)


def imagen(Os, r, pup):
    E = np.fft.ifft2(Os * pup)
    I = (E.real ** 2 + E.imag ** 2).astype(np.float32)
    m = S.MARG * S.UP
    return S.binear_cam(I[m:m + S.NCR * S.UP, m:m + S.NCR * S.UP])


def desajuste(obs, mod, leds, amp=False):
    num = den = 0.0
    for d in leds:
        o, m = obs[d].astype(float).ravel(), mod[d].astype(float).ravel()
        if amp:
            o, m = np.sqrt(np.clip(o, 0, None)), np.sqrt(np.clip(m, 0, None))
        a = (o @ m) / (m @ m)
        num += float(((o - a * m) ** 2).sum()); den += float((o ** 2).sum())
    return num / den


def minimo(x, y):
    i = int(np.argmin(y))
    if 0 < i < len(y) - 1:
        c = np.polyfit(x[i - 1:i + 2], y[i - 1:i + 2], 2)
        if c[0] > 0:
            return float(-c[1] / (2 * c[0]))
    return float(x[i])


def main():
    z, NA0 = 99.5, 0.070
    obj, _ = S.objeto(0, S.NROI)
    Os, R, delta = preparar(obj, z)
    grilla = np.round(np.arange(0.064, 0.0821, 0.0005), 5)
    res = dict(z=z, NA_verdad=NA0, delta_aa=delta, grilla=grilla.tolist(), casos=[])
    for w in (0.0, 0.002, 0.004, 0.008):
        obs = {d: imagen(Os, R[d], S.pupila(R[d], NA0, w)) for d in LEDS}
        esc = S.PICO / float(np.percentile(obs[(0, 0)], 99.9))
        rng = np.random.default_rng(777 + int(w * 1e4))
        obs_n = {d: S.ruido(obs[d] * esc, rng) for d in LEDS}
        curvas = {}
        mods = {}
        for NAh in grilla:
            mods[NAh] = {d: imagen(Os, R[d], pupila_dura_aa(R[d], NAh, delta)) for d in LEDS}
        for etq, O in (('sin_ruido', obs), ('ruido', obs_n)):
            for conj, leds in (('BF5', S.BF5), ('BF5+diag', LEDS)):
                for amp in (False, True):
                    y = np.array([desajuste(O, mods[NAh], leds, amp) for NAh in grilla])
                    k = f"{etq}|{conj}|{'amp' if amp else 'int'}"
                    nah = minimo(grilla, y)
                    curvas[k] = dict(NA_min=nah, NAz_min=nah * z, d_min=float(y.min()), curva=y.tolist())
                    print(f'w {w:.3f} {k}: NA_duro óptimo {nah:.4f} (NA·z {nah * z:.3f}; verdad {NA0 * z:.3f})', flush=True)
        res['casos'].append(dict(w=w, curvas=curvas))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resultados', 'fit_duro.json')
    with open(out, 'w') as f:
        json.dump(res, f, indent=1)


if __name__ == '__main__':
    main()

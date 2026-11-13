"""sim_borde.py -- modelar (en vez de excluir) los LEDs en el borde BF/DF (simulacion, 12/11).
Uso: python sim_borde.py [limite_s]   Escribe runs.jsonl (una linea por corrida; se puede leer incompleto). Semillas fijas.
Reutiliza SIN modificar ../sim_z/sim_z.py y ../sim_z_clave/sim_z_clave.py (objetos, ruido, metricas, margen).
Datos: pupila erf de ancho w (en NA; 0.011 = medido en datos reales, 0.005 = el de sim_z), centro sub-pixel, grilla 2x fina.
Variantes del solver (ePIE 20 epocas, NA 0.070):
  a      pupila dura (base)
  b008/b012  pupila dura, excluye LEDs con |NA_ilum-NA| < 0.008 / 0.012
  c      pupila blanda erf con el w real (fijo)
  d      pupila blanda con w barrido; se elige el w de menor residuo de amplitud en los LEDs de borde
  e      pupila dura, paso de cada LED ponderado por min(1, margen/0.012)
"""
import json, os, sys, time
import numpy as np
from scipy import fft as sfft
from scipy.special import erf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z")); sys.path.insert(0, os.path.join(HERE, "..", "sim_z_clave"))
import sim_z as S                                     # noqa: E402
import sim_z_clave as K                               # noqa: E402

T0 = time.time()
LIM = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
NAPX = S.DK * S.LAM                                   # NA por pixel espectral (0.0077)
C = np.complex64
OUT = os.path.join(HERE, "runs.jsonl")


def pupila(fx, fy, w):
    r = np.hypot(S.xx - fx, S.yy - fy)
    if w is None:
        return (r <= S.R).astype(np.float32)
    return (0.5 * (1 - erf((r - S.R) / (w / NAPX)))).astype(np.float32)


def forward(spec, g, w):
    out = {}
    for k in S.KEYS:
        wn, fx, fy = S.win(g, k, S.FINE)
        out[k] = (np.abs(sfft.ifft2(sfft.ifftshift(spec[wn] * pupila(fx, fy, w)))) ** 2 * S.LR ** 4).astype(np.float32)
    return out


def reconstruct(I, g, keys, w=None, peso=False, its=S.ITS, step=S.STEP):
    """Como S.reconstruct pero con pupila opcionalmente blanda (w) y paso por LED ponderado por el margen (peso)."""
    od = sorted(keys, key=lambda k: (S.ill_na(g, k), k))
    amp0 = np.sqrt(np.clip(I[od[0]], 0, None))
    spec = (sfft.fftshift(sfft.fft2(np.kron(amp0, np.ones((S.F, S.F), np.float32)).astype(C))) / S.F ** 2).astype(C)
    W, P, tg, wt = {}, {}, {}, {}
    for k in od:
        wn, fx, fy = S.win(g, k, S.HR)
        W[k] = wn; P[k] = pupila(fx, fy, w)
        tg[k] = np.sqrt(np.clip(I[k], 0, None))
        wt[k] = np.float32(min(1.0, abs(S.ill_na(g, k) - S.NA) / 0.012)) if peso else np.float32(1)
    for it in range(its):
        mu = np.float32(step * (1.0 - np.exp(-0.3 * it)))
        for k in od:
            if wt[k] == 0:
                continue
            wn = W[k]; ps = spec[wn]
            A = sfft.ifft2(sfft.ifftshift(ps * P[k]))
            D = sfft.fftshift(sfft.fft2(tg[k] * A / np.maximum(np.abs(A), 1e-12) - A))
            spec[wn] = ps + mu * wt[k] * P[k] * D
    # residuo de amplitud (costo) en los LEDs de borde (margen < 0.012) y en todos, sobre TODOS los LEDs medidos
    num = {"borde": 0.0, "todos": 0.0}; den = {"borde": 0.0, "todos": 0.0}
    for k in S.KEYS:
        wn, fx, fy = S.win(g, k, S.HR)
        A = np.abs(sfft.ifft2(sfft.ifftshift(spec[wn] * pupila(fx, fy, w))))
        t = np.sqrt(np.clip(I[k], 0, None))
        n_, d_ = float(np.sum((A - t) ** 2)), float(np.sum(t ** 2))
        num["todos"] += n_; den["todos"] += d_
        if abs(S.ill_na(g, k) - S.NA) < 0.012:
            num["borde"] += n_; den["borde"] += d_
    cost = {"c_" + b: (num[b] / den[b] if den[b] > 0 else None) for b in num}
    return sfft.ifft2(sfft.ifftshift(spec)), cost


CACHE = {}
def datos(z, io, objs, wd, seed):
    key = (z, io, wd)
    if key not in CACHE:
        if len(CACHE) > 3: CACHE.clear()
        CACHE[key] = forward(objs[io][0], S.geom(z), wd)
    g = S.geom(z)
    In, _ = S.add_noise(CACHE[key], g, z, np.random.default_rng(1000 + seed))
    return In, g


def corre(est, z, io, objs, wd, seed, var, wsolver=None):
    if time.time() - T0 > LIM:
        print("limite de reloj"); sys.exit(0)
    In, g = datos(z, io, objs, wd, seed)
    keys, w, peso = S.KEYS, None, False
    if var.startswith("b"):
        u = int(var[1:]) / 1000.0
        keys = [k for k in S.KEYS if abs(S.ill_na(g, k) - S.NA) >= u]
    elif var == "c": w = wd
    elif var == "d": w = wsolver
    elif var == "e": peso = True
    o, cost = reconstruct(In, g, keys, w, peso)
    _, truth, mask = objs[io]
    nbf, mg, _, _ = K.margen(z, S.NA)
    row = dict(est=est, z=z, obj=io, seed=seed, wd=wd, var=var, ws=w, nbf=nbf, margen=mg, n_excl=len(S.KEYS) - len(keys),
               **S.metrics(o, truth, mask), **K.extra(o, truth), **cost, t=round(time.time() - T0, 1))
    with open(OUT, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(est, z, io, seed, wd, var, w, round(row["err"], 3), round(row["e_c23"], 3), row["t"], flush=True)


def main():
    objs = [S.make_object(0), S.make_object(1)]
    ZS = [181.0, 168.0, 146.0, 249.0, 125.0, 120.0, 180.0, 103.0]
    V = ["a", "c", "e", "b012"]
    for z in ZS:                                      # 1) w real 0.011, semilla 0
        for io in (0, 1):
            for v in V: corre("p1", z, io, objs, 0.011, 0, v)
    for wd in (0.011, 0.005):                         # 2) variante d: barrido de w del solver, z=181, obj 0
        for ws in (0.003, 0.005, 0.008, 0.011, 0.015, 0.020):
            corre("d", 181.0, 0, objs, wd, 0, "d", ws)
    for z in (181.0, 168.0, 249.0):                   # 3) borde mas duro (w 0.005)
        for io in (0, 1):
            for v in ("a", "c", "e"): corre("p3", z, io, objs, 0.005, 0, v)
    for z in (181.0, 249.0):                          # 4) umbral 0.008
        for io in (0, 1): corre("p4", z, io, objs, 0.011, 0, "b008")
    for z in ZS:                                      # 5) segunda semilla
        for io in (0, 1):
            for v in V: corre("p1", z, io, objs, 0.011, 1, v)


if __name__ == "__main__":
    main()

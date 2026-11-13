"""sim_robusto.py -- el rescate por pupila blanda, ¿sobrevive a un desajuste de modelo? (simulacion, 12/11)
Uso: python sim_robusto.py [limite_s]   Escribe runs.jsonl (una linea por corrida; se puede leer incompleto). Semilla fija 0.
Importa SIN modificar ../sim_borde_leds/sim_borde.py (solver, pupila del solver), ../sim_z/sim_z.py y ../sim_z_clave/sim_z_clave.py.
DATOS (borde distinto del que asume el solver; grilla 2x fina, centro sub-pixel, ruido HDR de sim_z):
  erf     erf w 0.011, NA 0.070 (control = crimen inverso de sim_borde_leds)
  lin     rampa lineal con el mismo ancho 10-90 % que erf w 0.011
  cola    0.7*erf(w 0.006) + 0.3*erf(w 0.030): nucleo angosto + halo ancho
  naXXX   erf w 0.011 con NA real 0.0XXX (el solver cree 0.070)
  elip    erf w 0.011, NA 0.070 en x y 0.068 en y
  led     erf w 0.011 + LED finito: suma incoherente de 3x3 puntos (+-0.07 mm, disco de ~0.2 mm)
SOLVER (ePIE 20 epocas, NA 0.070): a dura; b012 dura excluyendo margen < 0.012; c erf w 0.011 fijo;
  d erf con w barrido (0.006/0.011/0.016/0.022), se elige el de menor residuo en los LEDs de borde (un w global, no por LED).
"""
import json, os, sys, time
import numpy as np
from scipy import fft as sfft
from scipy.special import erf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_borde_leds"))
import sim_borde as B                                 # noqa: E402  (trae S y K)
S, K = B.S, B.K
T0 = time.time()
LIM = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
OUT = os.path.join(HERE, "runs.jsonl")
W0 = 0.011
OFF = (-0.07, 0.0, 0.07)                              # mm, puntos del LED finito


def perfil(tipo, fx, fy):
    """Pupila de los DATOS (64x64, centro sub-pixel)."""
    dx, dy = S.xx - fx, S.yy - fy
    s = W0 / B.NAPX
    e = lambda r, R, w: 0.5 * (1 - erf((r - R) / (w / B.NAPX)))
    r = np.hypot(dx, dy)
    if tipo in ("erf", "led"):
        p = e(r, S.R, W0)
    elif tipo == "lin":
        p = np.clip(0.5 - (r - S.R) / (2.265 * s), 0, 1)          # 10-90 % igual al de erf (1.812 s)
    elif tipo == "cola":
        p = 0.7 * e(r, S.R, 0.006) + 0.3 * e(r, S.R, 0.030)
    elif tipo.startswith("na"):
        p = e(r, S.R * int(tipo[2:]) / 70.0, W0)            # na067 -> 0.067
    elif tipo == "elip":
        p = e(np.hypot(dx, dy * 0.070 / 0.068), S.R, W0)
    return p.astype(np.float32)


def forward(spec, z, tipo):
    gs = [S.geom(z)]
    if tipo == "led":
        gs = [S.geom(z, {k: (a, b) for k in S.KEYS}) for a in OFF for b in OFF]
    out = {k: np.zeros((S.LR, S.LR), np.float32) for k in S.KEYS}
    for g in gs:
        for k in S.KEYS:
            wn, fx, fy = S.win(g, k, S.FINE)
            out[k] += (np.abs(sfft.ifft2(sfft.ifftshift(spec[wn] * perfil(tipo, fx, fy)))) ** 2 * S.LR ** 4 / len(gs)).astype(np.float32)
    return out


CACHE = {}
def corre(est, z, io, objs, tipo, var, ws=None, seed=0):
    if time.time() - T0 > LIM:
        print("limite de reloj"); sys.exit(0)
    g = S.geom(z)
    key = (z, io, tipo)
    if key not in CACHE:
        CACHE.clear()
        CACHE[key] = forward(objs[io][0], z, tipo)
    In, _ = S.add_noise(CACHE[key], g, z, np.random.default_rng(1000 + seed))
    keys, w = S.KEYS, None
    if var == "b012":
        keys = [k for k in S.KEYS if abs(S.ill_na(g, k) - S.NA) >= 0.012]
    elif var == "c": w = W0
    elif var == "d": w = ws
    o, cost = B.reconstruct(In, g, keys, w)
    _, truth, mask = objs[io]
    nbf, mg, _, _ = K.margen(z, S.NA)
    row = dict(est=est, z=z, obj=io, seed=seed, datos=tipo, var=var, ws=w, nbf=nbf, margen=mg, n_excl=len(S.KEYS) - len(keys),
               **S.metrics(o, truth, mask), **K.extra(o, truth), **cost, t=round(time.time() - T0, 1))
    with open(OUT, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(est, z, io, tipo, var, w, round(row["err"], 3), round(row["e_c23"], 3), round(row["ph_esf"], 3), row["t"], flush=True)


def main_na(objs):
    """Bloque de radio desajustado (se corrio aparte: `python sim_robusto.py 150 na`)."""
    for t in ("na067", "na073"):
        for v in ("c", "b012", "a"): corre("p1", 181.0, 0, objs, t, v)
    for t in ("na064", "na076"):
        for v in ("c", "b012"): corre("p4", 181.0, 0, objs, t, v)
    for z in (249.0, 168.0):
        for t in ("na067", "na073"):
            for v in ("c", "b012"): corre("p2", z, 0, objs, t, v)
    for t in ("na067", "na073"):
        for ws in (0.006, 0.016, 0.022): corre("d", 181.0, 0, objs, t, "d", ws)
    for t in ("na067", "na073"):
        for v in ("c", "b012"): corre("p6", 146.0, 0, objs, t, v)
    for t in ("na067", "na073"):
        for v in ("c", "b012"): corre("p1", 181.0, 1, objs, t, v)


def main():
    objs = [S.make_object(0), S.make_object(1)]
    if "na" in sys.argv[2:]:
        return main_na(objs)
    T = ["lin", "cola", "na067", "na073", "elip", "led"]
    for t in ["erf"] + T:                             # 1) z=181, obj 0: a, b, c
        for v in ("c", "b012", "a"): corre("p1", 181.0, 0, objs, t, v)
    for z in (249.0, 168.0):                          # 2) 25 BF y 9 BF a medias
        for t in T:
            for v in ("c", "b012"): corre("p2", z, 0, objs, t, v)
    for t in T:                                       # 3) variante d: barrido de w, z=181
        for ws in (0.006, 0.016, 0.022): corre("d", 181.0, 0, objs, t, "d", ws)
    for t in ("na064", "na076", "na060", "na080"):    # 4) tolerancia de radio
        for v in ("c", "b012"): corre("p4", 181.0, 0, objs, t, v)
    for t in T:                                       # 5) segundo objeto
        for v in ("c", "b012"): corre("p1", 181.0, 1, objs, t, v)
    for z in (146.0, 103.0):                          # 6) referencias
        for t in T:
            for v in ("c", "b012"): corre("p6", z, 0, objs, t, v)
    for z in (249.0, 168.0):                          # 7) segundo objeto en 249/168
        for t in T:
            for v in ("c", "b012"): corre("p2", z, 1, objs, t, v)


if __name__ == "__main__":
    main()

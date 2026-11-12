"""Tarea B: ¿importa el ORDEN de recorrido de los LEDs en el solver FPM secuencial?

Simulación autocontenida (no toca scripts/ ni src/). El lazo de actualización es una copia
de `reconstruct` de scripts/fpm_solver/fpm_red.py (rama no-EPRY: spec[win] += mu * P * D),
generalizada a (a) orden arbitrario por época, (b) lotes / mini-lotes, (c) paso por LED.

Uso:  python sim_orden.py            (corre todo, 2 procesos, escribe runs.jsonl + rec_*.npz)
"""
from __future__ import annotations

import json
import os
import sys
import time
from functools import lru_cache

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "runs.jsonl")

# ---- geometría (imitando la real: 15x15, z=102 mm, paso 6 mm, NA 0.07, 0.63 um, factor 3)
LAM, NA, LRPX, Z_MM, PITCH_MM, NLED = 0.63, 0.07, 1.28, 102.0, 6.0, 15
N_LR, FACTOR = 32, 3      # 32 px (no 64) por presupuesto de tiempo: 2 núcleos compartidos
N_HR = N_LR * FACTOR
HRPX = LRPX / FACTOR
DN, DIAM_UM = 0.046, 5.0
EPOCHS = 160
EVAL_EVERY = 10
EPOCHS_FIJO = 40                       # paso fijo mu=1: sólo 80 épocas (presupuesto)
SEEDS = [0, 1, 2]
R_PUP = NA / LAM * N_LR * LRPX          # radio de pupila en px de frecuencia (9.1)
BANDS = {"BF": (0.0, 1.0), "bajo": (1.0, 3.0), "medio": (3.0, 5.5), "alto": (5.5, 8.1)}  # en unidades de NA_obj

VARIANTS = ["anillo_crec", "anillo_decr", "aleat_epoca", "lote", "minilote15", "residuo_desc", "anillo_paso_decr",
            "snake", "entrelazado", "espiral", "azimut", "aleat_fijo", "residuo_asc", "paso_residuo", "minilote45"]
STEPS = ["rampa", "fijo1"]             # rampa: mu=0.3(1-exp(-0.3 it)) (solver real); fijo1: mu=1 (proyección completa)


def led_table():
    c = (NLED - 1) / 2
    leds = []
    for r in range(NLED):
        for q in range(NLED):
            x, y = (q - c) * PITCH_MM, (r - c) * PITCH_MM
            d = np.sqrt(x * x + y * y + Z_MM ** 2)
            sx, sy = int(round(x / d / LAM * N_LR * LRPX)), int(round(y / d / LAM * N_LR * LRPX))
            leds.append(dict(r=r, q=q, ring=float(np.hypot(r - c, q - c)), ang=float(np.arctan2(r - c, q - c)),
                             cheb=int(max(abs(r - c), abs(q - c))), sx=sx, sy=sy, bf=bool(np.hypot(x, y) / d < NA)))
    return leds


LEDS = led_table()
NL = len(LEDS)
_c = N_HR // 2 - N_LR // 2
WIN = [(slice(_c + L["sy"], _c + L["sy"] + N_LR), slice(_c + L["sx"], _c + L["sx"] + N_LR)) for L in LEDS]
_yy, _xx = np.mgrid[:N_LR, :N_LR] - N_LR // 2
PUP = (np.hypot(_xx, _yy) <= R_PUP).astype(float)
COV = np.zeros((N_HR, N_HR))
for _w in WIN:
    COV[_w] += PUP
_Y, _X = np.mgrid[:N_HR, :N_HR] - N_HR // 2
KR = np.hypot(_X, _Y) / R_PUP           # |k| en unidades de NA_obj/lambda
BMASK = {b: (KR > max(lo, 1e-9)) & (KR <= hi) & (COV > 0) for b, (lo, hi) in BANDS.items()}
UNION = (COV > 0) & (KR > 1e-9)


def base_orders(rng):
    idx = list(range(NL))
    ring = sorted(idx, key=lambda i: (LEDS[i]["ring"], LEDS[i]["r"], LEDS[i]["q"]))
    o = {"anillo_crec": ring, "anillo_decr": ring[::-1]}
    o["espiral"] = sorted(idx, key=lambda i: (LEDS[i]["cheb"], LEDS[i]["ang"]))
    o["azimut"] = sorted(idx, key=lambda i: (LEDS[i]["ang"], LEDS[i]["ring"]))
    o["snake"] = sorted(idx, key=lambda i: (LEDS[i]["r"], LEDS[i]["q"] if LEDS[i]["r"] % 2 == 0 else -LEDS[i]["q"]))
    inter, a, b = [], 0, NL - 1          # entrelazado: alterna el más interno (BF) y el más externo (DF) restantes
    while a <= b:
        inter.append(ring[a]); a += 1
        if a <= b:
            inter.append(ring[b]); b -= 1
    o["entrelazado"] = inter
    o["aleat_fijo"] = list(rng.permutation(NL))
    return o


@lru_cache(maxsize=4)
def make_data(seed):
    rng = np.random.default_rng(1000 + seed)
    R = DIAM_UM / 2 / HRPX
    centers = []
    while len(centers) < 4:
        c = rng.uniform(R + 6, N_HR - R - 6, 2)
        if all(np.hypot(*(c - d)) > 2.3 * R for d in centers):
            centers.append(c)
    y, x = np.mgrid[:N_HR, :N_HR]
    thick = np.zeros((N_HR, N_HR))
    for cy, cx in centers:
        thick += 2 * np.sqrt(np.clip(R ** 2 - (x - cx) ** 2 - (y - cy) ** 2, 0, None)) * HRPX
    truth = np.exp(1j * 2 * np.pi / LAM * DN * thick) * (1 - 0.02 * thick / DIAM_UM)
    spec = np.fft.fftshift(np.fft.fft2(truth))
    gain = 5000.0 / FACTOR ** 4          # e- por unidad de intensidad: BF ~5000 e-
    I = np.empty((NL, N_LR, N_LR))
    for i, w in enumerate(WIN):
        clean = np.abs(np.fft.ifft2(spec[w] * PUP)) ** 2
        g = gain * (1.0 if LEDS[i]["bf"] else 20.0)      # DF con exposición 20x (como en la captura real)
        I[i] = (rng.poisson(clean * g) + rng.normal(0, 2.0, clean.shape)) / g
    tgt = np.sqrt(np.clip(I, 0, None))
    T = spec * UNION
    return dict(truth=truth, spec=spec, T=T, tgt=tgt, centers=np.array(centers), R=R,
                ph_true=float(2 * np.pi / LAM * DN * DIAM_UM))


def full_cost(spec, tgt):
    num = 0.0
    for i, w in enumerate(WIN):
        num += float(np.sum((np.abs(np.fft.ifft2(spec[w] * PUP)) - tgt[i]) ** 2))
    return num / float(np.sum(tgt ** 2))


def metrics(spec, d):
    S, T = spec, d["T"]
    m = COV > 0
    c = np.vdot(S[m], d["spec"][m]) / np.vdot(S[m], S[m])
    out = {"err": float(np.linalg.norm((c * S - T)[UNION]) / np.linalg.norm(T[UNION]))}
    for b, bm in BMASK.items():
        a, t = S[bm], d["spec"][bm]
        out["frc_" + b] = float(np.abs(np.vdot(a, t)) / (np.linalg.norm(a) * np.linalg.norm(t) + 1e-30))
    obj = np.fft.ifft2(np.fft.ifftshift(S * (COV > 0)))
    bg = obj[np.abs(np.angle(d["truth"])) < 1e-6].mean()
    ph = []
    for cy, cx in d["centers"]:
        iy, ix = int(round(cy)), int(round(cx))
        ph.append(np.angle(obj[iy - 1:iy + 2, ix - 1:ix + 2].mean() * np.conj(bg)))
    out["fase"] = float(np.mean(ph))                      # verdad: d["ph_true"] = 2.29 rad
    out["cost"] = full_cost(S, d["tgt"])
    return out


def run(job):
    variant, stepmode, seed = job
    t0 = time.time()
    d = make_data(seed)
    tgt = d["tgt"]
    rng = np.random.default_rng(7000 + seed)
    orders = base_orders(rng)
    bf0 = orders["anillo_crec"][0]
    o0 = np.kron(tgt[bf0], np.ones((FACTOR, FACTOR))).astype(complex) / FACTOR ** 2   # init "kron17"
    spec = np.fft.fftshift(np.fft.fft2(o0))
    ringmax = max(L["ring"] for L in LEDS)
    res = np.ones(NL)
    tnorm = np.mean(tgt ** 2, axis=(1, 2))
    hist = []
    for it in range(EPOCHS if stepmode == 'rampa' else EPOCHS_FIJO):
        mu = 0.3 * (1.0 - np.exp(-0.3 * it)) if stepmode == "rampa" else 1.0
        mult = np.ones(NL)
        if variant in orders:
            order = orders[variant]
        elif variant == "aleat_epoca" or variant.startswith("minilote") or variant == "lote":
            order = list(rng.permutation(NL))
        elif variant == "residuo_desc":
            order = orders["anillo_crec"] if it == 0 else list(np.argsort(-res))
        elif variant == "residuo_asc":
            order = orders["anillo_crec"] if it == 0 else list(np.argsort(res))
        elif variant == "paso_residuo":
            order = orders["anillo_crec"]
            if it > 0:
                mult = np.clip(res / np.median(res), 0.5, 1.5)
        elif variant == "anillo_paso_decr":
            order = orders["anillo_crec"]
            mult = np.array([1.0 - 0.6 * L["ring"] / ringmax for L in LEDS])
        else:
            raise ValueError(variant)
        bs = NL if variant == "lote" else int(variant[8:]) if variant.startswith("minilote") else 1
        if bs == 1:                                   # secuencial in-place (igual que fpm_red.reconstruct)
            for k in order:
                w = WIN[k]
                ps = spec[w]
                A = np.fft.ifft2(ps * PUP)
                amp = np.abs(A)
                res[k] = np.mean((amp - tgt[k]) ** 2) / tnorm[k]
                D = np.fft.fft2(tgt[k] * A / np.maximum(amp, 1e-12) - A)
                spec[w] = ps + (mu * mult[k]) * PUP * D
        else:                                         # lote / mini-lote: suma de correcciones / cobertura del lote
            for s in range(0, NL, bs):
                G = np.zeros_like(spec)
                C = np.zeros((N_HR, N_HR))
                for k in order[s:s + bs]:
                    w = WIN[k]
                    A = np.fft.ifft2(spec[w] * PUP)
                    amp = np.abs(A)
                    res[k] = np.mean((amp - tgt[k]) ** 2) / tnorm[k]
                    G[w] += PUP * np.fft.fft2(tgt[k] * A / np.maximum(amp, 1e-12) - A)
                    C[w] += PUP
                spec += mu * G / np.maximum(C, 1.0)
        ep = it + 1
        if ep % EVAL_EVERY == 0 or ep in (1, 2):
            m = metrics(spec, d)
            m["ep"] = ep
            hist.append(m)
    if stepmode == "rampa":
        np.savez_compressed(os.path.join(HERE, "rec", f"rec_{variant}_s{seed}.npz"), spec=spec.astype(np.complex64))
    return dict(variant=variant, step=stepmode, seed=seed, hist=hist, secs=time.time() - t0,
                cost_truth=full_cost(d["spec"], tgt))


if __name__ == "__main__":
    from multiprocessing import Pool
    os.makedirs(os.path.join(HERE, "rec"), exist_ok=True)
    only = sys.argv[1:]
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            r = json.loads(line)
            done.add((r["variant"], r["step"], r["seed"]))
    # Plan reducido por presupuesto de tiempo (~45 s por corrida de 160 épocas en esta máquina): ver INFORME.md
    plan = [(v, "rampa", s) for v in ("anillo_crec",) for s in SEEDS]
    plan += [(v, "rampa", s) for v in ("anillo_decr", "aleat_epoca", "lote", "minilote15", "residuo_desc",
                                       "anillo_paso_decr", "snake") for s in (0, 1)]
    plan += [(v, "fijo1", s) for v in ("anillo_crec", "anillo_decr", "aleat_epoca", "lote", "residuo_desc") for s in (0, 1)]
    plan += [(v, st, s) for st in STEPS for v in VARIANTS for s in SEEDS]      # resto, si alcanza el tiempo
    jobs = []
    for j in plan:
        if j not in done and j not in jobs and (not only or j[1] in only):
            jobs.append(j)
    print(len(jobs), "jobs", flush=True)
    with Pool(2) as pool:
        for r in pool.imap_unordered(run, jobs, chunksize=1):
            with open(OUT, "a") as f:
                f.write(json.dumps(r) + "\n")
            print(r["variant"], r["step"], r["seed"], f"{r['secs']:.1f}s", r["hist"][-1], flush=True)

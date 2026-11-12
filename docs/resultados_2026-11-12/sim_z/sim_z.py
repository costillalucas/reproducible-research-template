"""sim_z.py -- barrido de z de la matriz 15x15 en FPM (simulacion, 12/11).
Uso: python sim_z.py [e1] [e2a] [e3] [e2b]   (sin argumentos corre todo). Escribe runs.jsonl (una linea por corrida).

Sin crimen inverso: los datos se generan con (a) objeto en grilla 2x mas fina (0.16 um) que la HR del solver,
(b) pupila con borde suave erf y (c) centro de pupila sub-pixel exacto; el solver usa pupila dura y ventana entera.
Solver: nucleo ePIE de scripts/fpm_solver/fpm_red.py (step 0.3 con rampa, orden por NA creciente, init kron).
Geometria: 15x15, pitch 6 mm, NA 0.07, lambda 0.63 um, LR 1.28 um/px, LR 64 px, factor 4 (HR 256; con factor 3
el espectro HR no contiene las esquinas de la matriz a z = 80 mm).
"""
import json, os, sys, time
import numpy as np
from scipy import fft as sfft
from scipy.special import erf

HERE = os.path.dirname(os.path.abspath(__file__))
LAM, NA, LRPX, F, PITCH = 0.63, 0.07, 1.28, 4, 6.0
LR = 64; HR = LR * F; FINE = 2 * HR
DK = 1.0 / (LR * LRPX)
R = NA / LAM / DK                                  # radio de pupila en px (9.1)
KEYS = [(i, j) for i in range(-7, 8) for j in range(-7, 8)]
ITS, STEP = 20, 0.3
ZS = [80.0, 102.0, 120.0, 135.0, 150.0, 180.0]
EXPOS = [20.0, 111.0, 403.0, 1025.0]               # ms (HDR real)
FW, READ, Z0 = 30000.0, 3.0, 102.0
R0 = 0.5 * FW / 20.0                               # e-/px/ms para I=1 con el LED central a z=102 (BF a media escala en 20 ms)
yy, xx = (np.mgrid[:LR, :LR] - LR // 2).astype(np.float32)
T0 = time.time()
C = np.complex64


def geom(z, jit=None):
    """k -> (fx, fy [cyc/um], cos incidencia). jit: dict k -> (dx, dy) en mm."""
    g = {}
    for k in KEYS:
        dx, dy = (0.0, 0.0) if jit is None else jit[k]
        x, y = k[1] * PITCH + dx, k[0] * PITCH + dy
        d = np.sqrt(x * x + y * y + z * z)
        g[k] = (x / d / LAM, y / d / LAM, z / d)
    return g


def ill_na(g, k):
    return float(np.hypot(g[k][0], g[k][1]) * LAM)


def win(g, k, n):
    px, py = g[k][0] / DK, g[k][1] / DK
    ix, iy = int(round(px)), int(round(py))
    cx, cy = n // 2 + ix, n // 2 + iy
    return (slice(cy - LR // 2, cy + LR // 2), slice(cx - LR // 2, cx + LR // 2)), px - ix, py - iy


def make_object(kind):
    """Esferas de 5 um (dn 0.046 -> 2.3 rad) en grilla fina. kind 0: 8 separadas; kind 1: 16 densas (se tocan)."""
    rng = np.random.default_rng(100 + kind)
    px = LRPX / F / 2
    Y, X = np.mgrid[:FINE, :FINE] * px
    n, dmin = ((8, 8.0), (16, 5.05))[kind]
    cs = []
    while len(cs) < n:
        c = rng.uniform(6, FINE * px - 6, 2)
        if all(np.hypot(*(c - o)) > dmin for o in cs):
            cs.append(c)
    thick = np.zeros((FINE, FINE)); mask = np.zeros((FINE, FINE), bool)
    for c in cs:
        r2 = (X - c[0]) ** 2 + (Y - c[1]) ** 2
        thick = np.maximum(thick, 2 * np.sqrt(np.clip(2.5 ** 2 - r2, 0, None)))
        mask |= r2 < 2.3 ** 2
    obj = np.exp(-0.03 * thick) * np.exp(1j * 2 * np.pi / LAM * 0.046 * thick)
    spec = sfft.fftshift(sfft.fft2(obj.astype(C))) / FINE ** 2
    a = FINE // 2 - HR // 2
    truth = sfft.ifft2(sfft.ifftshift(spec[a:a + HR, a:a + HR])) * HR ** 2      # verdad limitada en banda a la grilla HR
    return spec, truth.astype(C), mask[::2, ::2]


def forward(spec, g):
    """Modelo fino: pupila erf centrada sub-pixel. Devuelve intensidades LR (I=1 para campo plano en BF)."""
    out = {}
    for k in KEYS:
        w, fx, fy = win(g, k, FINE)
        P = 0.5 * (1 - erf((np.hypot(xx - fx, yy - fy) - R) / 0.7))
        out[k] = (np.abs(sfft.ifft2(sfft.ifftshift(spec[w] * P.astype(np.float32)))) ** 2 * LR ** 4).astype(np.float32)
    return out


def add_noise(I, g, z, rng):
    """Poisson + lectura con HDR simplificado: por LED, la exposicion mas larga de EXPOS que no satura.
    Irradiancia del LED en la muestra ~ cos^3(theta) / z^2 (1/r^2 e incidencia oblicua)."""
    out, ts = {}, {}
    for k in KEYS:
        rate = R0 * (Z0 / z) ** 2 * g[k][2] ** 3
        t = EXPOS[0]
        for e in EXPOS:
            if I[k].max() * rate * e <= FW:
                t = e
        cnt = np.clip(rng.poisson(I[k] * rate * t) + rng.normal(0, READ, I[k].shape), None, FW)
        out[k] = (cnt / (rate * t)).astype(np.float32); ts[k] = t
    return out, ts


def reconstruct(I, g, keys, its=ITS, step=STEP):
    od = sorted(keys, key=lambda k: (ill_na(g, k), k))
    amp0 = np.sqrt(np.clip(I[od[0]], 0, None))
    spec = (sfft.fftshift(sfft.fft2(np.kron(amp0, np.ones((F, F), np.float32)).astype(C))) / F ** 2).astype(C)
    W, P, tg = {}, {}, {}
    for k in od:
        w, fx, fy = win(g, k, HR)
        W[k] = w; P[k] = (np.hypot(xx - fx, yy - fy) <= R).astype(np.float32)
        tg[k] = np.sqrt(np.clip(I[k], 0, None))
    for it in range(its):
        mu = np.float32(step * (1.0 - np.exp(-0.3 * it)))
        for k in od:
            w = W[k]; ps = spec[w]
            A = sfft.ifft2(sfft.ifftshift(ps * P[k]))
            D = sfft.fftshift(sfft.fft2(tg[k] * A / np.maximum(np.abs(A), 1e-12) - A))
            spec[w] = ps + mu * P[k] * D
    return sfft.ifft2(sfft.ifftshift(spec))


fy_, fx_ = np.mgrid[:HR, :HR] - HR // 2
KR = np.hypot(fx_, fy_) * DK * LAM                 # radio espectral en NA (absoluto, comun a todos los z)
EDGES = [0.0, NA, 0.2, 0.35, 0.5]
BANDS = ["BF", "bajo", "medio", "alto"]


def metrics(o, t, mask):
    c = np.vdot(o, t) / np.vdot(o, o)
    oc = o * c; d = oc - t
    m = {"err": float(np.linalg.norm(d) / np.linalg.norm(t))}
    Fd, Ft, Fo = (sfft.fftshift(sfft.fft2(a - a.mean())) for a in (d, t, oc))
    sel = [(b, (KR >= lo) & (KR < hi)) for b, lo, hi in zip(BANDS, EDGES[:-1], EDGES[1:])] + [("comun", KR < 0.30)]
    for b, s in sel:
        m["e_" + b] = float(np.sqrt(np.sum(np.abs(Fd[s]) ** 2) / np.sum(np.abs(Ft[s]) ** 2)))
        m["frc_" + b] = float(np.abs(np.sum(Fo[s] * np.conj(Ft[s]))) /
                              np.sqrt(np.sum(np.abs(Fo[s]) ** 2) * np.sum(np.abs(Ft[s]) ** 2)))
    m["ph_esf"] = float(np.sqrt(np.mean(np.angle(oc[mask] * np.conj(t[mask])) ** 2)))
    return m


def overlap(d):
    """Fraccion de area comun de dos discos de radio NA con centros a distancia d (en NA)."""
    if d >= 2 * NA:
        return 0.0
    return float((2 * NA * NA * np.arccos(d / (2 * NA)) - d / 2 * np.sqrt(4 * NA * NA - d * d)) / (np.pi * NA * NA))


def geo_table(z):
    g = geom(z)
    nas = {k: ill_na(g, k) for k in KEYS}
    ov = []
    for k in KEYS:
        for dk in ((0, 1), (1, 0)):
            q = (k[0] + dk[0], k[1] + dk[1])
            if q in g:
                ov.append(overlap(np.hypot(g[k][0] - g[q][0], g[k][1] - g[q][1]) * LAM))
    return dict(z=z, n_BF=sum(v < NA for v in nas.values()), n_DF=sum(v >= NA for v in nas.values()),
                ov_centro=100 * overlap(ill_na(g, (0, 1))), ov_medio=100 * float(np.mean(ov)), ov_min=100 * float(np.min(ov)),
                NA_syn_esq=NA + max(nas.values()), NA_syn_eje=NA + nas[(0, 7)],
                rel_irr_esq=float((Z0 / z) ** 2 * g[(7, 7)][2] ** 3), rel_irr_centro=float((Z0 / z) ** 2))


def log(row):
    row["t"] = round(time.time() - T0, 1)
    with open(os.path.join(HERE, "runs.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    print(row["est"], row.get("z"), row.get("var"), row.get("dz"), row.get("nbf"), round(row["err"], 4), row["t"], flush=True)


def main():
    todo = sys.argv[1:] or ["e1", "e2a", "e3", "e2b"]
    objs = [make_object(0), make_object(1)]
    with open(os.path.join(HERE, "geometria.json"), "w") as f:
        json.dump([geo_table(z) for z in ZS], f, indent=1)
    if "e1" in todo:      # ---- Estudio 1: barrido de z, sin y con ruido
        for z in ZS:
            g = geom(z)
            for io, (spec, truth, mask) in enumerate(objs):
                I = forward(spec, g)
                log(dict(est="e1", z=z, obj=io, var="limpio", seed=-1, **metrics(reconstruct(I, g, KEYS), truth, mask)))
                for s in range(3):
                    In, ts = add_noise(I, g, z, np.random.default_rng(1000 + s))
                    log(dict(est="e1", z=z, obj=io, var="ruido", seed=s, t_medio=float(np.mean(list(ts.values()))),
                             n_1025=int(sum(t == 1025.0 for t in ts.values())),
                             **metrics(reconstruct(In, g, KEYS), truth, mask)))
    def e2(dzs):          # ---- Estudio 2: z real = z nominal + dz, jitter 0.2 mm rms; reconstruccion con geometria nominal
        for dz in dzs:
            for z in [102.0, 135.0, 180.0]:
                gn = geom(z)
                for s in range(3):
                    rj = np.random.default_rng(2000 + s)
                    jit = {k: tuple(rj.normal(0, 0.2, 2)) for k in KEYS}
                    gt = geom(z + dz, jit)
                    for io, (spec, truth, mask) in enumerate(objs):
                        In, _ = add_noise(forward(spec, gt), gt, z + dz, np.random.default_rng(3000 + s))
                        log(dict(est="e2", z=z, dz=dz, obj=io, seed=s, **metrics(reconstruct(In, gn, KEYS), truth, mask)))

    def e3():             # ---- Estudio 3: numero de LEDs BF (los mas centrales) manteniendo todo el DF, z = 135 (9 BF)
        z = 135.0; g = geom(z)
        bf = sorted([k for k in KEYS if ill_na(g, k) < NA], key=lambda k: (ill_na(g, k), k))
        df = [k for k in KEYS if ill_na(g, k) >= NA]
        for s in range(3):
            for io, (spec, truth, mask) in enumerate(objs):
                In, _ = add_noise(forward(spec, g), g, z, np.random.default_rng(1000 + s))
                for n in [0, 1, 5, 9]:
                    log(dict(est="e3", z=z, nbf=n, obj=io, seed=s, **metrics(reconstruct(In, g, bf[:n] + df), truth, mask)))

    def e1x():            # ---- Estudio 1 bis: sin ruido, excluyendo los LEDs en el borde BF/DF (|NA_ilum - NA| < 0.012)
        for z in ZS:
            g = geom(z)
            keys = [k for k in KEYS if abs(ill_na(g, k) - NA) >= 0.012]
            for io, (spec, truth, mask) in enumerate(objs):
                log(dict(est="e1x", z=z, obj=io, var="limpio_sin_borde", seed=-1, n_excl=len(KEYS) - len(keys),
                         **metrics(reconstruct(forward(spec, g), g, keys), truth, mask)))

    for name in todo:     # orden por prioridad (presupuesto de reloj): e2a (dz 0, +-5), e3, e2b (dz +-2)
        if name == "e2a": e2([0.0, 5.0, -5.0])
        if name == "e3": e3()
        if name == "e2b": e2([2.0, -2.0])
        if name == "e1x": e1x()

if __name__ == "__main__":
    main()

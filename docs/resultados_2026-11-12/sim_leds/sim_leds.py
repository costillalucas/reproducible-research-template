"""sim_leds.py -- contribucion por LED en FPM (simulacion, 12/11).  Uso: python sim_leds.py
Autocontenido (numpy + matplotlib). El solver es una copia del nucleo de scripts/fpm_solver/fpm_red.py::reconstruct
(ePIE forma step_relative, step 0.3 con rampa 1-exp(-0.3 it), orden por anillo creciente, init kron del LED central),
pero acepta subconjuntos de LEDs. Geometria: 15x15, pitch 6 mm, z 102 mm, NA 0.07, lambda 0.63 um, LR 1.28 um/px, factor 3.
Semilla fija. Guarda resultados parciales en results.json a medida que salen.
"""
import json, os, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20261112
LAM, NA, LRPX, F, Z, PITCH, NLED = 0.63, 0.07, 1.28, 3, 102.0, 6.0, 15
LR, HR = 80, 240
HRPX = LRPX / F
ITS, STEP = 20, 0.3
DK = 1.0 / (LR * LRPX)                       # cyc/um por pixel de espectro (igual en LR y HR)
KEYS = [(i, j) for i in range(-7, 8) for j in range(-7, 8)]
T0 = time.time()


def led_shift(k):
    x, y = k[1] * PITCH, k[0] * PITCH
    d = np.sqrt(x * x + y * y + Z * Z)
    return x / d / LAM, y / d / LAM          # fx, fy (cyc/um)


def illum_na(k):
    fx, fy = led_shift(k)
    return float(np.hypot(fx, fy) * LAM)


NA_SYN = NA + max(illum_na(k) for k in KEYS)
yy, xx = np.mgrid[:LR, :LR] - LR // 2
PUP = (np.hypot(xx, yy) * DK <= NA / LAM).astype(float)
WIN = {}
for k in KEYS:
    fx, fy = led_shift(k)
    cx, cy = HR // 2 + int(round(fx / DK)), HR // 2 + int(round(fy / DK))
    WIN[k] = (slice(cy - LR // 2, cy + LR // 2), slice(cx - LR // 2, cx + LR // 2))
BF = [k for k in KEYS if illum_na(k) < NA]
BASE = [(i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)]       # BF (cruz de 5) + resto del anillo 1 (3x3)
ring = lambda k: float(np.hypot(*k))
order = lambda keys: sorted(keys, key=lambda k: (ring(k), k))


def make_object(rng):
    """Esferas de 5 um (dn = 0.046 -> 2.3 rad en el centro) con absorcion debil, sobre fondo plano."""
    Y, X = np.mgrid[:HR, :HR] * HRPX
    thick = np.zeros((HR, HR)); mask = np.zeros((HR, HR), bool)
    cs = []
    while len(cs) < 14:
        c = rng.uniform(6, HR * HRPX - 6, 2)
        if all(np.hypot(*(c - o)) > 5.6 for o in cs):
            cs.append(c)
    for c in cs:
        r2 = (X - c[0]) ** 2 + (Y - c[1]) ** 2
        thick = np.maximum(thick, 2 * np.sqrt(np.clip(2.5 ** 2 - r2, 0, None)))
        mask |= r2 < 2.5 ** 2
    ph = 2 * np.pi / LAM * 0.046 * thick
    amp = np.exp(-0.03 * thick)
    return amp * np.exp(1j * ph), mask


def forward(obj, keys):
    spec = np.fft.fftshift(np.fft.fft2(obj))
    return {k: np.abs(np.fft.ifft2(np.fft.ifftshift(spec[WIN[k]] * PUP))) ** 2 for k in keys}


def add_noise(I, rng, n0=3000.0, t_df=30.0, read=2.0):
    """Poisson + lectura. n0 fotones/px para I = <I_BF central>; DF con 30x de exposicion (como la captura real)."""
    ref = I[(0, 0)].mean()
    out = {}
    for k in KEYS:
        g = n0 / ref * (1.0 if k in BF else t_df)
        out[k] = (rng.poisson(I[k] * g) + rng.normal(0, read, I[k].shape)) / g
    return out


def reconstruct(I, keys, its=ITS, step=STEP):
    amp0 = np.sqrt(np.clip(I[(0, 0)], 0, None))
    o0 = np.kron(amp0, np.ones((F, F))).astype(complex) / F ** 2
    spec = np.fft.fftshift(np.fft.fft2(o0))
    od = order(keys)
    tg = {k: np.sqrt(np.clip(I[k], 0, None)) for k in od}
    for it in range(its):
        mu = step * (1.0 - np.exp(-0.3 * it))
        for k in od:
            w = WIN[k]
            ps = spec[w]
            A = np.fft.ifft2(np.fft.ifftshift(ps * PUP))
            amp = np.abs(A)
            D = np.fft.fftshift(np.fft.fft2(tg[k] * A / np.maximum(amp, 1e-12) - A))
            spec[w] = ps + mu * PUP * D
    return np.fft.ifft2(np.fft.ifftshift(spec))


fy_, fx_ = np.mgrid[:HR, :HR] - HR // 2
KR = np.hypot(fx_, fy_) * DK * LAM            # radio espectral en unidades de NA
EDGES = [0.0, NA, 0.2, 0.35, 0.45, KR.max() + 1e-9]   # "alto" = 0.35-0.45: cubierto en todo azimut (borde en eje llega a 0.45); "fuera" = esquinas + sin cubrir
BANDS = ["BF", "bajo", "medio", "alto", "fuera"]


def metrics(o, t, mask):
    c = np.vdot(o, t) / np.vdot(o, o)         # escalar complejo optimo (fase global + escala)
    oc = o * c
    d = oc - t
    m = {"err": float(np.linalg.norm(d) / np.linalg.norm(t))}
    Fd, Ft, Fo = (np.fft.fftshift(np.fft.fft2(a - a.mean())) for a in (d, t, oc))
    for b, lo, hi in zip(BANDS, EDGES[:-1], EDGES[1:]):
        s = (KR >= lo) & (KR < hi)
        m["e_" + b] = float(np.sqrt(np.sum(np.abs(Fd[s]) ** 2) / np.sum(np.abs(Ft[s]) ** 2)))
        m["frc_" + b] = float(np.abs(np.sum(Fo[s] * np.conj(Ft[s]))) /
                              np.sqrt(np.sum(np.abs(Fo[s]) ** 2) * np.sum(np.abs(Ft[s]) ** 2)))
    m["ph_esf"] = float(np.sqrt(np.mean(np.angle(oc[mask] * np.conj(t[mask])) ** 2)))
    return m


RES = {}
def save():
    RES["elapsed_s"] = time.time() - T0
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(RES, f, indent=1)


def octant(k):
    a, b = sorted((abs(k[0]), abs(k[1])))
    return (a, b)


def overlap_pct(k):
    """Solapamiento medio (% del area de pupila) con los 4 vecinos mas cercanos, con centros redondeados."""
    R = NA / LAM / DK
    c = lambda q: np.array([WIN[q][0].start, WIN[q][1].start], float)
    out = []
    for dk in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        q = (k[0] + dk[0], k[1] + dk[1])
        if q in WIN:
            d = np.hypot(*(c(k) - c(q)))
            out.append(0.0 if d >= 2 * R else (2 * R * R * np.arccos(d / (2 * R)) - d / 2 * np.sqrt(4 * R * R - d * d)) / (np.pi * R * R))
    return 100 * float(np.mean(out))


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    rng = np.random.default_rng(SEED)
    truth, mask = make_object(rng)
    Iclean = forward(truth, KEYS)
    I = add_noise(Iclean, rng)
    RES["setup"] = dict(LR=LR, HR=HR, its=ITS, step=STEP, NA_syn=NA_SYN, n_BF=len(BF), seed=SEED,
                        pupil_radius_px=NA / LAM / DK, bands_NA=EDGES)
    # ---- 2. linea base
    rec_clean = reconstruct(Iclean, KEYS)
    rec = reconstruct(I, KEYS)
    RES["base_clean"] = metrics(rec_clean, truth, mask)
    RES["base_noise"] = base = metrics(rec, truth, mask)
    RES["solo_3x3"] = metrics(reconstruct(I, BASE), truth, mask)
    save(); print("base", base, time.time() - T0, flush=True)
    np.savez_compressed(os.path.join(HERE, "objetos.npz"), truth=truth, rec=rec, rec_clean=rec_clean)

    # ---- 5. predictores analiticos (sin reconstruir N veces; usan solo la reconstruccion base, no la verdad)
    cov = np.zeros((HR, HR))
    for k in KEYS:
        cov[WIN[k]] += PUP
    S2 = np.abs(np.fft.fftshift(np.fft.fft2(rec))) ** 2
    pred = {}
    for k in KEYS:
        w = WIN[k]; m = PUP > 0
        A = np.fft.ifft2(np.fft.ifftshift(np.fft.fftshift(np.fft.fft2(rec))[w] * PUP))
        Dk = np.fft.fft2(np.sqrt(np.clip(I[k], 0, None)) * A / np.maximum(np.abs(A), 1e-12) - A)
        pred[k] = dict(geo=float(np.sum(1.0 / cov[w][m])),                    # fraccion de cobertura exclusiva
                       fisher=float(np.sum(S2[w][m] / cov[w][m])),            # energia espectral / redundancia
                       fisher_excl=float(np.sum(S2[w][m] * (cov[w][m] == 1))),  # energia en pixeles que SOLO ve k
                       grad=float(np.linalg.norm(Dk)),                        # norma del gradiente de Wirtinger en la solucion
                       overlap=overlap_pct(k), na=illum_na(k))
    RES["pred"] = {str(k): v for k, v in pred.items()}
    RES["cobertura"] = dict(min_dentro=float(cov[KR < NA_SYN - NA].min()), max=float(cov.max()),
                            frac_px_cubiertos_1vez=float(np.mean(cov[cov > 0] == 1)))
    save()

    # ---- 3. contribucion por LED en el octante: (i) leave-one-out, (ii) agregar a la base 3x3
    octs = sorted({octant(k) for k in KEYS})
    loo, add = {}, {}
    b3 = RES["solo_3x3"]
    for q in octs:
        if q != (0, 0):
            m = metrics(reconstruct(I, [k for k in KEYS if k != q]), truth, mask)
            loo[q] = {n: m[n] - base[n] for n in m}
        if q not in BASE:
            m = metrics(reconstruct(I, BASE + [q]), truth, mask)
            add[q] = {n: m[n] - b3[n] for n in m}
        RES["loo"] = {str(k): v for k, v in loo.items()}; RES["add"] = {str(k): v for k, v in add.items()}
    save(); print("loo/add listo", time.time() - T0, flush=True)
    # verificacion de simetria: LOO de imagenes especulares de 3 LEDs
    sym = {}
    for q in [(2, 5), (4, 7), (1, 3)]:
        for q2 in [(q[1], q[0]), (q[0], -q[1])]:
            m = metrics(reconstruct(I, [k for k in KEYS if k != q2]), truth, mask)
            sym[str(q2)] = dict(rep=str(q), d_err=m["err"] - base["err"], d_err_rep=loo[q]["err"],
                                d_alto=m["e_alto"] - base["e_alto"], d_alto_rep=loo[q]["e_alto"])
    RES["simetria"] = sym; save()

    # ---- 4. curva calidad vs numero de LEDs
    rest = [k for k in KEYS if k not in BASE]
    score = lambda k: loo[octant(k)]["err"]
    rankings = {
        "medido_LOO": sorted(rest, key=lambda k: -score(k)),
        "fisher": sorted(rest, key=lambda k: -pred[k]["fisher"]),
        "anillo_dentro_fuera": order(rest),
        "anillo_fuera_dentro": order(rest)[::-1],
    }
    for s in range(2):
        r = np.random.default_rng(SEED + 1 + s)
        rankings[f"azar{s}"] = [rest[i] for i in r.permutation(len(rest))]
    NS = [9, 49, 81, 113, 149, 225]
    curve = {}
    for name, rk in rankings.items():
        curve[name] = []
        for n in NS:
            if n == 225:
                m = base
            elif n == 9:
                m = b3
            else:
                m = metrics(reconstruct(I, BASE + rk[:n - 9]), truth, mask)
            curve[name].append(dict(n=n, **m))
        RES["curva"] = curve; save(); print("curva", name, time.time() - T0, flush=True)
    dam = [k for k in KEYS if (k[0] + k[1]) % 2 == 0 or k in BASE]
    RES["damero"] = dict(n=len(dam), **metrics(reconstruct(I, dam), truth, mask))
    # eliminacion hacia atras por grupos de simetria (greedy real, barato): quitar de a un grupo el de menor dano
    save()
    plots(truth, rec, loo, add, pred, curve, NS, base)
    save()


def to_map(d, name):
    M = np.full((NLED, NLED), np.nan)
    for k in KEYS:
        q = octant(k)
        if q in d:
            M[k[0] + 7, k[1] + 7] = d[q][name]
    return M


def plots(truth, rec, loo, add, pred, curve, NS, base):
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
    c = np.vdot(rec, truth) / np.vdot(rec, rec)
    for a, im, t in zip(ax, [np.angle(truth), np.angle(rec * c), np.angle(rec * c * np.conj(truth))],
                        ["fase verdad (rad)", "fase reconstruida, 225 LEDs", "error de fase (rad)"]):
        h = a.imshow(im, cmap="twilight" if "error" not in t else "RdBu", vmin=-np.pi if "error" not in t else -1,
                     vmax=np.pi if "error" not in t else 1); a.set_title(t); a.axis("off"); plt.colorbar(h, ax=a, fraction=0.046)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig1_objeto.png"), dpi=110); plt.close(fig)

    for d, tag, ttl in [(loo, "fig2_loo", "Leave-one-out: metrica(sin LED k) - metrica(225)"),
                        (add, "fig3_add", "Agregar LED k a la base 3x3: metrica(base+k) - metrica(base)")]:
        fig, ax = plt.subplots(1, 5, figsize=(21, 4.2))
        for a, n in zip(ax, ["err", "e_BF", "e_bajo", "e_alto", "frc_alto"]):
            M = to_map(d, n) * 100
            v = np.nanmax(np.abs(M))
            h = a.imshow(M, cmap="RdBu_r", vmin=-v, vmax=v); a.set_title(f"100 x delta {n}")
            a.set_xlabel("columna LED"); a.set_ylabel("fila LED"); plt.colorbar(h, ax=a, fraction=0.046)
        fig.suptitle(ttl + "  (rojo = sube; para err: quitar empeora / agregar empeora)")
        fig.tight_layout(); fig.savefig(os.path.join(HERE, tag + ".png"), dpi=110); plt.close(fig)

    fig, ax = plt.subplots(1, 4, figsize=(19, 4.4))
    for a, n in zip(ax, ["err", "e_bajo", "e_alto", "ph_esf"]):
        for name, pts in curve.items():
            if name.startswith("azar"):
                continue
            a.plot(NS, [p[n] for p in pts], "o-", label=name)
        az = np.array([[p[n] for p in curve[f"azar{s}"]] for s in range(2)])
        a.errorbar(NS, az.mean(0), yerr=az.std(0), fmt="s--", color="gray", label="azar (2 semillas)")
        a.axhline(base[n], color="k", lw=0.6); a.set_xlabel("numero de LEDs"); a.set_title(n); a.set_yscale("log")
    ax[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig4_curva.png"), dpi=110); plt.close(fig)

    qs = sorted(loo)
    y = np.array([loo[q]["err"] for q in qs])
    fig, ax = plt.subplots(1, 5, figsize=(22, 4.2))
    cor = {}
    for a, n in zip(ax, ["geo", "fisher", "fisher_excl", "grad", "overlap"]):
        x = np.array([pred[q][n] for q in qs])
        cor[n] = dict(spearman_err=spearman(x, y), spearman_alto=spearman(x, np.array([loo[q]["e_alto"] for q in qs])),
                      spearman_bajo=spearman(x, np.array([loo[q]["e_bajo"] for q in qs])),
                      pearson_err=float(np.corrcoef(x, y)[0, 1]))
        s = a.scatter(x, y * 100, c=[pred[q]["na"] for q in qs], cmap="viridis")
        a.set_xlabel(n); a.set_ylabel("100 x delta err LOO"); a.set_title(f"{n}: Spearman {cor[n]['spearman_err']:.2f}")
        if n in ("fisher", "fisher_excl", "geo"):
            a.set_xscale("symlog", linthresh=max(np.min(x[x > 0]) if np.any(x > 0) else 1, 1e-9))
    plt.colorbar(s, ax=ax[-1], label="NA de iluminacion")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig5_prediccion.png"), dpi=110); plt.close(fig)
    RES["correlacion_predictores_vs_LOO"] = cor
    print(json.dumps(cor, indent=1))


if __name__ == "__main__":
    main()
    print("total", time.time() - T0)

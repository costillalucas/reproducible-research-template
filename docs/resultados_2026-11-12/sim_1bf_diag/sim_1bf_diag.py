"""sim_1bf_diag.py -- por que no converge la fase con 1 solo LED BF, y que solver/prior lo rescata (simulacion, 12/11).
Uso: python sim_1bf_diag.py            (corre todo; semillas fijas; escribe runs.jsonl, fig1_mapas.png, fig2_variantes.png)
Reutiliza SIN modificar ../sim_z/sim_z.py, ../sim_z_clave/sim_z_clave.py y ../sim_z_1bf/sim_z_1bf.py (mismos datos:
modelo directo sin crimen inverso, ruido Poisson + lectura, exposicion extra de 5 ms). Un proceso, complex64, LR 64.
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("sim_z", "sim_z_clave", "sim_z_1bf"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import sim_z as S                                     # noqa: E402
import sim_z_clave as K                               # noqa: E402
import sim_z_1bf as B                                 # noqa: E402  (agrega la exposicion de 5 ms a S.EXPOS)
from scipy import fft as sfft                         # noqa: E402

C = np.complex64
T0 = time.time()
F, HR, LR = S.F, S.HR, S.LR
DISC = S.KR < S.NA                                    # disco del BF central en el espectro HR
DC = np.zeros((HR, HR), bool); DC[HR // 2, HR // 2] = True


def f2(o):
    return sfft.fftshift(sfft.fft2(o))


def if2(s):
    return sfft.ifft2(sfft.ifftshift(s))


def solve(I, g, keys, spec0=None, its=20, step=0.3, ramp=True, cost="amp", batch=False, unit=0.0, unit_its=None):
    """ePIE secuencial (cost amp / int / poisson) o gradiente por lotes con paso adaptativo e inercia (batch=True).
    unit: fuerza del prior de fase pura |o| = cte (mezcla con la proyeccion o/|o| al final de cada epoca)."""
    od = sorted(keys, key=lambda k: (S.ill_na(g, k), k))
    W, P, tg, II = {}, {}, {}, {}
    N = np.zeros((HR, HR), np.float32)
    for k in od:
        w, fx, fy = S.win(g, k, HR)
        W[k] = w; P[k] = (np.hypot(S.xx - fx, S.yy - fy) <= S.R).astype(np.float32)
        II[k] = np.clip(I[k], 0, None); tg[k] = np.sqrt(II[k])
    for k in set(od):
        N[W[k]] += P[k]
    sup = N > 0
    if spec0 is None:
        spec = (f2(np.kron(tg[od[0]], np.ones((F, F), np.float32)).astype(C)) / F ** 2).astype(C)
    else:
        spec = spec0.astype(C).copy()

    def upd(A, k):
        a2 = np.abs(A) ** 2
        if cost == "amp":
            return tg[k] * A / np.maximum(np.abs(A), 1e-12) - A
        if cost == "int":                              # gradiente del costo gaussiano en intensidad, normalizado
            return (II[k] - a2) * A / (2 * max(float(II[k].max()), float(a2.max()), 1e-20))
        return (np.clip(II[k] / np.maximum(a2, 1e-20), 0, 4) - 1) * A * 0.5      # Poisson

    def grad(sp):
        G = np.zeros((HR, HR), C); c = 0.0
        for k in od:
            A = if2(sp[W[k]] * P[k])
            c += float(np.sum((tg[k] - np.abs(A)) ** 2))
            G[W[k]] += P[k] * f2(upd(A, k))
        return G / np.maximum(N, 1), c

    v = np.zeros((HR, HR), C); mu_b = 1.0; cprev = np.inf; sprev = spec.copy()
    for it in range(its):
        if batch:
            G, c = grad(spec)
            if c > cprev:                              # paso adaptativo: si el costo sube, se revierte y se achica
                spec = sprev.copy(); mu_b *= 0.5; v[:] = 0
                G, c = grad(spec)
            else:
                mu_b = min(mu_b * 1.1, 1.5)
            cprev = c; sprev = spec.copy()
            v = 0.7 * v + np.float32(mu_b) * G
            spec = (spec + v).astype(C)
        else:
            mu = np.float32(step * (1.0 - np.exp(-0.3 * it))) if ramp else np.float32(step)
            for k in od:
                w = W[k]; ps = spec[w]
                A = if2(ps * P[k])
                spec[w] = ps + mu * P[k] * f2(upd(A, k))
        if unit > 0 and (unit_its is None or it < unit_its):
            o = if2(spec); a = np.abs(o)
            o = (1 - unit) * o + unit * a.mean() * o / np.maximum(a, 1e-12)
            spec = (f2(o) * sup).astype(C)
    return if2(spec)


def fit(o, t):
    return o * (np.vdot(o, t) / np.vdot(o, o))


def two_const(o, t, sel):
    """Ajusta una constante compleja a la parte 'sel' del espectro y otra al resto. Devuelve (objeto, fase rel, |rel|)."""
    Fo, Ft = f2(o), f2(t)
    c1 = np.vdot(Fo[sel], Ft[sel]) / np.vdot(Fo[sel], Fo[sel])
    c2 = np.vdot(Fo[~sel], Ft[~sel]) / np.vdot(Fo[~sel], Fo[~sel])
    return if2(np.where(sel, c1 * Fo, c2 * Fo)), float(np.angle(c1 / c2)), float(abs(c1 / c2))


def diag(o, t, mask):
    """Metricas con signo y sin el: global, fase invertida (conj), gemela conj(o(-r)), rampa, constantes separadas."""
    m = dict(S.metrics(o, t, mask)); m.update(K.extra(o, t))
    d = {}
    for name, v in (("conj", np.conj(o)), ("gemela", np.conj(np.roll(o[::-1, ::-1], 1, (0, 1)))),
                    ("espejo", np.roll(o[::-1, ::-1], 1, (0, 1)))):
        x = S.metrics(v, t, mask); d["err_" + name] = x["err"]; d["ph_" + name] = x["ph_esf"]
    X = np.abs(sfft.fft2(o * np.conj(t))); p = np.unravel_index(np.argmax(X), X.shape)
    sh = [int((q + HR // 2) % HR - HR // 2) for q in p]
    d["rampa_px"] = sh
    yy, xx = np.mgrid[:HR, :HR]
    x = S.metrics(o * np.exp(-2j * np.pi * (sh[0] * yy + sh[1] * xx) / HR), t, mask)
    d["err_sin_rampa"] = x["err"]; d["ph_sin_rampa"] = x["ph_esf"]
    for name, sel in (("dc", DC), ("disco", DISC)):
        o2, th, r = two_const(o, t, sel)
        x = S.metrics(o2, t, mask)
        d["err_2c_" + name] = x["err"]; d["ph_2c_" + name] = x["ph_esf"]; d["theta_" + name] = th; d["r_" + name] = r
    oc = fit(o, t)
    bg = ~mask
    ref_o = np.exp(-1j * np.angle(np.mean(oc[bg]))); ref_t = np.exp(-1j * np.angle(np.mean(t[bg])))
    d["fase_media_esf_rec"] = float(np.mean(np.angle(oc[mask] * ref_o)))      # fase media en esferas respecto del fondo
    d["fase_media_esf_verdad"] = float(np.mean(np.angle(t[mask] * ref_t)))
    d["amp_cv"] = float(np.std(np.abs(oc)) / np.mean(np.abs(oc)))             # cuanta amplitud espuria inventa
    d["amp_cv_verdad"] = float(np.std(np.abs(t)) / np.mean(np.abs(t)))
    m.update(d)
    return m


def log(row):
    row["t"] = round(time.time() - T0, 1)
    with open(os.path.join(HERE, "runs.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    print(row["z"], row["obj"], row["var"], "err %.3f ph %.3f | conj %.2f gem %.2f 2c_dc %.2f (th %.2f) 2c_disco %.2f (th %.2f) t=%s" % (
        row["err"], row["ph_esf"], row["ph_conj"], row["ph_gemela"], row["ph_2c_dc"], row["theta_dc"],
        row["ph_2c_disco"], row["theta_disco"], row["t"]), flush=True)


def variantes(truth):
    rng = np.random.default_rng(7)
    tn = truth * np.exp(1j * 0.5 * rng.normal(size=truth.shape))             # verdad + 0.5 rad rms de ruido de fase
    s_t = f2(truth / F ** 2); s_tn = f2(tn / F ** 2); s_c = f2(np.conj(truth) / F ** 2)
    s_r = f2(np.exp(2j * np.pi * rng.random(truth.shape)) / F ** 2)
    return [
        ("base_ePIE", dict()),
        ("ini_verdad", dict(spec0=s_t)),
        ("ini_verdad_ruido", dict(spec0=s_tn)),
        ("ini_conj_verdad", dict(spec0=s_c)),
        ("ini_fase_azar", dict(spec0=s_r)),
        ("AP_paso1", dict(step=1.0, ramp=False)),
        ("costo_intensidad", dict(cost="int", step=1.0, ramp=False, its=30)),
        ("costo_poisson", dict(cost="poisson", step=0.6, its=30)),
        ("lotes_adaptativo", dict(batch=True, its=60)),
        ("unit_0.5", dict(unit=0.5, its=30)),
        ("unit_1.0", dict(unit=1.0, its=30)),
        ("unit_1.0_60ep", dict(unit=1.0, its=60)),
        ("unit_solo_10ep_ini", dict(unit=1.0, unit_its=10, its=30)),
        ("unit_1.0_lotes", dict(unit=1.0, batch=True, its=60)),
    ]


def main():
    keep = {}
    casos = [(73.0, 0), (73.0, 1), (103.0, 0), (103.0, 1)]
    objs = {}
    for z, io in casos:
        if io not in objs:
            objs[io] = S.make_object(io)
        spec, truth, mask = objs[io]
        g = S.geom(z)
        keys = S.KEYS if z < 85.5 else B.solo_central(g)
        In, _ = S.add_noise(S.forward(spec, g), g, z, np.random.default_rng(1000))
        for var, kw in variantes(truth):
            o = solve(In, g, keys, **kw)
            log(dict(z=z, obj=io, var=var, seed=0, **diag(o, truth, mask)))
            if (z, io) == (73.0, 0) and var in ("base_ePIE", "ini_verdad_ruido", "unit_1.0"):
                keep[var] = fit(o, truth)
        if (z, io) == (73.0, 0):
            fig_mapas(keep, truth, mask)
        fig_variantes()


def fig_mapas(keep, t, mask):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = [("base_ePIE", "ePIE base (1 BF)"), ("unit_1.0", "ePIE + prior |o|=cte"), ("ini_verdad_ruido", "init verdad + ruido")]
    fig, ax = plt.subplots(2, 4, figsize=(15, 7.5))
    ref = np.exp(-1j * np.angle(np.mean(t[~mask])))
    im = ax[0, 0].imshow(np.angle(t * ref), cmap="twilight", vmin=-np.pi, vmax=np.pi); ax[0, 0].set_title("fase verdad (rad)")
    plt.colorbar(im, ax=ax[0, 0], fraction=0.046)
    r = np.round(S.KR / 0.02).astype(int); nb = r.max() + 1
    cnt = np.bincount(r.ravel(), minlength=nb)
    Pt = np.bincount(r.ravel(), np.abs(f2(t - t.mean())).ravel() ** 2, nb) / cnt
    for i, (k, lab) in enumerate(names):
        if k not in keep:
            continue
        o = keep[k]
        im = ax[0, i + 1].imshow(np.angle(o * ref), cmap="twilight", vmin=-np.pi, vmax=np.pi); ax[0, i + 1].set_title("fase: " + lab)
        plt.colorbar(im, ax=ax[0, i + 1], fraction=0.046)
        e = np.angle(o * np.conj(t))
        if i < 2:
            im = ax[1, i].imshow(e, cmap="RdBu_r", vmin=-np.pi, vmax=np.pi); ax[1, i].set_title("error de fase: " + lab)
            plt.colorbar(im, ax=ax[1, i], fraction=0.046)
        d = o - t
        Pd = np.bincount(r.ravel(), np.abs(f2(d - d.mean())).ravel() ** 2, nb) / cnt
        ax[1, 3].semilogy(np.arange(nb) * 0.02, Pd / np.maximum(Pt, 1e-30), label=lab)
    k = "base_ePIE"
    if k in keep:
        ax[1, 2].plot(np.abs(t)[HR // 2], "k", label="|verdad|"); ax[1, 2].plot(np.abs(keep[k])[HR // 2], label="|ePIE base|")
        if "unit_1.0" in keep:
            ax[1, 2].plot(np.abs(keep["unit_1.0"])[HR // 2], label="|con prior|")
        ax[1, 2].set_title("amplitud, fila central"); ax[1, 2].legend(fontsize=8)
    ax[1, 3].axvline(S.NA, color="gray", ls=":"); ax[1, 3].axhline(1, color="gray", lw=0.5)
    ax[1, 3].set_xlabel("frecuencia (NA)"); ax[1, 3].set_ylabel("|error|^2 / |verdad|^2"); ax[1, 3].set_xlim(0, 0.7)
    ax[1, 3].set_title("espectro radial del error (linea: NA del objetivo)"); ax[1, 3].legend(fontsize=8)
    for a in list(ax[0]) + [ax[1, 0], ax[1, 1]]:
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("1 BF, z = 73 mm, objeto 0 (8 esferas), simulacion")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig1_mapas.png"), dpi=110); plt.close(fig)


def fig_variantes():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [json.loads(l) for l in open(os.path.join(HERE, "runs.jsonl"))]
    vs = []
    for r in rows:
        if r["var"] not in vs:
            vs.append(r["var"])
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    for a, z in zip(ax, (73.0, 103.0)):
        for i, v in enumerate(vs):
            x = [r["ph_esf"] for r in rows if r["z"] == z and r["var"] == v]
            if x:
                a.barh(i, np.mean(x), color="#c44" if v.startswith("ini_") else ("#2a7" if v.startswith("unit") else "#468"))
                a.plot(x, [i] * len(x), "k.", ms=5)
        a.axvline(0.13, color="gray", ls=":"); a.set_yticks(range(len(vs))); a.set_yticklabels(vs); a.invert_yaxis()
        a.set_xlabel("RMS de fase en esferas (rad)"); a.set_title("z = %g mm, 1 BF%s (punteado: ref. 5 BF)" % (z, "" if z < 85 else " artificial"))
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig2_variantes.png"), dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()

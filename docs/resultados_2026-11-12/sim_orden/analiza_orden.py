"""Analiza runs.jsonl de sim_orden.py: tablas (tabla.md), figuras PNG y mapa de 'quién escribió último'."""
from __future__ import annotations

import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import sim_orden as so

HERE = so.HERE
runs = [json.loads(l) for l in open(so.OUT)]
G = defaultdict(dict)
for r in runs:
    G[(r["step"], r["variant"])][r["seed"]] = r
METS = ["err", "cost", "frc_BF", "frc_bajo", "frc_medio", "frc_alto", "fase"]


def val(r, ep, m):
    return next(h[m] for h in r["hist"] if h["ep"] == ep)


lines = []
for step, eps in (("rampa", (40, 100, 160)), ("fijo1", (20, 40))):
    ref = G.get((step, "anillo_crec"), {})
    for ep in eps:
        lines.append(f"\n### paso = {step}, época {ep}\n")
        lines.append("| variante | n | err complejo | Δerr vs anillo_crec (pareado) | costo LR (x1e-4) | FRC medio | FRC alto | fase esfera (rad; verdad 2.29) |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for v in so.VARIANTS:
            g = G.get((step, v))
            if not g:
                continue
            seeds = sorted(g)
            a = {m: np.array([val(g[s], ep, m) for s in seeds]) for m in METS}
            com = [s for s in seeds if s in ref]
            dl = np.array([val(g[s], ep, "err") - val(ref[s], ep, "err") for s in com])
            dtxt = f"{dl.mean():+.4f} ± {dl.std(ddof=1) if len(dl) > 1 else 0:.4f}" if len(dl) else "-"
            sd = lambda x: x.std(ddof=1) if len(x) > 1 else 0.0
            lines.append(f"| {v} | {len(seeds)} | {a['err'].mean():.4f} ± {sd(a['err']):.4f} | {dtxt} | "
                         f"{1e4 * a['cost'].mean():.2f} ± {1e4 * sd(a['cost']):.2f} | {a['frc_medio'].mean():.3f} ± {sd(a['frc_medio']):.3f} | "
                         f"{a['frc_alto'].mean():.3f} ± {sd(a['frc_alto']):.3f} | {a['fase'].mean():.3f} ± {sd(a['fase']):.3f} |")
ct = np.mean([r["cost_truth"] for r in runs])
lines.append(f"\nCosto LR del objeto verdadero (piso de ruido): {1e4 * ct:.2f} x1e-4\n")

# ---- distancia entre reconstrucciones de distintos órdenes vs distancia a la verdad (rampa, época 160)
lines.append("\n### Distancia entre órdenes (rampa, época 160): ||S_v - S_anillo|| / ||S_anillo - verdad|| en la banda sintética\n")
lines.append("| variante | cociente (media sobre semillas) |")
lines.append("|---|---|")
for v in so.VARIANTS:
    q = []
    for s in so.SEEDS:
        fa, fv = (os.path.join(HERE, "rec", f"rec_{x}_s{s}.npz") for x in ("anillo_crec", v))
        if v == "anillo_crec" or not (os.path.exists(fa) and os.path.exists(fv)):
            continue
        d = so.make_data(s)
        m = so.COV > 0
        al = lambda S: S * (np.vdot(S[m], d["spec"][m]) / np.vdot(S[m], S[m]))
        Sa, Sv = al(np.load(fa)["spec"]), al(np.load(fv)["spec"])
        q.append(np.linalg.norm((Sv - Sa)[so.UNION]) / np.linalg.norm((Sa - d["T"])[so.UNION]))
    if q:
        lines.append(f"| {v} | {np.mean(q):.3f} |")

# ---- figuras: curvas por época
cols = plt.cm.tab20(np.linspace(0, 1, len(so.VARIANTS)))
for step in so.STEPS:
    fig, ax = plt.subplots(2, 4, figsize=(19, 8))
    for (m, a) in zip(["err", "cost", "fase", "frc_BF", "frc_bajo", "frc_medio", "frc_alto"], ax.ravel()):
        for v, c in zip(so.VARIANTS, cols):
            g = G.get((step, v))
            if not g:
                continue
            eps = [h["ep"] for h in next(iter(g.values()))["hist"]]
            Y = np.array([[h[m] for h in r["hist"]] for r in g.values()])
            ls = "--" if v in ("lote", "minilote15", "minilote45") else ":" if v in ("residuo_desc", "residuo_asc", "paso_residuo", "anillo_paso_decr") else "-"
            a.plot(eps, Y.mean(0), ls, color=c, label=v, lw=1.6)
            a.fill_between(eps, Y.mean(0) - Y.std(0), Y.mean(0) + Y.std(0), color=c, alpha=0.12)
        a.set_title(m); a.set_xlabel("época"); a.grid(alpha=0.3)
        if m in ("err", "cost"):
            a.set_yscale("log")
        if m == "fase":
            a.axhline(2 * np.pi / so.LAM * so.DN * so.DIAM_UM, color="k", lw=0.8)
    ax[0, 0].legend(fontsize=7, ncol=2)
    ax[1, 3].axis("off")
    fig.suptitle(f"Orden de LEDs — paso {step} (media ± desvío sobre semillas; -- lotes, : adaptativos)")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, f"curvas_{step}.png"), dpi=110); plt.close(fig)

# ---- (d) mapa de quién escribió último
orders = so.base_orders(np.random.default_rng(7000))
kled = np.array([np.hypot(L["sx"], L["sy"]) / so.R_PUP for L in so.LEDS])
fig, ax = plt.subplots(2, 4, figsize=(18, 9))
lines.append("\n### Último escritor por píxel de frecuencia (geometría; unidades de NA_obj)\n")
lines.append("| orden | <|k_LED último| - |k_píxel|> | fracción de píxeles cuyo último escritor está más AFUERA que el píxel | posición media del último escritor en la época (0-1) |")
lines.append("|---|---|---|---|")
for j, v in enumerate(["anillo_crec", "anillo_decr", "snake", "aleat_fijo"]):
    last = -np.ones((so.N_HR, so.N_HR)); pos = np.zeros((so.N_HR, so.N_HR))
    for n, k in enumerate(orders[v]):
        w = so.WIN[k]
        last[w] = np.where(so.PUP > 0, k, last[w]); pos[w] = np.where(so.PUP > 0, n / so.NL, pos[w])
    m = last >= 0
    off = np.where(m, kled[last.astype(int).clip(0)] - so.KR, np.nan)
    lines.append(f"| {v} | {np.nanmean(off):+.3f} | {np.nanmean(off[m] > 0):.2f} | {pos[m].mean():.2f} |")
    im = ax[0, j].imshow(off, cmap="RdBu_r", vmin=-1, vmax=1); ax[0, j].set_title(f"{v}: |k_LED último| - |k| (NA)")
    plt.colorbar(im, ax=ax[0, j], fraction=0.046)
    im = ax[1, j].imshow(np.where(m, pos, np.nan), cmap="viridis"); ax[1, j].set_title("momento de la última escritura (0-1 de la época)")
    plt.colorbar(im, ax=ax[1, j], fraction=0.046)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "ultimo_escritor.png"), dpi=110); plt.close(fig)
cov = so.COV[so.COV > 0]
lines.append(f"\nCobertura (nº de LEDs que escriben cada píxel): media {cov.mean():.2f}, máx {cov.max():.0f}. "
             f"Peso del j-ésimo escritor contando desde el último en una época: mu(1-mu)^j -> con mu=0.3: 0.30, 0.21, 0.15, 0.10; con mu=1: 1, 0, 0.\n")
open(os.path.join(HERE, "tabla.md"), "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))

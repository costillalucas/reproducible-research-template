"""analiza_robusto.py -- lee runs.jsonl (aunque este incompleto) y escribe tablas.md y fig_robusto.png."""
import json, os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "runs.jsonl"))]
out = ["# Tablas (generadas por analiza_robusto.py). Celdas: err / error en banda NA<0.23 / fase en esferas [rad] (n)"]
TORD = ["erf", "lin", "cola", "na060", "na064", "na067", "na073", "na076", "na080", "elip", "led"]


def celda(v):
    if not v: return "-"
    m = lambda q: np.mean([r[q] for r in v])
    return f"{m('err'):.3f} / {m('e_c23'):.3f} / {m('ph_esf'):.2f} ({len(v)})"


g = defaultdict(list)
for r in rows:
    if r["var"] != "d":
        g[(r["z"], r["datos"], r["var"])].append(r)
for z in sorted({k[0] for k in g}):
    out.append(f"\n## z = {z:.0f} (media sobre objetos)\n\n| datos | a dura | b excl. 0.012 | c erf w 0.011 |\n|---|---|---|---|")
    for t in TORD:
        if any((z, t, v) in g for v in "abc") or (z, t, "b012") in g:
            out.append(f"| {t} | " + " | ".join(celda(g.get((z, t, v))) for v in ("a", "b012", "c")) + " |")

out.append("\n## Variante d (z = 181, objeto 0): err / residuo de borde por w del solver; * = w elegido (menor residuo)\n")
WS = [0.006, 0.011, 0.016, 0.022]
out.append("| datos | " + " | ".join(f"w {w}" for w in WS) + " | err de d | err de c | err de b |\n|" + "---|" * (len(WS) + 4))
dsel = {}
for t in TORD:
    d = {r["ws"]: r for r in rows if r["z"] == 181.0 and r["obj"] == 0 and r["datos"] == t and r["var"] in ("c", "d")}
    if len(d) < 2: continue
    best = min(d, key=lambda w: d[w]["c_borde"]); dsel[t] = d[best]
    b = [r for r in rows if r["z"] == 181.0 and r["obj"] == 0 and r["datos"] == t and r["var"] == "b012"]
    out.append(f"| {t} | " + " | ".join((f"{d[w]['err']:.3f} / {d[w]['c_borde']:.4f}" + ("*" if w == best else "")) if w in d else "-" for w in WS)
               + f" | {d[best]['err']:.3f} | {d[0.011]['err']:.3f} | " + (f"{b[0]['err']:.3f}" if b else "-") + " |")
open(os.path.join(HERE, "tablas.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")

# ---- figura: error en banda comun por desajuste, variantes b y c (y d en 181), paneles por z
zs = [z for z in (181.0, 249.0, 168.0, 146.0, 103.0) if any(k[0] == z for k in g)]
fig, axs = plt.subplots(1, len(zs), figsize=(3.6 * len(zs), 3.8), sharey=True)
axs = np.atleast_1d(axs)
COL = {"a": "#999999", "b012": "#1f77b4", "c": "#d62728"}
NOM = {"a": "a dura", "b012": "b excluir <0.012", "c": "c erf w 0.011 fijo"}
for ax, z in zip(axs, zs):
    ts = [t for t in TORD if any((z, t, v) in g for v in ("a", "b012", "c"))]
    for i, v in enumerate(("a", "b012", "c")):
        for j, t in enumerate(ts):
            for r in g.get((z, t, v), []):
                ax.plot(j + 0.2 * (i - 1), r["e_c23"], "os^"[i], color=COL[v], ms=5, label=NOM[v])
    if z == 181.0:
        for j, t in enumerate(ts):
            if t in dsel: ax.plot(j + 0.3, dsel[t]["e_c23"], "x", color="k", ms=6, label="d w ajustado")
    ax.set_xticks(range(len(ts))); ax.set_xticklabels(ts, rotation=60, fontsize=8)
    ax.set_yscale("log"); ax.set_title(f"z = {z:.0f} mm ({rows[[r['z'] for r in rows].index(z)]['nbf']} BF)", fontsize=10)
    ax.grid(alpha=0.3, which="both")
axs[0].set_ylabel("error relativo en banda comun (NA < 0.23)")
h, l = axs[0].get_legend_handles_labels(); u = dict(zip(l, h))
axs[0].legend(u.values(), u.keys(), fontsize=7, loc="best")
fig.suptitle("Pupila blanda con desajuste de modelo: datos con borde distinto del erf(w 0.011, NA 0.070) del solver", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_robusto.png"), dpi=130)
print("\n".join(out))

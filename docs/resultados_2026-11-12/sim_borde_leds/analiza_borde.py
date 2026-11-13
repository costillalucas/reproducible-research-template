"""analiza_borde.py -- lee runs.jsonl (aunque este incompleto) y escribe tablas.md y fig_borde.png."""
import json, os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "runs.jsonl"))]
MET = ["err", "e_c23", "frc_BF", "frc_bajo", "frc_medio", "ph_esf", "c_borde"]
NOM = {"a": "a base (dura)", "b008": "b excluir <0.008", "b012": "b excluir <0.012", "c": "c blanda w real",
       "e": "e paso ponderado"}
out = []


def tabla(titulo, sel, clave):
    g = defaultdict(list)
    for r in rows:
        if sel(r):
            g[clave(r)].append(r)
    out.append(f"\n## {titulo}\n\n| " + " | ".join(["caso", "n", "n_excl"] + MET) + " |\n|" + "---|" * (3 + len(MET)))
    for k in sorted(g, key=str):
        v = g[k]
        cel = []
        for m in MET:
            x = np.array([r[m] for r in v if r[m] is not None], float)
            cel.append(f"{x.mean():.3f} ± {x.std():.3f}" if x.size > 1 else (f"{x[0]:.3f}" if x.size else "-"))
        out.append("| " + " | ".join([str(k), str(len(v)), str(v[0]["n_excl"])] + cel) + " |")
    return g


g1 = tabla("w de datos 0.011 (borde real): z x variante (media ± desvio sobre objeto y semilla)",
           lambda r: r["est"] in ("p1", "p4"), lambda r: (r["z"], r["nbf"], round(r["margen"], 4), r["var"]))
tabla("w de datos 0.005 (semilla 0)", lambda r: r["est"] == "p3", lambda r: (r["z"], r["nbf"], r["var"]))
tabla("Variante d: barrido del w del solver (z=181, obj 0, semilla 0)", lambda r: r["est"] == "d",
      lambda r: ("w_datos", r["wd"], "w_solver", r["ws"]))
open(os.path.join(HERE, "tablas.md"), "w", encoding="utf-8").write("# Tablas (generadas por analiza_borde.py)\n" + "\n".join(out) + "\n")

# ---- figura
zs = sorted({k[0] for k in g1})
vs = [v for v in ("a", "b008", "b012", "e", "c") if any(k[3] == v for k in g1)]
col = {"a": "#8a8a8a", "b008": "#e0a030", "b012": "#c06010", "e": "#3070b0", "c": "#108060"}
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
for a, m, lab in ((ax[0], "e_c23", "error espectral, banda NA < 0.23"), (ax[1], "ph_esf", "RMS de fase en esferas (rad)")):
    for i, v in enumerate(vs):
        xs, ys, es = [], [], []
        for j, z in enumerate(zs):
            kk = [k for k in g1 if k[0] == z and k[3] == v]
            if kk:
                x = np.array([r[m] for r in g1[kk[0]]])
                xs.append(j + (i - (len(vs) - 1) / 2) * 0.16); ys.append(x.mean()); es.append(x.std())
        a.errorbar(xs, ys, es, fmt="o", color=col[v], label=NOM[v], capsize=2, ms=5)
    lab_z = []
    for z in zs:
        k = [k for k in g1 if k[0] == z][0]
        lab_z.append(f"{z:.0f}\n{k[1]} BF\nm {k[2]:.3f}")
    a.set_xticks(range(len(zs))); a.set_xticklabels(lab_z, fontsize=8)
    a.set_yscale("log"); a.set_ylabel(lab); a.set_xlabel("z (mm) / n BF / margen minimo"); a.grid(alpha=0.3, which="both")
    a.set_title("datos con borde erf w = 0.011")
ax[0].legend(fontsize=8)
for wd, mk in ((0.011, "o-"), (0.005, "s--")):
    d = sorted([r for r in rows if r["est"] == "d" and r["wd"] == wd], key=lambda r: r["ws"])
    if d:
        ax[2].plot([r["ws"] for r in d], [r["c_borde"] for r in d], mk, color="#108060", label=f"residuo LEDs de borde, w datos {wd}")
        ax[2].plot([r["ws"] for r in d], [r["e_c23"] for r in d], mk, color="#b03030", label=f"error real (e_c23), w datos {wd}")
        ax[2].axvline(wd, color="k", lw=0.5, ls=":")
ax[2].set_yscale("log"); ax[2].set_xlabel("w de la pupila del solver (NA)"); ax[2].set_title("variante d: barrido de w, z = 181 (13 BF)")
ax[2].legend(fontsize=7); ax[2].grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_borde.png"), dpi=110)
print("\n".join(out))

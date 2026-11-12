"""analiza_clave.py -- lee runs.jsonl (aunque este incompleto) y geometria.json; genera tablas.md y figuras."""
import json, os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "runs.jsonl")) if l.strip()]
geo = json.load(open(os.path.join(HERE, "geometria.json")))
out = []
M = ["err", "e_c23", "e_comun", "frc_BF", "frc_bajo", "frc_medio", "frc_alto", "ph_esf"]


def agg(sel, keyf):
    d = defaultdict(list)
    for r in rows:
        if sel(r):
            d[keyf(r)].append(r)
    return {k: dict({m: (float(np.mean([r[m] for r in v])), float(np.std([r[m] for r in v]))) for m in M},
                    n=len(v), nbf=v[0]["nbf_real"], mg=v[0]["margen_real"], n_excl=v[0]["n_excl"],
                    n1025=float(np.mean([r["n_1025"] for r in v]))) for k, v in sorted(d.items())}


def fmt(x):
    return f"{x[0]:.3f}±{x[1]:.3f}"


def tabla(titulo, a, cab, keyfmt):
    out.append(f"\n## {titulo}\n\n| {cab} | BF reales | margen min. | excl. | n | " + " | ".join(M) + " |\n|" + "---|" * (len(M) + 4 + cab.count("|") + 1))
    for k, v in a.items():
        out.append(f"| {keyfmt(k)} | {v['nbf']} | {v['mg']:.4f} | {v['n_excl']} | {v['n']} | " + " | ".join(fmt(v[m]) for m in M) + " |")


out.append("## Ventanas de z por conjunto BF completo (geometria exacta del simulador, paso 0.5 mm)\n")
out.append("| NA_obj | n BF | z min | z max | z de margen maximo | margen maximo | z con margen >= 0.010 | z con margen >= 0.007 |\n|---|---|---|---|---|---|---|---|")
for na, w in geo["ventanas"].items():
    for n, v in w.items():
        f = lambda x: "ninguno" if x is None else f"{x[0]:.1f}-{x[1]:.1f}"
        out.append(f"| {na} | {n} | {v['z_min']:.1f} | {v['z_max']:.1f} | {v['z_opt']:.1f} | {v['margen_max']:.4f} | {f(v['z_ok010'])} | {f(v['z_ok007'])} |")
out.append("\n## Geometria de los z simulados\n\n| z | BF | DF | solap. centro % | NA_syn eje | NA_syn esquina | irr. centro (rel. 102) | margen (NA 0.067) | margen (NA 0.070) | margen (NA 0.073) |\n|---|---|---|---|---|---|---|---|---|---|")
for g in sorted(geo["centros"], key=lambda g: g["z"]):
    mg = g["margen"]
    out.append(f"| {g['z']:.0f} | {g['n_BF']} | {g['n_DF']} | {g['ov_centro']:.0f} | {g['NA_syn_eje']:.3f} | {g['NA_syn_esq']:.3f} | {g['rel_irr_centro']:.2f} | "
               + " | ".join(f"{mg[k][1]:.4f} ({mg[k][0]} BF)" for k in ("0.067", "0.070", "0.073")) + " |")

A1 = agg(lambda r: r["est"] in ("e1", "e4"), lambda r: r["z"])
A2 = agg(lambda r: r["est"] in ("e1", "e2", "e4"), lambda r: r["z"])
A3 = agg(lambda r: r["est"] in ("e1", "e3"), lambda r: (r["z"], r["na_real"]))
A5 = agg(lambda r: r["est"] == "e5", lambda r: r["z"])
if A1: tabla("Exp. 1 y 4: centros de ventana (NA real 0.070, con ruido)", A1, "z", lambda k: f"{k:.0f}")
if A2: tabla("Exp. 2: centro vs borde de ventana (todos los z, NA real 0.070)", A2, "z", lambda k: f"{k:.0f}")
if A3: tabla("Exp. 3: NA_obj real de los datos vs solver 0.070", A3, "z | NA real", lambda k: f"{k[0]:.0f} | {k[1]:.3f}")
if A5: tabla("Exp. 5: excluyendo LEDs con |NA_ilum - 0.070| < 0.006", A5, "z", lambda k: f"{k:.0f}")
if A1:
    out.append("\nExposicion: " + "; ".join(f"z={z:.0f}: {v['n1025']:.0f}/225 LEDs en el tope de 1025 ms" for z, v in A1.items()))

C = {"err": "#222222", "e_c23": "#7b3fa0", "ph_esf": "#c0504d"}
if A1:
    zs = list(A1); lab = [f"{A1[z]['nbf']} BF\nz={z:.0f}" for z in zs]; x = np.arange(len(zs))
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
    for m, l in (("err", "err total"), ("e_c23", "error en banda comun NA<0.23")):
        ax[0].errorbar(x, [A1[z][m][0] for z in zs], [A1[z][m][1] for z in zs], marker="o", capsize=3, color=C[m], label=l)
    ax[0].set(yscale="log", ylabel="error complejo relativo", title="Calidad vs n BF (centro de ventana)")
    for b, c in zip(["BF", "bajo", "medio", "alto"], ["tab:blue", "tab:green", "tab:orange", "tab:red"]):
        ax[1].errorbar(x, [A1[z]["frc_" + b][0] for z in zs], [A1[z]["frc_" + b][1] for z in zs], marker="o", capsize=3, color=c, label=b)
    ax[1].set(ylabel="FRC por banda (NA absoluta)", title="FRC: BF 0-0.07, bajo -0.2, medio -0.35, alto -0.5")
    ax[2].errorbar(x, [A1[z]["ph_esf"][0] for z in zs], [A1[z]["ph_esf"][1] for z in zs], marker="o", capsize=3, color=C["ph_esf"], label="RMS fase en esferas")
    a2 = ax[2].twinx(); a2.plot(x, [1000 * A1[z]["mg"] for z in zs], "s--", color="gray", label="margen min. al borde (x1e-3 NA)")
    a2.set_ylabel("margen minimo al borde de pupila (1e-3 NA)"); a2.legend(fontsize=7, loc="upper center")
    ax[2].set(yscale="log", ylabel="rad", title="Fase en esferas y margen al borde")
    for a_ in ax:
        a_.set_xticks(x); a_.set_xticklabels(lab); a_.legend(fontsize=7, loc="upper left"); a_.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig1_calidad_vs_nbf.png"), dpi=130); plt.close(fig)

if A2:
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    b = geo["barrido"]
    ax[0].plot([r["z"] for r in b], [1000 * r["margen"] for r in b], color="gray", lw=1)
    ax[0].axhline(10, color="k", ls=":", lw=.8); ax[0].axhline(7, color="k", ls=":", lw=.8)
    for z, v in A2.items():
        ok = v["e_c23"][0] < 0.2
        ax[0].plot(z, 1000 * v["mg"], "o", color="tab:green" if ok else "tab:red")
        ax[0].annotate(f"{v['nbf']}", (z, 1000 * v["mg"]), textcoords="offset points", xytext=(4, 4), fontsize=8)
        ax[1].errorbar(1000 * v["mg"], v["e_c23"][0], v["e_c23"][1], marker="o", capsize=3, color="tab:green" if ok else "tab:red")
        ax[1].annotate(f"z={z:.0f} ({v['nbf']} BF)", (1000 * v["mg"], v["e_c23"][0]), textcoords="offset points", xytext=(5, 3), fontsize=7)
    ax[0].set(xlabel="z (mm)", ylabel="margen minimo |NA_ilum - NA_obj| (1e-3)", title="Margen al borde vs z (NA 0.070); punto = z simulado, numero = n BF\nverde: e_c23 < 0.2, rojo: falla")
    ax[1].set(xlabel="margen minimo al borde de pupila (1e-3 NA)", ylabel="error en banda comun NA<0.23", yscale="log", title="Centro vs borde de ventana: el error lo fija el margen, no el n BF")
    for a_ in ax: a_.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig2_centro_vs_borde.png"), dpi=130); plt.close(fig)

if A3:
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    zs = sorted({k[0] for k in A3}); nas = sorted({k[1] for k in A3}); wd = 0.8 / len(nas)
    for i, (na, c) in enumerate(zip(nas, ["#4f81bd", "#555555", "#e08a2e"])):
        for a_, m in zip(ax, ["e_c23", "ph_esf"]):
            xs = [j + (i - 1) * wd for j, z in enumerate(zs) if (z, na) in A3]
            a_.bar(xs, [A3[(z, na)][m][0] for z in zs if (z, na) in A3], wd * .92, yerr=[A3[(z, na)][m][1] for z in zs if (z, na) in A3],
                   color=c, capsize=2, label=f"NA real {na:.3f}")
    for a_, m in zip(ax, ["error en banda comun NA<0.23", "RMS fase en esferas (rad)"]):
        a_.set_xticks(range(len(zs))); a_.set_xticklabels([f"z={z:.0f}\n({A3[(z, 0.07)]['nbf'] if (z, 0.07) in A3 else '?'} BF nominal)" for z in zs])
        a_.set(yscale="log", ylabel=m); a_.legend(fontsize=8); a_.grid(alpha=.3, axis="y")
    fig.suptitle("Robustez a NA_obj incierta (solver siempre con 0.070)")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig3_robustez_na.png"), dpi=130); plt.close(fig)

open(os.path.join(HERE, "tablas.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
print("corridas:", len(rows), "ultimo t:", rows[-1]["t"] if rows else None)

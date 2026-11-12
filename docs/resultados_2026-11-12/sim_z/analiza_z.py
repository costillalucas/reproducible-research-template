"""analiza_z.py -- lee runs.jsonl (aunque este incompleto) y geometria.json; genera tablas.md y figuras."""
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


def agg(sel, keyf, mets):
    d = defaultdict(list)
    for r in rows:
        if sel(r):
            d[keyf(r)].append(r)
    return {k: {m: (float(np.mean([r[m] for r in v])), float(np.std([r[m] for r in v])), len(v)) for m in mets} for k, v in sorted(d.items())}


def fmt(x):
    return f"{x[0]:.3f}±{x[1]:.3f}"


out.append("## Geometria\n\n| z (mm) | BF | DF | solap. centro % | solap. medio % | solap. min % | NA_syn eje | NA_syn esquina | irradiancia centro (rel. z=102) | irradiancia esquina |\n|---|---|---|---|---|---|---|---|---|---|")
for g in geo:
    out.append(f"| {g['z']:.0f} | {g['n_BF']} | {g['n_DF']} | {g['ov_centro']:.0f} | {g['ov_medio']:.0f} | {g['ov_min']:.0f} | {g['NA_syn_eje']:.3f} | {g['NA_syn_esq']:.3f} | {g['rel_irr_centro']:.2f} | {g['rel_irr_esq']:.3f} |")

M1 = ["err", "e_comun", "e_BF", "e_bajo", "e_medio", "e_alto", "frc_BF", "frc_bajo", "frc_medio", "frc_alto", "ph_esf"]
A1 = {}
for var in ("limpio", "ruido"):
    A1[var] = a = agg(lambda r: r["est"] == "e1" and r["var"] == var, lambda r: r["z"], M1)
    if not a:
        continue
    n = max(v["err"][2] for v in a.values())
    out.append(f"\n## Estudio 1 ({var}; media±desvio sobre objetos x semillas, n={n})\n\n| z | " + " | ".join(M1) + " |\n|" + "---|" * (len(M1) + 1))
    for z, v in a.items():
        out.append(f"| {z:.0f} | " + " | ".join(fmt(v[m]) for m in M1) + " |")
ex = agg(lambda r: r["est"] == "e1" and r["var"] == "ruido", lambda r: r["z"], ["t_medio", "n_1025"])
if ex:
    out.append("\nExposicion: " + "; ".join(f"z={z:.0f}: t medio {v['t_medio'][0]:.0f} ms, {v['n_1025'][0]:.0f} LEDs en el tope de 1025 ms" for z, v in ex.items()))
# por objeto
ob = agg(lambda r: r["est"] == "e1" and r["var"] == "ruido", lambda r: (r["obj"], r["z"]), ["err", "e_comun", "ph_esf"])
if ob:
    out.append("\n### Estudio 1 por objeto (ruido; desvio = solo semillas de ruido)\n\n| objeto | z | err | e_comun | ph_esf |\n|---|---|---|---|---|")
    for (o, z), v in ob.items():
        out.append(f"| {o} | {z:.0f} | {fmt(v['err'])} | {fmt(v['e_comun'])} | {fmt(v['ph_esf'])} |")

if A1.get("ruido"):
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for var, ls in (("limpio", "--"), ("ruido", "-")):
        a = A1.get(var) or {}
        zs = list(a)
        if not zs:
            continue
        for b, c in zip(["BF", "bajo", "medio", "alto"], ["tab:blue", "tab:green", "tab:orange", "tab:red"]):
            ax[0].errorbar(zs, [a[z]["frc_" + b][0] for z in zs], [a[z]["frc_" + b][1] for z in zs], color=c, ls=ls, marker="o", ms=3, capsize=2,
                           label=f"{b} ({var})")
        for m, c in (("err", "k"), ("e_comun", "tab:purple")):
            ax[1].errorbar(zs, [a[z][m][0] for z in zs], [a[z][m][1] for z in zs], color=c, ls=ls, marker="o", ms=3, capsize=2, label=f"{m} ({var})")
        ax[2].errorbar(zs, [a[z]["ph_esf"][0] for z in zs], [a[z]["ph_esf"][1] for z in zs], color="k", ls=ls, marker="o", ms=3, capsize=2, label=var)
    ax[0].set(xlabel="z (mm)", ylabel="FRC por banda (NA absoluta)", title="FRC: BF 0-0.07, bajo -0.2, medio -0.35, alto -0.5")
    ax[1].set(xlabel="z (mm)", ylabel="error complejo relativo", title="err total y en banda comun (NA < 0.30)")
    ax[2].set(xlabel="z (mm)", ylabel="RMS fase en esferas (rad)", title="error de fase en esferas")
    for a_ in ax:
        a_.legend(fontsize=7); a_.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig1_calidad_vs_z.png"), dpi=130); plt.close(fig)

AX = agg(lambda r: r["est"] == "e1x", lambda r: r["z"], ["n_excl", "err", "e_comun", "frc_BF", "frc_medio", "ph_esf"])
if AX:
    out.append("")
    out.append("## Estudio 1 bis (sin ruido, excluyendo LEDs con |NA_ilum - NA_obj| < 0.012; n=2 objetos)")
    out.append("")
    out.append("| z | LEDs excluidos | err | e_comun | frc_BF | frc_medio | ph_esf |")
    out.append("|---|---|---|---|---|---|---|")
    for z, v in AX.items():
        out.append(f"| {z:.0f} | {v['n_excl'][0]:.0f} | " + " | ".join(fmt(v[m]) for m in ["err", "e_comun", "frc_BF", "frc_medio", "ph_esf"]) + " |")

M2 = ["err", "e_comun", "frc_bajo", "frc_medio", "frc_alto", "ph_esf"]
A2 = agg(lambda r: r["est"] == "e2", lambda r: (r["z"], r["dz"]), M2)
if A2:
    out.append("\n## Estudio 2 (z real = z nominal + dz, jitter 0.2 mm rms, con ruido; media±desvio)\n\n| z nominal | dz | n | " + " | ".join(M2) + " |\n|" + "---|" * (len(M2) + 3))
    for (z, dz), v in A2.items():
        out.append(f"| {z:.0f} | {dz:+.0f} | {v['err'][2]} | " + " | ".join(fmt(v[m]) for m in M2) + " |")
    out.append("\n### Degradacion relativa a dz=0 (cociente de medias)\n\n| z nominal | dz | err/err0 | e_comun/e_comun0 | ph_esf/ph_esf0 |\n|---|---|---|---|---|")
    for (z, dz), v in A2.items():
        if dz != 0 and (z, 0.0) in A2:
            b = A2[(z, 0.0)]
            out.append(f"| {z:.0f} | {dz:+.0f} | {v['err'][0]/b['err'][0]:.2f} | {v['e_comun'][0]/b['e_comun'][0]:.2f} | {v['ph_esf'][0]/b['ph_esf'][0]:.2f} |")
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    zs = sorted({k[0] for k in A2})
    for z, c in zip(zs, ["tab:blue", "tab:green", "tab:orange", "tab:red"]):
        dzs = sorted(k[1] for k in A2 if k[0] == z)
        for a_, m in zip(ax, ["err", "e_comun", "ph_esf"]):
            a_.errorbar(dzs, [A2[(z, d)][m][0] for d in dzs], [A2[(z, d)][m][1] for d in dzs], color=c, marker="o", ms=3, capsize=2, label=f"z nominal {z:.0f} mm")
    for a_, m in zip(ax, ["error complejo total", "error en banda comun (NA < 0.30)", "RMS fase en esferas (rad)"]):
        a_.set(xlabel="dz = z real - z nominal (mm)", ylabel=m); a_.legend(fontsize=7); a_.grid(alpha=.3)
    fig.suptitle("Robustez a error de z (jitter de LED 0.2 mm rms, con ruido, sin crimen inverso)")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig2_robustez_dz.png"), dpi=130); plt.close(fig)

M3 = ["err", "e_comun", "e_BF", "frc_BF", "frc_bajo", "frc_medio", "ph_esf"]
A3 = agg(lambda r: r["est"] == "e3", lambda r: (r["z"], r["nbf"]), M3)
if A3:
    out.append("\n## Estudio 3 (n LEDs BF usados + todo el DF, con ruido; media±desvio)\n\n| z | n BF | n | " + " | ".join(M3) + " |\n|" + "---|" * (len(M3) + 3))
    for (z, n), v in A3.items():
        out.append(f"| {z:.0f} | {n} | {v['err'][2]} | " + " | ".join(fmt(v[m]) for m in M3) + " |")
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for z, c in zip(sorted({k[0] for k in A3}), ["tab:orange", "tab:red"]):
        ns = sorted(k[1] for k in A3 if k[0] == z)
        for a_, m in zip(ax, ["err", "ph_esf"]):
            a_.errorbar(ns, [A3[(z, n)][m][0] for n in ns], [A3[(z, n)][m][1] for n in ns], color=c, marker="o", capsize=2, label=f"z {z:.0f} mm")
    for a_, m in zip(ax, ["error complejo total", "RMS fase en esferas (rad)"]):
        a_.set(xlabel="n de LEDs BF usados", ylabel=m); a_.legend(); a_.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig3_n_bf.png"), dpi=130); plt.close(fig)

open(os.path.join(HERE, "tablas.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
print("corridas:", len(rows), "ultimo t:", rows[-1]["t"] if rows else None)

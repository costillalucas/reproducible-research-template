"""figs.py -- figuras y resumen a partir de runs.jsonl (sim_1bf_rescate). Uso: python figs.py"""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "runs.jsonl"))]
TH = np.arange(24) * 2 * np.pi / 24
casos = sorted({(r["z"], r["obj"], r["seed"]) for r in rows})
get = lambda c, v: next((r for r in rows if (r["z"], r["obj"], r["seed"]) == c and r["var"] == v), None)

fig, ax = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
for j, (v, tit) in enumerate((("base", "sobre la solucion base (minimo falso)"), ("ini_verdad", "sobre init = verdad (minimo correcto)"))):
    for c in casos:
        r = get(c, v)
        if r is None: continue
        col = "#1f77b4" if c[0] < 85 else "#d95f02"; ls = "-" if c[1] == 0 else "--"
        ax[0, j].plot(TH, np.array(r["sweep_c"]) * 1e3, ls, color=col, lw=1.2, label="z=%g obj %d sem %d" % c)
        ax[1, j].plot(TH, r["sweep_ph"], ls, color=col, lw=1.2)
    ax[0, j].set_title("Barrido de la fase del DC " + tit, fontsize=10); ax[0, j].set_yscale("log")
    ax[0, j].set_ylabel("costo de amplitud relativo (x1e-3)"); ax[1, j].set_ylabel("RMS fase esferas (rad)")
    ax[1, j].set_xlabel("rotacion theta aplicada al DC (rad)"); ax[1, j].axhline(0.13, color="gray", ls=":")
ax[0, 0].legend(fontsize=7, ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig1_costo_vs_theta.png"), dpi=110); plt.close(fig)

vs = []
for r in rows:
    if r["var"] not in vs: vs.append(r["var"])
fig, ax = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
for a, zsel in zip(ax, (73.0, 103.0)):
    for i, v in enumerate(vs):
        x = [r["ph_esf"] for r in rows if r["z"] == zsel and r["var"] == v]
        if x:
            a.barh(i, np.mean(x), color="#9bb7d4"); a.plot(x, [i] * len(x), "k.", ms=6)
    # multi-inicio elegido por costo
    x = []
    for c in casos:
        if c[0] != zsel: continue
        m = [r for r in rows if (r["z"], r["obj"], r["seed"]) == c and r["var"].startswith("ini_th0")]
        if len(m) == 4: x.append(min(m, key=lambda r: r["costo"])["ph_esf"])
    if x:
        a.barh(len(vs), np.mean(x), color="#2a9d8f"); a.plot(x, [len(vs)] * len(x), "k.", ms=6)
    a.axvline(0.13, color="gray", ls=":"); a.set_yticks(range(len(vs) + 1)); a.set_yticklabels(vs + ["MULTI-INICIO (menor costo)"])
    a.invert_yaxis(); a.set_xlabel("RMS de fase en esferas (rad)")
    a.set_title("z = %g mm, 1 BF%s (punteado: ref. 5 BF)" % (zsel, "" if zsel < 85 else " artificial"))
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig2_variantes.png"), dpi=110); plt.close(fig)

print("caso | var: costo x1e3 / ph_esf / theta_dc")
for c in casos:
    print(c)
    for r in rows:
        if (r["z"], r["obj"], r["seed"]) == c:
            ex = " th_sel %.2f" % r["theta_sel"] if "theta_sel" in r else (" gan %.3f" % r["ganancia"] if "ganancia" in r else "")
            print("   %-20s %.3f  %.2f  %+.2f  s_bf %.3f%s" % (r["var"], r["costo"] * 1e3, r["ph_esf"], r["theta_dc"], r["s_bf"], ex))
    m = [r for r in rows if (r["z"], r["obj"], r["seed"]) == c and r["var"].startswith("ini_th0")]
    if len(m) == 4:
        b = min(m, key=lambda r: r["costo"]); print("   -> multi-inicio elige %s ph %.2f" % (b["var"], b["ph_esf"]))
    r = get(c, "base")
    if r: print("   barrido base: argmin costo theta=%.2f, argmin ph theta=%.2f" % (TH[int(np.argmin(r["sweep_c"]))], TH[int(np.argmin(r["sweep_ph"]))]))
    r = get(c, "ini_verdad")
    if r:
        cc = np.array(r["sweep_c"]); loc = [i for i in range(24) if cc[i] < cc[i - 1] and cc[i] < cc[(i + 1) % 24]]
        print("   barrido verdad: minimos locales theta=%s costos x1e3=%s" % ([round(float(TH[i]), 2) for i in loc], [round(float(cc[i]) * 1e3, 3) for i in loc]))

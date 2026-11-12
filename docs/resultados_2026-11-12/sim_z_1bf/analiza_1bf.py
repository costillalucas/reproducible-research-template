"""analiza_1bf.py -- tablas.md y figuras del estudio de 1 BF. Lee runs.jsonl propio y los de ../sim_z y ../sim_z_clave."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z"))
import sim_z as S                                     # noqa: E402


def rd(p):
    return [json.loads(l) for l in open(p) if l.strip()]


own = rd(os.path.join(HERE, "runs.jsonl"))
cl = rd(os.path.join(HERE, "..", "sim_z_clave", "runs.jsonl"))
sz = rd(os.path.join(HERE, "..", "sim_z", "runs.jsonl"))
COLS = ["err", "e_c23", "frc_BF", "frc_bajo", "frc_medio", "frc_alto", "ph_esf"]
geo = {t["z"]: t for t in json.load(open(os.path.join(HERE, "geometria.json")))}


def ms(rows, c):
    v = np.array([r[c] for r in rows if c in r])
    return (float(v.mean()), float(v.std())) if v.size else (float("nan"), 0.0)


def gt(z):
    t = S.geo_table(z)
    return t


grupos = []                                           # (etiqueta, z, nbf, filas)
for z in sorted({r["z"] for r in own if r["est"] == "e1"}):
    grupos.append(("1 BF real", z, 1, [r for r in own if r["est"] == "e1" and r["z"] == z]))
grupos.append(("1 BF real, borde (sim_z)", 80.0, 1, [r for r in sz if r["est"] == "e1" and r["z"] == 80.0 and r["var"] == "ruido"]))
for z in sorted({r["z"] for r in own if r["est"] == "e3"}):
    grupos.append(("1 BF artificial", z, 1, [r for r in own if r["est"] == "e3" and r["z"] == z]))
grupos.append(("1 BF artificial (sim_z)", 135.0, 1, [r for r in sz if r["est"] == "e3" and r.get("nbf") == 1]))
for z, n in ((103.0, 5), (146.0, 9), (216.0, 21)):
    grupos.append((f"ref {n} BF (sim_z_clave)", z, n, [r for r in cl if r["est"] == "e1" and r["z"] == z]))
for z, n in ((102.0, 5), (135.0, 9), (150.0, 9)):
    grupos.append((f"ref {n} BF (sim_z)", z, n, [r for r in sz if r["est"] == "e1" and r["z"] == z and r["var"] == "ruido"]))
for v in sorted({r["var"] for r in own if r["est"] == "e2"}):
    grupos.append((f"rescate {v}", 73.0, 1, [r for r in own if r["est"] == "e2" and r["var"] == v]))

L = ["| caso | z | BF/DF | solap. % | NA_syn eje/esq | margen | n | " + " | ".join(COLS) + " |", "|" + "---|" * (7 + len(COLS))]
pts = []
for et, z, n, rows in grupos:
    if not rows:
        continue
    t = gt(z)
    mg = min(abs(S.ill_na(S.geom(z), k) - S.NA) for k in S.KEYS)
    cel = []
    for c in COLS:
        m, s = ms(rows, c)
        cel.append(f"{m:.3f}±{s:.3f}")
    nb = n if "artificial" in et or "rescate" in et else t["n_BF"]
    L.append(f"| {et} | {z:.0f} | {nb}/{225 - t['n_BF'] if nb == t['n_BF'] else t['n_DF']} | {t['ov_centro']:.0f} | "
             f"{t['NA_syn_eje']:.3f}/{t['NA_syn_esq']:.3f} | {mg:.4f} | {len(rows)} | " + " | ".join(cel) + " |")
    pts.append((et, z, t["ov_centro"], ms(rows, "ph_esf"), ms(rows, "err"), ms(rows, "e_c23")))
sat = {z: np.mean([r["sat_bf"] for r in own if r["est"] == "e1" and r["z"] == z]) for z in sorted({r["z"] for r in own if r["est"] == "e1"})}
tb = {z: sorted({r["t_bf"] for r in own if r["est"] == "e1" and r["z"] == z}) for z in sat}
L += ["", "Exposicion del BF central (ms) y fraccion de pixeles saturados: " + "; ".join(f"z={z:.0f}: {tb[z]} / {sat[z]:.3f}" for z in sat)]
open(os.path.join(HERE, "tablas.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))

# ---- figura 1: fase y error vs solapamiento
est = {"1 BF real": ("o", "#c0392b"), "1 BF artificial": ("s", "#e08e0b"), "ref": ("^", "#1f6fb2"), "rescate": ("x", "#555555")}
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for a, idx, yl in ((ax[0], 3, "RMS de fase en esferas (rad)"), (ax[1], 5, "error en banda comun NA < 0.23 (e_c23)")):
    seen = set()
    for p in pts:
        key = next(k for k in est if p[0].startswith(k))
        m, c = est[key]
        a.errorbar(p[2], p[idx][0], yerr=p[idx][1], fmt=m, color=c, ms=7, capsize=3, label=None if key in seen else key)
        seen.add(key)
        a.annotate(f"{p[1]:.0f}", (p[2], p[idx][0]), textcoords="offset points", xytext=(5, 4), fontsize=7)
    a.set_yscale("log"); a.set_xlabel("solapamiento entre LEDs vecinos del centro (%)"); a.set_ylabel(yl); a.grid(alpha=0.3)
ax[0].axhline(0.2, ls=":", color="k", lw=0.8); ax[0].legend(fontsize=8)
ax[0].set_title("Fase vs solapamiento (etiqueta = z en mm)", fontsize=10); ax[1].set_title("Banda comun vs solapamiento", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig1_fase_vs_solapamiento.png"), dpi=130)

# ---- figura 2: FRC por bandas, 1 BF real vs referencias
fig, a = plt.subplots(figsize=(7, 4))
bands = ["frc_BF", "frc_bajo", "frc_medio", "frc_alto"]
sel = [g for g in grupos if g[3] and (g[0] == "1 BF real" or "sim_z_clave" in g[0])]
w = 0.8 / max(len(sel), 1)
for i, (et, z, n, rows) in enumerate(sel):
    a.bar(np.arange(4) + i * w, [ms(rows, b)[0] for b in bands], w, yerr=[ms(rows, b)[1] for b in bands],
          label=f"z={z:.0f} ({'1 BF' if et == '1 BF real' else et[4:9].strip()})", capsize=2)
a.set_xticks(np.arange(4) + 0.4 - w / 2); a.set_xticklabels(["BF 0-0.07", "bajo -0.2", "medio -0.35", "alto -0.5"])
a.set_ylabel("FRC"); a.set_xlabel("banda de NA absoluta"); a.legend(fontsize=8); a.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig2_frc_bandas.png"), dpi=130)

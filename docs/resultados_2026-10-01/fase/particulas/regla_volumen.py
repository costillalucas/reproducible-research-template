"""Regla con volumen de fase. Lee particulas.csv (de regla.py). python3 results/fase_2026-10-01/particulas/regla_volumen.py"""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "results/fase_2026-10-01/particulas"
LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}; NOM = {"red": "rojo", "green": "verde", "blue": "azul"}
COL = {"red": "#c0392b", "green": "#27ae60", "blue": "#2e6fd1"}
DN = {c: 0.045 + 0.0015 / l ** 2 for c, l in LAM.items()}  # sim_multiespectral_2026-09-29/sim.py:29,39-40
SH = {"red": np.array([6, 1]) * 512 / 1200, "blue": np.array([-5, 0]) * 512 / 1200, "green": np.zeros(2)}
L = [l.strip().split(",") for l in open(f"{O}/particulas.csv")][1:]
D = {}
for c in LAM:
    a = np.array([[float(x) for x in l[1:]] for l in L if l[0] == c and l[9] == "0" and l[10] == "0"])
    d, V = a[:, 0], a[:, 10]; yx = a[:, 4:6] - SH[c]
    dv = np.cbrt(np.clip(6 * V * LAM[c] / (2 * np.pi * DN[c] * np.pi), 0, None))
    D[c] = dict(d=d, V=V, dv=dv, yx=yx)
out = {"dn": DN, "por_color": {}, "cocientes_V": {}}
for c in LAM:
    d, dv = D[c]["d"], D[c]["dv"]; s = d >= 5
    out["por_color"][c] = dict(N_todos=int(len(d)), mediana_dvol_d_todos=float(np.median(dv / d)), N_d5=int(s.sum()),
        mediana_dvol_d_d5=float(np.median(dv[s] / d[s])), p25_d5=float(np.percentile(dv[s] / d[s], 25)),
        p75_d5=float(np.percentile(dv[s] / d[s], 75)), pearson_d5=float(np.corrcoef(d[s], dv[s])[0, 1]))
for c in ["green", "blue"]:
    q = []
    for i in range(len(D[c]["d"])):
        dd = np.hypot(*(D["red"]["yx"] - D[c]["yx"][i]).T); j = dd.argmin()
        if dd[j] < 2 and abs(D["red"]["d"][j] - D[c]["d"][i]) < 0.5 * max(D["red"]["d"][j], D[c]["d"][i]) and D["red"]["V"][j] > 0:
            q.append((D[c]["V"][i] / D["red"]["V"][j], min(D[c]["d"][i], D["red"]["d"][j])))
    q = np.array(q); s = q[:, 1] >= 5
    out["cocientes_V"][c] = dict(N_todos=len(q), mediana_todos=float(np.median(q[:, 0])), N_d5=int(s.sum()),
        mediana_d5=float(np.median(q[s, 0])) if s.any() else None,
        p25_d5=float(np.percentile(q[s, 0], 25)) if s.any() else None, p75_d5=float(np.percentile(q[s, 0], 75)) if s.any() else None,
        esperado=(DN[c] / LAM[c]) / (DN["red"] / LAM["red"]), esperado_sin_dispersion=LAM["red"] / LAM[c])
json.dump(out, open(f"{O}/resultados_volumen.json", "w"), indent=1); print(json.dumps(out, indent=1))
fig, ax = plt.subplots(1, 3, figsize=(15, 5.6), sharex=True, sharey=True)
for a, c in zip(ax, LAM):
    d, dv = D[c]["d"], D[c]["dv"]; s = d >= 5
    a.scatter(d[~s], dv[~s], s=10, alpha=0.3, color="0.5", edgecolor="none", label="d < 5 µm (volumen no calibrado)")
    a.scatter(d[s], dv[s], s=14, alpha=0.7, color=COL[c], edgecolor="none", label="d ≥ 5 µm")
    a.plot([0, 20], [0, 20], "k--", lw=1, label="y = x (esfera)"); a.axvline(5, color="0.7", lw=0.8)
    a.set_xlim(0, 20); a.set_ylim(0, 20); a.set_aspect("equal")
    a.set_title(f"{NOM[c]} ({int(LAM[c] * 1000)} nm), N(d ≥ 5 µm) = {s.sum()}"); a.set_xlabel("diámetro lateral equivalente (µm)")
ax[0].set_ylabel("diámetro desde el volumen de fase (µm)"); ax[0].legend(loc="upper left", fontsize=9)
plt.tight_layout(); plt.savefig(f"{O}/regla_volumen.png", dpi=110)

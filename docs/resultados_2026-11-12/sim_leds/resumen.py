"""resumen.py -- lee results.json (aunque este incompleto), imprime tablas y hace las figuras de mapas/curva/prediccion."""
import json, os, ast
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(H, "results.json")))
P = {ast.literal_eval(k): v for k, v in R["pred"].items()}
oc = lambda k: tuple(sorted((abs(k[0]), abs(k[1]))))
sp = lambda a, b: float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])
for n in ("base_clean", "base_noise", "solo_3x3", "damero"):
    if n in R:
        m = R[n]; print(n, m.get("n", ""), " ".join(f"{k}={m[k]:.3f}" for k in ("err", "e_bajo", "e_medio", "e_alto", "frc_medio", "frc_alto", "ph_esf")))
print("cobertura", R.get("cobertura"))
for tag in ("loo", "add"):
    D = {ast.literal_eval(k): v for k, v in R.get(tag, {}).items()}
    if not D:
        continue
    fig, ax = plt.subplots(1, 5, figsize=(21, 4.2))
    for a, n in zip(ax, ["err", "e_bajo", "e_medio", "e_alto", "frc_alto"]):
        M = np.full((15, 15), np.nan)
        for i in range(-7, 8):
            for j in range(-7, 8):
                if oc((i, j)) in D:
                    M[i + 7, j + 7] = 100 * D[oc((i, j))][n]
        v = np.nanmax(np.abs(M)); h = a.imshow(M, cmap="RdBu_r", vmin=-v, vmax=v); a.set_title(f"100 x delta {n}"); plt.colorbar(h, ax=a, fraction=0.046)
    fig.suptitle({"loo": "Leave-one-out: metrica(sin k) - metrica(225)", "add": "Agregar k a base 3x3: metrica(base+k) - metrica(base)"}[tag])
    fig.tight_layout(); fig.savefig(os.path.join(H, f"mapa_{tag}.png"), dpi=100); plt.close(fig)
    qs = sorted(D); r = np.array([np.hypot(*q) for q in qs])
    print(f"--- {tag}: n={len(qs)}; perjudiciales (delta err {'<0' if tag == 'loo' else '>0'}):",
          sum((D[q]['err'] < 0) if tag == "loo" else (D[q]['err'] > 0) for q in qs))
    for lo, hi in [(0, 1.5), (1.5, 3.5), (3.5, 5.5), (5.5, 7.5), (7.5, 10)]:
        s = [q for q in qs if lo <= np.hypot(*q) < hi]
        if s:
            print(f" anillo r[{lo},{hi}) n={len(s)} " + " ".join(f"d_{n}={100 * np.mean([D[q][n] for q in s]):+.3f}" for n in ("err", "e_bajo", "e_medio", "e_alto", "frc_alto")) + " (x100)")
    if tag == "loo":
        y = np.array([D[q]["err"] for q in qs])
        fig, ax = plt.subplots(1, 5, figsize=(21, 4))
        for a, n in zip(ax, ("geo", "fisher", "fisher_excl", "grad", "overlap")):
            x = np.array([P[q][n] for q in qs])
            print(f" predictor {n}: Spearman vs dErr {sp(x, y):+.2f}, vs d_alto {sp(x, np.array([D[q]['e_alto'] for q in qs])):+.2f}, vs d_bajo {sp(x, np.array([D[q]['e_bajo'] for q in qs])):+.2f}, vs d_medio {sp(x, np.array([D[q]['e_medio'] for q in qs])):+.2f}")
            a.scatter(x, 100 * y, c=r); a.set_xlabel(n); a.set_ylabel("100 x delta err LOO"); a.set_title(f"Spearman {sp(x, y):+.2f}")
        fig.tight_layout(); fig.savefig(os.path.join(H, "prediccion.png"), dpi=100); plt.close(fig)
print("simetria", json.dumps(R.get("simetria", {})))
C = R.get("curva", {})
if C:
    fig, ax = plt.subplots(1, 4, figsize=(19, 4.4))
    for a, n in zip(ax, ["err", "e_bajo", "e_alto", "ph_esf"]):
        for name, pts in C.items():
            a.plot([p["n"] for p in pts], [p[n] for p in pts], "o-" if "azar" not in name else "s--", label=name)
        a.set_yscale("log"); a.set_title(n); a.set_xlabel("numero de LEDs")
    ax[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(H, "curva.png"), dpi=100); plt.close(fig)
    for name, pts in C.items():
        print(name, " | ".join(f"N={p['n']}: err={p['err']:.3f} bajo={p['e_bajo']:.3f} alto={p['e_alto']:.3f} ph={p['ph_esf']:.3f}" for p in pts))

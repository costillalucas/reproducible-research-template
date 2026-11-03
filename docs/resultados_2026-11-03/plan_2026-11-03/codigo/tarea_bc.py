"""tarea_bc.py -- C2 (FRC complejo entre mitades en [2NA/λ, 0.45] 1/µm, sin ventana, 60 anillos) + C1/R/C3 de resumen.txt
para todas las corridas disponibles. Escribe bc_tabla.csv/.json y fig_bc_frc_mitades.png."""
import os, re, sys, json
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import comun_plan as C

P, R = C.P, C.R
RUNS = [("arco NA 0.0669 (real)", f"{R}/2026-10-30-red-b_arco", 0.0669),
        ("arco nulo DF (NA 0.0669)", f"{P}/red-b_arco_nulo_df", 0.0669),
        ("arco NA 0.074", f"{P}/red-b_arco_na074", 0.074),
        ("red-c NA 0.0669 (real)", f"{R}/2026-10-30-red-c", 0.0669),
        ("red-c NA 0.074", f"{P}/red-c_na074", 0.074),
        ("red-c nulo DF (NA 0.0669)", f"{P}/red-c_nulo_df", 0.0669)]
PX, LAM = 0.43, 0.63


def leer_resumen(d):
    s = open(os.path.join(d, "resumen.txt")).read()
    g = lambda rx: (lambda m: m.group(1) if m else None)(re.search(rx, s))
    return dict(R_train=g(r"R de ajuste[^:]*:\s+([\d.]+)"), C3=g(r"C3 artefacto[^:]*:\s+([\d.e+-]+)"),
                C1=g(r"C1 R held-out[^:]*:\s+([\d.]+)"), C1_A=g(r"mitad A ([\d.]+)"), C1_B=g(r"mitad B ([\d.]+)"),
                sin_fpm=g(r"sin FPM \(solo la imagen BF agrandada\): ([\d.]+)"), piso=g(r"piso de ruido: ([\d.]+)"),
                BF=g(r"LEDs BF:\s+(\[.*\])"), NA=g(r"NA ([\d.]+), factor"))


rows, curvas = [], {}
for nom, d, na in RUNS:
    if not os.path.exists(os.path.join(d, "objeto_mitadB.npy")):
        rows.append(dict(corrida=nom, dir=d, estado="NO DISPONIBLE")); continue
    h0, h1 = np.load(os.path.join(d, "objeto_mitadA.npy")), np.load(os.path.join(d, "objeto_mitadB.npy"))
    r = dict(corrida=nom, dir=d, NA_modelo=na, **leer_resumen(d))
    r["C2_banda_propia"] = C.c2(h0, h1, PX, na, LAM); r["banda_propia_1_um"] = [2 * na / LAM, 0.45]
    r["C2_banda_0669"] = C.c2(h0, h1, PX, 0.0669, LAM)            # misma banda para todas: [0.2124, 0.45]
    W = C.hann2(h0.shape[0])
    r["C2_hann_banda_0669"] = C.band_mean(C.frc((h0 - h0.mean()) * W, (h1 - h1.mean()) * W, PX), 2 * 0.0669 / LAM, 0.45)
    fr = C.frc_fino(h0, h1, PX, ventana=True); curvas[nom] = fr
    r["k_1_7_mitades_hann"] = C.cruce(fr, k0=2 * 0.0669 / LAM)   # primer cruce por debajo de 1/7 por encima de 2NA/λ
    rows.append(r); print(nom, {k: v for k, v in r.items() if k not in ("dir",)})
# veredicto con la regla de resolucion.py (frc >= 1/7 y >= nulo + 0.068), solo donde hay nulo propio
nulos = {c: next((r for r in rows if r["corrida"].startswith(c + " nulo") and "C2_banda_0669" in r), None) for c in ("arco", "red-c")}
for r in rows:
    if "C2_banda_0669" in r:
        r["C2_mayor_1_7"] = bool(r["C2_banda_0669"] >= 1 / 7)
        nu = nulos[r["corrida"].split()[0]]
        r["C2_menos_nulo"] = (r["C2_banda_0669"] - nu["C2_banda_0669"]) if nu else None
json.dump(rows, open(f"{P}/bc_tabla.json", "w"), indent=1, default=str)
cols = ["corrida", "NA_modelo", "BF", "R_train", "C1", "C1_A", "C1_B", "sin_fpm", "piso", "C3", "C2_banda_0669", "C2_banda_propia",
        "C2_hann_banda_0669", "C2_menos_nulo", "k_1_7_mitades_hann"]
with open(f"{P}/bc_tabla.csv", "w") as f:
    f.write(";".join(cols) + "\n")
    for r in rows:
        f.write(";".join(str(r.get(c, "")) if not isinstance(r.get(c), float) else f"{r[c]:.4f}" for c in cols) + "\n")
fig, ax = plt.subplots(figsize=(8, 4.5))
st = {"arco NA 0.0669 (real)": ("C3", "-"), "arco nulo DF (NA 0.0669)": ("0.4", "--"), "arco NA 0.074": ("C1", "-"),
      "red-c NA 0.0669 (real)": ("C0", "-"), "red-c NA 0.074": ("C2", "-"), "red-c nulo DF (NA 0.0669)": ("C0", "--")}
for nom, fr in curvas.items():
    y = np.convolve(fr[:, 1], np.ones(3) / 3, mode="same"); c, ls = st[nom]; ax.plot(fr[:, 0], y, color=c, ls=ls, lw=1.3, label=nom)
ax.axhline(1 / 7, color="k", lw=0.8, ls=":")
for k, t in [(0.0669 / LAM, "NA/λ (0.0669)"), (2 * 0.0669 / LAM, "2NA/λ (0.0669)"), (2 * 0.074 / LAM, "2NA/λ (0.074)"), (0.45, "0.45 (fin banda C2)"),
             (0.919, "corte sint. arco")]:
    ax.axvline(k, color="0.3", lw=0.7, ls="-."); ax.text(k, 0.98, t, rotation=90, fontsize=7, va="top", ha="right")
ax.axvspan(2 * 0.0669 / LAM, 0.45, color="y", alpha=0.12)
ax.set_xlim(0, 1 / (2 * PX)); ax.set_ylim(-0.05, 1.0); ax.set_xlabel("k [1/µm]"); ax.set_ylabel("FRC mitad A vs B (Hann, media móvil 3)")
ax.set_title("FRC complejo entre mitades de LEDs (amarillo = banda de C2 con NA 0.0669)", fontsize=9); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{P}/fig_bc_frc_mitades.png", dpi=130)

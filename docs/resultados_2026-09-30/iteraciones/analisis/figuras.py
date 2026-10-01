"""figuras.py -- figuras del barrido de épocas (lee los json de analizar.py y los obj_eNNN.npy de la tarea full).

  nice -n 19 python3 figuras.py            -> analisis/figs/*.png
Figuras:
  curvas_metricas.png   C1 (± sd entre folds, sin FPM), train_R y brecha, C2 con nulo y umbral 0.143, lattice
  c1_por_anillo.png     C1 de los LEDs no vistos por grupo de anillo
  estabilidad.png       correlación de amplitud y fase con el snapshot de 400 (bajas y banda C2) y cambio entre snapshots
  frc_curvas.png        FRC completa entre mitades a 0/5/20/40/120/400 épocas (y nulo)
  colores.png           coherencia entre colores vs época (si están los 3 colores)
  montaje_<ds>.png      amplitud y fase de la tarea full a 0/5/20/40/120/400 épocas, zona de 128 µm de las figuras
                        del deck; fase como report/informe/make_fig_fase_2809b.py (unwrap + polinomio orden 2, 0-3 rad)
"""
import json
import os
import sys

import numpy as np
from skimage.restoration import unwrap_phase
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt  # noqa: E401,E702

HERE = os.path.dirname(os.path.abspath(__file__))
IT = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figs"); os.makedirs(FIG, exist_ok=True)
COL = {"b_red": "#c0392b", "b_green": "#2e8b57", "b_blue": "#2f6fb5", "s3_red": "#8e5a2b"}
NOM = {"b_red": "rojo 28/09b", "b_green": "verde 28/09b", "b_blue": "azul 28/09b", "s3_red": "rojo set 3 (25/09)"}
X0 = 0.6  # la época 0 se dibuja en x = 0.6 (eje log)
plt.rcParams.update({"font.size": 12, "axes.titlesize": 13, "axes.grid": True, "grid.alpha": 0.3})

D = {}
for ds in COL:
    p = os.path.join(HERE, f"{ds}.json")
    if os.path.exists(p):
        D[ds] = json.load(open(p))


def ser(ds, k):
    ep = sorted(int(e) for e in D[ds]["epocas"])
    ep = [e for e in ep if e != 1]  # época 1 = época 0 (la rampa da paso 0 en la primera época)
    y = [D[ds]["epocas"][str(e)].get(k) for e in ep]
    x = [X0 if e == 0 else e for e in ep]
    xy = [(a, b) for a, b in zip(x, y) if b is not None]
    return (np.array([a for a, _ in xy]), np.array([b for _, b in xy])) if xy else (np.array([]), np.array([]))


def ejex(ax):
    ax.set_xscale("log"); ax.set_xticks([X0, 1, 2, 5, 10, 20, 40, 100, 200, 400])
    ax.set_xticklabels(["0", "1", "2", "5", "10", "20", "40", "100", "200", "400"])
    ax.set_xlim(0.5, 480); ax.axvline(40, color="0.5", ls=":", lw=1.2); ax.set_xlabel("épocas")


def curvas():
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))
    a = ax[0, 0]
    for ds in D:
        x, y = ser(ds, "C1"); _, s = ser(ds, "C1_sd")
        a.errorbar(x, y, yerr=s, color=COL[ds], lw=2, marker="o", ms=4, capsize=3, label=NOM[ds])
        if "C1_sin_fpm" in D[ds]:
            a.axhline(D[ds]["C1_sin_fpm"], color=COL[ds], ls="--", lw=1)
    a.set_ylim(0.3, 1.02); a.set_title("C1: R de LEDs no vistos (5 folds, anillo < 7)\n(guiones: sin FPM; barras: sd entre folds)")
    a.set_ylabel("R (menor es mejor)"); a.legend(fontsize=10)
    a = ax[0, 1]
    for ds in D:
        x, y = ser(ds, "trainR_folds"); a.plot(x, y, color=COL[ds], lw=2, marker="o", ms=4, label=f"{NOM[ds]}: entrenamiento")
        x, y = ser(ds, "C1"); a.plot(x, y, color=COL[ds], lw=1.2, ls="--", marker="s", ms=3, label=f"{NOM[ds]}: no vistos (C1)")
    a.set_ylim(0.25, 1.02); a.set_title("Entrenamiento (LEDs vistos, folds) contra no vistos"); a.set_ylabel("R")
    a.legend(fontsize=8, ncol=2)
    a = ax[1, 0]
    for ds in D:
        x, y = ser(ds, "C2"); a.plot(x, y, color=COL[ds], lw=2, marker="o", ms=4, label=f"{NOM[ds]}")
        x, y = ser(ds, "C2_nulo"); a.plot(x, y, color=COL[ds], lw=1.2, ls=":", marker="x", ms=4, label=f"{NOM[ds]}: nulo")
    a.axhline(0.143, color="k", lw=1.2, ls="--"); a.text(0.62, 0.147, "umbral 0.143", fontsize=10)
    a.set_title("C2: FRC entre mitades en [2NA/λ, 0.45] 1/µm (mayor es mejor)"); a.set_ylabel("FRC media en la banda")
    a.legend(fontsize=8, ncol=2); a.set_ylim(0, 0.25)
    a = ax[1, 1]
    for ds in D:
        x, y = ser(ds, "brecha"); a.plot(x, y, color=COL[ds], lw=2, marker="o", ms=4, label=NOM[ds])
    a.set_title("Brecha: C1 − R de entrenamiento (folds)"); a.set_ylabel("ΔR"); a.legend(fontsize=10)
    for a in ax.flat:
        ejex(a)
    fig.suptitle("Datos reales, A+init, paso 0.3 con rampa: métricas en función de las épocas (línea punteada: 40)", fontsize=14)
    plt.tight_layout(rect=(0, 0, 1, 0.96)); plt.savefig(os.path.join(FIG, "curvas_metricas.png"), dpi=90); plt.close()


def anillos():
    fig, ax = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    for a, g in zip(ax, ["DF_cercano_1.3-4", "DF_lejano_4-7", "fuera_>=7"]):
        for ds in D:
            x, y = ser(ds, f"C1_{g}"); _, s = ser(ds, f"C1_{g}_sd")
            a.errorbar(x, y, yerr=s, color=COL[ds], lw=2, marker="o", ms=4, capsize=3, label=NOM[ds])
        a.set_title({"DF_cercano_1.3-4": "campo oscuro cercano (anillo 1.3-4)", "DF_lejano_4-7": "campo oscuro lejano (anillo 4-7)",
                     "fuera_>=7": "anillo ≥ 7 (fuera de C1, informativo)"}[g]); ejex(a)
    ax[0].set_ylabel("R de LEDs no vistos"); ax[0].legend(fontsize=10)
    fig.suptitle("C1 por anillo de LED (los 6 LEDs de campo claro nunca quedan fuera de los folds)", fontsize=14)
    plt.tight_layout(rect=(0, 0, 1, 0.93)); plt.savefig(os.path.join(FIG, "c1_por_anillo.png"), dpi=90); plt.close()


def estabilidad():
    fig, ax = plt.subplots(2, 3, figsize=(17, 9.5))
    items = [("corrA_bajas_vs_400", "amplitud, bajas frecuencias (≤ NA/λ)"), ("corrA_C2_vs_400", "amplitud, banda de C2"),
             ("corrPhi_bajas_vs_400", "fase relativa, bajas frecuencias"), ("corrPhi_C2_vs_400", "fase relativa, banda de C2")]
    pos = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for (k, t), (i, j) in zip(items, pos):
        a = ax[i, j]
        for ds in D:
            x, y = ser(ds, k); a.plot(x, y, color=COL[ds], lw=2, marker="o", ms=4, label=NOM[ds])
            x, y = ser(ds, k.replace("400", "40")); a.plot(x, y, color=COL[ds], lw=1, ls="--", ms=3)
        a.set_title(f"corr. con el snapshot de 400 (—) y de 40 (--):\n{t}"); a.set_ylim(-0.1, 1.02); ejex(a)
    ax[0, 0].legend(fontsize=10)
    a = ax[0, 2]
    for ds in D:
        x, y = ser(ds, "dA_rel_prev"); a.plot(x, y, color=COL[ds], lw=2, marker="o", ms=4, label=NOM[ds])
    a.set_title("cambio relativo de la amplitud\nentre snapshots consecutivos"); a.set_ylabel("‖ΔA‖/‖A‖"); ejex(a)
    a = ax[1, 2]
    for ds in D:
        x, y = ser(ds, "dphi_rms_prev_rad"); a.plot(x, y, color=COL[ds], lw=2, marker="o", ms=4, label=NOM[ds])
    a.set_title("cambio de fase entre snapshots consecutivos\n(rms, fase global removida)"); a.set_ylabel("rad"); ejex(a)
    fig.suptitle("Estabilidad de la reconstrucción completa (interior del campo; los intervalos entre snapshots crecen con la época)", fontsize=14)
    plt.tight_layout(rect=(0, 0, 1, 0.95)); plt.savefig(os.path.join(FIG, "estabilidad.png"), dpi=90); plt.close()


def frcs():
    n = len(D); fig, ax = plt.subplots(1, n, figsize=(5.5 * n, 5), squeeze=False)
    cm = plt.get_cmap("viridis")
    for a, ds in zip(ax[0], D):
        fc = D[ds]["frc_curvas"]; lo, hi = D[ds]["banda_C2"]
        eps = sorted(fc.get("real", {}), key=int)
        for i, e in enumerate(eps):
            c = np.array(fc["real"][e]); a.plot(c[:, 0], c[:, 1], color=cm(i / max(1, len(eps) - 1)), lw=2, label=f"{e} ép.")
        for e in ("40", "400"):
            if e in fc.get("nulo", {}):
                c = np.array(fc["nulo"][e]); a.plot(c[:, 0], c[:, 1], color="0.5", lw=1, ls=":" if e == "40" else "--", label=f"nulo {e} ép.")
        a.axvspan(lo, hi, color="0.9", zorder=0); a.axhline(0.143, color="k", ls="--", lw=1)
        a.set_xlim(0, 1.0); a.set_ylim(-0.05, 1.02); a.set_xlabel("frecuencia (1/µm)"); a.set_title(f"{NOM[ds]}: FRC entre mitades")
        a.legend(fontsize=8)
    ax[0, 0].set_ylabel("FRC (gris: banda de C2)")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "frc_curvas.png"), dpi=90); plt.close()


def colores():
    p = os.path.join(HERE, "colores.json")
    if not os.path.exists(p):
        return
    C = json.load(open(p))["epocas"]
    ep = [e for e in sorted(C, key=int) if e != "1"]
    x = [X0 if e == "0" else int(e) for e in ep]
    fig, ax = plt.subplots(2, 3, figsize=(17, 9), sharey=True)
    est = {"red_green": ("#c0392b", "rojo-verde"), "blue_green": ("#2f6fb5", "azul-verde"), "red_blue": ("#7d3c98", "rojo-azul")}
    for i, q in enumerate(("amplitud", "fase")):
        for j, (b, bt) in enumerate((("banda_objetivo", "banda del objetivo (≤ NA/λ rojo)"), ("hasta_0.3", "hasta 0.3 1/µm"), ("todo", "todo el espectro"))):
            a = ax[i, j]
            for pr, (c, lab) in est.items():
                a.plot(x, [C[e][q][b][pr] for e in ep], color=c, lw=2, marker="o", ms=4, label=lab)
            a.set_title(f"{q}: {bt}"); ejex(a); a.set_ylim(-0.1, 1)
    ax[0, 0].legend(); ax[0, 0].set_ylabel("correlación"); ax[1, 0].set_ylabel("correlación")
    fig.suptitle("Coherencia entre colores (28/09 b; grilla del rojo, corrimientos fijos de comparar_colores.json)", fontsize=14)
    plt.tight_layout(rect=(0, 0, 1, 0.95)); plt.savefig(os.path.join(FIG, "colores.png"), dpi=90); plt.close()


# ---- montaje: zona y fase como report/informe/make_fig_fase_2809b.py / make_fig_rgb_2809b_es.py
def quitar_fondo(p, frac=70):  # = make_fig_fase_2809b.quitar_fondo
    n = p.shape[0]; y, x = np.mgrid[0:n, 0:n] / n
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    d = np.abs(p - np.median(p)); m = d < np.percentile(d, frac)
    c, *_ = np.linalg.lstsq(A[m], p[m], rcond=None)
    q = p - A @ c
    return q - np.median(q)


EPM = [0, 5, 20, 40, 120, 400]


def montaje(ds, tope=3.0):
    tdir = os.path.join(IT, "out", ds, f"real_A+init_z{D[ds]['z']:.1f}_full")
    if not all(os.path.exists(os.path.join(tdir, f"obj_e{e:03d}.npy")) for e in EPM):
        return
    fig, ax = plt.subplots(2, len(EPM), figsize=(3.3 * len(EPM) + 1, 7.4))
    amps, phs = [], []
    for e in EPM:
        o = np.load(os.path.join(tdir, f"obj_e{e:03d}.npy")).astype(complex)
        n = o.shape[0]; hr = 512.0 / n; L = int(round(128 / hr))
        r0 = int(round(450 * n / 1200))  # píxeles 450-750 de la grilla del rojo = misma porción (192 µm desde la esquina)
        z = o[r0:r0 + L, r0:r0 + L]
        amps.append(np.abs(z)); phs.append(quitar_fondo(unwrap_phase(np.angle(z))))
    lo, hi = np.percentile(np.concatenate([a.ravel() for a in amps[1:]]), [1, 99.5])
    for j, e in enumerate(EPM):
        ax[0, j].imshow(amps[j], cmap="gray", vmin=lo, vmax=hi, extent=[0, 128, 128, 0])
        im = ax[1, j].imshow(phs[j], cmap="magma", vmin=0, vmax=tope, extent=[0, 128, 128, 0])
        ax[0, j].set_title(f"{e} épocas" + (" (inicial)" if e == 0 else ""), fontsize=14)
        for a in ax[:, j]:
            a.set_xticks([]); a.set_yticks([]); a.grid(False)
    ax[0, 0].set_ylabel("amplitud", fontsize=14); ax[1, 0].set_ylabel("fase desenrollada", fontsize=14)
    ax[0, 0].plot([8, 38], [120, 120], color="w", lw=4); ax[0, 0].text(23, 112, "30 µm", color="w", ha="center", fontsize=12)
    cb = fig.colorbar(im, ax=ax[1, :].tolist(), fraction=0.015, pad=0.01, extend="max")
    cb.set_label(f"rad (satura en {tope:g})")
    fig.suptitle(f"{NOM[ds]}: reconstrucción completa según las épocas (zona de 128 µm; amplitud con la misma escala "
                 f"de grises en 5-400 ép.)", fontsize=13)
    plt.savefig(os.path.join(FIG, f"montaje_{ds}.png"), dpi=85, bbox_inches="tight"); plt.close()


if __name__ == "__main__":
    curvas(); anillos(); estabilidad(); frcs(); colores()
    for ds in (sys.argv[1:] or D):
        montaje(ds)
    print(sorted(os.listdir(FIG)))

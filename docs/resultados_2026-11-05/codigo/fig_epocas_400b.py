"""Figura: C2, C1 y d_vol vs épocas (03/11 rojo, 400 px, geometría B z102 NA .0669). Un panel por métrica (sin doble eje)."""
import json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/epocas_400b/"
r = json.load(open(D + "curvas.json")); ep = [x["ep"] for x in r]
AZUL, TXT, TXT2, GRILLA, FONDO = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": TXT2, "axes.labelcolor": TXT, "xtick.color": TXT2,
                     "ytick.color": TXT2, "axes.spines.top": False, "axes.spines.right": False})
paneles = [("C2", "C2  (FRC entre mitades, banda 0.21–0.45 µm⁻¹)\nmás alto = mitades más parecidas", 1 / 7, "umbral 1/7"),
           ("C1", "C1  (R held-out, mitades)\nmás bajo = mejor predicción de LEDs no vistos", None, None),
           ("d_vol", "d_vol de las esferas [µm]\n(mediana, ~62 partículas, Δn 0.046)", None, None)]
fig, axs = plt.subplots(1, 3, figsize=(13, 4), facecolor=FONDO)
for ax, (k, tit, hl, hlab) in zip(axs, paneles):
    y = [x[k] for x in r]; ax.set_facecolor(FONDO); ax.grid(axis="y", color=GRILLA, lw=.8); ax.set_axisbelow(True)
    ax.axvline(160, color=TXT2, lw=.8, ls=":"); ax.text(163, ax.get_ylim()[1], "", color=TXT2)
    if hl: ax.axhline(hl, color=TXT2, lw=.8, ls="--"); ax.text(398, hl, hlab, ha="right", va="bottom", color=TXT2, fontsize=9)
    ax.plot(ep, y, color=AZUL, lw=2, marker="o", ms=5, markeredgecolor=FONDO, markeredgewidth=1.5)
    for e in (20, 160, 400):
        v = y[ep.index(e)]; ax.annotate(f"{v:.3f}" if k != "d_vol" else f"{v:.2f}", (e, v), textcoords="offset points",
                                        xytext=(0, 9), ha="center", fontsize=9, color=TXT)
    ax.set_title(tit, fontsize=10, color=TXT, loc="left"); ax.set_xlabel("época"); ax.set_xlim(0, 410)
    ax.margins(y=0.18)
axs[1].text(0.97, 0.97, "ojo: eje ampliado\nvariación total 0.012 < diferencia\nentre mitades A–B ≈ 0.02", transform=axs[1].transAxes, ha="right", va="top", fontsize=8.5, color=TXT2)
axs[2].text(0.97, 0.80, "ojo: eje ampliado\ndesde ép. 80: 4.32–4.36 µm (±0.5 %)", transform=axs[2].transAxes, ha="right", va="top", fontsize=8.5, color=TXT2)
axs[0].text(165, axs[0].get_ylim()[0], " 160 = estándar", color=TXT2, fontsize=9, va="bottom")
fig.suptitle("03/11 rojo · recorte 400 px (360,80) · z 102 mm, NA 0.0669 · solver determinista", x=0.01, ha="left", color=TXT2, fontsize=9)
fig.tight_layout(); fig.savefig(D + "fig_epocas_400b.png", dpi=150, facecolor=FONDO); print("ok")

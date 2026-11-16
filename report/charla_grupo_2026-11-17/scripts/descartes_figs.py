#!/usr/bin/env python3
"""Dos figuras de tres paneles con la evidencia de las hipotesis descartadas.
Solo LEE datos. Salidas: descartes_exp.png y descartes_alg.png (2400x1000) junto a este script.
Cada numero sale del archivo indicado en el comentario del panel."""
import os, re, json, csv
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

AQUI = os.path.dirname(os.path.abspath(__file__))
R = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
A = "/home/chanoscopio/Documents/AleYLu"
FONDO, TARJ = "#F6F4EE", "#ECE8DE"
AZUL, NAR, NARC, GRIS, T1, T2 = "#2F6690", "#A9471A", "#E8925E", "#6B7280", "#1B2333", "#3E4756"
# 100 dpi: 1 pt = 1,389 px
F_TIT, F_CON, F_EJE, F_ROT = 26, 21.5, 19.5, 16      # 40, 30, 27, 22 px

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": F_EJE, "text.color": T1,
                     "axes.edgecolor": T2, "axes.labelcolor": T1, "xtick.color": T2, "ytick.color": T2,
                     "axes.facecolor": TARJ, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.linewidth": 1.6, "xtick.major.width": 1.6, "ytick.major.width": 1.6,
                     "xtick.major.size": 7, "ytick.major.size": 7})


def coma(x, n=3, signo=False):
    s = f"{x:+.{n}f}" if signo else f"{x:.{n}f}"
    return s.replace(".", ",").replace("-", "−")


def c1_resumen(path):
    """C1 y mitades A, B de un resumen.txt."""
    t = open(path, encoding="utf-8").read()
    m = re.search(r"C1 R held-out.*?:\s*([\d.]+)\s*\(mitad A ([\d.]+), mitad B ([\d.]+)", t)
    return tuple(float(x) for x in m.groups())


# ---------------------------------------------------------------- armazon
X0, W, SEP = 0.010, 0.3200, 0.0100       # tarjetas en coordenadas de figura


def lienzo():
    fig = plt.figure(figsize=(24, 10), dpi=100, facecolor=FONDO)
    return fig


def tarjeta(fig, i, titulo, rotulo, conclusion):
    """Dibuja la tarjeta i (0..2). Devuelve (x, ancho) de la tarjeta."""
    x = X0 + i * (W + SEP)
    fig.patches.append(FancyBboxPatch((x, 0.025), W, 0.95, transform=fig.transFigure,
                                      boxstyle="round,pad=0,rounding_size=0.012", mutation_aspect=2.4,
                                      fc=TARJ, ec="none", zorder=-5))
    # cruz dibujada (no caracter)
    cx, cy, h = x + 0.021, 0.905, 0.028
    w = h * 10 / 24
    for sx in (1, -1):
        fig.lines.append(Line2D([cx - sx * w / 2, cx + sx * w / 2], [cy - h / 2, cy + h / 2],
                                transform=fig.transFigure, color=GRIS, lw=7, solid_capstyle="round"))
    fig.text(x + 0.037, 0.905, titulo, fontsize=F_TIT, fontweight="bold", va="center", ha="left", color=T1)
    col = AZUL if rotulo.startswith("datos reales") and "sim" not in rotulo else NAR
    if "+" in rotulo:
        col = GRIS
    fig.text(x + 0.016, 0.828, rotulo.upper(), fontsize=F_ROT, fontweight="bold", va="center", ha="left",
             color="white", bbox=dict(boxstyle="round,pad=0.35", fc=col, ec="none"))
    fig.text(x + W / 2, 0.095, conclusion, fontsize=F_CON, fontweight="bold", va="center", ha="center",
             color=T1, linespacing=1.3)
    return x


def ejes(fig, x, rel):
    """rel = (x0, y0, w, h) con x relativo a la tarjeta (fraccion de W) e y en figura."""
    return fig.add_axes([x + rel[0] * W, rel[1], rel[2] * W, rel[3]])


# ======================================================================= FIGURA 1
def figura_exp():
    fig = lienzo()

    # ---- panel 1: ruido.  exposicion_snr.json (misma estadistica que exposicion.py) + resumen.txt 13/11
    est = json.load(open(os.path.join(AQUI, "exposicion_snr.json")))
    d = {t: {(int(f), int(c)): (s, g) for f, c, s, g in est[str(t)]} for t in (1025, 2048)}
    EJE = (17, 15)
    com = [k for k in sorted(set(d[1025]) & set(d[2048])) if d[1025][k][0] > 0 and d[2048][k][0] > 0
           and max(abs(k[0] - EJE[0]), abs(k[1] - EJE[1])) <= 7]
    ring = lambda k: int(round(np.hypot(k[0] - EJE[0], k[1] - EJE[1])))
    an = sorted({ring(k) for k in com})
    med = {t: [np.median([d[t][k][0] / d[t][k][1] for k in com if ring(k) == a]) for a in an] for t in (1025, 2048)}
    coc = np.array([(d[2048][k][0] / d[2048][k][1]) / (d[1025][k][0] / d[1025][k][1]) for k in com])
    print("P1: LEDs comunes %d, anillos %d-%d, cociente SNR mediana %.3f (p16 %.3f, p84 %.3f)" % (
        len(com), an[0], an[-1], np.median(coc), *np.percentile(coc, [16, 84])))
    c1 = {1025: c1_resumen(A + "/reconstrucciones/2026-11-13.a_15x15_flat12_1519/resumen.txt"),
          2048: c1_resumen(A + "/reconstrucciones/2026-11-13_15x15_flat12_1501/resumen.txt")}
    print("P1: C1", c1)
    x = tarjeta(fig, 0, "No es el ruido", "datos reales · 13/11",
                "×%s de señal/ruido, C1 igual" % coma(np.median(coc), 1))
    ax = ejes(fig, x, (0.135, 0.275, 0.42, 0.49))
    for t, c in ((1025, AZUL), (2048, NAR)):
        ax.plot(an, med[t], "-o", color=c, lw=4, ms=10)
    ax.set_yscale("log")
    ax.set_xlabel("anillo de LEDs")
    ax.set_ylabel("señal / ruido (mediana)")
    ax.set_xticks([a for a in an if a % 2 == 0])
    ax.set_yticks([1, 2, 5, 10, 20, 50]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50"])
    ax.minorticks_off()
    ax.set_ylim(min(med[1025]) * 0.7, max(med[2048]) * 1.5)
    ax.text(an[2], med[2048][2] * 1.18, "2048 ms", color=NAR, fontweight="bold", ha="left", va="bottom")
    ax.text(an[0], 1.6, "1025 ms", color=AZUL, fontweight="bold", ha="left", va="top")
    ax2 = ejes(fig, x, (0.68, 0.275, 0.295, 0.49))
    vals = [c1[1025][0], c1[2048][0]]
    ax2.bar([0, 1], vals, color=[AZUL, NAR], width=0.84)
    for i, v in enumerate(vals):
        ax2.text(i, v + 0.02, coma(v), ha="center", va="bottom", fontweight="bold", fontsize=18)
    ax2.set_ylim(0, 1); ax2.set_xlim(-0.65, 1.65)
    ax2.set_xticks([0, 1]); ax2.set_xticklabels(["1025", "2048"])
    ax2.set_yticks([0, 0.5, 1]); ax2.set_yticklabels(["0", "0,5", "1"])
    ax2.set_xlabel("exposición (ms)")
    ax2.set_title("error C1", fontsize=F_EJE, color=T1, pad=12)

    # ---- panel 2: magnificacion.  micrometro.json + recorte de fig_micrometro.png (la cruda ya no esta en disco)
    mj = json.load(open(R + "/docs/resultados_2026-10-20/offset_color/micrometro.json"))
    um_px, aum, per = mj["um_por_px"], mj["aumento"], mj["periodo_rayas_px"]
    nominal = 2.28
    x = tarjeta(fig, 1, "No es la magnificación", "datos reales · regla milimetrada",
                "medido: %s µm/px (%s×);\nel %s× nominal queda excluido" % (coma(um_px), coma(aum, 2), coma(nominal, 2)))
    import tifffile
    raw = tifffile.imread("/home/chanoscopio/Documents/AleYLu/regla_milimetrada.tif").astype(float)
    im = raw[180:580, 0:773]
    lo, hi = np.percentile(im, 1), np.percentile(im, 99.5)
    im = np.clip((im - lo) / (hi - lo), 0, 1)
    ax = ejes(fig, x, (0.035, 0.42, 0.93, 0.355))
    ax.imshow(im, cmap="gray", aspect="auto", interpolation="lanczos")
    ax.set_xticks([]); ax.set_yticks([])
    for s_ in ax.spines.values():
        s_.set_visible(False)
    per100 = 100.0 / um_px          # px por division de 100 um (77,5)
    x0r, yb = 20.0, 365
    ax.plot([x0r, x0r + 3 * per100], [yb, yb], color=NARC, lw=5, solid_capstyle="butt")
    for k in range(4):
        ax.plot([x0r + k * per100] * 2, [yb - 12, yb + 12], color=NARC, lw=4)
    ax.text(x0r + 3 * per100 + 14, yb, "cada división: 100 µm = %s px" % coma(per100, 1), color="white", fontsize=F_EJE,
            fontweight="bold", va="center", ha="left",
            bbox=dict(boxstyle="round,pad=0.25", fc="#1B2333", ec="none", alpha=0.85))
    ax.set_xlim(0, im.shape[1] - 1); ax.set_ylim(im.shape[0] - 1, 0)
    # recta de aumento
    ax3 = ejes(fig, x, (0.08, 0.285, 0.84, 0.06))
    fig.text(x + W / 2, 0.185, "con %s×, el error de predicción sube +0,069" % coma(nominal, 2), color=T2, ha="center", va="center", fontsize=F_EJE)
    ax3.set_xlim(2.2, 2.6); ax3.set_ylim(0, 1)
    ax3.spines["left"].set_visible(False); ax3.set_yticks([])
    ax3.patch.set_alpha(0)
    ax3.set_xticks([2.2, 2.3, 2.4, 2.5, 2.6]); ax3.set_xticklabels(["2,2", "2,3", "2,4", "2,5", "2,6×"])
    ax3.plot([aum], [0.0], "o", color=AZUL, ms=22, clip_on=False, zorder=5)
    ax3.plot([nominal], [0.0], "X", color=GRIS, ms=22, clip_on=False, zorder=5)
    ax3.text(aum, 0.75, "medido %s×" % coma(aum, 2), color=AZUL, fontweight="bold", ha="center", va="bottom")
    ax3.text(nominal, 0.75, "nominal %s×" % coma(nominal, 2), color=GRIS, fontweight="bold", ha="center", va="bottom")

    # ---- panel 3: posicion de la matriz
    # rotacion: C1 por mitades a la MISMA epoca (14) en snapshots/metricas_mitad{0,1}.csv
    def c1_ep(carp, ep=14):
        v = []
        for m in (0, 1):
            for r in csv.DictReader(open(f"{A}/reconstrucciones/{carp}/snapshots/metricas_mitad{m}.csv")):
                if int(r["epoca"]) == ep:
                    v.append(float(r["R_heldout_C1"]))
        return float(np.mean(v)), v
    base, vb = c1_ep("2026-10-23_1502")
    rp, _ = c1_ep("2026-10-23_rot+1")
    rm, _ = c1_ep("2026-10-23_rot-1")
    print("P3: base e14 %.5f (mitades %s), rot+1 %.5f (d %+.5f), rot-1 %.5f (d %+.5f)" % (base, vb, rp, rp - base, rm, rm - base))
    for n in ("2026-10-23_1502", "2026-10-23_rot+1", "2026-10-23_rot-1"):
        print("    resumen.txt", n, c1_resumen(f"{A}/reconstrucciones/{n}/resumen.txt"))
    # inclinacion: tabla.txt, filas tx1 / tx3 con assume = none, columna dC1
    inc = {}
    for l in open(A + "/respaldo_scratch_2026-10-28/inclinacion/tabla.txt"):
        p = l.split()
        m = re.search(r"\)\s+([+-][\d.]+)\s*\|", l)
        if m and len(p) > 2 and p[1] == "none" and p[0] in ("tx1", "ty1", "tx3", "ty3"):
            inc[p[0]] = float(m.group(1))
    print("P3: inclinacion dC1", inc)
    # referencia: |mitad A - mitad B| en epocas_400b/resumen.txt
    e4 = c1_resumen(R + "/docs/resultados_2026-11-05/epocas_400b/resumen.txt")
    ref = abs(e4[1] - e4[2])
    print("P3: mitades A-B epocas_400b %.3f ; 23/10 base %.3f" % (ref, abs(vb[0] - vb[1])))
    x = tarjeta(fig, 2, "No es la posición de la matriz", "datos reales + simulación",
                "errores de posición plausibles mueven C1\nmenos que la variación entre mitades")
    ax = ejes(fig, x, (0.165, 0.335, 0.80, 0.43))
    vals = [rp - base, rm - base, inc["tx1"], inc["tx3"]]
    cols = [AZUL, AZUL, NAR, NAR]
    ax.bar(range(4), vals, color=cols, width=0.62)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.0007, coma(v, 3, True), ha="center", va="bottom", fontweight="bold")
    ax.axhline(ref, color=GRIS, lw=3.5, ls=(0, (6, 4)))
    ax.text(-0.45, ref + 0.0008, "variación normal entre mitades ≈ %s" % coma(ref, 2), color=GRIS,
            ha="left", va="bottom", fontweight="bold")
    ax.axhline(0, color=T2, lw=1.6)
    ax.set_ylim(-0.001, 0.0255); ax.set_xlim(-0.6, 3.6)
    ax.set_yticks([0, 0.01, 0.02]); ax.set_yticklabels(["0", "0,01", "0,02"])
    ax.set_ylabel("cambio del error C1")
    ax.set_xticks(range(4)); ax.set_xticklabels(["giro\n+1°", "giro\n−1°", "inclin.\n1°", "inclin.\n3°"])
    ax.tick_params(axis="x", length=0, pad=10)
    fig.text(x + (0.165 + 0.20) * W, 0.215, "medido", color=AZUL, fontweight="bold", ha="center", fontsize=F_EJE)
    fig.text(x + (0.165 + 0.60) * W, 0.215, "simulado", color=NAR, fontweight="bold", ha="center", fontsize=F_EJE)

    fig.savefig(os.path.join(AQUI, "descartes_exp.png"), dpi=100, facecolor=FONDO)
    plt.close(fig)


# ======================================================================= FIGURA 2
def figura_alg():
    fig = lienzo()

    # ---- panel 4: iteraciones.  epocas_400b/curvas.json
    cur = json.load(open(R + "/docs/resultados_2026-11-05/epocas_400b/curvas.json"))
    ep = [r["ep"] for r in cur]; C1 = [r["C1"] for r in cur]; C2 = [r["C2"] for r in cur]
    print("P4: C1 %.3f -> %.3f ; C2 %.3f -> %.3f (ep %d -> %d)" % (C1[0], C1[-1], C2[0], C2[-1], ep[0], ep[-1]))
    x = tarjeta(fig, 0, "No son pocas iteraciones", "datos reales · rojo 03/11",
                "%d épocas: C1 casi no cambia\n(%s → %s)" % (ep[-1], coma(C1[0]), coma(C1[-1])))
    ax = ejes(fig, x, (0.175, 0.555, 0.775, 0.22))
    ax.plot(ep, C1, "-o", color=AZUL, lw=4, ms=8)
    ax.set_ylim(0, 1); ax.set_xlim(0, 415)
    ax.set_yticks([0, 0.5, 1]); ax.set_yticklabels(["0", "0,5", "1"])
    ax.set_xticks([0, 100, 200, 300, 400]); ax.set_xticklabels([])
    ax.set_ylabel("error C1")
    ax.text(400, C1[-1] + 0.07, "%s → %s" % (coma(C1[0]), coma(C1[-1])), color=AZUL, fontweight="bold", ha="right", va="bottom")
    ax = ejes(fig, x, (0.175, 0.275, 0.775, 0.22))
    ax.plot(ep, C2, "-o", color=NAR, lw=4, ms=8)
    ax.axhline(1 / 7, color=GRIS, lw=3, ls=(0, (6, 4)))
    ax.text(400, 1 / 7 - 0.012, "umbral 1/7", color=GRIS, fontweight="bold", ha="right", va="top")
    ax.text(395, C2[-1] + 0.012, "%s → %s, sigue subiendo" % (coma(C2[0]), coma(C2[-1])), color=NAR,
            fontweight="bold", ha="right", va="bottom")
    ax.set_ylim(0, 0.29); ax.set_xlim(0, 415)
    ax.set_yticks([0, 0.1, 0.2]); ax.set_yticklabels(["0", "0,1", "0,2"])
    ax.set_xticks([0, 100, 200, 300, 400])
    ax.set_ylabel("C2")
    ax.set_xlabel("época")

    # ---- panel 5: EPRY.  INFORME.md rojo 25/09 (tabla) + t3_causes.json verde 24/09
    rojo = {}
    for l in open(R + "/results/captura_2026-09-25_red/INFORME.md", encoding="utf-8"):
        m = re.match(r"\|\s*\**(A\+init[^|]*?|B \+ EPRY)\**\s*\|\s*\**([\d.]+) ± ([\d.]+)", l)
        if m:
            rojo["sin" if m.group(1).startswith("A+init") else "con"] = (float(m.group(2)), float(m.group(3)))
    t3 = json.load(open(R + "/results/captura_2026-09-24/j3/t3_causes/t3_causes.json"))["per_config"]
    verde = {"sin": (t3["base"]["heldout_res_mean"], t3["base"]["heldout_res_std"]),
             "con": (t3["d_epry"]["heldout_res_mean"], t3["d_epry"]["heldout_res_std"])}
    print("P5: rojo", rojo, "verde", verde)
    x = tarjeta(fig, 1, "No son aberraciones", "datos reales · 24 y 25/09",
                "recuperar la pupila no supera al mejor\nmétodo sin ella (y en verde empeora)")
    ax = ejes(fig, x, (0.165, 0.275, 0.80, 0.49))
    bw = 0.36
    for j, (nom, dd) in enumerate((("rojo", rojo), ("verde", verde))):
        for k, (cl, c) in enumerate((("sin", AZUL), ("con", NAR))):
            v, e = dd[cl]
            xx = j + (k - 0.5) * bw * 1.08
            ax.bar(xx, v, width=bw, color=c)
            ax.errorbar(xx, v, yerr=e, color=T1, lw=3, capsize=8, capthick=3)
            ax.text(xx, v + e + 0.02, coma(v), ha="center", va="bottom", fontweight="bold")
    ax.set_ylim(0, 1.08); ax.set_xlim(-0.6, 1.6)
    ax.set_yticks([0, 0.5, 1]); ax.set_yticklabels(["0", "0,5", "1"])
    ax.set_xticks([0, 1]); ax.set_xticklabels(["rojo (25/09)", "verde (24/09)"])
    ax.tick_params(axis="x", length=0, pad=10)
    ax.set_ylabel("error en imágenes no vistas")
    ax.text(-0.55, 1.06, "mejor método sin EPRY", color=AZUL, fontweight="bold", ha="left", va="top")
    ax.text(-0.55, 0.96, "con corrección (EPRY)", color=NAR, fontweight="bold", ha="left", va="top")

    # ---- panel 6: espesor.  sim_grueso_2026-10-20: INFORME.md (fila real) + resultados.json (A_ruido, B)
    rj = json.load(open(R + "/results/sim_grueso_2026-10-20/resultados.json"))
    cl3 = ("red", "green", "blue")
    delg = [rj["A_ruido"][c]["regla2_dvol_dseg_d5"] for c in cl3]
    grue = [rj["B"][c]["regla2_dvol_dseg_d5"] for c in cl3]
    real = None
    for l in open(R + "/results/sim_grueso_2026-10-20/INFORME.md", encoding="utf-8"):
        if l.startswith("| **Real"):
            real = [float(v) for v in re.findall(r"\|\s*\**([\d.]+)\**\s*(?=\|)", l)[:3]]
    print("P6: real", real, "delgada", delg, "gruesa", grue)
    x = tarjeta(fig, 2, "No es el espesor de las esferas", "simulación BPM · 20/10",
                "grueso ≈ delgado; el déficit real en verde\ny azul no lo explica el espesor")
    ax = ejes(fig, x, (0.135, 0.275, 0.845, 0.49))
    bw = 0.30
    for k, (vals, c) in enumerate(((real, GRIS), (delg, NARC), (grue, NAR))):
        for j, v in enumerate(vals):
            xx = j + (k - 1) * bw * 1.04
            ax.bar(xx, v, width=bw, color=c)
            ax.text(xx, v + 0.015, coma(v, 2), ha="center", va="bottom", fontweight="bold", fontsize=17.5)
    ax.set_ylim(0, 1.22); ax.set_xlim(-0.52, 2.52)
    ax.set_yticks([0, 0.5, 1]); ax.set_yticklabels(["0", "0,5", "1"])
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["rojo", "verde", "azul"])
    ax.tick_params(axis="x", length=0, pad=10)
    ax.set_ylabel("fase recuperada (d_vol / d)")
    for k, (t, c) in enumerate((("medido", GRIS), ("sim. delgada", NARC), ("sim. gruesa", NAR))):
        ax.text([-0.47, 0.42, 1.62][k], 1.2, t, color=c, fontweight="bold", ha="left", va="top")

    fig.savefig(os.path.join(AQUI, "descartes_alg.png"), dpi=100, facecolor=FONDO)
    plt.close(fig)


if __name__ == "__main__":
    figura_exp()
    figura_alg()

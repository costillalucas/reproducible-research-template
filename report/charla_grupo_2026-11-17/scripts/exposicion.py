#!/usr/bin/env python3
"""Figura 'Duplicar la exposicion no mejora la reconstruccion' (13/11/2026).
Solo LEE de AleYLu. Salida: exposicion.png (2400x1000) junto a este script.

Ruido: cada LED tiene 2 frames consecutivos. sigma = desvio (recortado a 4 sigma)
de (frame1 - frame2)/sqrt(2) sobre el recorte de la reconstruccion (filas 336:736,
columnas 392:792) = ruido temporal de UN frame en cuentas. Senal = media en ese
recorte de [media de los 2 frames - media de los 2 darks de igual exposicion].
SNR = senal / sigma. Se usan solo los LEDs de la grilla 15x15 de la reconstruccion que en ambas
capturas estan al tope de exposicion.
"""
import os, json, glob, re
import numpy as np, tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from idioma import EN, T, num, salida

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = "/home/chanoscopio/Documents/AleYLu"
CAP = {1025: BASE + "/imagenes_tomadas/2026-11-13.a", 2048: BASE + "/imagenes_tomadas/2026-11-13"}
REC = {1025: BASE + "/reconstrucciones/2026-11-13.a_15x15_flat12_1519",
       2048: BASE + "/reconstrucciones/2026-11-13_15x15_flat12_1501"}
COL = {1025: "#2F6690", 2048: "#A9471A"}
FONDO, T1, T2 = "#F6F4EE", "#1B2333", "#3E4756"
EJE = (17, 15)
R0, C0, N = 336, 392, 400            # recorte de la reconstruccion
LED_FOTO = (17, 8)                   # anillo 7, campo oscuro
Y0, X0, L = 440, 520, 200            # recorte de la foto (coordenadas del ROI)
UMBRAL = 0.05


def frames(carpeta, f, c, t):
    fs = sorted(glob.glob(f"{carpeta}/fila{f}_col{c}_colorr/{t}ms/*.tiff"))
    return [tifffile.imread(x).astype(np.float64) for x in fs]


def dark(t):
    d = frames(CAP[t] + "-dark", EJE[0], EJE[1], t)
    assert len(d) >= 2, "falta dark"
    return np.mean(d, axis=0)


def sigma_clip(d):
    d = d - np.median(d)
    s = d.std()
    for _ in range(5):
        s = d[np.abs(d) < 4 * s].std()
    return s


def estadistica():
    cache = os.path.join(AQUI, "exposicion_snr.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    out = {}
    for t in (1025, 2048):
        dk = dark(t)[R0:R0 + N, C0:C0 + N]
        filas = []
        for p in sorted(glob.glob(f"{CAP[t]}/fila*_col*_colorr/{t}ms")):
            f, c = map(int, re.search(r"fila(\d+)_col(\d+)_", p).groups())
            fr = frames(CAP[t], f, c, t)
            if len(fr) < 2:
                continue
            a, b = fr[0][R0:R0 + N, C0:C0 + N], fr[1][R0:R0 + N, C0:C0 + N]
            sen = float(np.mean((a + b) / 2 - dk))
            sig = float(sigma_clip(a - b) / np.sqrt(2))
            filas.append([f, c, sen, sig])
        out[str(t)] = filas
    json.dump(out, open(cache, "w"))
    return out


def c1(t):
    m = json.load(open(REC[t] + "/datos/metricas.json"))["heldout"]
    return float(np.mean(list(m.values()))), sorted(m.values())


def coma(x, n=3):
    return num(x, n)


def main():
    est = estadistica()
    d = {t: {(int(f), int(c)): (s, g) for f, c, s, g in est[str(t)]} for t in (1025, 2048)}
    comunes = sorted(set(d[1025]) & set(d[2048]))
    malos = [k for k in comunes if d[1025][k][0] <= 0 or d[2048][k][0] <= 0]
    print('LEDs con senal <= 0 (excluidos):', malos)
    comunes = [k for k in comunes if k not in malos]
    # solo la grilla 15x15 que uso la reconstruccion
    comunes = [k for k in comunes if max(abs(k[0] - EJE[0]), abs(k[1] - EJE[1])) <= 7]
    ring = lambda k: int(round(np.hypot(k[0] - EJE[0], k[1] - EJE[1])))
    anillos = sorted({ring(k) for k in comunes})
    med = {t: [np.median([d[t][k][0] / d[t][k][1] for k in comunes if ring(k) == a]) for a in anillos]
           for t in (1025, 2048)}
    cociente = np.array([(d[2048][k][0] / d[2048][k][1]) / (d[1025][k][0] / d[1025][k][1]) for k in comunes])
    print("LEDs comunes al tope:", len(comunes), "anillos", anillos[0], "-", anillos[-1])
    print("cociente SNR 2048/1025: mediana %.3f, p16 %.3f, p84 %.3f" % (
        np.median(cociente), *np.percentile(cociente, [16, 84])))
    for t in (1025, 2048):
        print(t, "sigma mediana %.2f cuentas, senal mediana %.2f cuentas" % (
            np.median([d[t][k][1] for k in comunes]), np.median([d[t][k][0] for k in comunes])))
    for a, x, y in zip(anillos, med[1025], med[2048]):
        print("anillo %2d  SNR 1025 %.2f  2048 %.2f  x%.2f" % (a, x, y, y / x))

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15, "text.color": T1,
                         "axes.edgecolor": T2, "axes.labelcolor": T1, "xtick.color": T2, "ytick.color": T2})
    # 24x10 in a 100 dpi -> 2400x1000 px; 1 pt = 100/72 px, asi 22 pt = 30,5 px y 25 pt = 34,7 px
    ET, TI = 22, 25
    fig = plt.figure(figsize=(24, 10), dpi=100, facecolor=FONDO)

    # --- panel 1: misma foto de campo oscuro
    fig.text(0.02, 0.945, T("Misma foto de campo oscuro", "Same dark-field photo"), fontsize=TI, fontweight="bold", va="center")
    im = {}
    for t in (1025, 2048):
        fr = frames(CAP[t], *LED_FOTO, t)
        im[t] = ((fr[0] + fr[1]) / 2 - dark(t))[Y0:Y0 + L, X0:X0 + L] / t * 1000.0   # cuentas/s
    vmin, vmax = np.percentile(im[2048], [1, 99.7])
    for i, t in enumerate((1025, 2048)):
        ax = fig.add_axes([0.02 + i * 0.205, 0.29, 0.195, 0.195 * 2.4])
        ax.imshow(im[t], cmap="gray", vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_edgecolor(COL[t]); s.set_linewidth(5)
        ax.set_title(f"{t} ms", fontsize=TI, color=COL[t], fontweight="bold", pad=12)
        print(t, "foto: desvio en zona de fondo (cuentas/s)", im[t][:40, :40].std())
    fig.text(0.02 + 0.40 / 2, 0.16, T(f"LED ({LED_FOTO[0]},{LED_FOTO[1]}), a 7 pasos del eje · menos dark\n"
               "misma escala de grises en cuentas/s",
               f"LED ({LED_FOTO[0]},{LED_FOTO[1]}), 7 steps from the axis · dark subtracted\n"
               "same gray scale in counts/s"), fontsize=ET, color=T2, ha="center", va="center", linespacing=1.3)

    # --- panel 2: SNR por anillo
    ax = fig.add_axes([0.505, 0.19, 0.20, 0.66])
    ax.set_facecolor(FONDO)
    for t in (1025, 2048):
        ax.plot(anillos, med[t], "-o", color=COL[t], lw=4, ms=11)
    ax.set_yscale("log")
    ax.set_xlabel(T("distancia del LED al eje (pasos)", "LED distance to axis (steps)"), fontsize=ET)
    ax.set_ylabel(T("señal / ruido (mediana)", "signal / noise (median)"), fontsize=ET)
    ax.tick_params(labelsize=ET, length=7, width=1.5)
    ax.tick_params(which="minor", length=4)
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: coma(v, 0) if v >= 1 else coma(v, 1)))
    ax.yaxis.set_minor_formatter(NullFormatter())
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=T2, alpha=0.15, lw=1.2)
    i = len(anillos) // 2
    ax.annotate("2048 ms", (anillos[i], med[2048][i]), xytext=(14, 14), textcoords="offset points",
                fontsize=ET, color=COL[2048], fontweight="bold")
    ax.annotate("1025 ms", (anillos[i], med[1025][i]), xytext=(-6, -52), textcoords="offset points",
                fontsize=ET, color=COL[1025], fontweight="bold", ha="right")
    fig.text(0.455, 0.945, T("Señal/ruido", "Signal/noise") + f": ×{coma(np.median(cociente), 1)}", fontsize=TI, fontweight="bold", va="center")

    # --- panel 3: C1
    ax = fig.add_axes([0.785, 0.24, 0.20, 0.61])
    ax.set_facecolor(FONDO)
    v = {t: c1(t) for t in (1025, 2048)}
    ref = v[1025][0]
    ax.axhspan(ref - UMBRAL, ref, color=FONDO, alpha=0.55, lw=0, zorder=3)
    ax.axhline(ref, color=T2, lw=2, ls=(0, (6, 4)), zorder=4)
    ax.axhline(ref - UMBRAL, color=T2, lw=2, ls=(0, (6, 4)), zorder=4)
    for i, t in enumerate((1025, 2048)):
        ax.bar(i, v[t][0], width=0.56, color=COL[t])
        ax.text(i, v[t][0] + 0.03, coma(v[t][0]), ha="center", va="bottom", fontsize=TI, fontweight="bold", color=COL[t])
    ax.set_xticks([0, 1]); ax.set_xticklabels(["1025 ms", "2048 ms"], fontsize=ET)
    for lab, t in zip(ax.get_xticklabels(), (1025, 2048)):
        lab.set_color(COL[t]); lab.set_fontweight("bold")
    ax.set_ylim(0, 0.88); ax.set_xlim(-0.5, 1.5)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: coma(x, 1)))
    ax.tick_params(labelsize=ET, length=7, width=1.5); ax.tick_params(axis="x", length=0, pad=10)
    ax.set_ylabel(T("C1, error en LEDs no vistos", "C1, error on unseen LEDs"), fontsize=ET)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.text(0.74, 0.945, T("Reconstrucción", "Reconstruction") + f": Δ = {coma(abs(v[2048][0] - v[1025][0]))}",
             fontsize=TI, fontweight="bold", va="center")
    fig.text(0.885, 0.065, T(f"banda clara: mejora mínima {coma(UMBRAL, 2)}\nmenor es mejor",
               f"light band: min. gain {coma(UMBRAL, 2)}\nlower is better"), fontsize=ET, color=T2, ha="center", va="center", linespacing=1.3)
    print("C1", {t: v[t] for t in v}, "dif", v[2048][0] - v[1025][0])

    fig.savefig(salida("exposicion.png", AQUI), dpi=100, facecolor=FONDO)


if __name__ == "__main__":
    main()

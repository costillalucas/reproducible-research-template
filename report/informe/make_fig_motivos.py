"""Cuatro figuras livianas para la slide 3 de la charla de 5 minutos: el MOTIVO de cada sugerencia de captura.
Solo datos reales y cálculos que ya están en el repo; nada se ajusta ni se inventa. Lee pocas imágenes crudas.
Correr desde la raíz del repo: python3 report/informe/make_fig_motivos.py [1 2 3 4 5]

1. fig_motivo_1_exposicion.png: captura 24/09, verde (foco verde), 10 ms iguales para todos los LEDs. Foto cruda del LED
   de luz directa (18,15) y de un LED de luz inclinada (18,20), en la misma escala de cuentas (0-4095, cámara de 12 bits).
   Derecha: mapa de señal/ruido estructural por LED a 100 ms, con la misma fórmula que
   results/captura_2026-09-24/stats_por_led/an.py (sqrt(struct² - struct_noise²) / struct_noise, de
   set_greenfoc_green_<t>.json). Cuenta de LEDs con S/R > 3: 25 a 10 ms y 131 a 100 ms (an.py).
2. fig_motivo_2_oscuras.png: foto a oscuras de 250 ms (LEDs apagados, 28/09 b, promedio de los 2 cuadros), y una foto de
   luz inclinada de 250 ms (rojo, LED (17,21), 28/09 b) antes y después de restar esa foto a oscuras, los tres en la misma
   escala absoluta. La mediana de la luz inclinada sobre el oscuro (5,9 cuentas en rojo) sale de prep_red.log. Recorte central de
   400 px (el mismo de prep_color.py y scripts/exposicion_z100.py). Los puntos brillantes del oscuro son píxeles calientes:
   un patrón fijo del sensor, que se repite de toma a toma (no es ruido aleatorio).
3. fig_motivo_3_mapa.png: tiempos de exposición por LED realmente usados el 28/09 (b), de
   data/captura_2026-09-28b/leds_por_tiempo_{rojo,verde,azul}.py (en µs), en ms. El verde se tomó con el campo claro a
   4 ms y se repitió a 16 ms (README de esa carpeta); el mapa muestra el archivo tal cual.
4. fig_motivo_4_distancia.png: pupila de cada LED en el espacio de frecuencias (círculo de radio NA/λ, centrado en la
   frecuencia de iluminación del LED), rojo 630 nm, NA 0,07, con la geometría de fpm_red.geometry(z) del 25/09 a 74 y a 98
   mm. El % de solapamiento es el de scripts/resumen_numbers.solapamiento_vecinos_pct: área común de las pupilas de
   (17,15) y (17,16), en % del área de una (31 % y 46 % en el deck).
5. fig_motivo_5_foco.png: captura del 28/09 a la tarde, foco ajustado solo en verde (results/captura_2026-09-28_rgb/,
   INFORME.md). Fila 1: foto cruda de luz directa (LED (18,15) dividido por la foto sin muestra, prep.npz de cada color),
   misma porción de 128 µm (píxeles 150-250 de la cámara), cada color estirado por sus propios percentiles 1 y 99,5.
   Fila 2: amplitud reconstruida (A+init, z 74 mm, out/obj_real_A+init_z74.0_full.npy), llevada a la grilla de 1200 px
   del rojo recortando el espectro (como multiespectral.to_grid), misma porción (píxeles 450-750, como reenfoque.py).
   Rojo y azul se alinean lateralmente con el verde por correlación de fase (corrimiento entero, como reenfoque.shift_to):
   solo se desplazan. Nota de confirmación: results/captura_2026-09-28b/FOCO_VS_SOLAPAMIENTO.md (captura de la noche, rojo en su
   foco: error en fotos no usadas 0,46; con el foco del verde: 0,81).
"""
import glob
import importlib.util
import json
import os
import sys

import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle

RAW = os.path.expanduser("~/Documents/AleYLu/imagenes_tomadas")
OUT = "report/informe/img"
plt.rcParams.update({"font.size": 15, "axes.titlesize": 17})
C = slice(360, 760)


def tif(p):
    import tifffile
    return tifffile.imread(p).astype(float)


def fig1():
    base = f"{RAW}/2026-09-24_green_enfocado/organizado/green/10ms"
    bf, df = tif(f"{base}/fila18_col15.tiff")[C, C], tif(f"{base}/fila18_col20.tiff")[C, C]
    st = "results/captura_2026-09-24/stats_por_led"

    def snr(t):
        L = json.load(open(f"{st}/set_greenfoc_green_{t}.json")); A = {k: np.zeros((13, 13)) for k in ("struct", "struct_noise")}
        for d in L:
            for k in A: A[k][d["r"] - 12, d["c"] - 9] = d[k]
        return np.sqrt(np.clip(A["struct"] ** 2 - A["struct_noise"] ** 2, 0, None)) / A["struct_noise"]
    s10, s100 = snr("10ms"), snr("100ms")
    fig = plt.figure(figsize=(13, 6.4))
    ax1 = fig.add_axes([0.02, 0.30, 0.27, 0.54]); ax2 = fig.add_axes([0.31, 0.30, 0.27, 0.54]); ax3 = fig.add_axes([0.66, 0.24, 0.25, 0.62])
    for a, im, t in ((ax1, bf, "luz directa (LED central)"), (ax2, df, "luz inclinada (5 LEDs al costado)")):
        h = a.imshow(im, cmap="gray", vmin=0, vmax=4095); a.set_title(t); a.axis("off")
    cax = fig.add_axes([0.06, 0.22, 0.48, 0.03]); cb = fig.colorbar(h, cax=cax, orientation="horizontal"); cb.set_label("cuentas (máximo del sensor: 4095)")
    h3 = ax3.imshow(s100, cmap="viridis", vmin=0, vmax=12, extent=[8.5, 21.5, 24.5, 11.5])
    ax3.contour(np.arange(9, 22), np.arange(12, 25), s100, levels=[3], colors="w", linewidths=2)
    ax3.set_title("señal/ruido por LED, 100 ms"); ax3.set_xlabel("columna del LED"); ax3.set_ylabel("fila del LED")
    c3 = fig.colorbar(h3, cax=fig.add_axes([0.925, 0.24, 0.015, 0.62])); c3.set_label("S/R (línea blanca: 3)")
    fig.suptitle("Misma exposición (10 ms) para todos los LEDs: la luz inclinada queda casi negra", fontsize=18)
    fig.text(0.02, 0.03, f"Verde, captura del 24/09. LEDs con S/R > 3: {int((s10 > 3).sum())} de 169 a 10 ms, "
             f"{int((s100 > 3).sum())} de 169 a 100 ms\n(a 100 ms la luz directa se satura: de ahí, corto para la luz directa y largo para la inclinada).",
             fontsize=14, color="0.3")
    fig.savefig(f"{OUT}/fig_motivo_1_exposicion.png", dpi=90); plt.close(fig)


def fig2():
    dk = np.mean([tif(p) for p in sorted(glob.glob(f"{RAW}/2026-09-28.b_dark/fila18_col15_colorb/250ms/*.tiff"))], axis=0)[C, C]
    s = tif(f"{RAW}/2026-09-28.b_red_enfocado/organizado/red/250ms/fila17_col21.tiff")[C, C]
    med = float(np.median(dk)); hot = int((dk > med + 50).sum())
    fig, ax = plt.subplots(1, 3, figsize=(15, 6.4))
    hi = np.percentile(s, 99.5)  # misma escala absoluta en los tres paneles
    h0 = ax[0].imshow(dk, cmap="gray", vmin=0, vmax=hi); ax[0].set_title("Foto a oscuras (LEDs apagados)")
    ax[1].imshow(s, cmap="gray", vmin=0, vmax=hi); ax[1].set_title("Luz inclinada, cruda")
    ax[2].imshow(s - dk, cmap="gray", vmin=0, vmax=hi); ax[2].set_title("Luz inclinada − oscuro")
    for a in ax: a.axis("off")
    c0 = fig.colorbar(h0, ax=ax[0], orientation="horizontal", fraction=0.05, pad=0.03); c0.set_label("cuentas")
    fig.suptitle("Con los LEDs apagados el sensor no da cero: hay un fondo propio", fontsize=18)
    fig.text(0.5, 0.03, f"Rojo, 250 ms, 28/09, recorte de 400 px, misma escala en los tres. Oscuro: mediana {med:.0f} cuentas, con píxeles calientes fijos del sensor.\n"
             "La luz inclinada suma en mediana solo 5,9 cuentas sobre ese fondo (results/captura_2026-09-28b/prep_red.log): sin restarlo, el fondo domina.",
             ha="center", fontsize=13, color="0.3")
    plt.tight_layout(rect=(0, 0.1, 1, 0.93)); fig.savefig(f"{OUT}/fig_motivo_2_oscuras.png", dpi=90); plt.close(fig)


def fig3():
    fig, ax = plt.subplots(1, 3, figsize=(15, 6.2))
    norm = LogNorm(4, 250)
    for a, (arch, nom) in zip(ax, (("rojo", "rojo"), ("verde", "verde"), ("azul", "azul"))):
        ns = {}; exec(open(f"data/captura_2026-09-28b/leds_por_tiempo_{arch}.py").read(), ns)
        M = np.full((15, 15), np.nan)
        for t_us, leds in ns["LEDS_POR_TIEMPO"].items():
            for r, c in leds: M[r - 11, c - 8] = t_us / 1000
        h = a.imshow(M, cmap="magma", norm=norm, extent=[7.5, 22.5, 25.5, 10.5]); a.set_title(nom)
        a.set_xlabel("columna del LED"); a.set_ylabel("fila del LED" if a is ax[0] else "")
    cb = fig.colorbar(h, ax=ax, fraction=0.02, pad=0.02, ticks=[4, 8, 16, 32, 64, 128, 250]); cb.set_label("tiempo de exposición (ms)")
    cb.ax.set_yticklabels(["4", "8", "16", "32", "64", "128", "250"])
    fig.suptitle("Tiempo de exposición de cada LED, calculado a partir de la captura anterior", fontsize=18)
    fig.text(0.45, 0.02, "Captura del 28/09, 15×15 LEDs. Centro: luz directa, corto; bordes: luz inclinada, hasta 250 ms (el máximo del programa).",
             ha="center", fontsize=13, color="0.3")
    fig.subplots_adjust(left=0.05, right=0.88, top=0.86, bottom=0.16, wspace=0.25)
    fig.savefig(f"{OUT}/fig_motivo_3_mapa.png", dpi=90); plt.close(fig)


def fig4():
    s = importlib.util.spec_from_file_location("F", "results/captura_2026-09-25_red/fpm_red.py"); F = importlib.util.module_from_spec(s)
    sys.path.insert(0, "results/captura_2026-09-25_red"); s.loader.exec_module(F)
    fig, ax = plt.subplots(1, 2, figsize=(13, 7))
    for a, z in zip(ax, (74.0, 98.0)):
        g = F.geometry(z); r = g["na"] / g["lam"]
        d = float(np.hypot(*np.subtract(g["fxy"][(17, 16)], g["fxy"][(17, 15)])))
        pct = 100 * (2 * r * r * np.arccos(d / (2 * r)) - d / 2 * np.sqrt(4 * r * r - d * d)) / (np.pi * r * r)
        f0 = np.array(g["fxy"][(17, 15)])
        for rr in range(15, 20):
            for cc in range(13, 18):
                fx, fy = np.array(g["fxy"][(rr, cc)]) - f0
                on = (rr, cc) in ((17, 15), (17, 16))
                a.add_patch(Circle((fx, fy), r, fill=on, alpha=0.35 if on else 1, fc="#D9692B" if on else "none",
                                   ec="#D9692B" if on else "#2F6FB0", lw=2.5 if on else 1.2))
        a.set_xlim(-0.5, 0.5); a.set_ylim(-0.5, 0.5); a.set_aspect("equal")
        a.set_title(f"matriz a {z:.0f} mm: {pct:.0f} % de solapamiento"); a.set_xlabel("frecuencia (1/µm)")
        a.set_ylabel("frecuencia (1/µm)" if z == 74 else "")
    fig.suptitle("Lo que ve cada LED en el espacio de frecuencias (rojo, NA 0,07)", fontsize=18)
    fig.text(0.5, 0.02, "Cada círculo es la pupila de un LED. Naranja: dos LEDs vecinos. Más lejos la matriz, más cerca los círculos y más se solapan.",
             ha="center", fontsize=13, color="0.3")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.16, wspace=0.2)
    fig.savefig(f"{OUT}/fig_motivo_4_distancia.png", dpi=90); plt.close(fig)


def fig5():
    B = "results/captura_2026-09-28_rgb"
    LAM = {"red": 630, "green": 530, "blue": 470}; NOM = {"red": "rojo", "green": "verde", "blue": "azul"}

    def to_grid(o, n=1200):
        H = o.shape[0]
        if H == n:
            return o
        S = np.fft.fftshift(np.fft.fft2(o)); a = (H - n) // 2
        return np.fft.ifft2(np.fft.ifftshift(S[a:a + n, a:a + n])) * (n / H) ** 2

    def shift_to(a, ref):
        R = np.fft.fft2(a - a.mean()) * np.conj(np.fft.fft2(ref - ref.mean())); R /= np.abs(R) + 1e-12
        r = np.fft.fftshift(np.real(np.fft.ifft2(R))); i = np.array(np.unravel_index(np.argmax(r), r.shape)) - np.array(r.shape) // 2
        return np.roll(a, tuple(-i), (0, 1))
    raw, amp = {}, {}
    for c in LAM:
        d = np.load(f"{B}/{c}/prep.npz"); i = [tuple(int(v) for v in k) for k in d["keys"]].index((18, 15))
        raw[c] = d["S"][i] / d["F"][i]
        amp[c] = np.abs(to_grid(np.load(f"{B}/{c}/out/obj_real_A+init_z74.0_full.npy").astype(complex)))
    for c in ("red", "blue"):
        raw[c] = shift_to(raw[c], raw["green"]); amp[c] = shift_to(amp[c], amp["green"])
    zl, zh = (slice(150, 250),) * 2, (slice(450, 750),) * 2
    fig, ax = plt.subplots(2, 3, figsize=(13, 9.8))
    for j, c in enumerate(LAM):
        for i, (im, t) in enumerate(((raw[c][zl], "foto cruda (luz directa)"), (amp[c][zh], "reconstrucción: amplitud"))):
            lo, hi = np.percentile(im, [1, 99.5]); ax[i, j].imshow(im, cmap="gray", vmin=lo, vmax=hi, extent=[0, 128, 128, 0]); ax[i, j].axis("off")
            ax[i, j].set_title(f"{NOM[c]} ({LAM[c]} nm)" + (", en foco" if c == "green" else "") + f"\n{t}", fontsize=14)
    fig.suptitle("Un solo foco (ajustado en verde): rojo y azul salen desenfocados", fontsize=18)
    fig.text(0.5, 0.025, "Captura de la tarde del 28/09, misma porción de 128 µm. Confirmación posterior (captura de la noche): el rojo en su propio foco\n"
             "predice las fotos que no usó con error 0,46; con el foco del verde, 0,81 (sin reconstruir, ~0,98).", ha="center", fontsize=13, color="0.3")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.1, hspace=0.2, wspace=0.05)
    fig.savefig(f"{OUT}/fig_motivo_5_foco.png", dpi=90); plt.close(fig)


pedidos = sys.argv[1:] or ["1", "2", "3", "4", "5"]
for k in pedidos:
    {"1": fig1, "2": fig2, "3": fig3, "4": fig4, "5": fig5}[k]()
    print("figura", k)

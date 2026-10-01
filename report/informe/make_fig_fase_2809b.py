"""Figura para la charla corta (slide de validación): foto cruda y fase reconstruida, captura 28/09 (b)
(matriz a 98 mm, cada color en su foco). Usa las salidas de results/captura_2026-09-28b/<color>/ (método A+init, z = 98 mm).

Procesamiento de la fase, sin nada que cree estructura:
1. Fase del objeto reconstruido completo, recortada a una zona de 128 µm.
2. Desenrollada con skimage.restoration.unwrap_phase: solo suma múltiplos de 2π donde la fase salta de -π a π, para que
   las partículas grandes (varios radianes) no se vean como anillos. Donde la amplitud es baja, el desenrollado puede
   equivocarse en una vuelta; la foto cruda al lado permite comparar.
3. Se resta un polinomio de orden 2 en x, y (fondo lento: inclinación y curvatura), ajustado por mínimos cuadrados solo
   en el 70 % de los píxeles más cercanos a la mediana (el fondo, no las partículas). Después se resta la mediana.
4. Escala de color lineal, de 0 a un tope fijo en radianes (último campo de CANDIDATAS); lo que supera el tope se pinta con el color máximo
   (escala saturada, declarada en la barra). No hay filtros de realce.
La foto cruda es la del LED del eje (18,15), dividida por la foto sin muestra, en la misma zona y del mismo color.

Correr desde la raíz del repo:
  python3 report/informe/make_fig_fase_2809b.py                    -> report/informe/img/fig_fase_2809b.png (elegida)
  python3 report/informe/make_fig_fase_2809b.py <carpeta> --todas  -> candidatas en <carpeta>/
"""
import os
import sys
import numpy as np
from skimage.restoration import unwrap_phase
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

B = "results/captura_2026-09-28b/"
NOMBRE = {"red": "Rojo (630 nm)", "green": "Verde (530 nm)", "blue": "Azul (470 nm)"}
# (color, fila y columna de la esquina en píxeles de la reconstrucción, rótulo de la zona, tope de la escala en rad)
# La zona de la slide 3 (fig_rgb_2809b) es la misma en los tres colores: 192 µm desde la esquina del campo de 512 µm.
CANDIDATAS = {
    "a_verde_misma_zona_tope1.5": ("green", 750, 750, "misma porción que la figura de los tres canales", 1.5),
    "b_verde_misma_zona_tope3": ("green", 750, 750, "misma porción que la figura de los tres canales", 3.0),
    "c_verde_otra_zona_tope1.5": ("green", 700, 300, "otra zona del mismo campo", 1.5),
    # descartada: en rojo el desenrollado falla (una región entera salta 2π arriba a la izquierda) por las franjas de fondo
    "x_rojo_misma_zona_descartada": ("red", 450, 450, "misma porción que la figura de los tres canales", 3.0),
}
ELEGIDA = "b_verde_misma_zona_tope3"
plt.rcParams.update({"font.size": 15, "axes.titlesize": 20})


def stretch(a, lo=0.5, hi=99.5):
    l, h = np.percentile(a, [lo, hi]); return np.clip((a - l) / (h - l), 0, 1)


def quitar_fondo(p, frac=70):
    n = p.shape[0]; y, x = np.mgrid[0:n, 0:n] / n
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    d = np.abs(p - np.median(p)); m = d < np.percentile(d, frac)
    c, *_ = np.linalg.lstsq(A[m], p[m], rcond=None)
    q = p - A @ c
    return q - np.median(q)


def figura(clave, out):
    color, r0, c0, zona, TOPE = CANDIDATAS[clave]
    o = np.load(f"{B}{color}/out/obj_real_A+init_z98.0_full.npy").astype(complex)
    hr = 512.0 / o.shape[0]; L = int(round(128 / hr)); f = o.shape[0] // 400
    ph = quitar_fondo(unwrap_phase(np.angle(o[r0:r0 + L, c0:c0 + L])))
    d = np.load(f"{B}{color}/prep.npz", allow_pickle=True)
    i = [tuple(k) for k in d["keys"]].index((18, 15))
    bf = (d["S"][i] / d["F"][i])[r0 // f:r0 // f + L // f, c0 // f:c0 // f + L // f]
    # ejes de posición fija: los dos paneles miden lo mismo; la barra de color va en un eje aparte
    fig = plt.figure(figsize=(11, 5.1))
    W, H, Y = 0.36, 0.36 * 11 / 5.1, 0.03
    ax = [fig.add_axes([0.03, Y, W, H]), fig.add_axes([0.45, Y, W, H])]
    cax = fig.add_axes([0.83, Y, 0.018, H])
    ax[0].imshow(stretch(bf), cmap="gray", extent=[0, 128, 128, 0]); ax[0].set_title("Foto cruda (luz directa)")
    im = ax[1].imshow(ph, cmap="magma", vmin=0, vmax=TOPE, extent=[0, 128, 128, 0]); ax[1].set_title("Fase desenrollada")
    for a in ax: a.axis("off")
    cb = fig.colorbar(im, cax=cax, extend="max")
    cb.set_label(f"retraso de la luz (rad; satura en {TOPE:g})", fontsize=14); cb.ax.tick_params(labelsize=14)
    ax[0].plot([8, 38], [120, 120], color="w", lw=5); ax[0].text(23, 113, "30 µm", color="w", ha="center", fontsize=17)
    fig.suptitle(f"{NOMBRE[color]}, {zona} (128 µm)", fontsize=17, y=0.985)
    plt.savefig(out, dpi=110); plt.close()
    print(out)


if "--todas" in sys.argv:
    carpeta = sys.argv[1]; os.makedirs(carpeta, exist_ok=True)
    for k in CANDIDATAS:
        figura(k, os.path.join(carpeta, f"fase_{k}.png"))
else:
    figura(ELEGIDA, "report/informe/img/fig_fase_2809b.png")

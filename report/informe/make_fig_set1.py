"""Figura para la charla y el resumen: la misma muestra en dos zonas (25/09, rojo). Set 3: partículas aisladas
que el modelo explica. Set 1: la luz inclinada está dominada por estrías en la dirección de iluminación
(dispersión en el volumen, fuera del modelo de muestra delgada). Correr desde la raíz del repo."""
import importlib.util
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt


def load(d):
    s = importlib.util.spec_from_file_location("F" + d[-4:], f"results/{d}/fpm_red.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.load_real()


D3, D1 = load("captura_2026-09-25_red"), load("captura_2026-09-25_red_set1")
ks = [((18, 15), "luz directa (18,15)"), ((19, 15), "luz inclinada (19,15)"), ((17, 20), "luz inclinada (17,20)"),
      ((21, 18), "luz inclinada (21,18)")]
fig, ax = plt.subplots(2, 4, figsize=(15, 7.6))
for i, (D, nm) in enumerate([(D3, "Zona 3: partículas aisladas"), (D1, "Zona 1: estrías en la dirección de la luz")]):
    for j, (k, t) in enumerate(ks):
        im = D["I"][k]; lo, hi = np.percentile(im, [1, 99.5])
        ax[i, j].imshow(im, cmap="gray", vmin=lo, vmax=hi); ax[i, j].axis("off")
        ax[i, j].set_title(f"{nm if j == 0 else ''}\n{t}", fontsize=12, loc="left")
fig.suptitle("Rojo, 25/09, dos zonas de la misma muestra: en la zona 1 el modelo no puede explicar la luz inclinada", fontsize=15)
fig.text(0.5, 0.01, "Cada foto: 512 µm. Las estrías siguen la dirección desde la que llega la luz de cada LED: luz dispersada por material fuera de foco.",
         ha="center", fontsize=11, color="0.35")
plt.tight_layout(rect=(0, 0.03, 1, 0.95)); plt.savefig("report/informe/img/fig_set1_vs_set3.png", dpi=100); plt.close()
print("report/informe/img/fig_set1_vs_set3.png")

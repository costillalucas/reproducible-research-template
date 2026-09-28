"""Figura para la charla: reconstruccion real en rojo (set 3, 2026-09-25), para no especialistas.
Usa las salidas de results/captura_2026-09-25_red (metodo A+init, z = 74 mm).
Correr desde la raiz del repo: python3 report/informe/make_fig_rojo.py"""
import numpy as np
from scipy import ndimage as ndi
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B = "results/captura_2026-09-25_red/"
OUT = "report/informe/img/fig_reconstruccion_roja.png"
plt.rcParams.update({"font.size": 12, "axes.titlesize": 14})

def stretch(a, lo=0.5, hi=99.5):
    l, h = np.percentile(a, [lo, hi]); return np.clip((a - l) / (h - l), 0, 1)

def rel_phase(o, sig=20):  # same as analyze.rel_phase: remove the slow phase background
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return np.angle(o * np.exp(-1j * np.angle(sm)))

d = np.load(B + "prep.npz", allow_pickle=True)
i = [tuple(k) for k in d["keys"]].index((17, 15))
bf = d["S"][i] / d["F"][i]              # direct-light photo divided by the no-sample flat
o = np.load(B + "out/obj_real_A+init_z74.0_full.npy").astype(complex)
zl, zs = (slice(150, 250),) * 2, (slice(450, 750),) * 2   # the same 128 um zone in LR and HR pixels
panels = [(bf[zl], "Foto cruda (luz directa)", "gray"),
          (np.abs(o)[zs], "Reconstrucción: brillo", "gray"),
          (rel_phase(o)[zs], "Reconstrucción: fase", "magma")]
fig, ax = plt.subplots(1, 3, figsize=(15, 5.4))
for a, (im, t, cm) in zip(ax, panels):
    a.imshow(stretch(im), cmap=cm, extent=[0, 128, 128, 0]); a.set_title(t); a.axis("off")
ax[0].plot([8, 38], [120, 120], color="w", lw=4); ax[0].text(23, 115, "30 µm", color="w", ha="center", fontsize=12)
fig.suptitle("Rojo, 25/09: la reconstrucción muestra las partículas y su fase, sin el patrón en red del verde", fontsize=16, y=0.99)
fig.text(0.5, 0.015, "Misma zona de 128 µm. La fase (cuánto se retrasa la luz) no aparece en ninguna foto: la deduce el programa.",
         ha="center", fontsize=11, color="0.35")
plt.tight_layout(rect=(0, 0.04, 1, 0.95)); plt.savefig(OUT, dpi=110); plt.close()
print(OUT)

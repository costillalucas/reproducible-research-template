"""Recorte, sin reprocesar, de la fila de arriba de docs/resultados_2026-09-29/conjunta/figs/fig3_mapas_t.png
(verdad de la simulación contra la reconstrucción conjunta A1_D1 a 240 épocas), para el apéndice de la charla de 5 minutos.
Solo recorta píxeles: no cambia datos ni escala. Correr desde la raíz del repo:
  python3 report/informe/make_fig_conjunta_recorte.py -> report/informe/img/fig_conjunta_verdad_vs_conjunta.png
Con --charla: redibuja los dos paneles desde los arreglos ya guardados del trabajo
(jobs/2026-09-29_170433_derive-conjunta-3colores-v3/work/conjunta_2026-09-30, mismo cálculo que su figuras.py, fig 3),
con títulos para la charla y barra de escala -> report/presentacion_agentes/img_charla/fig_conjunta_verdad_vs_conjunta.png
Escala: grilla común de 1600 px x 0.32 µm (comun.py:54-57, 87: LRPX = 1.28 µm / FACTOR 4), menos MARGEN = 100 px por
borde (comun.py:59; figuras.py recortar) -> 1400 px = 448 µm por panel."""
import sys
if "--charla" not in sys.argv:
    from PIL import Image
    im = Image.open("docs/resultados_2026-09-29/conjunta/figs/fig3_mapas_t.png")
    w, h = im.size
    im.crop((0, 45, w, 540)).save("report/informe/img/fig_conjunta_verdad_vs_conjunta.png")
    print(im.size, "->", (w, 540 - 45))
    sys.exit(0)

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
J = os.path.abspath("jobs/2026-09-29_170433_derive-conjunta-3colores-v3/work/conjunta_2026-09-30")
sys.path.insert(0, J); sys.path.insert(0, os.path.abspath("src"))
import metricas as M  # noqa: E402

PX = 0.32                                   # µm/px de la grilla común (comun.py:87)
assert abs(M.PX - PX) < 1e-12, M.PX         # metricas.py:105, vía optics.actual_hr_pixel_size_um(setup, 4)
rec = lambda a: np.asarray(a, float)[M.MARGEN:-M.MARGEN, M.MARGEN:-M.MARGEN]
t_ref = M.t_referencia()
with np.load(os.path.join(J, "out", "A1_D1.npz"), allow_pickle=True) as d:
    t_con = np.asarray(d["t"], float)
s1 = M.S1(t_con)
print(f"S1 A1_D1 = {s1:+.4f}")
vmax = float(np.percentile(rec(t_ref), 99))
LADO = rec(t_ref).shape[0] * PX             # 448 µm

def barra(ax, img, um=100):
    n = img.shape[0]; zona = img[int(0.8 * n):, :int(0.4 * n)]
    c, o = ("w", "k") if np.mean(np.clip(zona / vmax, 0, 1)) < 0.6 else ("k", "w")
    x0, y = 0.05 * LADO, 0.93 * LADO
    ax.plot([x0, x0 + um], [y, y], color=c, lw=5, solid_capstyle="butt",
            path_effects=[pe.Stroke(linewidth=8, foreground=o), pe.Normal()])
    ax.text(x0 + um / 2, y - 0.035 * LADO, f"{um} µm", color=c, ha="center", va="bottom", fontsize=15,
            path_effects=[pe.withStroke(linewidth=3, foreground=o)])

dec = lambda v: f"{v:.2f}".replace("-", "−").replace(".", ",")
paneles = [("Verdad (filtrada a la banda de los LEDs)\n ", t_ref),
           (f"Reconstrucción conjunta, 240 épocas\ncorrelación con la verdad: {dec(s1)}", t_con)]
fig = plt.figure(figsize=(11, 5.3))
W, H, Y = 0.37, 0.37 * 11 / 5.3, 0.02
ax = [fig.add_axes([0.02, Y, W, H]), fig.add_axes([0.44, Y, W, H])]
cax = fig.add_axes([0.84, Y, 0.018, H])
for a, (t, arr) in zip(ax, paneles):
    r = rec(arr)
    im = a.imshow(r, cmap="viridis", vmin=0, vmax=vmax, extent=[0, LADO, LADO, 0])
    a.set_title(t, fontsize=15); a.axis("off"); barra(a, r)
cb = fig.colorbar(im, cax=cax); cb.set_label("espesor (µm)", fontsize=14); cb.ax.tick_params(labelsize=13)
out = "report/presentacion_agentes/img_charla"; os.makedirs(out, exist_ok=True)
fig.savefig(f"{out}/fig_conjunta_verdad_vs_conjunta.png", dpi=110, bbox_inches="tight", pad_inches=0.08)
print(f"{out}/fig_conjunta_verdad_vs_conjunta.png")

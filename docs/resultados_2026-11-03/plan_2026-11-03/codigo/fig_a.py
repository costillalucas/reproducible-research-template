"""fig_a.py -- figuras de la tarea A: cuadros completos del LED central (azul 29/10 vs rojo-b 30/10) y panel 2x3 del recorte."""
import os, sys, numpy as np, tifffile, cv2, json
from scipy import ndimage as ndi
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import comun_plan as C
T = "/home/chanoscopio/Documents/AleYLu/imagenes_tomadas"; P = C.P
def L(p): x = tifffile.imread(p).astype(np.float32); return x
def bpn(x): x = x / ndi.gaussian_filter(x, 40); return (ndi.gaussian_filter(x, 1.5) - ndi.gaussian_filter(x, 10)).astype(np.float32)
fb = f"{T}/2026-10-29-blue/fila17_col15_colorb/16ms/imagen_frame_1.tiff"
fr = f"{T}/2026-10-30-red-b/fila17_col15_colorr/16ms/imagen_frame_1.tiff"
B, Rr = L(fb), L(fr)
# búsqueda del arco (parche azul filas 300:600, col 450:750) y de 4 parches más del cuadro azul dentro del cuadro rojo-b completo
bb, rb = bpn(B), bpn(Rr); out = []
for (f0, c0) in [(300, 450), (700, 100), (50, 50), (750, 650), (100, 700)]:
    t = bb[f0:f0 + 300, c0:c0 + 300]; res = cv2.matchTemplate(rb, t, cv2.TM_CCOEFF_NORMED); _, m, _, l = cv2.minMaxLoc(res)
    out.append(dict(parche_azul_fila_col=[f0, c0], ncc_max_en_rojo_b=round(float(m), 3), en_fila_col=[l[1], l[0]],
                    ncc_mismo_lugar=round(float(res[f0, c0]), 3)))
t = bb[300:600, 450:750]; res = cv2.matchTemplate(bpn(L(f"{T}/2026-10-29-blue-prueba-1151/fila17_col15_colorb/8ms/imagen_frame_1.tiff")), t, cv2.TM_CCOEFF_NORMED)
out.append(dict(control="mismo parche del arco en 2026-10-29-blue-prueba-1151 (otra toma azul)", ncc_max=round(float(res.max()), 3)))
json.dump(out, open(f"{P}/a_busqueda_campo.json", "w"), indent=1)
fig, ax = plt.subplots(1, 2, figsize=(11, 5.6))
for a, x, t in zip(ax, [B, Rr], ["2026-10-29-blue, LED (17,15) 16 ms, ROI 4000,874", "2026-10-30-red-b, LED (17,15) 16 ms, ROI 4000,874"]):
    lo, hi = np.percentile(x, [1, 99]); a.imshow(x, cmap="gray", vmin=lo, vmax=hi)
    a.add_patch(plt.Rectangle((415, 290), 400, 400, fill=False, color="y", lw=1.5)); a.set_title(t, fontsize=9); a.axis("off")
fig.suptitle("Cuadro completo del sensor (1120 px = 1.44 mm); recuadro amarillo = recorte 290,415 de ambas reconstrucciones", fontsize=9)
fig.tight_layout(); fig.savefig(f"{P}/fig_a_campos_completos.png", dpi=90)
# panel 2x3 del recorte
D = np.load(f"{P}/codigo/alineados_tmp.npz")
Or = np.load(f"{C.R}/2026-10-30-red-b_arco/objeto_complejo.npy"); Ob = C.fourier_resample(np.load(f"{C.R}/2026-10-29-blue_arco/objeto_complejo.npy").astype(complex), 1200)
ims = [(D["raw_b"], "azul: crudo (17,15)/flat, amplitud"), (np.abs(Ob), "azul: |O| (remuestreado a 0.43 µm)"), (C.rel_phase(Ob), "azul: fase relativa [rad]"),
       (np.real(C.fourier_resample(np.sqrt(np.clip(np.load(f"{C.R}/2026-10-30-red-b_arco/datos/prep.npz")["S"][112] / np.load(f"{C.R}/2026-10-30-red-b_arco/datos/prep.npz")["F"][112], 0, None)), 1200)), "rojo-b: crudo (17,15)/flat, amplitud"),
       (np.abs(Or), "rojo-b: |O|"), (C.rel_phase(Or), "rojo-b: fase relativa [rad]")]
fig, ax = plt.subplots(2, 3, figsize=(13, 8.8)); ext = [0, 1200 * 0.43, 1200 * 0.43, 0]
for a, (x, t) in zip(ax.ravel(), ims):
    lo, hi = np.percentile(x, [1, 99]); im = a.imshow(x, cmap="gray", vmin=lo, vmax=hi, extent=ext); a.set_title(t, fontsize=9)
    a.set_xlabel("µm", fontsize=8)
fig.suptitle("Recorte filas 290:690, col 415:815 (516 µm), grilla común 0.43 µm. Arriba azul 29/10, abajo rojo-b 30/10 (sin registrar: no hay campo común)", fontsize=9)
fig.tight_layout(); fig.savefig(f"{P}/fig_a_panel_2x3.png", dpi=85)
print(json.dumps(out, indent=0))

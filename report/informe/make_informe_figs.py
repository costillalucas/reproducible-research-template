"""Figuras del informe para no especialistas (captura 2026-09-24 y control sintetico).
Correr desde la raiz del repo: python3 report/informe/make_informe_figs.py"""
import os, shutil, sys, numpy as np, tifffile
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT = "report/informe/img"; os.makedirs(OUT, exist_ok=True)
R = os.path.expanduser("~/Documents/AleYLu/imagenes_tomadas/")
plt.rcParams.update({"font.size": 12, "axes.titlesize": 13})

def stretch(a, lo=0.5, hi=99.5):
    l, h = np.percentile(a, [lo, hi]); return np.clip((a - l) / (h - l), 0, 1)

def raw(r, c, ms):
    a = tifffile.imread(R + f"2026-09-24_green_enfocado/organizado/green/{ms}/fila{r}_col{c}.tiff").astype(float)
    d = tifffile.imread(R + f"2026-09-24_dark/organizado/green/{ms}/fila18_col15.tiff").astype(float)
    return (a - d)[360:760, 360:760]   # the same central 400 px crop the reconstructions use

def scalebar(ax, px_um, n, um=100):
    L = um / px_um; ax.plot([n * 0.06, n * 0.06 + L], [n * 0.93] * 2, color="w", lw=4)
    ax.text(n * 0.06 + L / 2, n * 0.89, f"{um} µm", color="w", ha="center", fontsize=11)

# 1. fotos crudas
sel = [((18, 15), "10ms", "Luz directa"), ((18, 17), "100ms", "Luz inclinada, 2 LEDs"),
       ((18, 20), "100ms", "Luz inclinada, 5 LEDs"), ((13, 15), "100ms", "Luz inclinada, 5 LEDs (otra dirección)")]
fig, ax = plt.subplots(1, 4, figsize=(16, 4.6))
for a, ((r, c), ms, t) in zip(ax, sel):
    a.imshow(stretch(raw(r, c, ms)), cmap="gray"); a.set_title(t); a.axis("off")
scalebar(ax[0], 1.28, 400)
fig.suptitle("Fotos crudas de la misma zona: cada ángulo de luz muestra otra cosa", fontsize=15, y=0.99)
fig.text(0.5, 0.01, "Verde, 24/09. Zona de 0,5 mm. Con luz inclinada solo llega la luz que desvía la muestra: las partículas se ven como puntos brillantes.",
         ha="center", fontsize=10.5, color="0.35")
plt.tight_layout(rect=(0, 0.04, 1, 0.95)); plt.savefig(f"{OUT}/fig_crudas.png", dpi=110); plt.close()

# 2. reconstruccion real
todos = np.load("results/captura_2026-09-24/j3/t4_final/obj_green_todos.npy")
solo = np.load("results/captura_2026-09-24/j3/t4_final/obj_green_solo_100ms.npy")
from PIL import Image
red128 = np.asarray(Image.open("results/captura_2026-09-24/test_green_c128/reconstructed_amplitude.png")).astype(float)
bf = raw(18, 15, "10ms")
s = 5  # upsampling factor at crop 400 -> 2000 px; show the same 128 LR px region as the crop-128 test
c0, n = (400 - 128) // 2, 128
fig, ax = plt.subplots(1, 4, figsize=(16, 4.6))
ax[0].imshow(stretch(bf[c0:c0 + n, c0:c0 + n]), cmap="gray"); ax[0].set_title("Foto cruda (luz directa)")
ax[1].imshow(stretch(red128), cmap="gray"); ax[1].set_title("Reconstrucción, recorte chico")
ax[2].imshow(stretch(np.abs(todos)[c0 * s:(c0 + n) * s, c0 * s:(c0 + n) * s]), cmap="gray"); ax[2].set_title("Recorte grande")
ax[3].imshow(stretch(np.abs(solo)[c0 * s:(c0 + n) * s, c0 * s:(c0 + n) * s]), cmap="gray"); ax[3].set_title("Recorte grande, sin luz directa")
for a in ax: a.axis("off")
scalebar(ax[0], 1.28, n, 50)
fig.suptitle("Las reconstrucciones muestran patrones regulares que no están en la muestra", fontsize=15, y=0.99)
fig.text(0.5, 0.01, "Misma zona de 164 µm, verde, 24/09. Brillo reconstruido. El patrón cambia con decisiones del programa (tamaño del recorte, qué fotos usa).",
         ha="center", fontsize=10.5, color="0.35")
plt.tight_layout(rect=(0, 0.04, 1, 0.95)); plt.savefig(f"{OUT}/fig_reconstruccion_real.png", dpi=110); plt.close()

# 3. sintetico: verdad vs reconstruccion con la geometria de hoy
sys.path.insert(0, "src")
from ptyco_full_simulator import config, led_array, optics, forward_model, reconstruction
st = config.default_setup("green", 13, objective="2_5x_na007", resolution_px=(128, 128), row_index_base=12,
                          col_index_base=9, z_distance_mm=75.0, led_center_offset_mm=(0.0, 3.0))
f = optics.upsampling_factor(st); hp = optics.actual_hr_pixel_size_um(st, f); lp = st.lr_pixel_size_um
import skimage.data as skd
from PIL import Image as _I
H = 128 * f
def _rs(a): a = np.asarray(_I.fromarray(a.astype(np.float32)).resize((H, H), _I.LANCZOS), float); return (a - a.min()) / np.ptp(a)
obj = (0.1 + 0.9 * _rs(skd.camera())) * np.exp(1j * 1.2 * _rs(skd.moon()))
grid = led_array.build_led_grid(st.led_array, st.wavelength_um)
lr = forward_model.simulate_lr_stack(obj, hp, grid, (128, 128), lp, st.objective.na, st.wavelength_um)
rec = reconstruction.reconstruct(lr, grid, hp, lp, st.objective.na, st.wavelength_um, f, iterations=100,
                                 step_relative=0.3, normalize_initial_guess=True)["object"]
key = min(lr, key=lambda k: abs(k[0] - 17.5) + abs(k[1] - 15))
fig, ax = plt.subplots(2, 3, figsize=(12, 9), gridspec_kw={"hspace": 0.25})
ax[0, 0].imshow(np.abs(obj), cmap="gray"); ax[0, 0].set_title("Muestra inventada: brillo")
ax[0, 1].imshow(lr[key], cmap="gray"); ax[0, 1].set_title("Una de las 169 fotos simuladas")
ax[0, 2].imshow(np.abs(rec), cmap="gray"); ax[0, 2].set_title("Reconstrucción: brillo")
ax[1, 0].imshow(np.angle(obj), cmap="viridis", vmin=0, vmax=1.2); ax[1, 0].set_title("Muestra inventada: fase")
ax[1, 1].axis("off"); ax[1, 1].text(0.5, 0.5, "La fase no aparece\nen ninguna foto:\nel programa la deduce", ha="center", va="center", fontsize=13)
ph = np.angle(rec * np.exp(-1j * np.angle(np.vdot(rec, obj).conj())))
ax[1, 2].imshow(ph, cmap="viridis", vmin=0, vmax=1.2); ax[1, 2].set_title("Reconstrucción: fase")
for a in ax.flat: a.set_xticks([]); a.set_yticks([])
ax[1, 1].axis("off")
fig.suptitle("Con datos simulados el programa recupera la muestra, incluida la fase", fontsize=15)
fig.text(0.5, 0.01, "Geometría real del montaje (13×13 LEDs, 75 mm, objetivo 2,5×), sin ruido, 100 iteraciones.", ha="center", fontsize=10.5, color="0.35")
plt.subplots_adjust(top=0.9, bottom=0.06); plt.savefig(f"{OUT}/fig_sintetico.png", dpi=100); plt.close()

# 4. congelado vs corregido: la figura ya existente de la presentación
LRD = os.path.expanduser("~/Documents/AleYLu/imagenes_tomadas/2025-12-12/organizado/green/9x9_recortada_400")
lr = np.asarray(Image.open(os.path.join(LRD, "fila17_col15.tiff")), float)
y0 = (lr.shape[0] - 128) // 2; lr_c = np.sqrt(np.clip(lr[y0:y0 + 128, y0:y0 + 128], 0, None))
fro = np.load("results/led_geometry_2025-12-12/fig09_frozen_panel.npz")["amplitude"]
tha = np.load("results/residual_floor_2025-12-12/fig09_thawed_panels.npz")["amplitude"]
fig, ax = plt.subplots(1, 3, figsize=(13, 4.9))
for a, im, t in zip(ax, [lr_c, fro, tha], ["Foto cruda\n ", "Algoritmo congelado\ndevuelve casi la misma foto", "Algoritmo corregido\nse mueve, pero da un moteado"]):
    a.imshow(stretch(im, 1, 99), cmap="gray"); a.set_title(t); a.axis("off")
fig.suptitle("Con los datos reales, el algoritmo no hacía nada", fontsize=15, y=0.99)
fig.text(0.5, 0.01, "Captura de diciembre de 2025, verde, zona de 205 µm. El congelamiento no se veía en las pruebas porque usaban imágenes diminutas.", ha="center", fontsize=10.5, color="0.35")
plt.tight_layout(rect=(0, 0.05, 1, 0.94)); plt.savefig(f"{OUT}/fig_congelado.png", dpi=110); plt.close()
print("ok", os.listdir(OUT))

"""Auditoría ítem 9: ¿el signo del offset del LED por posición en el sensor coincide con los datos?
Mide, en el flat (sin muestra) de los LEDs diagonales/borde, el brillo medio por tercios del ROI (izq/centro/der, arriba/centro/abajo)."""
import glob, numpy as np, tifffile
D = "/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/"
def img(car, k):
    d = glob.glob(f"{D}{car}/fila{k[0]}_col{k[1]}_colorr/*ms")
    d = max(d, key=lambda p: float(p.rsplit('/',1)[1][:-2]))
    t = float(d.rsplit('/',1)[1][:-2])
    fr = sorted(glob.glob(d + "/imagen_frame_*.tif*"))[:2]
    dk = glob.glob(f"{D}{car}-dark/*/{int(t)}ms/imagen_frame_*.tif*")[:2]
    dark = np.mean([tifffile.imread(f) for f in dk], 0) if dk else 189.
    return (np.mean([tifffile.imread(f).astype(float) for f in fr], 0) - dark) / t
for car in ("2026-11-03-red-sinmuestra", "2026-11-03-red"):
    print("==", car)
    for k in [(18,14),(18,16),(16,14),(16,16),(17,14),(17,16),(16,15),(18,15)]:
        a = img(car, k)
        cols = [a[:, s].mean() for s in (np.s_[0:373], np.s_[373:746], np.s_[746:1120])]
        rows = [a[s, :].mean() for s in (np.s_[0:373], np.s_[373:746], np.s_[746:1120])]
        crop = a[360:760, 80:480].mean()
        print(k, "cols izq/cen/der", " ".join(f"{v:7.3f}" for v in cols), "| filas arr/cen/aba", " ".join(f"{v:7.3f}" for v in rows), "| recorte %.3f" % crop)

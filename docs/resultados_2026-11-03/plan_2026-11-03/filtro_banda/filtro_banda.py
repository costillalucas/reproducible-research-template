"""Filtro pasabanda (anillo en k) aplicado igual a mitades A/B, completo y nulo.
Banda objetivo elegida por Lucas 03/11: k ~ 0.3 1/um (periodo 3.33 um), mas bandas de control.
OJO: la banda se eligio DESPUES de ver la joroba del FRC entre mitades -> sesgo de seleccion; por eso se reportan bandas vecinas."""
import numpy as np, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/"
CORR = {"red-c NA0.074": R+"plan_2026-11-03/red-c_na074/",
        "red-c NA0.0669": R+"2026-10-30-red-c/",
        "nulo DF (NA0.0669)": R+"plan_2026-11-03/red-c_nulo_df/"}
DX = 0.43  # um
BANDAS = {"control baja 0.12-0.20": (0.12, 0.20), "OBJETIVO 0.25-0.35": (0.25, 0.35), "control alta 0.38-0.45": (0.38, 0.45)}
M = 60  # margen px

def mapas(O):
    O = O / np.mean(O)
    return {"amp": np.abs(O) - np.mean(np.abs(O)), "fase": np.angle(O) - np.mean(np.angle(O))}

def pasabanda(x, k1, k2, suave=0.01):
    n = x.shape[0]; f = np.fft.fftfreq(n, DX); kx, ky = np.meshgrid(f, f); k = np.hypot(kx, ky)
    w = np.clip((k - (k1 - suave)) / (2*suave), 0, 1) * np.clip(((k2 + suave) - k) / (2*suave), 0, 1)
    w = 0.5 - 0.5*np.cos(np.pi*w)
    return np.real(np.fft.ifft2(np.fft.fft2(x) * w))

def r(a, b):
    a = a[M:-M, M:-M].ravel(); b = b[M:-M, M:-M].ravel(); return float(np.corrcoef(a, b)[0, 1])

res, filtrados = {}, {}
for nombre, d in CORR.items():
    O = {h: mapas(np.load(d + f"objeto_{h}.npy")) for h in ("mitadA", "mitadB", "complejo")}
    for bn, (k1, k2) in BANDAS.items():
        F = {h: {c: pasabanda(O[h][c], k1, k2) for c in ("amp", "fase")} for h in O}
        res[(nombre, bn)] = {
            "A-B amp": r(F["mitadA"]["amp"], F["mitadB"]["amp"]),
            "A-B fase": r(F["mitadA"]["fase"], F["mitadB"]["fase"]),
            "amp-fase (A)": r(F["mitadA"]["amp"], F["mitadA"]["fase"]),
            "amp-fase (B)": r(F["mitadB"]["amp"], F["mitadB"]["fase"]),
            "amp-fase (completa)": r(F["complejo"]["amp"], F["complejo"]["fase"]),
            # control de desalineacion: mitad B corrida 40 px (~17 um)
            "A-B amp corrida": r(F["mitadA"]["amp"], np.roll(F["mitadB"]["amp"], 40, axis=(0, 1))),
        }
        if bn.startswith("OBJETIVO"): filtrados[nombre] = F

cols = list(next(iter(res.values())).keys())
lin = ["| reconstrucción | banda (1/µm) | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 2)]
for (n, b), v in res.items():
    lin.append(f"| {n} | {b} | " + " | ".join(f"{v[c]:+.3f}" for c in cols) + " |")
tabla = "\n".join(lin); print(tabla)
open("tabla.md", "w").write(tabla + "\n")
json.dump({f"{n} | {b}": v for (n, b), v in res.items()}, open("tabla.json", "w"), indent=1)

# figura: zoom 100 um (233 px) en el centro, banda objetivo, amp y fase, mitades A/B, real NA0.074 vs nulo
c0, w = 600, 233; s = slice(c0 - w//2, c0 + w//2)
fig, ax = plt.subplots(2, 4, figsize=(16, 8.5))
for i, n in enumerate(["red-c NA0.074", "nulo DF (NA0.0669)"]):
    for j, (h, c) in enumerate([("mitadA", "amp"), ("mitadB", "amp"), ("mitadA", "fase"), ("mitadB", "fase")]):
        im = filtrados[n][h][c][s, s]; v = np.percentile(np.abs(filtrados[n][h][c][M:-M, M:-M]), 99)
        ax[i, j].imshow(im, cmap="RdBu_r", vmin=-v, vmax=v, extent=[0, w*DX, w*DX, 0])
        ax[i, j].set_title(f"{n}\n{h} {c}  (banda 0.25-0.35 1/µm)", fontsize=9)
fig.suptitle("Mismo filtro pasabanda en las dos mitades de LEDs: real (arriba) vs nulo DF (abajo). Zoom central 100 µm")
plt.tight_layout(); plt.savefig("fig_filtro_mitades.png", dpi=90)

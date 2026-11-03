"""fig_bc_objetos.py -- |O| y fase relativa, zoom central 400x400 px HR (172 µm), de real / NA 0.074 / nulo DF, arco y red-c."""
import os, sys, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import comun_plan as C
P, R = C.P, C.R
filas = [("rojo-b (arco)", [f"{R}/2026-10-30-red-b_arco", f"{P}/red-b_arco_na074", f"{P}/red-b_arco_nulo_df"]),
         ("red-c", [f"{R}/2026-10-30-red-c", f"{P}/red-c_na074", f"{P}/red-c_nulo_df"])]
tit = ["NA 0.0669", "NA 0.074", "nulo DF (NA 0.0669)"]
fig, ax = plt.subplots(4, 3, figsize=(11, 14.5)); s = slice(400, 800); ext = [0, 400 * 0.43, 400 * 0.43, 0]
for i, (nom, ds) in enumerate(filas):
    for j, d in enumerate(ds):
        for q in range(2):
            a = ax[2 * i + q, j]
            if not os.path.exists(f"{d}/objeto_complejo.npy"):
                a.set_title(f"{nom} {tit[j]}: no disponible", fontsize=8); a.axis("off"); continue
            o = np.load(f"{d}/objeto_complejo.npy").astype(complex)
            x = (np.abs(o) if q == 0 else C.rel_phase(o))[s, s]
            lo, hi = np.percentile(x, [1, 99]); a.imshow(x, cmap="gray", vmin=lo, vmax=hi, extent=ext)
            a.set_title(f"{nom}, {tit[j]}: {'|O|' if q == 0 else 'fase rel.'}", fontsize=8); a.tick_params(labelsize=7)
fig.suptitle("Zoom central 400x400 px HR (172 µm, píxel 0.43 µm); escala de grises 1-99 % por panel", fontsize=9)
fig.tight_layout(); fig.savefig(f"{P}/fig_bc_objetos.png", dpi=80)

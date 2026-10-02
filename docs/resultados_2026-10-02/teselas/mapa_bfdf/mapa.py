"""mapa.py -- mapa analítico BF/DF por LED en el campo de 400 px (28/09b), modelo de fuente puntual.
En el punto r de la muestra, LED j: sin(theta) = (r_LED - r)/sqrt(|r_LED - r|^2 + z^2); BF sii |sin| < NA.
Error de k del modelo de k único (k evaluado en r=0, como hace la reconstrucción) en bins espectrales
(1 bin = 1/(400*lrpx)) y como fracción del radio de pupila NA/λ."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "results", "captura_2026-09-24", "j3", "common"))
import cv_common as cc
from ptyco_full_simulator import config, led_array

Z, NA, CROP, N = 98.0, 0.07, 400, 201          # N: muestreo del campo (201x201 puntos)
DIE = {"red": 1.06, "green": 0.63, "blue": 0.15}
# radio BF ajustado libre en docs/resultados_2026-10-01/geometria/frontera (conjunto_R_libre), del que salen los DIE
RLIB = {"red": 7.074, "green": 7.122, "blue": 7.108}
out = {}
for color in ("red", "green", "blue"):
    for var, dy, Rbf in (("nominal", 0.0, None), ("die", DIE[color], None), ("die_Rlibre", DIE[color], RLIB[color])):
        na = NA if Rbf is None else float(np.sin(np.arctan(Rbf / Z)))
        s = config.default_setup(color, 15, objective=cc.OBJECTIVE, resolution_px=(CROP, CROP), row_index_base=11,
                                 col_index_base=8, z_distance_mm=Z, led_center_offset_mm=(0.0, 3.0 + dy))
        lam, lrpx, cfg = s.wavelength_um, s.lr_pixel_size_um, s.led_array
        half = CROP * lrpx / 2 / 1000.0                     # mm
        u = np.linspace(-half, half, N)
        X, Y = np.meshgrid(u, u)                            # X: columnas (x), Y: filas (y), mm
        binw = 1.0 / (CROP * lrpx)                          # µm^-1
        rp = NA / lam / binw   # pupila del objetivo (NA 0.07) para normalizar                                # radio de pupila en bins
        leds = {}
        for row in range(cfg.row_base, cfg.row_base + cfg.grid_size):
            for col in range(cfg.col_base, cfg.col_base + cfg.grid_size):
                lx, ly = led_array.led_position_mm(row, col, cfg)
                dx, dy_ = lx - X, ly - Y
                D = np.sqrt(dx**2 + dy_**2 + Z**2)
                sx, sy = dx / D, dy_ / D
                bf = np.hypot(sx, sy) < na
                s0x, s0y = lx / np.sqrt(lx**2 + ly**2 + Z**2), ly / np.sqrt(lx**2 + ly**2 + Z**2)
                kerr = np.hypot(sx - s0x, sy - s0y) / lam / binw   # bins
                Rbf_ = Z * np.tan(np.arcsin(na))
                leds[(row, col)] = dict(bf=bf, kerr=kerr, sx=sx, sy=sy, front_um=(Rbf_ - np.hypot(lx, ly)) * 1000,
                                        frac=float(bf.mean()))
        out[(color, var)] = dict(na=na, leds=leds, rp=rp, lam=lam, lrpx=lrpx, half_um=half * 1000, binw=binw)

def tiles(n):
    idx = np.array_split(np.arange(N), n)
    return [(a, b) for a in idx for b in idx]

summary = {}
lines = []
P = lambda *a: lines.append(" ".join(str(x) for x in a))
for (color, var), o in out.items():
    L = o["leds"]
    P(f"\n## {color} {var} (NA_BF={o['na']:.4f}): λ={o['lam']} µm, lrpx={o['lrpx']:.4f} µm, campo ±{o['half_um']:.0f} µm, "
      f"radio pupila {o['rp']:.1f} bins (1 bin = {o['binw']*1e3:.3f} mm^-1)")
    strad = {k: v for k, v in L.items() if 0 < v["frac"] < 1}
    nbf = sum(v["frac"] == 1 for v in L.values())
    P(f"BF en todo el campo: {sorted(k for k, v in L.items() if v['frac'] == 1)}")
    for k, v in sorted(strad.items()):
        P(f"  A HORCAJADAS {k}: fracción BF={v['frac']:.3f}, frontera a {v['front_um']:+.0f} µm del centro "
          f"(+ = centro BF), err k max={v['kerr'].max():.2f} bins")
    km = np.array([v["kerr"].max() for v in L.values()])
    kmax_key = max(L, key=lambda k: L[k]["kerr"].max())
    P(f"err k max (campo completo): rango {km.min():.2f}-{km.max():.2f} bins = {km.min()/o['rp']:.3f}-{km.max()/o['rp']:.3f} R_pupila (peor {kmax_key})")
    tl = {}
    for n in (1, 2, 3, 4):
        st, ke = [], []
        for a, b in tiles(n):
            ca, cb = a[len(a)//2], b[len(b)//2]
            st.append(sum(1 for v in L.values() if 0 < v["bf"][np.ix_(a, b)].mean() < 1))
            ke.append(max(float(np.hypot(v["sx"][np.ix_(a, b)] - v["sx"][ca, cb], v["sy"][np.ix_(a, b)] - v["sy"][ca, cb]).max())
                          / o["lam"] / o["binw"] for v in L.values()))
        tl[n] = dict(strad_per_tile=st, n_tiles_with_straddle=int(sum(x > 0 for x in st)), kerr_tile_max_bins=max(ke), kerr_tile_max_frac=max(ke) / o['rp'])
        P(f"  teselas {n}x{n} ({CROP//n} px): horcajadas/tesela = {st}; err k max (vs k del centro de la tesela) = {max(ke):.2f} bins = {max(ke)/o['rp']:.3f} R_pup")
    summary[f"{color}_{var}"] = dict(rp_bins=o["rp"], straddle={str(k): dict(frac=v["frac"], front_um=v["front_um"],
                                     kerr_max=float(v["kerr"].max())) for k, v in strad.items()},
                                     kerr_max_bins=float(km.max()), kerr_max_frac=float(km.max() / o["rp"]),
                                     n_bf_full=int(nbf), tiles=tl)
print("\n".join(lines))
open(os.path.join(HERE, "salida.txt"), "w").write("\n".join(lines) + "\n")
json.dump(summary, open(os.path.join(HERE, "resumen.json"), "w"), indent=1)

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
vars_ = ("nominal", "die", "die_Rlibre"); cols = ("red", "green", "blue")
fig, axs = plt.subplots(3, 3, figsize=(11, 10.5), constrained_layout=True)
for i, var in enumerate(vars_):
    for j, color in enumerate(cols):
        L = out[(color, var)]["leds"]; ax = axs[i, j]
        rows = sorted({k[0] for k in L}); cl = sorted({k[1] for k in L})
        sub_r = [r for r in rows if 14 <= r <= 21]; sub_c = [c for c in cl if 11 <= c <= 19]
        M = np.array([[L[(r, c)]["frac"] for c in sub_c] for r in sub_r])
        im = ax.imshow(M, cmap="viridis", vmin=0, vmax=1, origin="upper")
        for a_, r in enumerate(sub_r):
            for b_, c in enumerate(sub_c):
                f = M[a_, b_]
                if 0 < f < 1: ax.text(b_, a_, f"{f:.2f}", ha="center", va="center", fontsize=8, color="w" if f < .5 else "k", weight="bold")
                elif f == 1: ax.text(b_, a_, "BF", ha="center", va="center", fontsize=7, color="k")
        ax.set_xticks(range(len(sub_c)), sub_c, fontsize=7); ax.set_yticks(range(len(sub_r)), sub_r, fontsize=7)
        ax.set_title(f"{color} - {var} (NA_BF {out[(color, var)]['na']:.4f})", fontsize=9)
        if j == 0: ax.set_ylabel("fila LED")
        if i == 2: ax.set_xlabel("columna LED")
fig.colorbar(im, ax=axs, shrink=0.6, label="fracción del campo 400 px en campo claro")
fig.suptitle("28/09b: fracción BF por LED (fuente puntual, z=98 mm). Números = LEDs a horcajadas", fontsize=11)
fig.savefig(os.path.join(HERE, "fraccion_bf.png"), dpi=130)

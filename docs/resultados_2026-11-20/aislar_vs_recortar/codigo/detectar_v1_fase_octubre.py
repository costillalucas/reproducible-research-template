"""detectar.py -- (paso 2) partículas en la reconstrucción A (200 px crudos) con la segmentación de octubre
(results/rojo_fase_2026-10-20/analisis.py:particulas, sin tocarla) y selección de partículas aisladas para los recortes B.

Uso: python3 detectar.py <OUT>
-> OUT/seleccion.json (partículas elegidas con su centro en px del ROI y el recorte B20), OUT/fig_seleccion.png
"""
import json, os, sys
import numpy as np
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
sys.path.insert(0, os.path.join(REPO, "results", "rojo_fase_2026-10-20"))
sys.path.insert(0, os.path.join(REPO, "results", "offset_color_2026-10-02"))
import analisis as AN          # noqa: E402  (particulas, dvol, LAM, DN)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt  # noqa: E402

OUT = sys.argv[1]
A = os.path.join(OUT, "A_200")
met = json.load(open(os.path.join(A, "datos", "metricas.json")))
f0, c0, n = met["recorte"]; hr = met["hrpx"]
o = np.load(os.path.join(A, "objeto_complejo.npy"))
fac = o.shape[0] // n
assert abs(hr - 1.29 / fac) < 1e-3, (hr, fac)
rows, info = AN.particulas(o, hr)
print(f"recorte A: filas {f0}:{f0+n}, col {c0}:{c0+n}; factor {fac}; hr {hr:.4f}; ruido {info['noise']:.3f} rad, umbral {info['thr']:.3f} rad;"
      f" {len(rows)} partículas segmentadas (sin borde, margen {info['mg']} px HR = {info['mg']*hr:.1f} µm)")
# centro en px HR del objeto completo -> px crudos del ROI. Píxel HR i <-> píxel crudo i/fac (mismo origen; ver README)
for r in rows:
    r["yi"], r["xi"] = r["y"] / hr, r["x"] / hr
    r["fil_roi"], r["col_roi"] = f0 + r["yi"] / fac, c0 + r["xi"] / fac
    r["dvol"] = float(AN.dvol(r["V"]))
# aislamiento: distancia (borde a borde aproximado) a cualquier otra región segmentada (incluye las 'malas'/'fusionadas')
lab = info["lab"]; mg = info["mg"]
from scipy import ndimage as ndi  # noqa: E402
dist_otros = {}
for r in rows:
    m = lab == r["k"]
    otros = (lab > 0) & ~m
    dt = ndi.distance_transform_edt(~otros)
    dist_otros[r["k"]] = float(dt[m].min() * hr) if otros.any() else 1e9
sel, desc = [], []
for r in rows:
    motivo = []
    if r["bad"] or r["merged"]: motivo.append("bad/merged")
    if r["V"] <= 0: motivo.append("V<=0")
    if not (3.0 <= r["d"] <= 9.0): motivo.append(f"d_ap {r['d']:.1f} fuera de 3-9 µm")
    if r["elong"] > 1.4: motivo.append(f"elong {r['elong']:.2f}")
    if dist_otros[r["k"]] < 8.0: motivo.append(f"vecino a {dist_otros[r['k']]:.1f} µm")
    # recorte B20 centrado debe caer dentro del recorte A con >= 10 px crudos de margen
    fr, cr = r["fil_roi"], r["col_roi"]
    ok_borde = (f0 + 10 <= round(fr - 10) and round(fr - 10) + 20 <= f0 + n - 10 and
                c0 + 10 <= round(cr - 10) and round(cr - 10) + 20 <= c0 + n - 10)
    if not ok_borde: motivo.append("B20 cerca del borde de A")
    r["dist_vecino_um"] = dist_otros[r["k"]]
    r["motivo_excl"] = motivo
    (desc if motivo else sel).append(r)
sel.sort(key=lambda r: -r["V"])
print(f"candidatas aisladas: {len(sel)}")
for r in rows:
    print(f"  k {r['k']:3d}  ROI ({r['fil_roi']:7.1f},{r['col_roi']:7.1f})  d_ap {r['d']:5.2f}  V {r['V']:7.2f}  dvol {r['dvol']:5.2f}"
          f"  elong {r['elong']:.2f} fill {r['fill']:.2f} vecino {r['dist_vecino_um']:6.1f}  {'OK' if not r['motivo_excl'] else ';'.join(r['motivo_excl'])}")
NMAX = int(os.environ.get("NMAX", 15))
elegidas = sel[:NMAX]
out = []
for i, r in enumerate(elegidas, 1):
    d = dict(id=f"P{i:02d}", k=r["k"], fil_roi=r["fil_roi"], col_roi=r["col_roi"], d_ap=r["d"], V_oct=r["V"], dvol_oct=r["dvol"],
             pico=r["phi"], elong=r["elong"], fill=r["fill"], dist_vecino_um=r["dist_vecino_um"])
    for t in (20, 40):
        d[f"rec{t}"] = [int(round(r["fil_roi"] - t / 2)), int(round(r["col_roi"] - t / 2))]
    rr, cc = d["rec40"]; d["B40_dentro_de_A"] = bool(f0 <= rr and rr + 40 <= f0 + n and c0 <= cc and cc + 40 <= c0 + n)
    out.append(d)
json.dump(dict(recorte_A=[f0, c0, n], factor=fac, hr=hr, ruido=info["noise"], umbral=info["thr"], margen_px_hr=mg,
               todas=[{k: v for k, v in r.items() if k not in ()} for r in rows], elegidas=out),
          open(os.path.join(OUT, "seleccion.json"), "w"), indent=1, default=float)
# figura
ph = np.zeros(o.shape); ph[mg:o.shape[0] - mg, mg:o.shape[1] - mg] = info["ph"]
fig, ax = plt.subplots(1, 2, figsize=(15, 7.5))
ext = (c0, c0 + n, f0 + n, f0)
ax[0].imshow(np.abs(o), cmap="gray", extent=ext); ax[0].set_title("A: amplitud (200 px crudos; ejes = px del ROI)")
h = ax[1].imshow(ph, cmap="viridis", vmin=-0.5, vmax=np.percentile(ph, 99.8), extent=ext)
plt.colorbar(h, ax=ax[1], fraction=0.046, label="fase sin fondo (rad, método octubre)")
ax[1].set_title("A: fase (margen de 16 µm sin analizar) — elegidas en rojo, descartadas en gris")
for a_ in ax:
    a_.add_patch(plt.Rectangle((c0 + mg / fac, f0 + mg / fac), n - 2 * mg / fac, n - 2 * mg / fac, fill=False, ec="w", ls=":"))
for r in desc:
    ax[1].plot(r["col_roi"], r["fil_roi"], "x", color="0.6", ms=5)
for d in out:
    for t, ls in ((20, "-"),):
        rr, cc = d[f"rec{t}"]
        for a_ in ax:
            a_.add_patch(plt.Rectangle((cc, rr), t, t, fill=False, ec="r", ls=ls, lw=1))
    for a_ in ax:
        a_.text(d["col_roi"] + 11, d["fil_roi"] - 11, d["id"], color="r", fontsize=9, weight="bold")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_seleccion.png"), dpi=110)
print("elegidas:", [(d["id"], d["rec20"], round(d["d_ap"], 2)) for d in out])

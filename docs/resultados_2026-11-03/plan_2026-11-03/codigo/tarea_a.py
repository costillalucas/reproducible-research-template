"""tarea_a.py -- rojo (red-b_arco) vs azul (blue_arco), mismo campo y recorte. Uso: python3 tarea_a.py [ruta_objeto_rojo etiqueta]
Escribe a_registro.json, a_frc.json/.csv, fig_a_*.png en plan_2026-11-03/."""
import os, sys, json
import numpy as np
from scipy import ndimage as ndi
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage.registration import phase_cross_correlation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun_plan as C

P = C.P
RED = sys.argv[1] if len(sys.argv) > 1 else os.path.join(C.R, "2026-10-30-red-b_arco", "objeto_complejo.npy")
TAG = sys.argv[2] if len(sys.argv) > 2 else "real"
PX = 0.43; N = 1200

Or = np.load(RED).astype(complex)
Ob = C.fourier_resample(np.load(os.path.join(C.R, "2026-10-29-blue_arco", "objeto_complejo.npy")).astype(complex), N)


def raw_amp(ds):
    d = np.load(os.path.join(C.R, ds, "datos", "prep.npz"))
    i = [tuple(k) for k in d["keys"]].index((17, 15))
    s, f = d["S"][i].astype(float), d["F"][i].astype(float)
    a = np.sqrt(np.clip(s / np.maximum(f, 1e-6 * f.max()) * f.mean(), 0, None))   # S/F·<F> como el BF del solver
    return a, np.real(C.fourier_resample(a, N))


raw_r_lr, raw_r = raw_amp("2026-10-30-red-b_arco")
raw_b_lr, raw_b = raw_amp("2026-10-29-blue_arco")


def bp(x):
    return ndi.gaussian_filter(x, 2) - ndi.gaussian_filter(x, 15)


def norm(x):
    return (x - x.mean()) / (x.std() + 1e-12)


# --- registro rojo -> azul: traslación subpíxel (pasabanda de |O|), y barrido de escala con traslación re-ajustada ---
W = C.hann2(N)
ar, ab = np.abs(Or), np.abs(Ob)
sh, err, _ = phase_cross_correlation(bp(ab) * W, bp(ar) * W, upsample_factor=20)
shp, _, _ = phase_cross_correlation(bp(C.rel_phase(Ob)) * W, bp(C.rel_phase(Or)) * W, upsample_factor=20)
shraw, _, _ = phase_cross_correlation(bp(raw_b) * W, bp(raw_r) * W, upsample_factor=20)


def zoom_c(x, s):
    """escala s alrededor del centro (s>1 agranda)."""
    c = (np.array(x.shape) - 1) / 2
    M = np.eye(2) / s; off = c - M @ c
    if np.iscomplexobj(x):
        return ndi.affine_transform(x.real, M, off, order=3) + 1j * ndi.affine_transform(x.imag, M, off, order=3)
    return ndi.affine_transform(x, M, off, order=3)


m = slice(150, N - 150)
esc = []
for s in np.arange(0.97, 1.0301, 0.005):
    z = zoom_c(ar, s)
    sh_s, _, _ = phase_cross_correlation(bp(ab) * W, bp(z) * W, upsample_factor=10)
    zz = ndi.shift(z, sh_s, order=1)
    esc.append((float(s), float(np.corrcoef(bp(zz)[m, m].ravel(), bp(ab)[m, m].ravel())[0, 1]), [float(v) for v in sh_s]))
best = max(esc, key=lambda t: t[1])


def mover(x, shift, s=1.0):
    if s != 1.0:
        x = zoom_c(x, s)
    if np.iscomplexobj(x):
        return ndi.shift(x.real, shift, order=3) + 1j * ndi.shift(x.imag, shift, order=3)
    return ndi.shift(x, shift, order=3)


Ora = mover(Or, sh)
ncc = float(np.corrcoef(bp(np.abs(Ora))[m, m].ravel(), bp(ab)[m, m].ravel())[0, 1])
reg = dict(rojo=RED, etiqueta=TAG, despl_amp_px=[float(v) for v in sh], despl_amp_um=[float(v) * PX for v in sh],
           despl_fase_px=[float(v) for v in shp], despl_crudo_px=[float(v) for v in shraw],
           ncc_pasabanda_amp_tras_registro=ncc, escala_barrido=esc, escala_mejor=best[0], ncc_escala_mejor=best[1],
           nota="desplazamiento = lo que hay que aplicar al ROJO para superponerlo al AZUL (filas, columnas), píxel 0.43 µm")
json.dump(reg, open(os.path.join(P, f"a_registro_{TAG}.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in reg.items() if k != "escala_barrido"}, indent=1))

# --- FRC rojo vs azul (Hann, anillos 0.012 1/µm) ---
raw_ra = mover(raw_r, shraw)
pares = {
    "crudo_rojo_vs_crudo_azul (amp BF central)": (raw_ra, raw_b),
    "|O| rojo vs |O| azul": (np.abs(Ora), ab),
    "fase rel rojo vs fase rel azul": (C.rel_phase(Ora), C.rel_phase(Ob)),
    "O complejo rel (sin fase baja frec.)": (C.rel_complex(Ora), C.rel_complex(Ob)),
}
if abs(best[0] - 1) > 0.004:
    Ors = mover(Or, best[2], best[0])
    pares[f"|O| rojo (escala {best[0]:.3f}) vs |O| azul"] = (np.abs(Ors), ab)
curvas, cruces = {}, {}
for nom, (x, y) in pares.items():
    fr = C.frc_fino(x, y, PX)
    curvas[nom] = fr; k7 = C.cruce(fr)
    cruces[nom] = dict(k_1_7=k7, periodo_um=(1 / k7 if k7 else None))
    print(f"{nom:45s} cruce 1/7 en k = {k7}  (periodo {1 / k7 if k7 else None})")
# control: |O| rojo corrido 150 px (no debe correlacionar)
fr = C.frc_fino(np.roll(np.abs(Ora), 150, 1), ab, PX); curvas["control |O| rojo corrido 150 px"] = fr
cruces["control |O| rojo corrido 150 px"] = dict(k_1_7=C.cruce(fr), periodo_um=None)

geo_r = C.k_sint("red", (-0.093, 1.930), 3); geo_b = C.k_sint("blue", (-0.093, 0.119), 5)
json.dump(dict(cruces=cruces, geo_rojo=geo_r, geo_azul=geo_b,
               curvas={k: v[:, :2].round(4).tolist() for k, v in curvas.items()}),
          open(os.path.join(P, f"a_frc_{TAG}.json"), "w"), indent=0)
with open(os.path.join(P, f"a_frc_{TAG}.csv"), "w") as f:
    noms = list(curvas); f.write("k_1_um," + ",".join(f'"{n}"' for n in noms) + "\n")
    for i in range(len(curvas[noms[0]])):
        f.write(f"{curvas[noms[0]][i, 0]:.4f}," + ",".join(f"{curvas[n][i, 1]:.4f}" for n in noms) + "\n")

fig, ax = plt.subplots(figsize=(8, 4.5))
cols = ["0.5", "C3", "C0", "C2", "C4", "0.8"]
for (nom, fr), c in zip(curvas.items(), cols):
    y = np.convolve(fr[:, 1], np.ones(3) / 3, mode="same")
    ax.plot(fr[:, 0], y, color=c, lw=1.4 if "control" not in nom else 1, ls="--" if "control" in nom else "-", label=nom)
ax.axhline(1 / 7, color="k", lw=0.8, ls=":"); ax.text(1.0, 1 / 7 + 0.01, "1/7", fontsize=8)
for k, t, c in [(geo_r["k_obj"], "NA/λ rojo", "C3"), (2 * geo_r["k_obj"], "2NA/λ rojo", "C3"), (geo_b["k_obj"], "NA/λ azul", "C0"),
                (geo_r["k_sint"], "corte sint. rojo", "C3"), (geo_b["k_sint"], "corte sint. azul", "C0")]:
    if k < 1 / (2 * PX):
        ax.axvline(k, color=c, lw=0.8, ls="-." if "sint" in t else ":")
        ax.text(k, 0.97, t, rotation=90, fontsize=7, va="top", ha="right", color=c)
ax.set_xlim(0, 1 / (2 * PX)); ax.set_ylim(-0.1, 1.0)
ax.set_xlabel("frecuencia espacial k [1/µm]  (periodo = 1/k)"); ax.set_ylabel("FRC (media móvil 3 anillos)")
ax.set_title(f"FRC rojo vs azul, campo del arco (rojo = {TAG}); Hann, anillos 0.012 1/µm, grilla 0.43 µm", fontsize=9)
ax.legend(fontsize=7, loc="upper right", bbox_to_anchor=(0.93, 0.80)); fig.tight_layout()
fig.savefig(os.path.join(P, f"fig_a_frc_{TAG}.png"), dpi=130)

if TAG == "real":
    np.savez_compressed(os.path.join(P, "codigo", "alineados_tmp.npz"), Ora=Ora.astype(np.complex64), Ob=Ob.astype(np.complex64),
                        raw_r=raw_ra.astype(np.float32), raw_b=raw_b.astype(np.float32))

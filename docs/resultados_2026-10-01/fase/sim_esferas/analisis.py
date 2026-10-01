"""Mide fase recuperada vs verdadera por esfera. Procesamiento de fase como report/informe/make_fig_fase_2809b.py:
unwrap_phase (skimage) + resta de polinomio de orden 2 ajustado al 70 % de píxeles más cercanos a la mediana + mediana.
Por esfera: fondo local = mediana del anillo R+4..R+8 µm; pico = máximo en disco de radio max(R, 1 µm);
volumen = suma de fase en disco R+3 µm × área de píxel; diámetro aparente = 2 sqrt(área sobre medio pico / pi)."""
import json, os, sys
import numpy as np
from skimage.restoration import unwrap_phase
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim

def quitar_fondo(p, frac=70):
    n = p.shape[0]; y, x = np.mgrid[0:n, 0:n] / n
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    d = np.abs(p - np.median(p)); m = d < np.percentile(d, frac)
    c, *_ = np.linalg.lstsq(A[m], p[m], rcond=None); q = p - A @ c
    return q - np.median(q)

def medir(ph, px):
    n = ph.shape[0]; yy, xx = (np.mgrid[:n, :n] + 0.5) * px; out = []
    k0 = 2 * np.pi / sim.LAM * sim.DN
    for d, (cy, cx) in zip(sim.DIAM, sim.CENT):
        R = d / 2; r = np.hypot(yy - cy, xx - cx)
        bg = np.median(ph[(r > R + 4) & (r < R + 8)]); q = ph - bg
        pk = q[r <= max(R, 1.0)].max(); vol = q[r <= R + 3].sum() * px * px
        loc = r <= R + 4; area = (q[loc] > pk / 2).sum() * px * px
        tp, tv = k0 * d, k0 * 4 / 3 * np.pi * R ** 3
        out.append(dict(d_um=d, pico_true=tp, pico_rec=float(pk), pico_ratio=float(pk / tp), vol_true=tv,
                        vol_rec=float(vol), vol_ratio=float(vol / tv), d_aparente=float(2 * np.sqrt(area / np.pi))))
    return out

runs = sorted(f[4:-4] for f in os.listdir(os.path.join(HERE, "out")) if f.endswith(".npy"))
res, ph_all = {}, {}
for name in runs:
    o = np.load(os.path.join(HERE, "out", f"obj_{name}.npy")).astype(complex)
    px = sim.FOV / o.shape[0]
    ph = quitar_fondo(unwrap_phase(np.angle(o))); ph_all[name] = ph
    res[name] = medir(ph, px)
    print(name, " ".join(f"{m['d_um']}:{m['pico_ratio']:.2f}/{m['vol_ratio']:.2f}/{m['d_aparente']:.1f}" for m in res[name]))
H = o.shape[0]; t = sim.truth(H); ph_true = 2 * np.pi * sim.DN * t / sim.LAM
res["verdad_en_grilla_HR"] = medir(ph_true, px)
json.dump(res, open(os.path.join(HERE, "resultados.json"), "w"), indent=1)

plt.rcParams.update({"font.size": 13})
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
est = {"limpio_40": ("C0", "--", "sin ruido, 40 épocas"), "limpio_400": ("C0", "-", "sin ruido, 400 épocas"),
       "ruido_40": ("C3", "--", "con ruido, 40 épocas"), "ruido_400": ("C3", "-", "con ruido, 400 épocas")}
for name in runs:
    c, ls, lab = est[name]; m = res[name]; D = [x["d_um"] for x in m]
    ax[0].plot(D, [x["pico_ratio"] for x in m], ls, color=c, marker="o", label=lab)
    ax[1].plot(D, [x["vol_ratio"] for x in m], ls, color=c, marker="o", label=lab)
    ax[2].plot(D, [x["d_aparente"] for x in m], ls, color=c, marker="o", label=lab)
ax[2].plot([0, 10.5], [0, 10.5], ":", color="gray", label="diámetro real")
for a in ax[:2]: a.axhline(1, color="gray", ls=":"); a.set_ylim(0, 2.5)
ax[0].set_title("Pico de fase: recuperado / verdadero"); ax[1].set_title("Volumen de fase: recuperado / verdadero")
ax[2].set_title("Diámetro aparente (ancho a media altura)")
for a in ax: a.set_xlabel("diámetro de la esfera (µm)"); a.grid(alpha=0.3)
ax[2].set_ylabel("µm"); ax[0].legend(fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(HERE, "curva_calibracion.png"), dpi=110); plt.close()

best = "ruido_400" if "ruido_400" in ph_all else runs[-1]
fig, ax = plt.subplots(2, 6, figsize=(16, 6))
ext = 10
for j, (d, (cy, cx)) in enumerate(zip(sim.DIAM, sim.CENT)):
    sl = (slice(int((cy - ext) / px), int((cy + ext) / px)), slice(int((cx - ext) / px), int((cx + ext) / px)))
    vmax = 2 * np.pi / sim.LAM * sim.DN * d
    for i, (img, lab) in enumerate([(ph_true, "verdadera"), (ph_all[best], "recuperada")]):
        im = ax[i, j].imshow(img[sl], cmap="magma", vmin=0, vmax=vmax, extent=[0, 2 * ext, 2 * ext, 0])
        ax[i, j].axis("off"); plt.colorbar(im, ax=ax[i, j], fraction=0.046, label="rad")
        ax[i, j].set_title(f"{d} µm, {lab}", fontsize=12)
    ax[1, j].plot([1.5, 6.5], [18, 18], color="w", lw=4); ax[1, j].text(4, 16.5, "5 µm", color="w", ha="center")
fig.suptitle(f"Fase verdadera y recuperada ({est[best][2]}); escala de color 0 a pico verdadero de cada esfera")
plt.tight_layout(); plt.savefig(os.path.join(HERE, "mapas_fase.png"), dpi=100); plt.close()

"""figuras.py (21/10 tarde) -- figs/recon_r500.png: BF crudo (amplitud sqrt(I) upsampleada), amplitud y fase de la reconstrucción full
e160 (recorte entero de 172 µm y zoom central de 60 µm); figs/frc_r500.png: FRC entre mitades (complejo y fase) con el nulo, r500 vs la
mañana r21 (captura_2026-10-21/eval/resolucion_r21_red_final.json) y 28/09b (rojo_resolucion_2026-10-20/resolucion_final.json),
y R held-out por anillo con piso de ruido (heldout_anillos.json)."""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import comun as C
from resolucion import objs

FIG = os.path.join(C.HERE, "..", "figs")
F, geo, D = C.load(); px = geo["hrpx"]
O = objs("final", 160)["full"]; O = O * np.exp(-1j * np.angle(np.sum(O)))
H = O.shape[0]; f = H // D["I"][(17, 15)].shape[0]
raw = np.real(F.fourier_upsample(np.sqrt(np.clip(D["I"][(17, 15)], 0, None)), f))
ph = C.rel_phase(O)
fig, ax = plt.subplots(2, 3, figsize=(13.5, 9))
z = int(30 / px); c = H // 2
for i, (sl, tt) in enumerate(((np.s_[:, :], "recorte entero (516 µm)"), (np.s_[c - z:c + z, c - z:c + z], "zoom central (60 µm)"))):
    for j, (img, t, cm) in enumerate(((raw, "BF crudo (17,15), amplitud", "gray"), (np.abs(O), "rec. amplitud |o|", "gray"),
                                      (ph, "rec. fase relativa (rad)", "twilight"))):
        im = img[sl]; ext = (0, im.shape[1] * px, im.shape[0] * px, 0)
        lo, hi = np.percentile(im, [0.5, 99.5])
        h = ax[i, j].imshow(im, cmap=cm, vmin=lo, vmax=hi, extent=ext); plt.colorbar(h, ax=ax[i, j], fraction=0.046)
        ax[i, j].set_title(f"{t} — {tt}", fontsize=9); ax[i, j].set_xlabel("µm", fontsize=8)
plt.suptitle("21/10 tarde, esferas 500 nm: rojo_500 full, 160 épocas", fontsize=11)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "recon_r500.png"), dpi=100); plt.close()

R = {"r500 (esferas 500 nm)": json.load(open(os.path.join(C.HERE, "resolucion_r500_red_final.json"))),
     "r21 mañana": json.load(open(os.path.join(C.RES, "captura_2026-10-21", "eval", "resolucion_r21_red_final.json"))),
     "28/09b": json.load(open(os.path.join(C.RES, "rojo_resolucion_2026-10-20", "resolucion_final.json")))}
HO = json.load(open(os.path.join(C.HERE, "heldout_anillos.json")))
na, lam = geo["na"], geo["lam"]
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
for j, q in enumerate(("complejo", "fase")):
    for (n, r), col in zip(R.items(), ("C0", "C1", "C2")):
        cu = r["epocas"]["160"]["curvas"][q]; k = np.array(cu["k"])
        ax[j].plot(k, cu["frc"], c=col, label=f"{n} mitades"); ax[j].plot(k, cu["nulo"], c=col, ls=":", lw=1, label=f"{n} nulo")
    ax[j].axhline(1 / 7, c="gray", ls="--", lw=1)
    for kk, t in ((na / lam, "NA/λ"), (2 * na / lam, "2NA/λ")):
        ax[j].axvline(kk, c="k", lw=0.8, ls="-."); ax[j].text(kk, 0.95, t, fontsize=7)
    ax[j].set_xlim(0, 0.9); ax[j].set_ylim(-0.1, 1); ax[j].set_xlabel("k (1/µm)"); ax[j].set_ylabel("FRC"); ax[j].set_title(f"FRC entre mitades, {q}, e160", fontsize=10)
    ax[j].legend(fontsize=7)
for (n, key), col in zip((("r500 (esferas 500 nm)", "r500 (tarde) e160"), ("r21 mañana", "r21 centrado e160"), ("28/09b", "28/09b e160"),
                          ("m2 (16/10)", "m2 (16/10) e40")), ("C0", "C1", "C2", "C3")):
    if key not in HO:
        continue
    a = HO[key]["anillos"]; q = sorted(a, key=int)
    ax[2].plot([int(x) for x in q], [a[x]["R"] for x in q], "o-", c=col, label=f"{n} R ({key.split()[-1]})")
    ax[2].plot([int(x) for x in q], [a[x]["piso"] for x in q], ":", c=col, label=f"{n} piso de ruido")
ax[2].set_xlabel("anillo (pasos desde el eje)"); ax[2].set_ylabel("R held-out mediano (5 folds)"); ax[2].legend(fontsize=7); ax[2].set_title("held-out por anillo", fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "frc_r500.png"), dpi=100); plt.close()

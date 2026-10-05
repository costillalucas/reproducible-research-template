"""etapa1.py -- etapa 1 (solo rojo, full): rampa vs época y volumen de fase, base (offset (0,3)) vs die (0,4.06).
Escribe etapa1.json y figs/. Uso: nice python3 etapa1.py"""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from skimage.restoration import unwrap_phase

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import volumen
from runner import ramp
T = "real_A+init_z98.0_full"
BASE = os.path.join(HERE, "..", "iteraciones_2026-09-30", "out", "b_red", T)
OFF = os.path.join(HERE, "out", "die", "b_red", T)
NEG = os.path.join(HERE, "out", "die_neg", "b_red", T)
HR, LAM = 512 / 1200, 0.63
rd = lambda p: {r["epoch"]: r for r in map(json.loads, open(os.path.join(p, "metrics.jsonl")))}
mo, mb, mn = rd(OFF), rd(BASE), rd(NEG)
res = {"rampa": {}, "trainR": {}, "volumen_rojo": {}}
for e in sorted(mo):
    fb = os.path.join(BASE, f"obj_e{e:03d}.npy")
    res["rampa"][e] = dict(base=ramp(np.load(fb), HR, LAM), die=mo[e]["ramp"], die_neg=mn.get(e, {}).get("ramp"))
    res["trainR"][e] = dict(base=mb[e]["train_R"], die=mo[e]["train_R"], die_neg=mn.get(e, {}).get("train_R"))
for e in (5, 40, 160):
    for tag, p in (("base", BASE), ("die", OFF)):
        f = os.path.join(p, f"obj_e{e:03d}.npy")
        if os.path.exists(f):
            v = volumen.medir({"red": np.load(f)})
            res["volumen_rojo"][f"{tag}_e{e}"] = dict(v["por_color"]["red"], ruido=v["ruido"]["red"])
json.dump(res, open(os.path.join(HERE, "etapa1.json"), "w"), indent=1)
os.makedirs(os.path.join(HERE, "figs"), exist_ok=True)
# rampa vs época
E = sorted(res["rampa"])
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for tag, lab, c in (("base", "nominal (0, 3) mm", "0.4"), ("die", "die rojo (0, 4.06) mm", "#c0392b"), ("die_neg", "signo opuesto (0, 1.94) mm", "#2e6fd1")):
    ee = [e for e in E if res["rampa"][e][tag]]
    ax[0].plot([max(e, 0.5) for e in ee], [res["rampa"][e][tag]["dy_mm"] for e in ee], "o-", color=c, label=lab)
    ee = [e for e in E if res["trainR"][e][tag] is not None]
    ax[1].plot([max(e, 0.5) for e in ee], [res["trainR"][e][tag] for e in ee], "o-", color=c, label=lab)
for a in ax: a.set_xscale("log"); a.set_xlabel("época"); a.grid(alpha=.3)
ax[0].axhline(-1.06, ls=":", color="k", lw=1); ax[0].axhline(-2.12, ls=":", color="k", lw=1)
ax[0].set_ylabel("rampa → Δy LED equivalente (mm)"); ax[0].legend(fontsize=8)
ax[1].set_ylabel("R afín medio, LEDs de entrenamiento (full)"); ax[1].set_ylim(0.3, 0.5)
fig.suptitle("Rojo 28/09b, full: rampa de fase y residuo vs época"); fig.tight_layout()
fig.savefig(os.path.join(HERE, "figs", "rampa_vs_epoca_rojo.png"), dpi=110); plt.close(fig)
# mapas de fase
fig, ax = plt.subplots(2, 3, figsize=(14, 9.4))
for i, (tag, p) in enumerate((("nominal (0, 3)", BASE), ("die rojo (0, 4.06)", OFF))):
    for j, e in enumerate((5, 40, 160)):
        o = np.load(os.path.join(p, f"obj_e{e:03d}.npy")); ph = unwrap_phase(np.angle(o))
        ph -= np.median(ph); r = res["rampa"][e]["base" if i == 0 else "die"]
        im = ax[i, j].imshow(ph, cmap="twilight_shifted" if False else "RdBu_r", vmin=-15, vmax=15, extent=[0, 512, 512, 0])
        ax[i, j].set_title(f"{tag}, época {e}\nrampa p-p {r['ptp']:.1f} rad ({r['dy_mm']:+.2f} mm)", fontsize=9)
        ax[i, j].set_xlabel("x (µm)"); ax[i, j].set_ylabel("y (µm, eje de filas LED)")
fig.colorbar(im, ax=ax, shrink=0.6, label="fase desenrollada (rad)")
fig.savefig(os.path.join(HERE, "figs", "mapas_fase_rojo.png"), dpi=90); plt.close(fig)
print(json.dumps(res["volumen_rojo"], indent=1))
for e in E: print(e, {k: (round(v["ptp"], 2), round(v["dy_mm"], 3)) if v else None for k, v in res["rampa"][e].items()}, res["trainR"][e])

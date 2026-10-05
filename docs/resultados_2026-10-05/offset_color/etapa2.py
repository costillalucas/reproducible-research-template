"""etapa2.py -- verde/azul (die vs nominal): rampa, residuo, rayas; diagnóstico de rayas en rojo (todas las variantes a 40
épocas). Escribe etapa2.json y figs/mapas_fase_gb.png, figs/diag_rayas_rojo.png. (El volumen va aparte: vol_fijo.py.)"""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from skimage.restoration import unwrap_phase
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from runner import ramp, VARIANTS
from rayas2 import path, rayas
LAM = {"b_red": 0.63, "b_green": 0.53, "b_blue": 0.47}
T = "real_A+init_z98.0_full"
met = lambda var, ds: {r["epoch"]: r for r in map(json.loads, open(os.path.dirname(path(var, ds, 0)) + "/metrics.jsonl"))}
res = {"gb": {}, "diag_rojo": {}}
for ds in ("b_green", "b_blue"):
    mb, md = met("base", ds), met("die", ds); hr = 512 / 2000; r = {}
    for e in (5, 40, 160):
        r[e] = dict(trainR_nom=mb[e]["train_R"], trainR_die=md[e]["train_R"],
                    rampa_nom=ramp(np.load(path("base", ds, e)), hr, LAM[ds]), rampa_die=md[e]["ramp"],
                    rayas_nom=rayas(np.load(path("base", ds, e))), rayas_die=rayas(np.load(path("die", ds, e))))
    res["gb"][ds] = r; print(ds, "listo", flush=True)
DIAG = ["base", "die", "d090", "d120", "d106_z101", "d106_na072", "die_sin18", "die_sin3", "nom_sin18", "g_die_sin18"]
for v in DIAG:
    if not os.path.exists(path(v, "b_red", 40)): continue
    m = met(v, "b_red"); r = {}
    for e in (5, 20, 40):
        if not os.path.exists(path(v, "b_red", e)): continue
        r[e] = dict(rayas=rayas(np.load(path(v, "b_red", e))), trainR=m[e]["train_R"], heldoutR=m[e]["heldout_R_ring_lt7"],
                    rampa=m[e].get("ramp") or ramp(np.load(path(v, "b_red", e)), 512 / 1200, 0.63))
    res["diag_rojo"][v] = r; print(v, {e: round(x["rayas"]["rms_perfil_rad"], 3) for e, x in r.items()}, flush=True)
res["g_excl"] = {}
for v in ("g_die_sin18", "g_nom_sin18"):
    m = met(v, "b_green")
    res["g_excl"][v] = {e: dict(rayas=rayas(np.load(path(v, "b_green", e))), trainR=m[e]["train_R"], rampa=m[e]["ramp"]) for e in (5, 40)}
res["rojo_160"] = {}
for v in ("base", "die", "nom_sin18_160", "die_sin18_160"):
    m = met(v, "b_red")
    res["rojo_160"][v] = {e: dict(trainR=m[e]["train_R"], rampa=m[e].get("ramp") or ramp(np.load(path(v, "b_red", e)), 512 / 1200, 0.63))
                          for e in sorted(m) if e <= 160 and (m[e].get("ramp") or os.path.exists(path(v, "b_red", e)))}
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
for v, lab, c, ls in (("base", "nominal, 225 LEDs", "0.4", "-"), ("die", "die, 225 LEDs", "#c0392b", "-"),
                      ("nom_sin18_160", "nominal sin (18,14),(18,16)", "0.4", "--"), ("die_sin18_160", "die sin (18,14),(18,16)", "#c0392b", "--")):
    d = res["rojo_160"][v]; E = sorted(d)
    ax[0].plot([max(e, .5) for e in E], [d[e]["rampa"]["ptp"] for e in E], "o" + ls, color=c, label=lab, ms=4)
    ax[1].plot([max(e, .5) for e in E], [d[e]["trainR"] for e in E], "o" + ls, color=c, label=lab, ms=4)
for a in ax: a.set_xscale("log"); a.set_xlabel("época"); a.grid(alpha=.3)
ax[0].set_ylabel("rampa global p-p (rad)"); ax[1].set_ylabel("R afín medio, LEDs de entrenamiento"); ax[1].set_ylim(.3, .5); ax[0].legend(fontsize=8)
fig.suptitle("Rojo full: rampa y residuo con y sin las LEDs (18,14),(18,16)"); fig.tight_layout()
fig.savefig(os.path.join(HERE, "figs", "rampa_sin18_rojo.png"), dpi=110); plt.close(fig)
json.dump(res, open(os.path.join(HERE, "etapa2.json"), "w"), indent=1, default=float)


def mapa(o, lim):
    o = o.astype(complex); N = o.shape[0]; hr = 512 / N
    u = o / np.maximum(abs(o), 1e-6); s = 60 / hr
    bg = ndi.gaussian_filter(u.real, s) + 1j * ndi.gaussian_filter(u.imag, s)
    return np.angle(o * np.conj(bg))


fig, ax = plt.subplots(2, 4, figsize=(17, 9))
for i, ds in enumerate(("b_green", "b_blue")):
    for j, (v, e) in enumerate((("base", 40), ("die", 40), ("base", 160), ("die", 160))):
        ry = res["gb"][ds][e]["rayas_nom" if v == "base" else "rayas_die"]
        ax[i, j].imshow(mapa(np.load(path(v, ds, e)), 2), cmap="RdBu_r", vmin=-2, vmax=2, extent=[0, 512, 512, 0])
        ax[i, j].set_title(f"{ds[2:]} {'nominal' if v == 'base' else 'die'} ép. {e}\nrayas rms {ry['rms_perfil_rad']:.2f} rad", fontsize=9)
fig.suptitle("Fase con fondo lento quitado (demodulación σ = 60 µm), ±2 rad; y = eje de filas LED"); fig.tight_layout()
fig.savefig(os.path.join(HERE, "figs", "mapas_fase_gb.png"), dpi=80); plt.close(fig)
vs = [v for v in DIAG if v in res["diag_rojo"]]
fig, ax = plt.subplots(2, (len(vs) + 1) // 2, figsize=(4 * ((len(vs) + 1) // 2), 8.4)); ax = ax.ravel()
for a, v in zip(ax, vs):
    a.imshow(mapa(np.load(path(v, "b_red", 40)), 2), cmap="RdBu_r", vmin=-2, vmax=2, extent=[0, 512, 512, 0])
    x = res["diag_rojo"][v][40]
    a.set_title(f"{v}: rayas {x['rayas']['rms_perfil_rad']:.2f} rad\nR_train {x['trainR']:.3f}", fontsize=9)
for a in ax[len(vs):]: a.axis("off")
fig.suptitle("Rojo, full, época 40: diagnóstico de rayas (fase demodulada σ = 60 µm, ±2 rad)"); fig.tight_layout()
fig.savefig(os.path.join(HERE, "figs", "diag_rayas_rojo.png"), dpi=80); plt.close(fig)

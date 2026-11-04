"""Auditoría ítem 7: fase de las esferas en 2026-11-03-red_1311 (y mitades, nulo) con el MISMO método de volumen de fase del
20/10 (results/rojo_fase_2026-10-20/analisis.py: particulas, importado sin modificar) + estadística simple de la fase."""
import sys, json, numpy as np, importlib.util
from scipy import ndimage as ndi
from skimage.restoration import unwrap_phase
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
spec = importlib.util.spec_from_file_location("analisis", REPO + "/results/rojo_fase_2026-10-20/analisis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/"
HR, LAM = 0.43, 0.63
DN_REPO = A.DN                              # 0.0488 (supuesto del repo)
DN_TAB = 1.523 - 1.477                      # nylon (supuesto) - DMSO (tabla) = 0.046
def Vteo(d, dn): return 2 * np.pi * dn / LAM * (np.pi / 6) * d ** 3
def pico(d, dn): return 2 * np.pi * dn * d / LAM
out = dict(DN_repo=DN_REPO, DN_tabla=DN_TAB,
           teoria={f"d{d}": dict(pico_rad=pico(d, DN_REPO), V_rad_um2=Vteo(d, DN_REPO)) for d in (3, 5, 7, 10)})
objs = {"full": R + "2026-11-03-red_1311/objeto_complejo.npy", "mitadA": R + "2026-11-03-red_1311/objeto_mitadA.npy",
        "mitadB": R + "2026-11-03-red_1311/objeto_mitadB.npy", "nulo_full": R + "plan_2026-11-04/red_nulo_df/objeto_complejo.npy"}
# referencia 20/10 (28/09b, rojo_final e160), mismo método
ref = REPO + "/results/offset_color_2026-10-02/out/rojo_final/b_red/real_A+init_z98.0_full/obj_e160.npy"
objs["ref_28-09b_e160"] = ref
info_full = None
for n, p in objs.items():
    o = np.load(p).astype(complex)
    rows, info = A.particulas(o, HR)
    ok = A.tabla(rows)
    ph = info["ph"]
    r = dict(N_seg=len(rows), N_ok=len(ok), ruido_rad=info["noise"], umbral_rad=info["thr"],
             fase_p01_p99=[float(np.percentile(ph, 1)), float(np.percentile(ph, 99))],
             fase_p001_p999=[float(np.percentile(ph, 0.1)), float(np.percentile(ph, 99.9))],
             amp_cv=float(np.std(np.abs(o)) / np.mean(np.abs(o))))
    if ok:
        V = np.array([x["V"] for x in ok]); pk = np.array([x["phi"] for x in ok]); d = np.array([x["d"] for x in ok])
        dv = A.dvol(V) / 1.0499    # calibración sim del 20/10 (d_vol = 1.050 d)
        r.update(pico_mediana=float(np.median(pk)), pico_p90=float(np.percentile(pk, 90)), pico_max=float(pk.max()),
                 V_mediana=float(np.median(V)), V_p90=float(np.percentile(V, 90)), d_ap_mediana=float(np.median(d)),
                 d_vol_mediana=float(np.median(dv)), d_vol_p90=float(np.percentile(dv, 90)), d_vol_max=float(dv.max()),
                 n_dvol_ge4=int((dv >= 4).sum()))
    # fase NEGATIVA: ¿hay objetos con fase < 0 (mismo umbral)?
    sm = ndi.gaussian_filter(ph, 1.0 / HR); lab, nneg = ndi.label(sm < -info["thr"])
    r["N_regiones_fase_negativa"] = int(nneg)
    out[n] = r
    if n == "full":
        info_full = (o, info, ok)
    print(n, json.dumps(r))
json.dump(out, open("fase_esferas.json", "w"), indent=1)
# figura: fase sin fondo (método 20/10) del full, con las partículas OK marcadas, y perfiles de las 4 de mayor volumen
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
o, info, ok = info_full
ph = info["ph"]; mg = info["mg"]
fig, ax = plt.subplots(1, 3, figsize=(17, 5.6))
L = ph.shape[0] * HR
im = ax[0].imshow(ph, cmap="RdBu_r", vmin=-2.5, vmax=2.5, extent=(0, L, L, 0)); plt.colorbar(im, ax=ax[0], fraction=0.046)
ax[0].set_title("fase desenrollada sin fondo (método 20/10), rad (escala fija ±2.5, no percentiles)\n2026-11-03-red_1311 (borde de 16 µm quitado)", fontsize=9)
for x in ok: ax[0].plot(x["x"] - mg * HR, x["y"] - mg * HR, "o", mfc="none", mec="lime", ms=8)
am = np.abs(o)[mg:-mg, mg:-mg]
lo, hi = np.percentile(am, [0.5, 99.5]); im = ax[1].imshow(am, cmap="gray", vmin=lo, vmax=hi, extent=(0, L, L, 0)); plt.colorbar(im, ax=ax[1], fraction=0.046)
ax[1].set_title("amplitud reconstruida", fontsize=9)
top = sorted(ok, key=lambda x: -x["V"])[:4]
for x in top:
    cy, cx = int(round(x["y"] / HR)) - mg, int(round(x["x"] / HR)) - mg
    s = np.arange(-25, 26); prof = ph[cy, np.clip(cx + s, 0, ph.shape[1] - 1)]
    ax[2].plot(s * HR, prof, label=f"V {x['V']:.1f} rad·µm², d_ap {x['d']:.1f} µm")
xx = np.linspace(-2.5, 2.5, 101); ax[2].plot(xx, pico(5, DN_REPO) * np.sqrt(1 - (xx / 2.5) ** 2), "k--", label="esfera 5 µm teórica (Δn 0.0488)")
ax[2].set_xlabel("µm"); ax[2].set_ylabel("fase (rad)"); ax[2].legend(fontsize=7); ax[2].set_title("perfiles horizontales: 4 partículas de mayor volumen", fontsize=9)
plt.tight_layout(); plt.savefig("fig_fase_esferas.png", dpi=100)

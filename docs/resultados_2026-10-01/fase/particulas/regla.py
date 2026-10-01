"""Regla incorporada: diámetro lateral vs espesor desde la fase, captura 28/09b. Correr desde la raíz del repo:
python3 results/fase_2026-10-01/particulas/regla.py
Carga y convenciones copiadas de report/informe/make_fig_fase_2809b.py (unwrap_phase + polinomio orden 2 en el 70 % de
píxeles cercanos a la mediana) y make_fig_rgb_2809b_es.py (corrimientos de comparar_colores.json, px de la grilla 1200)."""
import json, os
import numpy as np
from scipy import ndimage as ndi
from skimage.restoration import unwrap_phase
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

B = "results/captura_2026-09-28b"; OUT = "results/fase_2026-10-01/particulas"
LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}
NOM = {"red": "rojo", "green": "verde", "blue": "azul"}
COL = {"red": "#c0392b", "green": "#27ae60", "blue": "#2e6fd1"}
A_DN, B_DN = 0.045, 0.0015  # results/sim_multiespectral_2026-09-29/sim.py:29 y :39-40 (hipótesis del modelo)
DN = {c: A_DN + B_DN / l ** 2 for c, l in LAM.items()}
cmp = json.load(open(os.path.join(B, "comparar_colores.json")))["reconstrucciones"]
HR_RED = 512.0 / 1200


def quitar_fondo(p, frac=70, m_extra=None):  # igual que make_fig_fase_2809b.quitar_fondo, con grilla rectangular
    n0, n1 = p.shape; y, x = np.mgrid[0:n0, 0:n1]; x = x / n1; y = y / n0
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    d = np.abs(p - np.median(p)); m = d < np.percentile(d, frac)
    if m_extra is not None: m &= m_extra
    c, *_ = np.linalg.lstsq(A[m], p[m], rcond=None)
    q = p - A @ c
    return q - np.median(q[m])


res = {}
for c in LAM:
    o = np.load(f"{B}/{c}/out/obj_real_A+init_z98.0_full.npy").astype(complex)
    N = o.shape[0]; hr = 512.0 / N
    mg = int(round(16 / hr)); o = o[mg:N - mg, mg:N - mg]  # borde de 16 µm fuera
    amp = np.abs(o)
    # fondo lento de fase (franjas/inclinación) quitado demodulando con el campo complejo suavizado (sigma 12 µm),
    # para que el desenrollado no tenga que cruzar franjas de fondo (en rojo el desenrollado global falla sin esto)
    u = o / np.maximum(amp, 1e-6); bgc = ndi.gaussian_filter(u.real, 12 / hr) + 1j * ndi.gaussian_filter(u.imag, 12 / hr)
    w = np.angle(o * np.conj(bgc)); w_raw = np.angle(o)
    ph = quitar_fondo(unwrap_phase(w))
    # segunda pasada: rehacer el fondo excluyendo partículas
    sm = ndi.gaussian_filter(ph, 1.0 / hr)
    bgmask = ~ndi.binary_dilation(sm > 0.3, iterations=int(3 / hr))
    ph = quitar_fondo(ph, frac=90, m_extra=bgmask); sm = ndi.gaussian_filter(ph, 1.0 / hr)
    noise = 1.4826 * np.median(np.abs(sm[bgmask] - np.median(sm[bgmask])))
    thr = max(0.3, 5 * noise)
    lab, n = ndi.label(sm > thr)
    objs = ndi.find_objects(lab)
    ring_w = int(round(2 / hr)); rows = []
    for k, sl in enumerate(objs, 1):
        r0, r1, c0, c1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if r0 == 0 or c0 == 0 or r1 == lab.shape[0] or c1 == lab.shape[1]: continue
        pad = ring_w + 4
        R0, R1, C0, C1 = max(r0 - pad, 0), min(r1 + pad, lab.shape[0]), max(c0 - pad, 0), min(c1 + pad, lab.shape[1])
        L = lab[R0:R1, C0:C1]; m = L == k
        area = m.sum() * hr * hr; d = 2 * np.sqrt(area / np.pi)
        if d < 1.0: continue  # por debajo de la resolución lateral
        # descartar cúmulos: solidez baja (área / área de la cáscara convexa aproximada por el rectángulo del momento)
        yy, xx = np.nonzero(m); cov = np.cov(np.stack([yy, xx])) if len(yy) > 2 else np.eye(2)
        ev = np.sort(np.linalg.eigvalsh(cov)); elong = np.sqrt(ev[1] / max(ev[0], 1e-9))
        fill = m.sum() / (np.pi * 4 * np.sqrt(ev[0] * ev[1]) + 1e-9)  # área / elipse equivalente por momentos
        ring = ndi.binary_dilation(m, iterations=ring_w) & ~ndi.binary_dilation(m, iterations=2) & (L == 0)
        if ring.sum() < 10: continue
        P = ph[R0:R1, C0:C1]; bg = np.median(P[ring]); pk = np.percentile(P[m], 95) - bg; Vphi = float((P[m] - bg).sum() * hr * hr)
        # control del desenrollado: desenrollar solo el recorte y comparar
        Pl = unwrap_phase(w[R0:R1, C0:C1]); pkl = np.percentile(Pl[m], 95) - np.median(Pl[ring])
        ring_sd = np.std(P[ring])
        bad = abs(pkl - pk) > 1.0 or ring_sd > 1.0
        cy, cx = ndi.center_of_mass(m)
        rows.append(dict(d=d, phi=pk, V=Vphi, phi_loc=pkl, y=(R0 + cy + mg) * hr, x=(C0 + cx + mg) * hr, elong=elong, fill=fill,
                         bad=bool(bad), amp_min=float(np.percentile(amp[R0:R1, C0:C1][m], 5))))
    res[c] = dict(rows=rows, noise=float(noise), thr=float(thr), n_lab=int(n), hr=hr)
    print(c, N, "ruido", round(noise, 3), "umbral", round(thr, 2), "regiones", n, "candidatas", len(rows), flush=True)

# --- selección y espesor
tab = {}
for c in LAM:
    R = res[c]["rows"]
    for r in R:
        r["merged"] = r["elong"] > 2.0 or r["fill"] < 0.6
        r["t"] = r["phi"] * LAM[c] / (2 * np.pi * DN[c])
    ok = [r for r in R if not r["merged"] and not r["bad"]]
    d = np.array([r["d"] for r in ok]); t = np.array([r["t"] for r in ok])
    tab[c] = dict(N_cand=len(R), N_merged=sum(r["merged"] for r in R), N_unwrap_bad=sum(r["bad"] for r in R), N=len(ok),
                  frac_unwrap_bad=sum(r["bad"] for r in R) / max(len(R), 1),
                  mediana_t_sobre_d=float(np.median(t / d)), p25=float(np.percentile(t / d, 25)), p75=float(np.percentile(t / d, 75)),
                  pearson=float(np.corrcoef(d, t)[0, 1]),
                  spearman=float(np.corrcoef(np.argsort(np.argsort(d)), np.argsort(np.argsort(t)))[0, 1]),
                  mediana_d=float(np.median(d)), mediana_t=float(np.median(t)), dn=DN[c])
    for lo, hi in [(1, 3), (3, 6), (6, 20)]:
        s = (d >= lo) & (d < hi)
        tab[c][f"t/d_{lo}-{hi}um"] = [int(s.sum()), float(np.median(t[s] / d[s])) if s.any() else None]
    res[c]["ok"] = ok

# --- emparejar colores por centroide (marco del verde: restar corrimiento en px de la grilla 1200)
def pos(c, r):
    s = np.array(cmp.get(f"corrimiento_{c}_px_HR", [0, 0])) * HR_RED if c != "green" else np.zeros(2)
    return np.array([r["y"], r["x"]]) - s
rat = {}
for c in ["green", "blue"]:
    P = np.array([pos("red", r) for r in res["red"]["ok"]])
    q = []
    for r in res[c]["ok"]:
        dd = np.hypot(*(P - pos(c, r)).T); j = np.argmin(dd)
        rr = res["red"]["ok"][j]
        if dd[j] < 2.0 and abs(rr["d"] - r["d"]) < 0.5 * max(rr["d"], r["d"]) and rr["phi"] > 0.5:
            q.append((r["phi"] / rr["phi"], rr["d"], dd[j]))
    q = np.array(q).reshape(-1, 3)
    if len(q) == 0: rat[c] = dict(N=0); continue
    exp = (DN[c] / LAM[c]) / (DN["red"] / LAM["red"])
    rat[c] = dict(N=len(q), mediana=float(np.median(q[:, 0])), p25=float(np.percentile(q[:, 0], 25)),
                  p75=float(np.percentile(q[:, 0], 75)), esperado=float(exp), esperado_sin_dispersion=LAM["red"] / LAM[c],
                  dist_mediana_um=float(np.median(q[:, 2])))
json.dump(dict(tabla=tab, cocientes=rat, ruido={c: res[c]["noise"] for c in LAM}), open(f"{OUT}/resultados.json", "w"), indent=1, default=float)
with open(f"{OUT}/particulas.csv", "w") as f:
    f.write("color,d_um,phi_rad,phi_local_rad,t_um,y_um,x_um,elong,fill,cumulo,desenrollado_dudoso,Vphi_rad_um2\n")
    for c in LAM:
        for r in res[c]["rows"]:
            f.write(f"{c},{r['d']:.3f},{r['phi']:.3f},{r['phi_loc']:.3f},{r['t']:.3f},{r['y']:.2f},{r['x']:.2f},{r['elong']:.2f},{r['fill']:.2f},{int(r['merged'])},{int(r['bad'])},{r['V']:.4f}\n")
print(json.dumps(tab, indent=1, default=float)); print(json.dumps(rat, indent=1, default=float))

# --- figuras
fig, ax = plt.subplots(1, 3, figsize=(15, 5.6), sharex=True, sharey=True)
for a, c in zip(ax, LAM):
    ok = res[c]["ok"]; d = [r["d"] for r in ok]; t = [r["t"] for r in ok]
    a.scatter(d, t, s=10, alpha=0.5, color=COL[c], edgecolor="none")
    a.plot([0, 20], [0, 20], "k--", lw=1, label="y = x (esfera)")
    a.set_xlim(0, 20); a.set_ylim(0, 20); a.set_aspect("equal")
    a.set_title(f"{NOM[c]} ({int(LAM[c] * 1000)} nm), N = {len(ok)}"); a.set_xlabel("diámetro lateral equivalente (µm)")
ax[0].set_ylabel("espesor desde la fase (µm)"); ax[0].legend(loc="upper left")
plt.tight_layout(); plt.savefig(f"{OUT}/dispersion_t_vs_d.png", dpi=110); plt.close()
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for c in LAM:
    ok = res[c]["ok"]
    ax[0].hist([r["d"] for r in ok], bins=np.arange(0, 15.5, 0.5), histtype="step", lw=2, color=COL[c], label=NOM[c])
    ax[1].hist([r["t"] for r in ok], bins=np.arange(0, 15.5, 0.5), histtype="step", lw=2, color=COL[c], label=NOM[c])
ax[0].set_xlabel("diámetro lateral equivalente (µm)"); ax[1].set_xlabel("espesor desde la fase (µm)")
for a in ax: a.set_ylabel("número de partículas"); a.legend()
plt.tight_layout(); plt.savefig(f"{OUT}/histogramas.png", dpi=110); plt.close()

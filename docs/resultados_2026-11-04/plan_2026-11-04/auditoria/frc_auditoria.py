"""Auditoría ítems 4-6: C2 y cruce 1/7 con distintas definiciones; fase relativa entre mitades por anillo.
Solo lee: objetos de 2026-11-03-red_1311 y plan_2026-11-04/red_nulo_df."""
import sys, json, numpy as np
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo")
import comun_plan as C
from scipy.signal.windows import tukey
R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/"
D = {"real": R + "2026-11-03-red_1311", "nulo": R + "plan_2026-11-04/red_nulo_df"}
PX, LAM = 0.43, 0.63
def sm5(y, n=5): return np.convolve(np.r_[np.full(n // 2, y[0]), y, np.full(n // 2, y[-1])], np.ones(n) / n, "valid")
def last_above(k, y, thr, run=3, k0=0.02, k1=0.9):
    ok = (y >= thr) & (k > k0) & (k <= k1)
    for i in range(len(k) - 1, run - 2, -1):
        if ok[i - run + 1:i + 1].all(): return float(k[i])
def relfase(a, b, px, edges):
    Fa = np.fft.fftshift(np.fft.fft2((a - a.mean()) * C.hann2(a.shape[0]))); Fb = np.fft.fftshift(np.fft.fft2((b - b.mean()) * C.hann2(a.shape[0])))
    H = a.shape[0]; fy, fx = np.mgrid[:H, :H] - H // 2; kr = np.hypot(fx, fy) / (H * px)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (kr >= lo) & (kr < hi); s = np.sum(Fa[m] * np.conj(Fb[m]))
        # coherencia de la fase: |sum| / sum|.|  (1 = misma rotación en todo el anillo)
        out.append((round(0.5 * (lo + hi), 3), round(float(np.degrees(np.angle(s))), 1), round(float(np.abs(s) / np.sum(np.abs(Fa[m] * np.conj(Fb[m])))), 3)))
    return out
res = {}
for nom, d in D.items():
    h0, h1 = np.load(d + "/objeto_mitadA.npy").astype(complex), np.load(d + "/objeto_mitadB.npy").astype(complex)
    r = {}
    for na in (0.0669, 0.070, 0.072, 0.074):
        r[f"C2_NA{na}"] = C.c2(h0, h1, PX, na, LAM)
        r[f"C2_NA{na}_hann"] = C.band_mean(C.frc((h0 - h0.mean()) * C.hann2(1200), (h1 - h1.mean()) * C.hann2(1200), PX), 2 * na / LAM, 0.45)
    fr60 = C.frc(h0, h1, PX)
    r["anillos_banda_C2_60"] = int(((fr60[:, 0] >= 2 * 0.0669 / LAM) & (fr60[:, 0] < 0.45)).sum())
    r["FRC_por_subbanda"] = {f"[{a},{b}]": C.band_mean(fr60, a, b) for a, b in [(0.106, 0.212), (0.212, 0.30), (0.30, 0.40), (0.40, 0.45), (0.45, 0.6), (0.6, 0.9)]}
    ff = C.frc_fino(h0, h1, PX, ventana=True)
    r["cruce_plan_(Hann,primer_cruce,sm3)"] = C.cruce(ff, k0=2 * 0.0669 / LAM)
    r["cruce_plan_k0=NA/lam"] = C.cruce(ff, k0=0.0669 / LAM)
    # estimador del 20/10 (resolucion.py): Tukey 0.2, fase global quitada, anillos 0.012, sm5, último por encima en 3 anillos
    W = np.outer(tukey(1200, 0.2), tukey(1200, 0.2))
    v = [(o * np.exp(-1j * np.angle(np.sum(o)))) for o in (h0, h1)]
    v = [(o - o.mean()) * W for o in v]
    kmax = 1 / (2 * PX); nb = int(round(kmax / 0.012))
    f2 = C.frc(v[0], v[1], PX, nb, kmax)
    r["cruce_20/10_(Tukey,ultimo_por_encima,sm5)"] = last_above(f2[:, 0], sm5(f2[:, 1]), 1 / 7)
    r["banda_C2_estimador_20/10"] = C.band_mean(f2, 2 * 0.0669 / LAM, 0.45)
    r["fase_relativa_mitades_(k,grados,coherencia)"] = relfase(h0, h1, PX, [0.02, 0.06, 0.106, 0.15, 0.212, 0.3, 0.4, 0.5, 0.6, 0.8])
    for kk in [k for k in r if k.startswith("cruce") and r[k]]:
        r[kk] = dict(k=r[kk], periodo_um=1 / r[kk], NA_ef_campo=r[kk] * LAM)
    res[nom] = r
    np.save(f"frc_{nom}.npy", ff)
json.dump(res, open("frc_auditoria.json", "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))

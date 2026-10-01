"""Evolución de la fase reconstruida con las épocas (captura 28/09 b, A+init z=98, campo entero).
Convención de fase de report/informe/make_fig_fase_2809b.py: unwrap_phase + polinomio orden 2 ajustado al 70 % de
píxeles más cercanos a la mediana, luego se resta la mediana. Correr desde la raíz del repo."""
import json, sys, numpy as np
from skimage.restoration import unwrap_phase
from scipy import ndimage as ndi
from skimage.measure import regionprops, label

B = "results/iteraciones_2026-09-30/out/b_{}/real_A+init_z98.0_full/obj_e{:03d}.npy"
OUT = "results/fase_2026-10-01/epocas/"
EP = [0, 1, 2, 3, 5, 8, 12, 20, 30, 40, 60, 80, 120, 160, 240, 320, 400]
CAMPO = 512.0  # µm

def quitar_fondo(p, frac=70, sub=4):
    n = p.shape[0]; y, x = np.mgrid[0:n, 0:n] / n
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    ps, As = p[::sub, ::sub], A[::sub, ::sub]
    d = np.abs(ps - np.median(ps)); m = d < np.percentile(d, frac)
    c, *_ = np.linalg.lstsq(As[m], ps[m], rcond=None)
    sup = A @ c
    q = p - sup
    return q - np.median(q), sup - sup.mean()

def elegir(ph, px):
    ph = ph - ndi.gaussian_filter(ph, 12.0 / px)  # pasa-altos: quita rampas/fondo lento (rojo)
    s = ndi.gaussian_filter(ph, 1.5)
    bgmad = 1.4826 * np.median(np.abs(ph - np.median(ph)))
    thr = max(0.35, 6 * bgmad)
    lab = label(s > thr)
    props = regionprops(lab, intensity_image=ph)
    cand = []
    n = ph.shape[0]
    dil_all = lab > 0
    for p in props:
        if p.area * px * px < 0.8: continue
        r = np.sqrt(p.area / np.pi)
        marg = int(r + 12)
        r0, c0, r1, c1 = p.bbox
        if r0 - marg < 0 or c0 - marg < 0 or r1 + marg > n or c1 + marg > n: continue
        if p.eccentricity > 0.8 or p.solidity < 0.85: continue
        box = lab[r0 - marg:r1 + marg, c0 - marg:c1 + marg]
        if np.any((box > 0) & (box != p.label)): continue
        cand.append(dict(lab=p.label, bbox=[int(r0), int(c0), int(r1), int(c1)], area=int(p.area),
                         d_um=float(2 * r * px), cy=float(p.centroid[0]), cx=float(p.centroid[1])))
    cand.sort(key=lambda c: c["d_um"])
    k = min(16, len(cand))
    idx = np.unique(np.round(np.linspace(0, len(cand) - 1, k)).astype(int))
    return [cand[i] for i in idx], lab, thr, bgmad, len(cand)

def medir(ang_full, c, lab, px):
    r0, c0, r1, c1 = c["bbox"]; r = np.sqrt(c["area"] / np.pi); marg = int(r + 12)
    sl = (slice(r0 - marg, r1 + marg), slice(c0 - marg, c1 + marg))
    ph = unwrap_phase(ang_full[sl])
    m = lab[sl] == c["lab"]
    m_in = ndi.binary_dilation(m, iterations=2)
    ring = ndi.binary_dilation(m, iterations=int(r) + 10) & ~ndi.binary_dilation(m, iterations=int(r / 2) + 4)
    bg = np.median(ph[ring])
    q = ph - bg
    return dict(peak=float(np.percentile(q[m], 95)), vol=float(q[m_in].sum() * px * px),
                bgstd=float(q[ring].std()))

res = {}
for col in sys.argv[1:]:
    o = np.load(B.format(col, 400)); n = o.shape[0]; px = CAMPO / n
    ph400, _ = quitar_fondo(unwrap_phase(np.angle(o)))
    parts, lab, thr, bgmad, ncand = elegir(ph400, px)
    print(col, n, px, "umbral", thr, "candidatas", ncand, "elegidas", len(parts), flush=True)
    bgmask = ndi.binary_dilation(lab > 0, iterations=8)  # fuera = fondo
    R = dict(px=px, n=n, thr=thr, ncand=ncand, parts=parts, ep=EP, g={}, p={})
    prev = None; prevc = None
    for e in EP:
        oe = np.load(B.format(col, e))
        ang = np.angle(oe)
        uw = unwrap_phase(ang)
        ph, sup = quitar_fondo(uw)
        # referencia: mediana del fondo
        ph = ph - np.median(ph[~bgmask])
        g = dict(bgstd=float(ph[~bgmask].std()),
                 bgstd_rob=float(1.4826 * np.median(np.abs(ph[~bgmask] - np.median(ph[~bgmask])))),
                 frac_gt_pi=float(np.mean(np.abs(ph) > np.pi)),
                 frac_wrap=float(np.mean(np.abs(uw - ang) > 1)),
                 sup_ptp=float(sup.max() - sup.min()),
                 lf_bg_std=float(ndi.gaussian_filter(np.where(bgmask, 0, ph), 30)[~bgmask].std()),
                 bgstd_hp=float(1.4826 * np.median(np.abs((ph - ndi.gaussian_filter(ph, 12.0 / px))[~bgmask]))),
                 rel_ph=None, rel_c=None)
        if prev is not None:
            g["rel_ph"] = float(np.sqrt(np.mean((ph - prev) ** 2)) / max(np.sqrt(np.mean(ph ** 2)), 1e-12))
            g["rel_c"] = float(np.linalg.norm(oe - prevc) / np.linalg.norm(oe))
        prev, prevc = ph, oe
        R["g"][e] = g
        R["p"][e] = [medir(ang, c, lab, px) for c in parts]
        if e in (0, 5, 40, 400):
            np.save(OUT + f"ph_{col}_e{e:03d}.npy", ph.astype(np.float32))
        print(col, e, {k: (round(v, 4) if v is not None else None) for k, v in g.items()}, flush=True)
    res[col] = R
    json.dump(res, open(OUT + f"fase_epocas_{col}.json", "w"), indent=1); res = {}

"""vol_fijo.py -- volumen de fase con MÁSCARA FIJA: las partículas (máscara, anillo de fondo, d) se segmentan en el objeto
nominal (iteraciones_2026-09-30, misma época) con el procedimiento de volumen.py; el volumen se mide con esas mismas
máscaras en la fase procesada (mismo quitado de fondo) del objeto die. Así el umbral/ruido del die no cambia la
segmentación. Salida: d_vol/d (mediana, d >= 5 µm) con d nominal, V_die/V_nom por partícula, y cocientes entre colores
V_G/V_R, V_B/V_R (emparejados como en volumen.medir) para nominal y die. Uso: nice python3 vol_fijo.py [EP ...]"""
import json, os, sys
import numpy as np
from scipy import ndimage as ndi
from skimage.restoration import unwrap_phase
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from volumen import quitar_fondo, LAM, DN, SH
from rayas2 import path
COL = {"red": "b_red", "green": "b_green", "blue": "b_blue"}


def fase(o):
    o = o.astype(complex); N = o.shape[0]; hr = 512.0 / N; mg = int(round(16 / hr)); o = o[mg:N - mg, mg:N - mg]
    u = o / np.maximum(abs(o), 1e-6); bgc = ndi.gaussian_filter(u.real, 12 / hr) + 1j * ndi.gaussian_filter(u.imag, 12 / hr)
    w = np.angle(o * np.conj(bgc)); ph = quitar_fondo(unwrap_phase(w))
    sm = ndi.gaussian_filter(ph, 1.0 / hr); bgmask = ~ndi.binary_dilation(sm > 0.3, iterations=int(3 / hr))
    ph = quitar_fondo(ph, frac=90, m_extra=bgmask); sm = ndi.gaussian_filter(ph, 1.0 / hr)
    noise = 1.4826 * np.median(np.abs(sm[bgmask] - np.median(sm[bgmask])))
    return ph, w, sm, noise, hr, mg


def segmentar(ph, w, sm, noise, hr, mg):   # = volumen.particulas, pero devuelve las máscaras
    thr = max(0.3, 5 * noise); lab, n = ndi.label(sm > thr); ring_w = int(round(2 / hr)); P = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        r0, r1, c0, c1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if r0 == 0 or c0 == 0 or r1 == lab.shape[0] or c1 == lab.shape[1]: continue
        pad = ring_w + 4
        R0, R1, C0, C1 = max(r0 - pad, 0), min(r1 + pad, lab.shape[0]), max(c0 - pad, 0), min(c1 + pad, lab.shape[1])
        L = lab[R0:R1, C0:C1]; m = L == k; d = 2 * np.sqrt(m.sum() * hr * hr / np.pi)
        if d < 1.0: continue
        yy, xx = np.nonzero(m); cov = np.cov(np.stack([yy, xx])) if len(yy) > 2 else np.eye(2)
        ev = np.sort(np.linalg.eigvalsh(cov)); elong = np.sqrt(ev[1] / max(ev[0], 1e-9))
        fill = m.sum() / (np.pi * 4 * np.sqrt(ev[0] * ev[1]) + 1e-9)
        ring = ndi.binary_dilation(m, iterations=ring_w) & ~ndi.binary_dilation(m, iterations=2) & (L == 0)
        if ring.sum() < 10: continue
        box = (slice(R0, R1), slice(C0, C1)); Pp = ph[box]; pk = np.percentile(Pp[m], 95) - np.median(Pp[ring])
        Pl = unwrap_phase(w[box]); pkl = np.percentile(Pl[m], 95) - np.median(Pl[ring])
        if abs(pkl - pk) > 1.0 or np.std(Pp[ring]) > 1.0 or elong > 2.0 or fill < 0.6: continue
        cy, cx = ndi.center_of_mass(m)
        P.append(dict(box=box, m=m, ring=ring, d=d, y=(R0 + cy + mg) * hr, x=(C0 + cx + mg) * hr))
    return P


def vol(ph, p, hr):
    Pp = ph[p["box"]]; return float((Pp[p["m"]] - np.median(Pp[p["ring"]])).sum() * hr * hr)


def dvol(V, c): return np.cbrt(np.clip(6 * V * LAM[c] / (2 * np.pi * DN[c] * np.pi), 0, None))


def analizar(e, var="die", ref="base", cols=None):
    R, out = {}, {"por_color": {}, "cocientes_V": {}}
    for c, ds in COL.items():
        if cols and c not in cols: continue
        pb, pd = path(ref, ds, e), path(var, ds, e)
        if not (os.path.exists(pb) and os.path.exists(pd)): continue
        fb = fase(np.load(pb)); fd = fase(np.load(pd)); hr = fb[4]
        P = segmentar(*fb)
        d = np.array([p["d"] for p in P]); Vb = np.array([vol(fb[0], p, hr) for p in P]); Vd = np.array([vol(fd[0], p, hr) for p in P])
        yx = np.array([[p["y"], p["x"]] for p in P]) - SH[c]; s = (d >= 5) & (Vb > 0)
        R[c] = dict(d=d, Vb=Vb, Vd=Vd, yx=yx)
        out["por_color"][c] = dict(N_d5=int(s.sum()), dvol_d_nom=float(np.median(dvol(Vb[s], c) / d[s])),
                                   dvol_d_die=float(np.median(dvol(Vd[s], c) / d[s])),
                                   Vdie_Vnom=float(np.median(Vd[s] / Vb[s])), p25=float(np.percentile(Vd[s] / Vb[s], 25)),
                                   p75=float(np.percentile(Vd[s] / Vb[s], 75)), ruido_nom=float(fb[3]), ruido_die=float(fd[3]))
    if "red" in R:
        for c in ("green", "blue"):
            if c not in R: continue
            qb, qd = [], []
            for i in range(len(R[c]["d"])):
                dd = np.hypot(*(R["red"]["yx"] - R[c]["yx"][i]).T); j = dd.argmin()
                if dd[j] < 2 and abs(R["red"]["d"][j] - R[c]["d"][i]) < 0.5 * max(R["red"]["d"][j], R[c]["d"][i]) \
                        and min(R["red"]["d"][j], R[c]["d"][i]) >= 5 and R["red"]["Vb"][j] > 0 and R["red"]["Vd"][j] > 0:
                    qb.append(R[c]["Vb"][i] / R["red"]["Vb"][j]); qd.append(R[c]["Vd"][i] / R["red"]["Vd"][j])
            out["cocientes_V"][c] = dict(N=len(qb), nom=float(np.median(qb)) if qb else None, die=float(np.median(qd)) if qd else None,
                                         esperado=(DN[c] / LAM[c]) / (DN["red"] / LAM["red"]))
    return out


if __name__ == "__main__":
    res = {}
    for e in (map(int, sys.argv[1:]) if len(sys.argv) > 1 else (5, 40, 160)):
        res[e] = analizar(e); print(e, json.dumps(res[e], indent=1), flush=True)
    f = os.path.join(HERE, "vol_fijo.json"); old = json.load(open(f)) if os.path.exists(f) else {}
    old.update({str(k): v for k, v in res.items()}); json.dump(old, open(f, "w"), indent=1)

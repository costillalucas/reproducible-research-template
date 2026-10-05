"""volumen.py -- regla de volumen de fase (copia funcional de docs/resultados_2026-10-01/fase/particulas/regla.py +
regla_volumen.py), parametrizada por los objetos de entrada. Mismas constantes (DN de sim.py, d >= 5 µm,
corrimientos entre colores de comparar_colores.json, criterios de selección y de emparejamiento).

medir(objs) con objs = {"red": array, "green": array, "blue": array} (grilla completa de cada color) devuelve
dict(por_color={c: mediana d_vol/d (d>=5), N, p25, p75, pearson}, cocientes_V={green|blue: mediana V_c/V_R (d>=5)}).
"""
import numpy as np
from scipy import ndimage as ndi
from skimage.restoration import unwrap_phase

LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}
DN = {c: 0.045 + 0.0015 / l ** 2 for c, l in LAM.items()}
SH = {"red": np.array([6, 1]) * 512 / 1200, "blue": np.array([-5, 0]) * 512 / 1200, "green": np.zeros(2)}


def quitar_fondo(p, frac=70, m_extra=None):
    n0, n1 = p.shape; y, x = np.mgrid[0:n0, 0:n1]; x = x / n1; y = y / n0
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], -1)
    d = np.abs(p - np.median(p)); m = d < np.percentile(d, frac)
    if m_extra is not None: m &= m_extra
    c, *_ = np.linalg.lstsq(A[m], p[m], rcond=None)
    q = p - A @ c
    return q - np.median(q[m])


def particulas(o):
    o = o.astype(complex); N = o.shape[0]; hr = 512.0 / N
    mg = int(round(16 / hr)); o = o[mg:N - mg, mg:N - mg]
    amp = np.abs(o)
    u = o / np.maximum(amp, 1e-6); bgc = ndi.gaussian_filter(u.real, 12 / hr) + 1j * ndi.gaussian_filter(u.imag, 12 / hr)
    w = np.angle(o * np.conj(bgc))
    ph = quitar_fondo(unwrap_phase(w))
    sm = ndi.gaussian_filter(ph, 1.0 / hr)
    bgmask = ~ndi.binary_dilation(sm > 0.3, iterations=int(3 / hr))
    ph = quitar_fondo(ph, frac=90, m_extra=bgmask); sm = ndi.gaussian_filter(ph, 1.0 / hr)
    noise = 1.4826 * np.median(np.abs(sm[bgmask] - np.median(sm[bgmask])))
    thr = max(0.3, 5 * noise)
    lab, n = ndi.label(sm > thr)
    ring_w = int(round(2 / hr)); rows = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        r0, r1, c0, c1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if r0 == 0 or c0 == 0 or r1 == lab.shape[0] or c1 == lab.shape[1]: continue
        pad = ring_w + 4
        R0, R1, C0, C1 = max(r0 - pad, 0), min(r1 + pad, lab.shape[0]), max(c0 - pad, 0), min(c1 + pad, lab.shape[1])
        L = lab[R0:R1, C0:C1]; m = L == k
        area = m.sum() * hr * hr; d = 2 * np.sqrt(area / np.pi)
        if d < 1.0: continue
        yy, xx = np.nonzero(m); cov = np.cov(np.stack([yy, xx])) if len(yy) > 2 else np.eye(2)
        ev = np.sort(np.linalg.eigvalsh(cov)); elong = np.sqrt(ev[1] / max(ev[0], 1e-9))
        fill = m.sum() / (np.pi * 4 * np.sqrt(ev[0] * ev[1]) + 1e-9)
        ring = ndi.binary_dilation(m, iterations=ring_w) & ~ndi.binary_dilation(m, iterations=2) & (L == 0)
        if ring.sum() < 10: continue
        P = ph[R0:R1, C0:C1]; bg = np.median(P[ring]); pk = np.percentile(P[m], 95) - bg; V = float((P[m] - bg).sum() * hr * hr)
        Pl = unwrap_phase(w[R0:R1, C0:C1]); pkl = np.percentile(Pl[m], 95) - np.median(Pl[ring])
        bad = abs(pkl - pk) > 1.0 or np.std(P[ring]) > 1.0
        merged = elong > 2.0 or fill < 0.6
        cy, cx = ndi.center_of_mass(m)
        rows.append(dict(d=d, phi=pk, V=V, y=(R0 + cy + mg) * hr, x=(C0 + cx + mg) * hr, bad=bool(bad), merged=bool(merged)))
    return rows, float(noise)


def medir(objs):
    D, out = {}, {"por_color": {}, "cocientes_V": {}, "ruido": {}}
    for c, o in objs.items():
        rows, noise = particulas(o); out["ruido"][c] = noise
        ok = [r for r in rows if not r["bad"] and not r["merged"]]
        d = np.array([r["d"] for r in ok]); V = np.array([r["V"] for r in ok])
        yx = np.array([[r["y"], r["x"]] for r in ok]) - SH[c]
        dv = np.cbrt(np.clip(6 * V * LAM[c] / (2 * np.pi * DN[c] * np.pi), 0, None))
        D[c] = dict(d=d, V=V, dv=dv, yx=yx)
        s = d >= 5
        out["por_color"][c] = dict(N_todos=int(len(d)), N_d5=int(s.sum()), mediana_dvol_d_d5=float(np.median(dv[s] / d[s])),
                                   p25_d5=float(np.percentile(dv[s] / d[s], 25)), p75_d5=float(np.percentile(dv[s] / d[s], 75)),
                                   pearson_d5=float(np.corrcoef(d[s], dv[s])[0, 1]))
    if "red" in D:
        for c in ("green", "blue"):
            if c not in D: continue
            q = []
            for i in range(len(D[c]["d"])):
                dd = np.hypot(*(D["red"]["yx"] - D[c]["yx"][i]).T); j = dd.argmin()
                if dd[j] < 2 and abs(D["red"]["d"][j] - D[c]["d"][i]) < 0.5 * max(D["red"]["d"][j], D[c]["d"][i]) and D["red"]["V"][j] > 0:
                    q.append((D[c]["V"][i] / D["red"]["V"][j], min(D[c]["d"][i], D["red"]["d"][j])))
            q = np.array(q).reshape(-1, 2); s = q[:, 1] >= 5
            out["cocientes_V"][c] = dict(N_d5=int(s.sum()), mediana_d5=float(np.median(q[s, 0])) if s.any() else None,
                                         esperado=(DN[c] / LAM[c]) / (DN["red"] / LAM["red"]))
    return out


if __name__ == "__main__":   # verificación: reproduce la regla del 01/10 sobre los objetos base de 40 épocas
    import json
    B = "/home/chanoscopio/Documents/LucasC/reproducible-research-template/results/captura_2026-09-28b"
    r = medir({c: np.load(f"{B}/{c}/out/obj_real_A+init_z98.0_full.npy") for c in LAM})
    print(json.dumps(r, indent=1))

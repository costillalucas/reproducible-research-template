#!/usr/bin/env python3
"""medir.py -- FWHM del spot de cada partícula en: LR BF crudo, reconstrucción 200 px (amp/fase), nulo DF 200 px (amp/fase),
recorte 20 px (amp/fase), nulo DF 20 px (amp/fase) y, si existen, recortes 40 / 80 px.

Método (igual para todas las imágenes):
  * centro inicial = posición de la partícula (píxel LR elegido en seleccionar.py; en HR = 3·píxel LR, convención de
    fourier_upsample: la muestra HR j está en j/3 px LR);
  * normalización local: b = media compleja del objeto en el anillo 7.5–11 µm alrededor del centro; amplitud = |o|/|b|,
    fase = angle(o / b) (para el LR BF: sqrt(I) / mediana del anillo);
  * signo del spot = signo de (media del disco r < 1 µm − media del anillo);
  * ajuste gaussiano 2D isótropo + constante (scipy curve_fit), primero en r < 7 µm, después re-ajuste en r < max(2 µm,
    1.5·FWHM) (ventana adaptada, para que los lóbulos/anillos externos no inflen el ancho); FWHM = 2.3548·sigma;
    centro libre dentro de ±3 µm, sigma en [0.1, 8] µm. Se guarda también contraste = |A| y la relación contraste/ruido
    (|A| / desvío del anillo).
  * chequeo independiente: FWHM de perfil radial (media por anillos de 0.2 µm alrededor del centro ajustado; primer cruce
    de la mitad de |A| sobre la constante, interpolado).
  * similitud con la referencia: correlación (Pearson) de la amplitud normalizada y |correlación compleja| normalizada
    (o_norm = o/b) entre el recorte chico (o el nulo) y la MISMA zona de la reconstrucción de 200 px, en el disco r < 8 µm.
  * control de fondo: el mismo ajuste en 8 posiciones por región SIN partícula (lejos de todo candidato), para saber qué
    "FWHM" devuelve el ajuste cuando no hay spot (grano de ruido/speckle).
  * LEDs que cambian BF/DF por el redondeo, por partícula (con el offset de su recorte chico; = redondeo.py).
Salida: medidas.json, medidas.csv, fondo.json.
"""
import csv
import glob
import json
import os
import sys

import numpy as np
from scipy.optimize import curve_fit

P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes"
K = 2 * np.sqrt(2 * np.log(2))


def gauss(xy, A, x0, y0, s, C):
    x, y = xy
    return A * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * s * s)) + C


def ajustar(img, cy, cx, px, compleja=True, cual="amp", s0=1.5):
    """img: arreglo (complejo si compleja). cy, cx: centro en píxeles (float). Devuelve dict de medidas."""
    H, W = img.shape
    yy, xx = np.mgrid[:H, :W]
    Y, X = (yy - cy) * px, (xx - cx) * px
    R = np.hypot(X, Y)
    an = (R >= 7.5) & (R <= 11)
    if an.sum() < 10:
        return None
    if compleja:
        b = img[an].mean()
        z = img / b
        v = np.abs(z) if cual == "amp" else np.angle(z)
    else:
        v = img / np.median(img[an])
    ruido = float(v[an].std())
    c0 = float(v[an].mean())
    sgn = 1.0 if v[R < 1.0].mean() - c0 >= 0 else -1.0
    res = None
    rmax = 7.0
    for _ in range(2):
        m = R < rmax
        p0 = (sgn * max(abs(v[R < 1.0].mean() - c0), 1e-3), 0.0, 0.0, s0 if res is None else res[3], c0)
        lo = (-np.inf, -3, -3, 0.1, -np.inf); hi = (np.inf, 3, 3, 8.0, np.inf)
        try:
            res, _ = curve_fit(gauss, (X[m], Y[m]), v[m], p0=p0, bounds=(lo, hi), maxfev=20000)
        except Exception:
            return dict(fwhm=np.nan, fwhm_radial=np.nan, contraste=np.nan, snr=np.nan, ruido=ruido, ok=False)
        rmax = max(2.0, 1.5 * K * res[3])
    A, x0, y0, s, C = res
    # perfil radial alrededor del centro ajustado
    Rr = np.hypot(X - x0, Y - y0)
    e = np.arange(0, 7.01, 0.2)
    idx = np.digitize(Rr.ravel(), e) - 1
    ok = (idx >= 0) & (idx < len(e) - 1)
    prof = np.bincount(idx[ok], (v.ravel()[ok] - C) * np.sign(A), len(e) - 1) / np.maximum(np.bincount(idx[ok], None, len(e) - 1), 1)
    rc = 0.5 * (e[:-1] + e[1:])
    cnt = np.bincount(idx[ok], None, len(e) - 1)
    good = cnt > 0
    rc, prof = rc[good], prof[good]
    half = prof[0] / 2
    fr = np.nan
    for i in range(1, len(prof)):
        if prof[i] < half <= prof[i - 1]:
            fr = 2 * (rc[i - 1] + (half - prof[i - 1]) * (rc[i] - rc[i - 1]) / (prof[i] - prof[i - 1]))
            break
    return dict(fwhm=float(K * s), fwhm_radial=float(fr), contraste=float(abs(A)), signo=int(np.sign(A)),
                snr=float(abs(A) / max(ruido, 1e-9)), ruido=ruido, dx=float(x0), dy=float(y0), ok=bool(s < 7.9 and s > 0.11))


def similitud(a, b, cy, cx, px):
    """a, b: objetos complejos del mismo tamaño y grilla, centrados en (cy, cx)."""
    H = a.shape[0]
    yy, xx = np.mgrid[:H, :H]
    R = np.hypot(yy - cy, xx - cx) * px
    an = (R >= 7.5) & (R <= 11); d = R < 8
    za, zb = a / a[an].mean(), b / b[an].mean()
    aa, ab = np.abs(za[d]), np.abs(zb[d])
    ca = float(np.corrcoef(aa, ab)[0, 1])
    u, v = za[d] - za[d].mean(), zb[d] - zb[d].mean()
    cc = float(np.abs(np.vdot(u, v)) / np.sqrt(np.vdot(u, u).real * np.vdot(v, v).real))
    return ca, cc


def main():
    sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo")
    sys.path.insert(0, os.path.join(P0, "codigo"))
    os.environ.setdefault("Z_MM", "99.5"); os.environ.setdefault("NA_OBJ", "0.0720"); os.environ.setdefault("LAM_NM", "617")
    import reconstruir_plan as RP
    F, _ = RP.cargar_solver("red", 3)
    J = json.load(open(os.path.join(P0, "particulas.json")))
    regs = J["regiones"]
    cache = {}

    def ref(nombre, reg):
        key = (nombre, reg)
        if key not in cache:
            f = os.path.join(P0, "runs", f"{nombre}_{reg}", "objeto_complejo.npy")
            cache[key] = np.load(f) if os.path.exists(f) else None
        return cache[key]

    lrcache = {}
    filas = []
    for p in J["particulas"]:
        reg = p["region"]
        if reg not in lrcache:
            D = F.load_real(os.path.join(P0, "runs", f"ref_{reg}", "datos", "prep.npz"))
            lrcache[reg] = D["I"][RP.CENTRO_LED]
        fr, cr = p["fila_rec"], p["col_rec"]
        row = dict(id=p["id"], region=reg, fila_roi=p["fila_roi"], col_roi=p["col_roi"], energia=p["energia"], vecino_um=p["vecino_um"])
        lr = np.sqrt(np.clip(lrcache[reg], 0, None))
        m = ajustar(lr, fr, cr, 1.29, compleja=False, s0=2.5)
        row.update({f"LR_{k}": v for k, v in m.items()})
        if ref("nulo", reg) is not None and ref("ref", reg) is not None:
            ca, cc = similitud(ref("nulo", reg), ref("ref", reg), 3 * fr, 3 * cr, 0.43)
            row["nulo200_corr_amp"], row["nulo200_corr_cplx"] = ca, cc
        for brazo in ("ref", "nulo"):
            o = ref(brazo, reg)
            if o is None:
                continue
            for cual in ("amp", "fase"):
                m = ajustar(o, 3 * fr, 3 * cr, 0.43, cual=cual)
                row.update({f"{brazo}200_{cual}_{k}": v for k, v in m.items()})
        for d in sorted(glob.glob(os.path.join(P0, "runs", "chicos_*"))):
            tag = os.path.basename(d).replace("chicos_", "c")
            f = os.path.join(d, f"{p['id']}.npz")
            if not os.path.exists(f):
                continue
            z = np.load(f)
            o = z["obj"]
            n = o.shape[0] // 3
            # misma zona de la referencia 200 px (grilla HR: muestra j <-> j/3 px LR)
            o_ref = ref("ref", reg)
            a0, b0 = 3 * (fr - n // 2), 3 * (cr - n // 2)
            if o_ref is not None:
                ca, cc = similitud(o, o_ref[a0:a0 + 3 * n, b0:b0 + 3 * n], 3 * (n // 2), 3 * (n // 2), float(z["hrpx"]))
                row[f"{tag}_corr_amp"], row[f"{tag}_corr_cplx"] = ca, cc
            if "nulo" not in tag:
                import recortes_chicos as RC
                geo = F.geometry(RP.Z_MM, offset_mm=tuple(z["offset_mm"]), crop=n)
                row[f"{tag}_cambian"] = [list(k) for k in RC.leds_que_cambian(F, geo, sorted(geo["fxy"]), n)]
            for cual in ("amp", "fase"):
                m = ajustar(o, 3 * (n // 2), 3 * (n // 2), float(z["hrpx"]), cual=cual)
                if m is None:
                    continue
                row.update({f"{tag}_{cual}_{k}": v for k, v in m.items()})
            row[f"{tag}_t_s"] = float(z["t_s"])
            row[f"{tag}_err_final"] = float(z["hist"][-1])
        filas.append(row)
    json.dump(filas, open(os.path.join(P0, "medidas.json"), "w"), indent=1)
    # control de fondo: posiciones sin partícula (energía local < 0.05 en 12 px a la redonda), 8 por región, seed 1
    from scipy import ndimage as ndi
    q = np.load(os.path.join(P0, "datos", "q_bf_roi.npy")).astype(float)
    h = q - ndi.median_filter(q, 31); e = np.sqrt(ndi.gaussian_filter(h ** 2, 2.5))
    libre = ndi.maximum_filter(e, 25) < 0.06
    rng = np.random.default_rng(1)
    fondo = []
    for reg, (f0, c0, nn) in regs.items():
        cand = [(y, x) for y in range(f0 + 30, f0 + nn - 30, 3) for x in range(c0 + 30, c0 + nn - 30, 3) if libre[y, x]]
        for i in rng.choice(len(cand), size=min(8, len(cand)), replace=False):
            y, x = cand[i]
            r = dict(region=reg, fila_roi=int(y), col_roi=int(x))
            for brazo in ("ref", "nulo"):
                for cual in ("amp", "fase"):
                    m = ajustar(ref(brazo, reg), 3 * (y - f0), 3 * (x - c0), 0.43, cual=cual)
                    r[f"{brazo}200_{cual}_fwhm"] = m["fwhm"]; r[f"{brazo}200_{cual}_ok"] = m["ok"]
            fondo.append(r)
    json.dump(fondo, open(os.path.join(P0, "fondo.json"), "w"), indent=1)
    for col in ("ref200_amp_fwhm", "ref200_fase_fwhm", "nulo200_amp_fwhm", "nulo200_fase_fwhm"):
        v = np.array([r[col] for r in fondo if r[col.replace("fwhm", "ok")]])
        print(f"FONDO {col:24s} {np.median(v):.2f} [{np.percentile(v, 25):.2f}–{np.percentile(v, 75):.2f}] (n={len(v)})")
    cols = sorted({k for r in filas for k in r}, key=lambda k: (k not in ("id", "region"), k))
    with open(os.path.join(P0, "medidas.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader(); [w.writerow(r) for r in filas]
    # resumen
    def med(col):
        v = np.array([r.get(col, np.nan) for r in filas], float)
        okc = col.replace("_fwhm", "_ok")
        okv = np.array([r.get(okc, False) for r in filas], bool) if col.endswith("_fwhm") else np.isfinite(v)
        v = v[np.isfinite(v) & okv]
        if len(v) == 0:
            return "—"
        q1, q2, q3 = np.percentile(v, [25, 50, 75])
        return f"{q2:.2f} [{q1:.2f}–{q3:.2f}] (n={len(v)})"
    for col in sorted({k for r in filas for k in r if k.endswith("_fwhm") or k.endswith("_fwhm_radial") or k.endswith("_snr") or "_corr_" in k}):
        print(f"{col:32s} {med(col)}")


if __name__ == "__main__":
    main()

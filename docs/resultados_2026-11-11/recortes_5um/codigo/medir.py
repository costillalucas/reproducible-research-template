#!/usr/bin/env python3
"""medir.py -- métricas por esfera de 5 µm en cada brazo, SIEMPRE sobre la misma huella física: los 20x20 px LR (25.8 µm)
centrados en el píxel de la esfera (= huella del recorte de 20 px).
Brazos: b400 (= r400 filtrado por la pupila coherente NA/λ: banda de UNA imagen BF, línea de base sin FPM), r20sc (recorte de
20 px sin los LEDs que cambian BF/DF por redondeo), LR (sqrt(I) del LED (17,15), BF/flat, 20 px crudos, 1.29 µm), r400 (epocas_400b e160), r200 (epocas_200 e160, solo las 3
esferas dentro), r20 / r40 / r80 (recortes chicos, 160 ép.), n400 (red_nulo_df, 400 px, 160 ép., DF permutado) y n20 (recorte 20 nulo).
Convención HR: píxel LR j <-> muestra HR 3j (fourier_upsample).
Por imagen:
  * antes: se quita la rampa lineal de fase medida fuera de la esfera (r >= 6 µm; producto de vecinos, = rampa.py);
  * z = o / b, b = media compleja en el anillo 7.5-11 µm alrededor del píxel de la esfera; después se resta a |z| y a angle(z) un
    PLANO ajustado en ese anillo (quita rampas de fase de baja frecuencia; NO quita el escalón de envoltura del recorte de 20 px);
    para LR: a = sqrt(I)/mediana del anillo, menos su plano.
  * señal: fase = angle(z) (sin signo forzado); amplitud = |z|-1 con el signo de la media del disco r<1.5 µm (en LR la esfera
    es oscura -> señal = 1-|a|).
  * centro = centroide de la señal positiva en r < 4 µm del píxel de la esfera (2 pasadas). desplaz = distancia al centro
    medido en r400 (µm).
  * FWHM_g: gaussiana 2D isótropa + constante ajustada en r < 6 µm (curve_fit), 2.3548·sigma.
  * perfil radial (anillos de 0.2 µm) alrededor del centro; p0 = máximo del perfil en r < 1.5 µm;
    FWHM_r = 2·(primer r donde p < p0/2); BORDE 10-90 = r(p < 0.1 p0) - r(p < 0.9 p0) (cruces interpolados, primer cruce
    hacia afuera desde el máximo).
  * volumen de fase = suma de angle(z) en r < 5 µm (y en r < 3.5 µm, menos sensible al fondo) · área del píxel (rad·µm²);
    fase_envuelta = algún |fase| > 2.8 rad en r < 3 µm (posible envoltura: esa esfera no sirve para volumen/FWHM de fase).
  * marco: desvío estándar de la fase en el marco exterior de 1 px LR (3 px HR) de la huella (envoltura/borde).
Salida: medidas.json, medidas.csv.
"""
import csv, json, os
import numpy as np
from scipy.optimize import curve_fit

P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/"
B = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/"
K = 2 * np.sqrt(2 * np.log(2))
LRPX, HRPX = 1.29, 0.43


def plano(v, X, Y, m):
    A = np.c_[np.ones(m.sum()), X[m], Y[m]]
    c, *_ = np.linalg.lstsq(A, v[m], rcond=None)
    return v - (c[0] + c[1] * X + c[2] * Y)


def gauss(xy, A, x0, y0, s, C):
    x, y = xy
    return A * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * s * s)) + C


def cruce(rc, p, nivel, i0):
    for i in range(i0 + 1, len(p)):
        if p[i] < nivel <= p[i - 1]:
            return rc[i - 1] + (nivel - p[i - 1]) * (rc[i] - rc[i - 1]) / (p[i] - p[i - 1])
    return np.nan


def metricas(v, px, X, Y, R):
    """v: señal (positiva en la esfera). Devuelve FWHM_g, FWHM_r, borde, p0, centro."""
    cy = cx = 0.0
    for _ in range(2):
        Rc = np.hypot(X - cx, Y - cy)
        w = np.clip(v, 0, None) * (Rc < 4)
        if w.sum() <= 0:
            break
        cx, cy = (w * X).sum() / w.sum(), (w * Y).sum() / w.sum()
    Rc = np.hypot(X - cx, Y - cy)
    m = Rc < 6
    try:
        p, _ = curve_fit(gauss, (X[m], Y[m]), v[m], p0=(max(v[Rc < 1.5].mean(), 1e-3), cx, cy, 1.5, 0),
                         bounds=((-np.inf, cx - 3, cy - 3, 0.1, -np.inf), (np.inf, cx + 3, cy + 3, 8, np.inf)), maxfev=20000)
        fg = K * p[3] if 0.11 < p[3] < 7.9 else np.nan
    except Exception:
        fg = np.nan
    e = np.arange(0, 8.01, 0.2)
    idx = np.digitize(Rc.ravel(), e) - 1
    ok = (idx >= 0) & (idx < len(e) - 1)
    cnt = np.bincount(idx[ok], None, len(e) - 1)
    pr = np.bincount(idx[ok], v.ravel()[ok], len(e) - 1) / np.maximum(cnt, 1)
    rc = 0.5 * (e[:-1] + e[1:])
    g = cnt > 0
    rc, pr = rc[g], pr[g]
    sel = rc < 1.5
    i0 = int(np.argmax(np.where(sel, pr, -np.inf)))
    p0 = pr[i0]
    if p0 <= 0:
        return dict(fwhm_g=fg, fwhm_r=np.nan, borde=np.nan, p0=float(p0), cx=cx, cy=cy)
    r50, r90, r10 = (cruce(rc, pr, f * p0, i0) for f in (0.5, 0.9, 0.1))
    return dict(fwhm_g=float(fg), fwhm_r=float(2 * r50), borde=float(r10 - r90), p0=float(p0), cx=float(cx), cy=float(cy))


def medir(img, px, lr=False):
    n = img.shape[0]
    c = 10 if lr else 30
    yy, xx = np.mgrid[:n, :n]
    X, Y = (xx - c) * px, (yy - c) * px
    R = np.hypot(X, Y)
    an = (R >= 7.5) & (R <= 11)
    out = {}
    if lr:
        a = np.sqrt(np.clip(img, 0, None)); a = a / np.median(a[an])
        a = plano(a, X, Y, an) + 1
        sgn = 1.0 if a[R < 1.5].mean() >= 1 else -1.0
        r = metricas(sgn * (a - 1), px, X, Y, R)
        out.update({f"amp_{k}": v for k, v in r.items()}); out["amp_signo"] = sgn
        return out
    # rampa lineal de fase fuera de la esfera (r >= 6 µm), por producto de vecinos; se quita ANTES de normalizar (= rampa.py)
    zz = img / np.abs(img).clip(1e-12); far = R >= 6
    gx = np.angle((zz[:, 1:] * np.conj(zz[:, :-1]))[far[:, 1:] & far[:, :-1]].sum())
    gy = np.angle((zz[1:, :] * np.conj(zz[:-1, :]))[far[1:, :] & far[:-1, :]].sum())
    out["rampa_bins_x"], out["rampa_bins_y"] = float(gx * n / (2 * np.pi)), float(gy * n / (2 * np.pi))
    img = img * np.exp(-1j * (gx * (xx - c) + gy * (yy - c)))
    z = img / img[an].mean()
    am = plano(np.abs(z), X, Y, an) + 1
    ph = plano(np.angle(z), X, Y, an)
    sgn = 1.0 if am[R < 1.5].mean() >= 1 else -1.0
    r = metricas(sgn * (am - 1), px, X, Y, R)
    out.update({f"amp_{k}": v for k, v in r.items()}); out["amp_signo"] = sgn
    r = metricas(ph, px, X, Y, R)
    out.update({f"fase_{k}": v for k, v in r.items()})
    Rc = np.hypot(X - r["cx"], Y - r["cy"])
    out["fase_vol"] = float(ph[Rc < 5].sum() * px * px)
    out["fase_vol35"] = float(ph[Rc < 3.5].sum() * px * px)
    out["fase_fondo_rms"] = float(ph[an].std())          # rms de la fase (ya sin plano) en el anillo 7.5-11 µm
    out["fase_pico"] = float(ph[Rc < 1.5].mean())
    out["fase_envuelta"] = bool((np.abs(np.angle(z))[Rc < 3] > 2.8).any())   # algún píxel |fase| > 2.8 rad en r < 3 µm
    fr = np.ones_like(ph, bool); fr[3:-3, 3:-3] = False
    out["marco_std_fase"] = float(np.angle(z)[fr].std())
    return out


def main():
    J = json.load(open(P0 + "particulas.json"))["particulas"]
    o400 = np.load(B + "epocas_400b/snapshots/objeto_full_e160.npy")
    o200 = np.load(B + "epocas_200/snapshots/objeto_full_e160.npy")
    n400 = np.load(B + "red_nulo_df/objeto_complejo.npy")
    # r400 pasado por la pupila coherente del objetivo (NA 0.06686 / λ 0.63, círculo en el espectro del objeto de 400 px):
    # la MISMA reconstrucción limitada a la banda de una sola imagen BF -> línea de base 'sin FPM' para FWHM / borde de la fase.
    S = np.fft.fftshift(np.fft.fft2(o400)); N = S.shape[0]
    f = np.fft.fftshift(np.fft.fftfreq(N, d=HRPX)); FX, FY = np.meshgrid(f, f)
    b400 = np.fft.ifft2(np.fft.ifftshift(S * (np.hypot(FX, FY) < 0.069 * 1.25 / 1.29 / 0.63)))
    filas = []
    for p in J:
        y, x = 3 * p["fila400"], 3 * p["col400"]
        arms = {"r400": o400[y - 30:y + 30, x - 30:x + 30], "n400": n400[y - 30:y + 30, x - 30:x + 30],
                "b400": b400[y - 30:y + 30, x - 30:x + 30]}
        if p["en_200"]:
            arms["r200"] = o200[y - 330:y - 270, x - 330:x - 270]
        lr = None
        for t, nom in ((20, "r20"), (20, "r20_nulo"), (20, "r20_sincambian"), (40, "r40"), (80, "r80")):
            f = P0 + f"runs/{nom}/{p['id']}.npz"
            if os.path.exists(f):
                d = np.load(f); o = d["obj"]; c = 3 * (t // 2)
                arms[nom.replace("r20_nulo", "n20").replace("r20_sincambian", "r20sc")] = o[c - 30:c + 30, c - 30:c + 30]
                if nom == "r20":
                    lr = d["lr_bf"]; tiempo = float(d["t_s"]); camb = d["cambian"].tolist()
                arms[nom.replace("r20_nulo", "n20").replace("r20_sincambian", "r20sc") + "_t"] = float(d["t_s"])
        fila = dict(id=p["id"], fila400=p["fila400"], col400=p["col400"], en_200=p["en_200"])
        if lr is not None:
            fila.update({f"LR_{k}": v for k, v in medir(lr, LRPX, lr=True).items()}); fila["cambian_r20"] = camb
        ref = None
        for nom, img in arms.items():
            if nom.endswith("_t"):
                fila[f"t_{nom[:-2]}"] = img; continue
            m = medir(img, HRPX)
            if nom == "r400":
                ref = (m["fase_cx"], m["fase_cy"])
            fila.update({f"{nom}_{k}": v for k, v in m.items()})
        for nom in [n for n in arms if not n.endswith("_t")]:
            fila[f"{nom}_desplaz"] = float(np.hypot(fila[f"{nom}_fase_cx"] - ref[0], fila[f"{nom}_fase_cy"] - ref[1]))
        filas.append(fila)
    json.dump(filas, open(P0 + "medidas.json", "w"), indent=1, default=float)
    keys = sorted({k for f in filas for k in f})
    with open(P0 + "medidas.csv", "w") as fh:
        w = csv.DictWriter(fh, keys); w.writeheader(); [w.writerow(f) for f in filas]
    print(len(filas), "esferas medidas")


if __name__ == "__main__":
    main()

"""esferas.py -- medición directa de resolución con esferas aisladas de 500 nm (muestra 2026-10-21.500), pedida 21/10 tarde.

Una esfera de 0.5 µm es sub-resolución para NA_obj (λ/NA = 9.4 µm) y casi puntual para la NA sintética: su imagen ES la PSF coherente
(de campo complejo) del sistema. Se mide el ancho de esa imagen en:
  * crudo: BF (17,15) del objetivo del solver (S/F·<F>), en amplitud sqrt(I) Fourier-upsampleada al píxel HR (igual que C4/resolucion);
    a primer orden I ≈ b² + 2b·Re(s⊗h), así que el ancho de la desviación de intensidad/amplitud es el de la PSF de amplitud.
  * reconstrucción (full, mitades, nulo/mezcladas): |Δo| (campo complejo menos el fondo complejo local), amplitud y fase relativa.
Detección EN EL CRUDO (la primera versión, picos aislados de |Δo| del full, no encontró ninguno: la reconstrucción tiene textura
granular en todo el campo): picos de |LoG| (sigma 2.5 µm) del BF crudo > 5·MAD, a > 15 µm del borde y fuera del polvo; AISLADA = ningún
otro pico crudo (> 0.4 del propio) a < 15 µm y |desviación cruda| en el anillo 7–15 µm < 0.5 de la central; desviación central > 4·MAD.
El centro en la reconstrucción es el máximo de |Δo| (full) a < 3 µm del pico crudo, refinado por centroide.
Ancho: FWHM del perfil radial (promedio azimutal desde el centroide sub-píxel, fondo = mediana del anillo 10–14 µm), cruce a media altura
interpolado. Teoría coherente (pupila circular, PSF de amplitud 2J1(v)/v): FWHM = 0.705·λ/NA; para NA_obj y para NA_obj + NA_ilum de
los anillos usados (todas las LEDs entrenadas; también hasta el anillo 8, último con SNR/frame ≥ 3).
Barrido de refoco: el campo complejo full se propaga (espectro angular, en aire) dz ∈ [-40, 40] µm y se mide la mediana del FWHM.
Uso: python3 esferas.py [EPOCA]   -> esferas_<DS>.json, ../figs/esferas_<DS>.png"""
import json, os, sys
import numpy as np
from scipy import ndimage as ndi
from scipy.special import j1
from scipy.optimize import brentq
import comun as C
from resolucion import objs

ep = int(sys.argv[1]) if len(sys.argv) > 1 else 160
ISO_R, ISO_PK, ISO_ANN = (float(os.environ.get(k, d)) for k, d in (("ISO_R", 15), ("ISO_PK", 0.4), ("ISO_ANN", 0.5)))
TAG = os.environ.get("TAG", "")
F, geo, D = C.load()
px, lam, na = geo["hrpx"], geo["lam"], geo["na"]
O = objs("final", ep)
H = O["full"].shape[0]; f = H // D["I"][(17, 15)].shape[0]
raw = np.real(F.fourier_upsample(np.sqrt(np.clip(D["I"][(17, 15)], 0, None)), f))
dust = ndi.zoom(D["mask"][(17, 15)] == 0, f, order=0) if D["mask"][(17, 15)].dtype == bool else None
ok = np.ones((H, H), bool)
if dust is not None:
    ok &= ~ndi.binary_dilation(dust, iterations=int(8 / px))
m = int(18 / px); ok[:m] = ok[-m:] = False; ok[:, :m] = ok[:, -m:] = False

# NA sintética
fxy = np.array([geo["fxy"][k] for k in D["keys"]]); rg = np.array([F.ring(k) for k in D["keys"]])
nai = np.hypot(fxy[:, 0], fxy[:, 1]) * lam
k_fwhm = brentq(lambda v: 2 * j1(v) / v - 0.5, 1, 3) / np.pi   # FWHM = k_fwhm·λ/NA  (0.705)
teo = {"NA_obj": na, "FWHM_NA_obj_um": k_fwhm * lam / na,
       "NA_sint_todas": na + nai.max(), "FWHM_NA_sint_todas_um": k_fwhm * lam / (na + nai.max()),
       "NA_sint_anillo_le8": na + nai[rg <= 8.5].max(), "FWHM_NA_sint_anillo_le8_um": k_fwhm * lam / (na + nai[rg <= 8.5].max()),
       "NA_sint_anillo_lt7": na + nai[rg < 7].max(), "FWHM_NA_sint_anillo_lt7_um": k_fwhm * lam / (na + nai[rg < 7].max()),
       "FWHM_lim_pixel_HR_um": 2 * px, "k_fwhm": k_fwhm}


def dev(o, s=10.0):
    """campo complejo menos el fondo complejo local (gauss s µm); fase de referencia global."""
    o = o * np.exp(-1j * np.angle(np.sum(o)))
    bg = ndi.gaussian_filter(o.real, s / px) + 1j * ndi.gaussian_filter(o.imag, s / px)
    return o - bg, bg


def radial_fwhm(img, cy, cx, rmax=14.0):
    """perfil radial (paso 0.5 px) alrededor de (cy,cx) sub-píxel; fondo = mediana en 10–14 µm; FWHM por cruce a media altura."""
    r0 = int(rmax / px) + 2
    y0, x0 = int(round(cy)), int(round(cx))
    sub = img[y0 - r0:y0 + r0 + 1, x0 - r0:x0 + r0 + 1]
    yy, xx = np.mgrid[-r0:r0 + 1, -r0:r0 + 1]
    rr = np.hypot(yy + y0 - cy, xx + x0 - cx) * px
    bgv = np.median(sub[(rr > 10) & (rr < 14)])
    e = np.arange(0, 10 + 1e-9, px / 2); idx = np.digitize(rr.ravel(), e) - 1; okb = (idx >= 0) & (idx < len(e) - 1)
    cnt = np.bincount(idx[okb], None, len(e) - 1)
    prof = np.bincount(idx[okb], (sub.ravel() - bgv)[okb], len(e) - 1) / np.maximum(cnt, 1)
    rc = 0.5 * (e[:-1] + e[1:])
    nz = cnt > 0                      # bins vacíos (radios sin píxel) fuera: si no, cuentan como 0 y fingen un cruce
    rc, prof = rc[nz], prof[nz]
    p0 = prof[0]
    if p0 <= 0:
        return None, rc, prof
    pn = prof / p0
    i = np.argmax(pn < 0.5)
    if i == 0 or pn[i] >= 0.5:
        return None, rc, prof
    r_half = rc[i - 1] + (0.5 - pn[i - 1]) * (rc[i] - rc[i - 1]) / (pn[i] - pn[i - 1])
    return 2 * r_half, rc, prof


def centroid(img, y, x, r=2):
    w = img[y - r:y + r + 1, x - r:x + r + 1]; w = np.clip(w - w.min(), 0, None)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    s = w.sum() or 1
    return y + (w * yy).sum() / s, x + (w * xx).sum() / s


def detect(o):
    d, _ = dev(o)
    a = ndi.gaussian_filter(np.abs(d), 1)
    thr = np.median(a) + 6 * 1.4826 * np.median(np.abs(a - np.median(a)))
    pk = (a == ndi.maximum_filter(a, size=int(3 / px))) & (a > thr) & ok
    ys, xs = np.nonzero(pk)
    vals = a[ys, xs]
    yy, xx = np.mgrid[-int(12 / px):int(12 / px) + 1, -int(12 / px):int(12 / px) + 1]
    rr = np.hypot(yy, xx) * px; ann = (rr > 4) & (rr < 12)
    iso = []
    for y, x, v in zip(ys, xs, vals):
        dd = np.hypot(ys - y, xs - x) * px
        if np.any((dd > 0) & (dd < 12) & (vals > 0.3 * v)):
            continue
        r0 = int(12 / px); w = a[y - r0:y + r0 + 1, x - r0:x + r0 + 1]
        if w.shape != ann.shape or w[ann].max() > 0.35 * v:
            continue
        iso.append((y, x, v))
    return a, thr, len(ys), iso


def propagate(o, dz):
    k = np.fft.fftfreq(H, px); KX, KY = np.meshgrid(k, k)
    kz = np.sqrt(np.clip((1 / lam) ** 2 - KX ** 2 - KY ** 2, 0, None))
    return np.fft.ifft2(np.fft.fft2(o) * np.exp(2j * np.pi * dz * kz))


a_full, thr, npk, _iso_rec = detect(O["full"])
rd = raw - ndi.gaussian_filter(raw, 10 / px)
rmad = 1.4826 * np.median(np.abs(rd - np.median(rd)))
# detección en el CRUDO (lo que es una esfera visible en BF): |LoG| con sigma 2.5 µm (~PSF de NA_obj), picos > 5 MAD;
# AISLADA = sin otro pico crudo (> 0.4 del propio) a < 15 µm y |rd| en el anillo 7–15 µm < 0.5 de |rd| en el centro.
lg = -ndi.gaussian_laplace(rd, 2.5 / px)
for sgn in (1,):
    al = np.abs(lg); lthr = np.median(al) + 5 * 1.4826 * np.median(np.abs(al - np.median(al)))
    pk = (al == ndi.maximum_filter(al, size=int(6 / px))) & (al > lthr) & ok
ys, xs = np.nonzero(pk); vals = al[ys, xs]
r0 = int(ISO_R / px); yy, xx = np.mgrid[-r0:r0 + 1, -r0:r0 + 1]; rr = np.hypot(yy, xx) * px; ann = (rr > 7) & (rr < ISO_R)
iso = []
for y, x, v in zip(ys, xs, vals):
    dd = np.hypot(ys - y, xs - x) * px
    if np.any((dd > 0) & (dd < ISO_R) & (vals > ISO_PK * v)):
        continue
    w = np.abs(rd[y - r0:y + r0 + 1, x - r0:x + r0 + 1])
    if w.shape != ann.shape or w[ann].max() > ISO_ANN * abs(rd[y, x]):
        continue
    iso.append((y, x, float(a_full[y, x])))
npk_raw = len(ys)
rows = []
CEN = {t: [] for t in ("x01", "x10", "scr_x01", "scr_x10", "raw")}
r3 = int(3 / px)
views = {}
for n in ("full", "half0", "half1", "half0_scr", "half1_scr"):
    d, bg = dev(O[n])
    views[n] = dict(cmplx=np.abs(d), amp=np.abs(O[n] * np.exp(-1j * np.angle(np.sum(O[n])))) - np.abs(bg),
                    fase=np.angle((O[n] * np.exp(-1j * np.angle(np.sum(O[n])))) * np.exp(-1j * np.angle(bg))))
for y, x, v in iso:
    rv = rd[y, x]
    if abs(rv) < 4 * rmad:
        continue
    Y0, X0 = y, x
    CEN["raw"].append(centroid(al, y, x))
    # centro: máximo de |Δo| del full (suavizado 1 px) a < 3 µm del pico crudo, refinado por centroide
    r3 = int(3 / px); w = a_full[y - r3:y + r3 + 1, x - r3:x + r3 + 1]; iy, ix = np.unravel_index(np.argmax(w), w.shape)
    y, x = y - r3 + iy, x - r3 + ix
    cy, cx = centroid(a_full, y, x)
    row = dict(y_um=float(cy * px), x_um=float(cx * px), pico_cmplx=float(v), crudo_desv_sobre_mad=float(rv / rmad))
    w, _, _ = radial_fwhm(np.sign(rv) * rd, cy, cx); row["crudo"] = w
    for n, vv in views.items():
        for q, img in vv.items():
            s = 1.0
            if q != "cmplx":
                c0 = img[int(round(cy)) - 1:int(round(cy)) + 2, int(round(cx)) - 1:int(round(cx)) + 2].mean()
                s = np.sign(c0) or 1.0
            w, _, _ = radial_fwhm(s * img, cy, cx); row[f"{n}_{q}"] = w
    # validación cruzada (sin sesgo de selección del centro): centro = máximo de |Δo| de una mitad (suav. 1 px, < 3 µm del pico crudo),
    # ancho medido en la OTRA mitad; igual para las mitades mezcladas (nulo)
    for a, b, tag in (("half0", "half1", "x01"), ("half1", "half0", "x10"), ("half0_scr", "half1_scr", "scr_x01"), ("half1_scr", "half0_scr", "scr_x10")):
        A = ndi.gaussian_filter(views[a]["cmplx"], 1); y0, x0 = Y0, X0
        w = A[y0 - r3:y0 + r3 + 1, x0 - r3:x0 + r3 + 1]; iy, ix = np.unravel_index(np.argmax(w), w.shape)
        ca = centroid(A, y0 - r3 + iy, x0 - r3 + ix); CEN[tag].append(ca)
        ww, _, _ = radial_fwhm(views[b]["cmplx"], *ca); row[f"{tag}_cmplx"] = ww
    rows.append(row)


def med(key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return dict(n=len(v), mediana=float(np.median(v)) if v else None, p25=float(np.percentile(v, 25)) if v else None,
                p75=float(np.percentile(v, 75)) if v else None)


# FRC LOCAL en ventanas de 20 µm sobre las esferas (Hann), entre mitades y entre mitades mezcladas: correlación compleja del Δo en
# bandas de k (1/µm). Es C2 restringido a donde hay objetos (el FRC global lo diluye la textura/ruido del resto del campo).
BANDS = {"[0,NA/λ]": (0, na / lam), "[NA/λ,2NA/λ]": (na / lam, 2 * na / lam), "[2NA/λ,0.45]": (2 * na / lam, 0.45), "[0.45,0.9]": (0.45, 0.9)}
hwf = int(10 / px); hann = np.outer(np.hanning(2 * hwf + 1), np.hanning(2 * hwf + 1))
kk = np.fft.fftfreq(2 * hwf + 1, px); KR = np.hypot(*np.meshgrid(kk, kk))
frc_loc = {}
rng = np.random.default_rng(0); oy, ox = np.nonzero(ok); ri = rng.choice(len(oy), 300, replace=False)
RAND = list(zip(oy[ri].astype(float), ox[ri].astype(float)))   # control: ventanas al azar en el campo
for a, b, tag, pos in (("half0", "half1", "mitades", CEN["raw"]), ("half0_scr", "half1_scr", "nulo", CEN["raw"]),
                       ("half0", "half1", "mitades_azar", RAND), ("half0_scr", "half1_scr", "nulo_azar", RAND)):
    da, db = dev(O[a])[0], dev(O[b])[0]; per = {k: [] for k in BANDS}
    for c in pos:
        y, x = int(round(c[0])), int(round(c[1]))
        A = np.fft.fft2(da[y - hwf:y + hwf + 1, x - hwf:x + hwf + 1] * hann); B = np.fft.fft2(db[y - hwf:y + hwf + 1, x - hwf:x + hwf + 1] * hann)
        for k, (lo, hi) in BANDS.items():
            m = (KR >= lo) & (KR < hi)
            per[k].append(float(np.abs(np.sum(A[m] * np.conj(B[m]))) / np.sqrt(np.sum(np.abs(A[m]) ** 2) * np.sum(np.abs(B[m]) ** 2))))
    frc_loc[tag] = {k: dict(mediana=float(np.median(v)), media=float(np.mean(v)), n=len(v)) for k, v in per.items() if v}
keys = ["crudo"] + [f"{n}_{q}" for n in views for q in ("cmplx", "amp", "fase")] + [f"{t}_cmplx" for t in CEN if t != "raw"]


def shift_win(img, cy, cx, hw):
    """ventana (2hw+1)² centrada sub-píxel en (cy,cx) (corrimiento de Fourier sobre una ventana más grande)."""
    y0, x0 = int(round(cy)), int(round(cx)); g = hw + 4
    w = img[y0 - g:y0 + g + 1, x0 - g:x0 + g + 1]
    sh = ndi.fourier_shift(np.fft.fft2(w), (y0 - cy, x0 - cx))
    return np.fft.ifft2(sh)[4:-4, 4:-4]


# promedio (stack) del Δo COMPLEJO sobre esferas: lo que no es reproducible (ruido, textura) se promedia a 0.
# (a) alineado en el centroide CRUDO (|LoG| del BF, independiente de toda reconstrucción), sin rotar fases (esferas iguales, mismo foco
#     -> misma PSF compleja); el error de centrado del crudo ensancha el promedio: es una cota superior del ancho.
# (b) cruzado: centro sub-píxel y fase de referencia tomados de UNA mitad, promedio de la OTRA (independiente del ruido de la otra).
hw = int(14 / px); stack = {}


def stack_fwhm(acc):
    M = np.abs(np.mean(acc, 0))
    ww, rc, prof = radial_fwhm(np.pad(M, 4), hw + 4, hw + 4)
    return dict(n=len(acc), FWHM_um=ww, perfil=(prof / prof[0]).tolist() if prof[0] else None, r=rc.tolist())


dd_ = {n: dev(O[n])[0] for n in O}
for n in list(O) + ["crudo"]:
    img = rd if n == "crudo" else dd_[n]
    stack[f"crudo_centro_{n}"] = stack_fwhm([shift_win(img, *c, hw) for c in CEN["raw"]])
for a, b, tag in (("half0", "half1", "x01"), ("half1", "half0", "x10"), ("half0_scr", "half1_scr", "scr_x01"), ("half1_scr", "half0_scr", "scr_x10")):
    acc = []
    for (cy, cx) in CEN[tag]:
        ca = dd_[a][int(round(cy)), int(round(cx))]
        acc.append(shift_win(dd_[b], cy, cx, hw) * np.exp(-1j * np.angle(ca)))
    if acc:
        stack[tag] = stack_fwhm(acc)
res = {k: med(k) for k in keys}
# refoco del full: mediana del FWHM complejo vs dz
dzs = list(range(-40, 41, 5))
ref = {}
for dz in dzs:
    od = propagate(O["full"], dz) if dz else O["full"]
    d, _ = dev(od)
    ws = []
    for r in rows:
        w, _, _ = radial_fwhm(np.abs(d), r["y_um"] / px, r["x_um"] / px)
        if w is not None:
            ws.append(w)
    ref[dz] = float(np.median(ws)) if ws else None
    print(f"dz {dz:+4d} µm  FWHM |Δo| mediana {ref[dz]}", flush=True)
out = dict(DS=C.DS, VAR=C.VAR, epoca=ep, hrpx=px, teoria=teo, n_picos_rec=npk, n_picos_crudo=npk_raw, umbral_rec=float(thr), n_aisladas=len(iso),
           n_medidas=len(rows), aislamiento=dict(R_um=ISO_R, pico_frac=ISO_PK, anillo_frac=ISO_ANN), resumen=res, stack_cruzado=stack, frc_local=frc_loc, refoco_mediana_FWHM_cmplx=ref, esferas=rows)
json.dump(out, open(os.path.join(C.HERE, f"esferas_{C.DS}{TAG}.json"), "w"), indent=1, default=float)
print(json.dumps(teo, indent=0))
print("picos rec", npk, "picos crudo", npk_raw, "aisladas", len(iso), "medidas", len(rows))
for k, v in res.items():
    print(f"{k:22s} n {v['n']:3d}  FWHM mediana {v['mediana']}  [{v['p25']}, {v['p75']}]")
print("FRC local", json.dumps({t: {k: round(v["mediana"], 3) for k, v in d.items()} for t, d in frc_loc.items()}))
for k, v in stack.items():
    print(f"stack {k:8s} n {v['n']}  FWHM {v['FWHM_um']}")

# figura: 6 esferas (crudo / |Δo| full / fase full / nulo) + perfiles radiales medianos
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
FIG = os.path.join(C.HERE, "..", "figs"); os.makedirs(FIG, exist_ok=True)
sel = sorted(rows, key=lambda r: -r["pico_cmplx"])[:6]
fig, ax = plt.subplots(5, max(len(sel), 1) + 1, figsize=(2.3 * (len(sel) + 1) + 1, 12), squeeze=False)
hw = int(10 / px)
panels = [("crudo BF (17,15), ampl.", np.sign(1) * rd), ("rec |Δo| full", views["full"]["cmplx"]), ("rec |Δo| mitad 0", views["half0"]["cmplx"]),
          ("rec |Δo| mitad 1", views["half1"]["cmplx"]), ("nulo |Δo| (half0_scr)", views["half0_scr"]["cmplx"])]
for j, r in enumerate(sel):
    y, x = int(round(r["y_um"] / px)), int(round(r["x_um"] / px))
    for i, (t, img) in enumerate(panels):
        w = img[y - hw:y + hw + 1, x - hw:x + hw + 1]
        ax[i, j].imshow(w, cmap="gray", extent=(-10, 10, 10, -10)); ax[i, j].set_xticks([]); ax[i, j].set_yticks([])
        if j == 0:
            ax[i, j].set_ylabel(t, fontsize=8)
    ax[0, j].set_title(f"({r['y_um']:.0f},{r['x_um']:.0f}) µm", fontsize=8)
# perfiles medianos normalizados
for i, (lbl, getimg, sg) in enumerate([("crudo", lambda: rd, None), ("rec full |Δo|", lambda: views["full"]["cmplx"], 1),
                                        ("nulo |Δo|", lambda: views["half0_scr"]["cmplx"], 1), ("mitad0 |Δo|", lambda: views["half0"]["cmplx"], 1)]):
    P = []
    for r in rows:
        cy, cx = r["y_um"] / px, r["x_um"] / px
        img = getimg()
        s = sg if sg else np.sign(r["crudo_desv_sobre_mad"])
        _, rc, prof = radial_fwhm(s * img, cy, cx)
        if prof[0] > 0:
            P.append(prof / prof[0])
    if P:
        ax[i, -1].plot(rc, np.median(P, 0), "k"); ax[i, -1].axhline(0.5, ls=":", c="gray"); ax[i, -1].set_xlim(0, 10)
        ax[i, -1].set_title(f"{lbl}: FWHM med {res[{'crudo': 'crudo', 'rec full |Δo|': 'full_cmplx', 'nulo |Δo|': 'half0_scr_cmplx', 'mitad0 |Δo|': 'half0_cmplx'}[lbl]]['mediana'] or float('nan'):.2f} µm", fontsize=8)
        for key, ls in (("FWHM_NA_obj_um", "--"), ("FWHM_NA_sint_anillo_le8_um", "-.")):
            ax[i, -1].axvline(teo[key] / 2, ls=ls, c="C3" if ls == "--" else "C2", lw=1)
ax[4, -1].axis("off")
ax[3, -1].set_xlabel("r (µm); rojo: HWHM teórico NA_obj; verde: NA_sint (anillo ≤ 8)", fontsize=7)
plt.suptitle(f"{C.DS} {C.VAR} e{ep}: esferas aisladas (n={len(rows)}), ventanas de 20 µm", fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(FIG, f"esferas_{C.DS}{TAG}.png"), dpi=100); plt.close()

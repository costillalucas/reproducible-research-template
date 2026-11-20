"""comparar2.py -- (pasos 3 y 5) misma partícula: A (recorte de 200 px reconstruido, después ventana) contra B (ventana cruda
chica reconstruida sola: B20 y, si existe, B40). Cada partícula se compara con el recorte A que la contiene (seleccion.json).

MEDIDAS (la MISMA función, mismo centro físico y misma apertura, para la ventana de A y para B):
  centro = posición de la partícula detectada en A (px del ROI) -> px HR de la ventana; apertura r_ap = 6 µm; fondo = anillo
  8..11 µm (cabe en la ventana B20: semilado 12.9 µm).
  * V_fase  [rad·µm²]: volumen de fase como en octubre: fase desenvuelta (skimage unwrap_phase) − plano ajustado en el anillo,
            integrada en r <= r_ap; d_vol = cbrt(6Vλ/(2πΔn·π)) / 1.050 (Δn = 0.0488 de analisis.py, calibración de octubre).
            SOLO es cuantitativo si la amplitud no se anula: se marca 'vortice' si min(|o|/|fondo|) < 0.3 en la apertura.
  * S       [µm²]: integral compleja de (o/fondo − 1) en la apertura (fondo = media compleja del anillo). No necesita
            desenvolver; para un objeto débil Im S ≈ V_fase y −2·Re S ≈ área de extinción. Se informan |S|, Re, Im.
  * A_abs   [µm²]: Σ (1 − |o|/|fondo|)·hr² (área "oscura").
COMPARACIÓN DE CAMPOS en la ventana común: constante de fase global fuera (c = Σ A·conj(B)); ρ_c = correlación compleja de
(o/fondo − 1) (|ρ_c| = 1 idénticos salvo escala/fase); Pearson de amplitud; Pearson de la fase envuelta relativa al fondo
(fuera de los vórtices es igual a la desenvuelta; con vórtices es solo orientativo); ρ_c_hp = la misma correlación
tras quitar la gaussiana compleja de σ 3 µm (estructura fina, sin el fondo de baja frecuencia); norma de esa estructura
fina B/A normalizada por el fondo y sin normalizar; fondo_B/A = |media del anillo| de B / la de A; error relativo ‖A−B'‖/‖A‖;
desplazamiento A↔B (correlación de fase de |o/fondo − 1| con ventana Hann, subpíxel, solo se informa).
C1: datos/metricas.json de cada corrida. C2: FRC complejo de las mitades (comun_plan.c2 = c2_rojo.py, banda [0.212, 0.45] 1/µm)
para cada A entero y, ventana contra ventana, para A recortado y para B (orientativo: pocos píxeles por anillo).

Uso: python3 comparar2.py <OUT>  -> tabla.csv, resultados.json, fig_dispersion.png, fig_grilla_B20.png (y B40)
"""
import csv, json, os, sys
import numpy as np
from scipy import ndimage as ndi
from skimage.restoration import unwrap_phase
from skimage.registration import phase_cross_correlation
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
sys.path.insert(0, os.path.join(REPO, "results", "rojo_fase_2026-10-20"))
sys.path.insert(0, os.path.join(REPO, "results", "offset_color_2026-10-02"))
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo")
import analisis as AN  # noqa: E402
import comun_plan as CP  # noqa: E402
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt  # noqa: E402

OUT = sys.argv[1]
CORR = 1.050
NA_C2, LAM = 0.0669, AN.LAM
R_AP, AN_IN, AN_OUT = 6.0, 8.0, 11.0
S = json.load(open(os.path.join(OUT, "seleccion.json")))
TAMS = [t for t in (20, 40) if os.path.isdir(os.path.join(OUT, f"B{t}"))]


def cargar(d):
    m = json.load(open(os.path.join(d, "datos", "metricas.json")))
    o = {k: np.load(os.path.join(d, f)) for k, f in
         (("full", "objeto_complejo.npy"), ("h0", "objeto_mitadA.npy"), ("h1", "objeto_mitadB.npy"))}
    return m, o


def c1(m):
    return float(np.mean(list(m["heldout"].values()))) if m.get("heldout") else None


Acache = {}
for nomA in S["As"]:
    m, o = cargar(os.path.join(OUT, nomA))
    Acache[nomA] = dict(m=m, o=o, C2=CP.c2(o["h0"], o["h1"], m["hrpx"], NA_C2, LAM))


def geom(shape, yx, hr):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    d = np.hypot((yy - yx[0]) * hr, (xx - yx[1]) * hr)
    return yy, xx, d


def medir(o, yx, hr):
    yy, xx, d = geom(o.shape, yx, hr)
    ap, an = d <= R_AP, (d >= AN_IN) & (d <= AN_OUT)
    bg = o[an].mean()
    u = o / bg
    Sc = complex((u[ap] - 1).sum() * hr * hr)
    A_abs = float((1 - np.abs(u[ap])).sum() * hr * hr)
    minamp = float(np.abs(u[ap]).min())
    ph = unwrap_phase(np.angle(u))
    Am = np.stack([np.ones(an.sum()), yy[an], xx[an]], 1)
    cf, *_ = np.linalg.lstsq(Am, ph[an], rcond=None)
    phb = ph - (cf[0] + cf[1] * yy + cf[2] * xx)
    V = float(phb[ap].sum() * hr * hr)
    return dict(V_fase=V, dvol=float(AN.dvol(V)) / CORR if V > 0 else float("nan"), vortice=bool(minamp < 0.3), min_amp_rel=minamp,
                S_abs=abs(Sc), S_re=Sc.real, S_im=Sc.imag, A_abs=A_abs, pico_fase=float(np.percentile(phb[d <= 2], 95))), u, phb


def comparar(a, b, yx, hr):
    c = np.sum(a * np.conj(b)); b2 = b * np.exp(1j * np.angle(c))
    yy, xx, d = geom(a.shape, yx, hr)
    an = (d >= AN_IN) & (d <= AN_OUT)
    da, db = a / a[an].mean() - 1, b2 / b2[an].mean() - 1
    W = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    sh, _, _ = phase_cross_correlation(np.abs(da) * W, np.abs(db) * W, upsample_factor=10)
    rho = np.sum(da * np.conj(db)) / np.sqrt(np.sum(np.abs(da) ** 2) * np.sum(np.abs(db) ** 2))
    pa, pb = np.angle(da + 1), np.angle(db + 1)
    r = lambda u, v: float(np.corrcoef(u.ravel(), v.ravel())[0, 1])
    # pasa-altos (se quita la gaussiana compleja de σ 3 µm, modo 'wrap'): ¿coincide la estructura fina aunque el fondo no?
    hp = lambda z: z - (ndi.gaussian_filter(z.real, 3 / hr, mode="wrap") + 1j * ndi.gaussian_filter(z.imag, 3 / hr, mode="wrap"))
    ha, hb = hp(da), hp(db)
    rho_hp = np.sum(ha * np.conj(hb)) / np.sqrt(np.sum(np.abs(ha) ** 2) * np.sum(np.abs(hb) ** 2))
    return dict(rho_c_abs=float(abs(rho)), rho_c_fase=float(np.angle(rho)), rho_c_hp=float(abs(rho_hp)),
                norma_hp_B_sobre_A=float(np.linalg.norm(hb) / np.linalg.norm(ha)),
                norma_hp_sin_normalizar_B_sobre_A=float(np.linalg.norm(hp(b2)) / np.linalg.norm(hp(a))),
                fondo_B_sobre_A=float(abs(b2[an].mean()) / abs(a[an].mean())), pearson_amp=r(np.abs(a), np.abs(b2)),
                pearson_fase=r(pa, pb), err_rel=float(np.linalg.norm(a - b2) / np.linalg.norm(a)),
                desplaz_px_hr=[float(x) for x in sh], amp_B_sobre_A=float(np.abs(b2).mean() / np.abs(a).mean())), b2


res = dict(As={k: dict(recorte=v["m"]["recorte"], C1=c1(v["m"]), C3=v["m"]["lattice"], R_ajuste=v["m"]["train_R"],
                       sin_fpm=v["m"]["sin_fpm"], offset_mm=v["m"]["offset_mm"], C2=v["C2"]) for k, v in Acache.items()},
           parametros=dict(R_AP=R_AP, anillo=[AN_IN, AN_OUT], CORR=CORR, DN=AN.DN, LAM=LAM, banda_C2=[2 * NA_C2 / LAM, 0.45]),
           particulas=[])
figdat = []
for p in S["elegidas"]:
    Ad = Acache[p["A"]]; hr = Ad["m"]["hrpx"]; f0, c0, nA = Ad["m"]["recorte"]; fac = Ad["o"]["full"].shape[0] // nA
    R = dict(id=p["id"], A=p["A"], fil_roi=p["fil_roi"], col_roi=p["col_roi"], ext=p["ext"], elong=p["elong"], Dmax=p["Dmax"])
    fd = dict(id=p["id"])
    for t in TAMS:
        rb, cb = p[f"rec{t}"]; dB = os.path.join(OUT, f"B{t}", f"f{rb}_c{cb}")
        if not os.path.exists(os.path.join(dB, "datos", "metricas.json")):
            R[f"B{t}"] = dict(error="sin resultado (no se corrió o falló)"); continue
        mB, oB = cargar(dB)
        assert list(mB["recorte"][:2]) == [rb, cb] and abs(mB["hrpx"] - hr) < 1e-6
        i0, j0, n = (rb - f0) * fac, (cb - c0) * fac, t * fac
        if not (i0 >= 0 and j0 >= 0 and i0 + n <= nA * fac and j0 + n <= nA * fac):
            R[f"B{t}"] = dict(error="ventana fuera de A"); continue
        aw = {k: v[i0:i0 + n, j0:j0 + n] for k, v in Ad["o"].items()}
        yx = ((p["fil_roi"] - rb) * fac, (p["col_roi"] - cb) * fac)
        mA_, uA, phA = medir(aw["full"], yx, hr)
        mB_, uB, phB = medir(oB["full"], yx, hr)
        cmp_, b2 = comparar(aw["full"], oB["full"], yx, hr)
        R[f"A_w{t}"] = mA_
        R[f"B{t}"] = dict(**mB_, C1=c1(mB), C3=mB["lattice"], R_ajuste=mB["train_R"], sin_fpm=mB["sin_fpm"], offset_mm=mB["offset_mm"],
                          t_total_min=mB["t_total_s"] / 60, C2_ventana_B=CP.c2(oB["h0"], oB["h1"], hr, NA_C2, LAM),
                          C2_ventana_A=CP.c2(aw["h0"], aw["h1"], hr, NA_C2, LAM), **cmp_)
        g = np.exp(-1j * np.angle(aw["full"].sum()))
        fd[t] = dict(a=aw["full"] * g, b=b2 * g, uA=uA, uB=b2 / b2[geom(b2.shape, yx, hr)[2] >= AN_IN].mean(), yx=yx, hr=hr)
    # CONTROL A vs A': la misma ventana 20 px en OTRO recorte A de 200 px que también la contiene (otro recorte, otro offset
    # de LED): cuánto difieren dos reconstrucciones 'grandes' entre sí, para calibrar las diferencias A vs B.
    rb, cb = p["rec20"]
    for nom2, A2 in Acache.items():
        if nom2 == p["A"]: continue
        g0, h0_, n2 = A2["m"]["recorte"]
        if not (g0 <= rb and rb + 20 <= g0 + n2 and h0_ <= cb and cb + 20 <= h0_ + n2): continue
        i0, j0, n = (rb - f0) * fac, (cb - c0) * fac, 20 * fac
        k0, l0 = (rb - g0) * fac, (cb - h0_) * fac
        a1 = Ad["o"]["full"][i0:i0 + n, j0:j0 + n]; a2 = A2["o"]["full"][k0:k0 + n, l0:l0 + n]
        yx = ((p["fil_roi"] - rb) * fac, (p["col_roi"] - cb) * fac)
        m1, _, _ = medir(a1, yx, hr); m2, _, _ = medir(a2, yx, hr); cm, _ = comparar(a1, a2, yx, hr)
        R.setdefault("control_AA", []).append(dict(A2=nom2, margen_A2_px=float(min(rb - g0, g0 + n2 - rb - 20, cb - h0_, h0_ + n2 - cb - 20)),
                                                   A=m1, A2m=m2, **cm))
    res["particulas"].append(R); figdat.append(fd)

# ---------- tabla
f2 = lambda x: "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.2f}"
f3 = lambda x: "" if x is None else f"{x:.3f}"
cols = ["id", "A", "fil_roi", "col_roi", "ext_um", "elong"]
for t in TAMS:
    cols += [f"V_A{t}", f"V_B{t}", f"vortice_A", f"vortice_B{t}", f"dvol_A{t}", f"dvol_B{t}", f"|S|_A{t}", f"|S|_B{t}",
             f"ImS_A{t}", f"ImS_B{t}", f"Aabs_A{t}", f"Aabs_B{t}", f"rho_c_B{t}", f"rho_c_hp_B{t}", f"normhp_B/A{t}", f"normhp_crudo_B/A{t}", f"fondo_B/A{t}", f"r_amp_B{t}", f"r_fase_B{t}", f"err_rel_B{t}",
             f"desplaz_um_B{t}", f"C1_A", f"C1_B{t}", f"C2win_A{t}", f"C2win_B{t}"]
with open(os.path.join(OUT, "tabla.csv"), "w", newline="") as fh:
    W = csv.writer(fh); W.writerow(cols)
    for R in res["particulas"]:
        row = [R["id"], R["A"], f"{R['fil_roi']:.1f}", f"{R['col_roi']:.1f}", f2(R["ext"]), f2(R["elong"])]
        for t in TAMS:
            a, b = R.get(f"A_w{t}"), R[f"B{t}"]
            if a is None:
                row += [b.get("error", "")] + [""] * 24; continue
            row += [f2(a["V_fase"]), f2(b["V_fase"]), int(a["vortice"]), int(b["vortice"]), f2(a["dvol"]), f2(b["dvol"]),
                    f2(a["S_abs"]), f2(b["S_abs"]), f2(a["S_im"]), f2(b["S_im"]), f2(a["A_abs"]), f2(b["A_abs"]),
                    f3(b["rho_c_abs"]), f3(b["rho_c_hp"]), f3(b["norma_hp_B_sobre_A"]), f3(b["norma_hp_sin_normalizar_B_sobre_A"]), f3(b["fondo_B_sobre_A"]), f3(b["pearson_amp"]), f3(b["pearson_fase"]), f3(b["err_rel"]),
                    f2(np.hypot(*b["desplaz_px_hr"]) * 0.43), f3(res["As"][R["A"]]["C1"]), f3(b["C1"]),
                    f3(b["C2_ventana_A"]), f3(b["C2_ventana_B"])]
        W.writerow(row)

# ---------- agregado
def q(x):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    if not len(x): return None
    return dict(N=int(len(x)), mediana=float(np.median(x)), p25=float(np.percentile(x, 25)), p75=float(np.percentile(x, 75)),
                min=float(x.min()), max=float(x.max()))
agg = {}
for t in TAMS:
    ok = [R for R in res["particulas"] if f"A_w{t}" in R]
    if not ok: continue
    nv = [R for R in ok if not (R[f"A_w{t}"]["vortice"] or R[f"B{t}"]["vortice"])]
    agg[f"B{t}"] = dict(
        N=len(ok), N_sin_vortice=len(nv), N_vortice_A=sum(R[f"A_w{t}"]["vortice"] for R in ok),
        N_vortice_B=sum(R[f"B{t}"]["vortice"] for R in ok),
        V_B_sobre_A_sin_vortice=q([R[f"B{t}"]["V_fase"] / R[f"A_w{t}"]["V_fase"] for R in nv]),
        Sabs_B_sobre_A=q([R[f"B{t}"]["S_abs"] / R[f"A_w{t}"]["S_abs"] for R in ok]),
        ImS_B_menos_A=q([R[f"B{t}"]["S_im"] - R[f"A_w{t}"]["S_im"] for R in ok]),
        Aabs_B_sobre_A=q([R[f"B{t}"]["A_abs"] / R[f"A_w{t}"]["A_abs"] for R in ok]),
        rho_c=q([R[f"B{t}"]["rho_c_abs"] for R in ok]), rho_c_hp=q([R[f"B{t}"]["rho_c_hp"] for R in ok]),
        norma_hp_B_sobre_A=q([R[f"B{t}"]["norma_hp_B_sobre_A"] for R in ok]),
        norma_hp_sin_normalizar_B_sobre_A=q([R[f"B{t}"]["norma_hp_sin_normalizar_B_sobre_A"] for R in ok]),
        fondo_B_sobre_A=q([R[f"B{t}"]["fondo_B_sobre_A"] for R in ok]), pearson_amp=q([R[f"B{t}"]["pearson_amp"] for R in ok]),
        pearson_fase=q([R[f"B{t}"]["pearson_fase"] for R in ok]), err_rel=q([R[f"B{t}"]["err_rel"] for R in ok]),
        desplaz_um=q([np.hypot(*R[f"B{t}"]["desplaz_px_hr"]) * 0.43 for R in ok]),
        C1_B=q([R[f"B{t}"]["C1"] for R in ok]), sin_fpm_B=q([R[f"B{t}"]["sin_fpm"] for R in ok]),
        C1_B_menos_sinfpm=q([R[f"B{t}"]["C1"] - R[f"B{t}"]["sin_fpm"] for R in ok]),
        C2_ventana_A=q([R[f"B{t}"]["C2_ventana_A"] for R in ok]), C2_ventana_B=q([R[f"B{t}"]["C2_ventana_B"] for R in ok]),
        offset_mm_B=q([np.hypot(*R[f"B{t}"]["offset_mm"]) for R in ok]))
ctl = [c for R in res["particulas"] for c in R.get("control_AA", [])]
if ctl:
    agg["control_A_vs_A2_w20"] = dict(N=len(ctl), rho_c=q([c["rho_c_abs"] for c in ctl]), rho_c_hp=q([c["rho_c_hp"] for c in ctl]),
        norma_hp_A2_sobre_A=q([c["norma_hp_B_sobre_A"] for c in ctl]), pearson_amp=q([c["pearson_amp"] for c in ctl]),
        err_rel=q([c["err_rel"] for c in ctl]), Sabs_A2_sobre_A=q([c["A2m"]["S_abs"] / c["A"]["S_abs"] for c in ctl]),
        Aabs_A2_sobre_A=q([c["A2m"]["A_abs"] / c["A"]["A_abs"] for c in ctl]),
        pares=[(R["id"], R["A"], c["A2"], round(c["rho_c_abs"], 3), round(c["A"]["S_abs"], 2), round(c["A2m"]["S_abs"], 2))
               for R in res["particulas"] for c in R.get("control_AA", [])])
res["agregado"] = agg
json.dump(res, open(os.path.join(OUT, "resultados.json"), "w"), indent=1, default=float)
print(json.dumps(dict(As=res["As"], agregado=agg), indent=1, default=float))

# ---------- figura de dispersión
mk = {20: "o", 40: "s"}
fig, ax = plt.subplots(1, 3, figsize=(16, 5))
for j, (key, tt) in enumerate((("V_fase", "volumen de fase V (rad·µm²)\nhueco = hay vórtice (no cuantitativo)"),
                               ("S_abs", "|S| = |∫(o/fondo − 1)| (µm²)"), ("A_abs", "área oscura ∫(1 − |o|/|fondo|) (µm²)"))):
    vals = []
    for t in TAMS:
        ok = [R for R in res["particulas"] if f"A_w{t}" in R]
        for R in ok:
            x, y = R[f"A_w{t}"][key], R[f"B{t}"][key]
            vort = key == "V_fase" and (R[f"A_w{t}"]["vortice"] or R[f"B{t}"]["vortice"])
            ax[j].plot(x, y, mk[t], mfc="none" if vort else f"C{TAMS.index(t)}", mec=f"C{TAMS.index(t)}", ms=7)
            if t == TAMS[0]:
                ax[j].annotate(R["id"][1:], (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
            vals += [x, y]
        ax[j].plot([], [], mk[t], color=f"C{TAMS.index(t)}", label=f"B{t}")
    lo, hi = min(vals + [0]), max(vals)
    lim = [lo - 0.05 * (hi - lo), hi + 0.05 * (hi - lo)]
    ax[j].plot(lim, lim, "k--", lw=.8, label="y = x"); ax[j].set_xlim(lim); ax[j].set_ylim(lim)
    ax[j].set_xlabel("A (recorte 200 px, ventana después)"); ax[j].set_ylabel("B (ventana cruda reconstruida sola)")
    ax[j].set_title(tt, fontsize=9); ax[j].legend(fontsize=8)
plt.suptitle(f"Misma partícula, misma apertura (r = {R_AP:g} µm, fondo {AN_IN:g}–{AN_OUT:g} µm), A vs B", fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig_dispersion.png"), dpi=110); plt.close()

# ---------- grilla por tamaño
for t in TAMS:
    P = [fd for fd in figdat if t in fd]
    if not P: continue
    fig, ax = plt.subplots(len(P), 6, figsize=(14, 2.35 * len(P)))
    ax = np.atleast_2d(ax)
    for i, fd in enumerate(P):
        d = fd[t]; hr = d["hr"]; L = d["a"].shape[0] * hr; ext = (0, L, L, 0)
        aa, ab = np.abs(d["uA"]), np.abs(d["uB"])
        pa, pb = np.angle(d["uA"]), np.angle(d["uB"])
        dph = np.angle(d["uA"] * np.conj(d["uB"])); damp = aa - ab
        ims = [(aa, "gray", 0, 1.3, "A |o|/|fondo|"), (ab, "gray", 0, 1.3, f"B{t} |o|/|fondo|"),
               (pa, "twilight", -np.pi, np.pi, "A fase − fondo (rad)"), (pb, "twilight", -np.pi, np.pi, f"B{t} fase − fondo"),
               (dph, "RdBu_r", -1.5, 1.5, "fase A−B (rad)"), (damp, "RdBu_r", -0.5, 0.5, "amp A−B")]
        for j, (im, cm, vmin, vmax, tt) in enumerate(ims):
            h = ax[i, j].imshow(im, cmap=cm, vmin=vmin, vmax=vmax, extent=ext, interpolation="nearest")
            ax[i, j].add_patch(plt.Circle((d["yx"][1] * hr, d["yx"][0] * hr), R_AP, fill=False, ec="y", lw=0.6, ls=":"))
            ax[i, j].set_xticks([]); ax[i, j].set_yticks([])
            if i == 0: ax[i, j].set_title(tt, fontsize=9)
            if i == 0 and j in (1, 3, 4, 5): plt.colorbar(h, ax=ax[i, j], fraction=0.046)
        R = next(r for r in res["particulas"] if r["id"] == fd["id"])
        b = R[f"B{t}"]
        ax[i, 0].set_ylabel(f"{fd['id']} ({R['A'].replace('A_200', 'A')})\n|S| A {R[f'A_w{t}']['S_abs']:.1f} B {b['S_abs']:.1f}\n"
                            f"|ρc| {b['rho_c_abs']:.2f}", fontsize=7)
    plt.suptitle(f"A (recorte 200 px, ventana después) vs B{t} (ventana {t}x{t} px crudos = {t * 1.29:.0f} µm, reconstruida sola). "
                 f"Misma escala de color en toda la columna. Círculo = apertura r {R_AP:g} µm.", fontsize=9)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, f"fig_grilla_B{t}.png"), dpi=80); plt.close()
print("figuras listas")

"""resolucion.py -- FRC entre mitades (complejo / amplitud / fase) contra el nulo de geometría permutada, espectro radial
de la reconstrucción contra el BF crudo, y C2 con la definición previa. Escribe resolucion_<fuente>.json.

    python3 resolucion.py previo            # 28/09b rojo, geometría vieja (z 98, lrpx 1.28, NA 0.07), 40 épocas
    python3 resolucion.py final 40 160      # rojo_final (z 102, lrpx 1.29, NA 0.0669), épocas pedidas
Definiciones:
  curvas   = FRC con ventana de Tukey (0.2), anillos de 0.012 1/µm, suavizadas con media móvil de 5 anillos (0.06 1/µm);
  k_1/7    = MAYOR frecuencia (<= 0.9 1/µm) hasta la que el FRC suavizado se mantiene >= 1/7 en 3 anillos seguidos;
  k_nulo   = primera frecuencia >= NA/λ desde la que FRC - FRC_nulo (suavizados) queda bajo 3σ = 3/sqrt(n_anillo) (del anillo
             SIN suavizar: conservador) en 3 anillos seguidos. Se arranca en NA/λ porque a k < 0.03 el nulo iguala al real
             (fondo e init compartidos). Hay además un exceso chico (~0.03) cerca del Nyquist HR (k > 0.9, fuera de la banda
             sintética de los anillos < 7) que se informa aparte como artefacto compartido, no como resolución.
             en 3 anillos seguidos (más allá, indistinguible del azar). Se toma la mayor y no la primera porque a k < 0.03 1/µm
             el nulo iguala al real (fondo e init compartidos) y el FRC ronda 1/7 dentro de la banda del objetivo;
  NA_ef    = λ·k (convención de campo: corte coherente del objetivo = NA/λ; el BF crudo, que es intensidad, llega a 2NA/λ).
  C2       = media del FRC complejo SIN ventana (fpm_red.frc, 60 anillos) en [2NA/λ, 0.45] 1/µm (= criterios_b.py)."""
import json, os, sys
import numpy as np
from scipy.signal.windows import tukey
import comun as C

HERE = C.HERE


def objs(src, ep=None):
    if src == "previo":
        O = os.path.join(C.B28, "out"); ld = lambda n: np.load(f"{O}/obj_real_A+init_z98.0_{n}.npy").astype(complex)
    else:
        O = os.path.join({"r500_red": C.OC, "r21_red": os.path.join(C.RES, "captura_2026-10-21")}.get(C.DS, C.OCO), "out", C.VAR, C.DS); ld = lambda n: np.load(f"{O}/real_A+init_z98.0_{n}/obj_e{ep:03d}.npy").astype(complex)
    return {n: ld(n) for n in ("full", "half0", "half1", "half0_scr", "half1_scr")}


def win(H):
    w = tukey(H, 0.2); return np.outer(w, w)


def views(o, W):
    o = o * np.exp(-1j * np.angle(np.sum(o)))
    a = np.abs(o); p = C.rel_phase(o)
    return {"complejo": (o - o.mean()) * W, "amplitud": (a - a.mean()) * W, "fase": (p - p.mean()) * W}


def sm(y, n=5):
    return np.convolve(np.r_[np.full(n // 2, y[0]), y, np.full(n // 2, y[-1])], np.ones(n) / n, "valid")


def last_above(k, y, thr, run=3, k0=0.02, k1=0.9):
    ok = (y >= thr) & (k > k0) & (k <= k1)
    for i in range(len(k) - 1, run - 2, -1):
        if ok[i - run + 1:i + 1].all():
            return float(k[i])
    return None


def first_below(k, y, thr, k0=0.02, run=1):
    bad = (y < thr) & (k > k0)
    for i in range(len(k) - run + 1):
        if bad[i:i + run].all():
            return float(k[i])
    return None


def analyze(O, px, na, lam, raw, raw2, F):
    H = O["full"].shape[0]; W = win(H)
    v = {n: views(O[n], W) for n in O}
    kmax = 1 / (2 * px); nb = int(round(kmax / 0.012))
    out = {"curvas": {}, "res": {}}
    for q in ("complejo", "amplitud", "fase"):
        fr = C.frc(v["half0"][q], v["half1"][q], px, nb, kmax)
        fn = C.frc(v["half0_scr"][q], v["half1_scr"][q], px, nb, kmax)
        k, y, n = fr[:, 0], fr[:, 1], fr[:, 2]
        sig3 = 3 / np.sqrt(np.maximum(n, 1) / (1 if q == "complejo" else 2))
        k7 = last_above(k, sm(y), 1 / 7); kn = first_below(k, sm(y - fn[:, 1]), sig3, k0=na / lam, run=3)
        hi_ex = float(np.mean((y - fn[:, 1])[k > 0.9]))
        bands = {"[0,NA/λ]": (0, na / lam), "[NA/λ,2NA/λ]": (na / lam, 2 * na / lam), "[2NA/λ,0.45]": (2 * na / lam, 0.45),
                 "[0.45,0.9]": (0.45, 0.9)}
        out["curvas"][q] = dict(k=k.tolist(), frc=y.tolist(), nulo=fn[:, 1].tolist(), sig3=sig3.tolist())
        out["res"][q] = dict(k_1_7=k7, periodo_1_7_um=(1 / k7 if k7 else None), NA_ef_1_7=(lam * k7 if k7 else None),
                             exceso_k_mayor_0p9=hi_ex, k_nulo=kn, periodo_nulo_um=(1 / kn if kn else None), NA_ef_nulo=(lam * kn if kn else None),
                             bandas={b: [C.band_mean(fr, *r), C.band_mean(fn, *r)] for b, r in bands.items()})
    # C2 con la definición previa (sin ventana, 60 anillos hasta kmax total)
    c2 = lambda a, b, lo: C.band_mean(C.frc(a, b, px), lo, 0.45)
    out["C2"] = dict(frc=c2(O["half0"], O["half1"], 2 * na / lam), nulo=c2(O["half0_scr"], O["half1_scr"], 2 * na / lam),
                     frc_banda_0222=c2(O["half0"], O["half1"], 0.222), nulo_banda_0222=c2(O["half0_scr"], O["half1_scr"], 0.222),
                     banda=[2 * na / lam, 0.45])
    out["C2"]["PASS"] = bool(out["C2"]["frc"] >= 0.143 and out["C2"]["frc"] >= out["C2"]["nulo"] + 0.068)
    # espectros radiales (potencia normalizada a la media en [0.02, NA/λ]); BF crudo: amplitud sqrt(I) Fourier-upsampleada
    f = H // raw.shape[0]
    ru = np.real(F.fourier_upsample(np.sqrt(np.clip(raw, 0, None)), f))
    ru2 = np.real(F.fourier_upsample(np.sqrt(np.clip(raw2, 0, None)), f))
    sp = lambda a: np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    cs = lambda a, b: np.real(np.fft.fftshift(np.fft.fft2(a)) * np.conj(np.fft.fftshift(np.fft.fft2(b))))
    rw = lambda a: (a - a.mean()) * W
    a0, a1 = rw(np.abs(O["half0"])), rw(np.abs(O["half1"]))
    s0, s1 = rw(np.abs(O["half0_scr"])), rw(np.abs(O["half1_scr"]))
    spec = {"crudo_BF": sp(rw(ru)), "crudo_cruzado_2BF": cs(rw(ru), rw(ru2)), "rec_amp_full": sp(rw(np.abs(O["full"]))),
            "rec_amp_cruzado_mitades": cs(a0, a1), "rec_amp_cruzado_nulo": cs(s0, s1)}
    rad = {}
    for n, P in spec.items():
        k, m, _ = C.radial(P, px, nb, kmax)
        norm = np.mean(m[(k > 0.02) & (k < na / lam)]) if "cruzado" not in n else None
        rad[n] = m
    # normalizar todo por la potencia propia en [0.02, NA/λ] (cruzados: por la del espectro directo correspondiente)
    lowm = (k > 0.02) & (k < na / lam)
    ref = {"crudo_BF": rad["crudo_BF"], "crudo_cruzado_2BF": rad["crudo_BF"], "rec_amp_full": rad["rec_amp_full"],
           "rec_amp_cruzado_mitades": rad["rec_amp_full"], "rec_amp_cruzado_nulo": rad["rec_amp_full"]}
    out["espectro"] = {"k": k.tolist(), **{n: (rad[n] / np.mean(ref[n][lowm])).tolist() for n in rad}}
    # fracción de potencia reproducible (espectro cruzado) por encima de 2NA/λ, relativa a la de [0.02, 2NA/λ]
    hi = (k >= 2 * na / lam) & (k < 0.9); lo = (k > 0.02) & (k < 2 * na / lam)
    nn = _ * 0 + 1
    def frac(m):  # integrado en 2D: peso k
        return float(np.sum(m[hi] * k[hi]) / np.sum(m[lo] * k[lo]))
    tot = np.sum(rad["rec_amp_full"][lo] * k[lo]); totr = np.sum(rad["crudo_BF"][lo] * k[lo])
    acum = lambda m, t: (np.cumsum((m * k)[::-1])[::-1] / t).tolist()
    out["espectro"]["acum_cruzado_mitades"] = acum(rad["rec_amp_cruzado_mitades"], tot)
    out["espectro"]["acum_cruzado_nulo"] = acum(rad["rec_amp_cruzado_nulo"], tot)
    out["espectro"]["acum_cruzado_crudo"] = acum(rad["crudo_cruzado_2BF"], totr)
    out["potencia_reproducible_sobre_2NA"] = {n: frac(rad[n]) for n in ("crudo_cruzado_2BF", "rec_amp_cruzado_mitades", "rec_amp_cruzado_nulo")}
    # FRC entre los dos BF crudos (17,15) y (18,15), en LR: hasta dónde llega lo reproducible en la foto cruda
    Wl = win(raw.shape[0]); frr = C.frc((raw - raw.mean()) * Wl, (raw2 - raw2.mean()) * Wl, px * f, int(round(1 / (2 * px * f) / 0.012)), 1 / (2 * px * f))
    sig = 3 / np.sqrt(np.maximum(frr[:, 2], 1) / 2)
    out["crudo_FRC_2BF"] = dict(k=frr[:, 0].tolist(), frc=frr[:, 1].tolist(), sig3=sig.tolist(),
                                k_1_7=last_above(frr[:, 0], sm(frr[:, 1]), 1 / 7), k_3sig=last_above(frr[:, 0], sm(frr[:, 1]), sig))
    return out


if __name__ == "__main__":
    src = sys.argv[1]
    if src == "previo":
        F, geo, D = C.load_old(); runs = [(None, objs("previo"))]
    else:
        F, geo, D = C.load(); runs = [(int(e), objs("final", int(e))) for e in sys.argv[2:]]
    raw, raw2 = D["I"][(17, 15)], D["I"][(18, 15)]   # 2 BF crudos (en r21_red ambos son BF de la cruz)
    f = np.array([geo["fxy"][k] for k in D["keys"]]); rg = np.array([F.ring(k) for k in D["keys"]])
    nai = np.hypot(f[:, 0], f[:, 1]) * geo["lam"]
    res = dict(geometria=dict(lam=geo["lam"], NA_obj=geo["na"], hrpx=geo["hrpx"], lrpx=geo["lrpx"],
                              NA_ilum_max=float(nai.max()), NA_ilum_max_anillo_lt7=float(nai[rg < 7].max()),
                              NA_sint=float(geo["na"] + nai.max()), NA_sint_anillo_lt7=float(geo["na"] + nai[rg < 7].max()),
                              k_campo_obj=geo["na"] / geo["lam"], k_int_obj=2 * geo["na"] / geo["lam"],
                              k_campo_sint=(geo["na"] + nai.max()) / geo["lam"]), epocas={})
    for ep, O in runs:
        r = analyze(O, geo["hrpx"], geo["na"], geo["lam"], raw, raw2, F)
        res["epocas"][str(ep)] = r
        print(src, ep, json.dumps({q: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r["res"][q].items() if k != "bandas"} for q in r["res"]}))
        print("   bandas", {q: {b: [round(x, 3) for x in v] for b, v in r["res"][q]["bandas"].items()} for q in r["res"]})
        print("   C2", r["C2"], "\n   pot>2NA", r["potencia_reproducible_sobre_2NA"], "\n   crudo FRC", r["crudo_FRC_2BF"]["k_1_7"], r["crudo_FRC_2BF"]["k_3sig"])
    print(res["geometria"])
    json.dump(res, open(os.path.join(HERE, f"resolucion_{C.DS}_{src}.json"), "w"), indent=1)

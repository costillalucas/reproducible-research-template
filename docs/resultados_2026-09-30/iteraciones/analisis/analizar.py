"""analizar.py -- métricas en función de la época para el barrido de iter_runner (datos reales, 2026-09-30).

Lee out/<dataset>/<tarea>/ (metrics.jsonl, obj_eNNN.npy) y calcula, para cada época disponible de SNAPS:
- C1(e): media ± sd entre folds de heldout_R_ring_lt7 (igual que criterios_b.py a e=40) y diferencia
  pareada C1(e) - C1(40) por fold; referencia sin FPM (real_nofpm_z<z>.json, per_led anillo < 7).
- C1 por grupo de anillo de los LEDs no vistos (los 6 de campo claro nunca quedan fuera):
  DF cercano 1.3 <= anillo < 4, DF lejano 4 <= anillo < 7, y (solo informativo) anillo >= 7.
- train_R(e) (media sobre folds y de la tarea full), brecha C1 - train_R de los folds; solver_err; lattice(e) (full).
- C2(e) = band_mean(frc(half0_e, half1_e), 2NA/lam, 0.45) y nulo con half*_scr; curva FRC completa en FRC_EPOCHS.
- Estabilidad del objeto full (también con la amplitud sin fondo lento, A - gauss(A, 20 px), sufijo _hp): cambio relativo de amplitud entre snapshots consecutivos, rms del cambio de fase
  (fase global removida), y correlación de amplitud y de fase relativa (multiespectral.rel_phase, sigma 20 px) de
  cada snapshot con el de 40 y el de 400 épocas; lo mismo filtrado a bajas frecuencias (<= NA/lam, sufijo _bajas)
  y a la banda de C2 ([2NA/lam, 0.45), sufijo _C2). Interior: se descarta un borde de n/12 px.
- Coherencia entre colores (solo si los tres b_* tienen el snapshot): igual que comparar_colores.py (grilla del rojo
  1200 px, corrimientos leídos de comparar_colores.json y fijos para todas las épocas, pasabajos en tres bandas,
  máscara 100:-100) para la amplitud; lo mismo para la fase relativa.

Uso (desde cualquier lugar; usar nice):  nice -n 19 python3 analizar.py [dataset ...]
   sin argumentos: todos los datasets con datos (b_red, b_green, b_blue, s3_red) + colores.
Escribe analisis/<dataset>.json y analisis/colores.json. Verifica e=40 contra criterios_b.json (28/09 b).
"""
import glob
import importlib.util
import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
IT = os.path.dirname(HERE)
RES = os.path.dirname(IT)
B = os.path.join(RES, "captura_2026-09-28b")
DS = {  # dataset -> (carpeta fpm_red, z, color, prefijo tareas)
    "b_red": (os.path.join(B, "red"), 98.0, "red"),
    "b_green": (os.path.join(B, "green"), 98.0, "green"),
    "b_blue": (os.path.join(B, "blue"), 98.0, "blue"),
    "s3_red": (os.path.join(RES, "captura_2026-09-25_red"), 74.0, "red"),
}
SNAPS = [0, 1, 2, 3, 5, 8, 12, 20, 30, 40, 60, 80, 120, 160, 240, 320, 400]
FRC_EPOCHS = [0, 5, 20, 40, 120, 400]
GRUPOS = {"DF_cercano_1.3-4": (1.3, 4.0), "DF_lejano_4-7": (4.0, 7.0), "fuera_>=7": (7.0, 99.0)}
LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}


def mod(d, tag):
    s = importlib.util.spec_from_file_location("F_" + tag, os.path.join(d, "fpm_red.py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def tdir(ds, name):
    return os.path.join(IT, "out", ds, f"real_A+init_z{DS[ds][1]:.1f}_{name}")


def rows(ds, name):
    p = os.path.join(tdir(ds, name), "metrics.jsonl")
    if not os.path.exists(p):
        return {}
    out = {}
    for line in open(p):
        line = line.strip()
        if line:
            r = json.loads(line); out[r["epoch"]] = r
    return out


def objp(ds, name, e):
    return os.path.join(tdir(ds, name), f"obj_e{e:03d}.npy")


def load_obj(ds, name, e):
    p = objp(ds, name, e)
    return np.load(p).astype(complex) if os.path.exists(p) else None


def rel_phase(o, sig=20):  # = multiespectral.rel_phase
    sm = ndi.gaussian_filter(o.real, sig) + 1j * ndi.gaussian_filter(o.imag, sig)
    return np.angle(o * np.exp(-1j * np.angle(sm)))


def corr(a, b, m):  # = multiespectral.corr
    a, b = a[m] - a[m].mean(), b[m] - b[m].mean()
    return float(np.sum(a * b) / np.sqrt(np.sum(a * a) * np.sum(b * b)))


def to_grid(o, n=1200):  # = multiespectral.to_grid
    H = o.shape[0]
    if H == n:
        return o
    S = np.fft.fftshift(np.fft.fft2(o)); a = (H - n) // 2
    return np.fft.ifft2(np.fft.ifftshift(S[a:a + n, a:a + n])) * (n / H) ** 2


def ms(v):
    v = [x for x in v if x is not None]
    return (float(np.mean(v)), float(np.std(v)), len(v)) if v else (None, None, 0)


def analizar(ds):
    d, z, color = DS[ds]
    F = mod(d, ds)
    g = F.geometry(z)
    lam, hrpx = g["lam"], g["hrpx"]
    lo = 2 * g["na"] / lam
    out = dict(dataset=ds, color=color, z=z, lam=lam, hrpx=hrpx, banda_C2=[lo, 0.45], epocas={})
    nof = os.path.join(d, "out", "tasks", f"real_nofpm_z{z:.1f}.json")
    if os.path.exists(nof):
        out["C1_sin_fpm"] = float(np.mean([v[0] for v in json.load(open(nof))["per_led"].values() if v[2] < 7]))
    folds = {f: rows(ds, f"f{f}") for f in range(5)}
    full = rows(ds, "full")
    frc_curvas = {}
    ep_ok = [e for e in SNAPS if any(e in folds[f] for f in folds) or e in full]
    O = {}  # snapshots full (para estabilidad)
    for e in ep_ok:
        r = {}
        c1 = [folds[f][e]["heldout_R_ring_lt7"] if e in folds[f] else None for f in range(5)]
        r["C1"], r["C1_sd"], r["C1_nfolds"] = ms(c1)
        r["C1_folds"] = c1
        tr = [folds[f][e]["train_R"] if e in folds[f] else None for f in range(5)]
        r["trainR_folds"], r["trainR_folds_sd"], _ = ms(tr)
        r["brecha"] = (r["C1"] - r["trainR_folds"]) if r["C1"] is not None else None
        for gname, (a, b) in GRUPOS.items():
            vals = []
            for f in range(5):
                if e in folds[f]:
                    x = [v[0] for v in folds[f][e]["per_led"].values() if not v[3] and a <= v[2] < b]
                    vals.append(float(np.mean(x)) if x else None)
            r[f"C1_{gname}"], r[f"C1_{gname}_sd"], _ = ms(vals)
        if e in full:
            fr = full[e]
            r["trainR_full"] = fr["train_R"]; r["solver_err_full"] = fr["solver_err"]; r["lattice"] = fr["lattice"]
            pl = fr["per_led"].values()
            r["trainR_full_BF"] = float(np.mean([v[0] for v in pl if v[2] < 1.3]))
            r["trainR_full_DF_1.3-7"] = float(np.mean([v[0] for v in pl if 1.3 <= v[2] < 7]))
            r["trainR_full_>=7"] = float(np.mean([v[0] for v in pl if v[2] >= 7]))
        h = [load_obj(ds, n, e) for n in ("half0", "half1", "half0_scr", "half1_scr")]
        if all(x is not None for x in h[:2]):
            c = F.frc(h[0], h[1], hrpx); r["C2"] = F.band_mean(c, lo, 0.45)
            r["FRC_bajas"] = F.band_mean(c, 0.0, g["na"] / lam)  # informativo: FRC media en [0, NA/lam)
            if e in FRC_EPOCHS:
                frc_curvas.setdefault("real", {})[e] = c.tolist()
        if all(x is not None for x in h[2:]):
            c = F.frc(h[2], h[3], hrpx); r["C2_nulo"] = F.band_mean(c, lo, 0.45)
            r["FRC_bajas_nulo"] = F.band_mean(c, 0.0, g["na"] / lam)
            if e in FRC_EPOCHS:
                frc_curvas.setdefault("nulo", {})[e] = c.tolist()
        del h
        o = load_obj(ds, "full", e)
        if o is not None:
            O[e] = o
        out["epocas"][e] = r
        print(ds, e, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != "C1_folds"}, flush=True)
    # diferencia pareada respecto de e=40
    if 40 in out["epocas"]:
        ref = out["epocas"][40]["C1_folds"]
        for e, r in out["epocas"].items():
            dd = [a - b for a, b in zip(r["C1_folds"], ref) if a is not None and b is not None]
            r["C1_menos_C1_40"], r["C1_menos_C1_40_sd"], _ = ms(dd)
    # estabilidad
    if O:
        n = next(iter(O.values())).shape[0]; bd = n // 12
        m = np.zeros((n, n), bool); m[bd:-bd, bd:-bd] = True
        A = {e: np.abs(o) for e, o in O.items()}
        P = {e: rel_phase(o) for e, o in O.items()}
        AH = {e: a - ndi.gaussian_filter(a, 20) for e, a in A.items()}  # amplitud sin fondo lento (sigma 20 px)
        kr = np.hypot(*np.meshgrid(np.fft.fftfreq(n, hrpx), np.fft.fftfreq(n, hrpx), indexing="ij"))
        BAND = {"bajas": kr <= g["na"] / lam, "C2": (kr >= lo) & (kr < 0.45)}  # <= NA/lam ; [2NA/lam, 0.45)
        filt = lambda a, k: np.real(np.fft.ifft2(np.fft.fft2(a) * BAND[k]))
        AB = {k: {e: filt(A[e], k) for e in A} for k in BAND}
        PB = {k: {e: filt(P[e], k) for e in P} for k in BAND}
        es = sorted(O)
        for i, e in enumerate(es):
            r = out["epocas"][e]
            if i > 0:
                p = es[i - 1]
                r["dA_rel_prev"] = float(np.linalg.norm((A[e] - A[p])[m]) / np.linalg.norm(A[e][m]))
                r["dA_hp_rel_prev"] = float(np.linalg.norm((AH[e] - AH[p])[m]) / np.linalg.norm(AH[e][m]))
                q = O[e][m] * np.conj(O[p][m])
                dphi = np.angle(q * np.exp(-1j * np.angle(np.sum(q))))
                r["dphi_rms_prev_rad"] = float(np.sqrt(np.mean(dphi ** 2)))
                r["prev_epoch"] = p
            for ref in (40, 400):
                if ref in O:
                    r[f"corrA_vs_{ref}"] = corr(A[e], A[ref], m)
                    r[f"corrA_hp_vs_{ref}"] = corr(AH[e], AH[ref], m)
                    r[f"corrPhi_vs_{ref}"] = corr(P[e], P[ref], m)
                    for k in BAND:
                        r[f"corrA_{k}_vs_{ref}"] = corr(AB[k][e], AB[k][ref], m)
                        r[f"corrPhi_{k}_vs_{ref}"] = corr(PB[k][e], PB[k][ref], m)
                    q = np.vdot(O[ref][m], O[e][m])
                    r[f"corrC_vs_{ref}"] = float(np.abs(q) / (np.linalg.norm(O[e][m]) * np.linalg.norm(O[ref][m])))
    out["frc_curvas"] = frc_curvas
    # verificación contra el INFORME de 28/09 b
    cb = os.path.join(B, "criterios_b.json")
    if ds.startswith("b_") and 40 in out["epocas"]:
        ref = json.load(open(cb))[color]; r = out["epocas"][40]; v = {}
        for k, kr in (("C1", "C1_R"), ("C2", "C2_frc"), ("C2_nulo", "C2_nulo"), ("lattice", "C3_lattice")):
            if r.get(k) is not None:
                v[k] = dict(nuestro=r[k], referencia=ref[kr], difabs=abs(r[k] - ref[kr]))
        if r["C1_nfolds"] < 5:
            v["nota"] = f"C1 con {r['C1_nfolds']} folds de 5"
        if "C1_sin_fpm" in out:
            v["C1_sin_fpm"] = dict(nuestro=out["C1_sin_fpm"], referencia=ref["C1_nofpm"])
        out["verificacion_e40"] = v
        print(ds, "VERIFICACION e=40", json.dumps(v), flush=True)
    json.dump(out, open(os.path.join(HERE, f"{ds}.json"), "w"), indent=1, default=float)
    return out


def colores():
    cmp = json.load(open(os.path.join(B, "comparar_colores.json")))
    sh = {"red": cmp["reconstrucciones"]["corrimiento_red_px_HR"], "blue": cmp["reconstrucciones"]["corrimiento_blue_px_HR"],
          "green": [0, 0]}
    n = 1200; PX = 512.0 / n
    fy, fx = np.meshgrid(np.fft.fftfreq(n, PX), np.fft.fftfreq(n, PX), indexing="ij")
    kr = np.hypot(fx, fy)
    m = np.zeros((n, n), bool); m[100:-100, 100:-100] = True
    bandas = ((0.07 / 0.63, "banda_objetivo"), (0.3, "hasta_0.3"), (10.0, "todo"))
    pares = (("red", "green"), ("blue", "green"), ("red", "blue"))
    out = dict(nota="corrimientos fijos de comparar_colores.json (medidos a 40 épocas); 'corrimiento_medido' = "
                    "correlación de fase del snapshot, como control", epocas={})
    for e in SNAPS:
        O = {c: load_obj(f"b_{c}", "full", e) for c in LAM}
        if any(o is None for o in O.values()):
            continue
        G = {c: np.roll(to_grid(O[c]), tuple(-np.array(sh[c])), (0, 1)) for c in LAM}
        r = {"amplitud": {}, "fase": {}, "corrimiento_medido": {}}
        A = {c: np.abs(G[c]) for c in LAM}
        P = {c: rel_phase(G[c]) for c in LAM}
        for c in ("red", "blue"):  # control: corrimiento residual tras aplicar el fijo
            a = A[c] - ndi.gaussian_filter(A[c], 20); b = A["green"] - ndi.gaussian_filter(A["green"], 20)
            R = np.fft.fft2(a) * np.conj(np.fft.fft2(b)); R /= np.abs(R) + 1e-12
            rr = np.fft.fftshift(np.real(np.fft.ifft2(R))); i = np.unravel_index(np.argmax(rr), rr.shape)
            r["corrimiento_medido"][c] = (np.array(i) - n // 2).tolist()
        for fmax, nm in bandas:
            filt = kr <= fmax
            LA = {c: np.real(np.fft.ifft2(np.fft.fft2(A[c]) * filt)) for c in LAM}
            LP = {c: np.real(np.fft.ifft2(np.fft.fft2(P[c]) * filt)) for c in LAM}
            r["amplitud"][nm] = {f"{a}_{b}": corr(LA[a], LA[b], m) for a, b in pares}
            r["fase"][nm] = {f"{a}_{b}": corr(LP[a], LP[b], m) for a, b in pares}
        out["epocas"][e] = r
        print("colores", e, json.dumps(r), flush=True)
    if 40 in out["epocas"]:
        out["verificacion_e40_amplitud"] = {nm: {p: dict(nuestro=out["epocas"][40]["amplitud"][nm][p],
                                                        referencia=cmp["reconstrucciones"][nm][p]) for p in cmp["reconstrucciones"][nm]}
                                            for _, nm in bandas}
    json.dump(out, open(os.path.join(HERE, "colores.json"), "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    args = sys.argv[1:] or [d for d in DS if os.path.isdir(os.path.join(IT, "out", d))] + ["colores"]
    for a in args:
        colores() if a == "colores" else analizar(a)

"""particiones_c2.py -- C2 por partición aleatoria (fase B). Lee out_part/<DS>/p<s>_h<h>/obj_eNNN.npy.

Por partición y época (20, 40, 120, 400):
- C2 oficial: F.band_mean(F.frc(h0, h1, hrpx), 2NA/lam, 0.45), campo entero, sin ventana (= analizar.py / criterios_b).
- C2 Hann: misma variante que revision/rev_c2b.py: interior (borde n//12 descartado), media restada, ventana de Hann
  2D, FRC propia de 60 anillos hasta kmax (frc_band, copia de revision/rev_obj.py), media de los anillos en la banda.
Referencia: la partición oficial (damero, out/<DS>/..._half0/_half1), con las dos definiciones.
Resumen: media, sd poblacional (ddof = 0) y muestral (ddof = 1) entre particiones, mín, máx, n > 0.143.
Uso: nice -n 19 python3 particiones_c2.py [DS ...]   (por defecto b_red b_blue). Escribe particiones_<DS>.json.
"""
import glob
import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IT = os.path.dirname(HERE)
RES = os.path.dirname(IT)
DS = {"b_red": (os.path.join(RES, "captura_2026-09-28b", "red"), 98.0),
      "b_green": (os.path.join(RES, "captura_2026-09-28b", "green"), 98.0),
      "b_blue": (os.path.join(RES, "captura_2026-09-28b", "blue"), 98.0),
      "s3_red": (os.path.join(RES, "captura_2026-09-25_red"), 74.0)}
EP = [20, 40, 120, 400]
UMBRAL = 0.143


def mod(d, tag):
    s = importlib.util.spec_from_file_location("F_" + tag, os.path.join(d, "fpm_red.py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def kgrid(n, p):
    f = np.fft.fftfreq(n, p); return np.hypot(*np.meshgrid(f, f, indexing="ij"))


def frc_band(a, b, p, lo, hi, nb=60):  # = revision/rev_obj.frc_band
    n = a.shape[0]; A = np.fft.fft2(a - a.mean()); Bb = np.fft.fft2(b - b.mean()); k = kgrid(n, p)
    edges = np.linspace(0, k.max(), nb + 1); idx = np.digitize(k.ravel(), edges) - 1
    x = (A * np.conj(Bb)).ravel()
    num = np.abs(np.bincount(idx, x.real, nb + 1) + 1j * np.bincount(idx, x.imag, nb + 1))
    den = np.sqrt(np.bincount(idx, np.abs(A.ravel()) ** 2, nb + 1) * np.bincount(idx, np.abs(Bb.ravel()) ** 2, nb + 1)) + 1e-30
    c = 0.5 * (edges[:-1] + edges[1:]); v = (num / den)[:nb]; m = (c >= lo) & (c < hi)
    return float(v[m].mean())


def c2_hann(h0, h1, p, lo):  # = revision/rev_c2b.py
    n = h0.shape[0]; bd = n // 12; s = slice(bd, n - bd)
    w = np.outer(np.hanning(n - 2 * bd), np.hanning(n - 2 * bd))
    a, b = h0[s, s], h1[s, s]
    return frc_band((a - a.mean()) * w, (b - b.mean()) * w, p, lo, 0.45)


def both(F, h0, h1, p, lo):
    return dict(C2=F.band_mean(F.frc(h0, h1, p), lo, 0.45), C2_hann=c2_hann(h0, h1, p, lo))


def stats(v):
    v = np.array(v, float)
    return dict(n=len(v), media=float(v.mean()), sd_pob=float(v.std()), sd_muestral=float(v.std(ddof=1)) if len(v) > 1 else None,
                min=float(v.min()), max=float(v.max()), n_sobre_umbral=int(np.sum(v > UMBRAL)), valores=v.tolist())


def main(ds):
    d, z = DS[ds]
    F = mod(d, ds); g = F.geometry(z); p, lo = g["hrpx"], 2 * g["na"] / g["lam"]
    out = dict(dataset=ds, banda=[lo, 0.45], umbral=UMBRAL, oficial={}, particiones={}, resumen={})
    tdir = lambda t: os.path.join(IT, "out", ds, f"real_A+init_z{z:.1f}_{t}")
    for e in EP:
        f0, f1 = (os.path.join(tdir(t), f"obj_e{e:03d}.npy") for t in ("half0", "half1"))
        if os.path.exists(f0) and os.path.exists(f1):
            out["oficial"][e] = both(F, np.load(f0).astype(complex), np.load(f1).astype(complex), p, lo)
    seeds = sorted({int(os.path.basename(x).split("_")[0][1:]) for x in glob.glob(os.path.join(IT, "out_part", ds, "p*_h0"))})
    for s in seeds:
        r = {}
        for e in EP:
            f0, f1 = (os.path.join(IT, "out_part", ds, f"p{s}_h{h}", f"obj_e{e:03d}.npy") for h in (0, 1))
            if os.path.exists(f0) and os.path.exists(f1):
                r[e] = both(F, np.load(f0).astype(complex), np.load(f1).astype(complex), p, lo)
        out["particiones"][s] = r
        print(ds, f"p{s}", {e: {k: round(v, 4) for k, v in x.items()} for e, x in r.items()}, flush=True)
    for e in EP:
        for k in ("C2", "C2_hann"):
            v = [out["particiones"][s][e][k] for s in seeds if e in out["particiones"][s]]
            if v:
                out["resumen"].setdefault(e, {})[k] = stats(v)
    # cambio pareado por partición respecto de 40
    for k in ("C2", "C2_hann"):
        for e in EP:
            dv = [out["particiones"][s][e][k] - out["particiones"][s][40][k] for s in seeds
                  if e in out["particiones"][s] and 40 in out["particiones"][s]]
            if dv and e != 40:
                out["resumen"][e][k + "_menos_40"] = stats(dv)
    print(ds, "oficial", json.dumps(out["oficial"]), flush=True)
    print(ds, "resumen", json.dumps({e: {k: {q: (round(x, 4) if isinstance(x, float) else x) for q, x in v.items() if q != "valores"}
                                          for k, v in r.items()} for e, r in out["resumen"].items()}), flush=True)
    json.dump(out, open(os.path.join(HERE, f"particiones_{ds}.json"), "w"), indent=1)


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["b_red", "b_blue"]):
        main(a)

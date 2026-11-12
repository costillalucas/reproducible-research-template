"""sim_z_clave.py -- alturas clave de la matriz 15x15: conjuntos BF completos (5, 9, 13, 21, 25) (simulacion, 12/11).
Uso: python sim_z_clave.py [geo] [e1] [e2] [e3] [e4] [e5]   (sin argumentos corre todo, en ese orden de prioridad).
Reutiliza SIN modificar ../sim_z/sim_z.py (modelo directo sin crimen inverso, ruido, solver ePIE, metricas).
Escribe runs.jsonl (una linea por corrida, se puede leer incompleto) y geometria.json. Semillas fijas.
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z"))
import sim_z as S                                     # noqa: E402
from scipy import fft as sfft                         # noqa: E402

T0 = time.time()
NA0, R_SOLVER = S.NA, S.R
CENTROS = {103.0: 5, 146.0: 9, 181.0: 13, 216.0: 21}  # z central -> n BF nominal
NSEED = 2
BC = 0.23                                             # banda comun absoluta: NA_syn en eje a z=249 es 0.236


def margen(z, na):
    """(n_BF, margen minimo |NA_ilum - na| sobre los 225 LEDs, margen del ultimo BF, margen del primer DF)."""
    g = S.geom(z)
    v = np.array([S.ill_na(g, k) for k in S.KEYS])
    bf = v[v < na]; df = v[v >= na]
    return int(bf.size), float(np.min(np.abs(v - na))), float(na - bf.max()), float(df.min() - na)


def geo():
    zs = np.arange(80.0, 262.01, 0.5)
    out = {"ventanas": {}, "centros": [], "barrido": []}
    for na in (0.067, 0.070, 0.073):
        rows = [(z,) + margen(z, na) for z in zs]
        if na == 0.070:
            out["barrido"] = [dict(z=float(z), n_BF=n, margen=m) for z, n, m, _, _ in rows]
        w = {}
        for n in (5, 9, 13, 21, 25):
            r = [x for x in rows if x[1] == n]
            best = max(r, key=lambda x: x[2])
            ok = [x[0] for x in r if x[2] >= 0.010]; ok7 = [x[0] for x in r if x[2] >= 0.007]
            w[n] = dict(z_min=float(r[0][0]), z_max=float(r[-1][0]), z_opt=float(best[0]), margen_max=best[2],
                        z_ok010=[float(min(ok)), float(max(ok))] if ok else None,
                        z_ok007=[float(min(ok7)), float(max(ok7))] if ok7 else None)
        out["ventanas"][f"{na:.3f}"] = w
    for z in list(CENTROS) + [249.0, 125.0, 168.0, 174.0, 188.0]:
        t = S.geo_table(z)
        t["margen"] = {f"{na:.3f}": margen(z, na)[:2] for na in (0.067, 0.070, 0.073)}
        out["centros"].append(t)
    json.dump(out, open(os.path.join(HERE, "geometria.json"), "w"), indent=1)


def extra(o, t):
    """Error y FRC en la banda absoluta comun NA < BC (misma normalizacion que S.metrics)."""
    c = np.vdot(o, t) / np.vdot(o, o)
    oc = o * c; d = oc - t
    Fd, Ft, Fo = (sfft.fftshift(sfft.fft2(a - a.mean())) for a in (d, t, oc))
    s = S.KR < BC
    return {"e_c23": float(np.sqrt(np.sum(np.abs(Fd[s]) ** 2) / np.sum(np.abs(Ft[s]) ** 2))),
            "frc_c23": float(np.abs(np.sum(Fo[s] * np.conj(Ft[s]))) / np.sqrt(np.sum(np.abs(Fo[s]) ** 2) * np.sum(np.abs(Ft[s]) ** 2)))}


def log(row):
    row["t"] = round(time.time() - T0, 1)
    with open(os.path.join(HERE, "runs.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    print(row["est"], row["z"], row["na_real"], row["obj"], row["seed"], round(row["err"], 4), round(row["e_c23"], 4), row["t"], flush=True)


def corrida(est, z, objs, na_real=NA0, seeds=range(NSEED), excl=None):
    """Datos con NA_obj real = na_real; el solver usa siempre NA 0.070. excl: umbral de exclusion de LEDs de borde."""
    g = S.geom(z)
    keys = S.KEYS if excl is None else [k for k in S.KEYS if abs(S.ill_na(g, k) - NA0) >= excl]
    nbf, mg, _, _ = margen(z, na_real)
    for io, (spec, truth, mask) in enumerate(objs):
        S.R = R_SOLVER * na_real / NA0                # pupila real de los datos
        I = S.forward(spec, g)
        S.R = R_SOLVER                                # el solver no conoce la NA real
        for s in seeds:
            In, ts = S.add_noise(I, g, z, np.random.default_rng(1000 + s))
            o = S.reconstruct(In, g, keys)
            log(dict(est=est, z=z, na_real=na_real, obj=io, seed=int(s), nbf_real=nbf, margen_real=mg, n_excl=len(S.KEYS) - len(keys),
                     n_1025=int(sum(t == 1025.0 for t in ts.values())), **S.metrics(o, truth, mask), **extra(o, truth)))


def main():
    todo = sys.argv[1:] or ["geo", "e1", "e2", "e3", "e4", "e5"]
    if "geo" in todo:
        geo()
    objs = [S.make_object(0), S.make_object(1)]
    for name in todo:
        if name == "e1":                              # centros de ventana
            for z in CENTROS:
                corrida("e1", z, objs)
        if name == "e2":                              # control 'a medias': mismo n BF, cerca del borde de la ventana
            for z in (125.0, 168.0, 174.0, 188.0):
                corrida("e2", z, objs)
        if name == "e3":                              # NA_obj real distinta de la del solver
            for na in (0.067, 0.073):
                for z in CENTROS:
                    corrida("e3", z, objs, na_real=na)
        if name == "e4":                              # 25 BF
            corrida("e4", 249.0, objs)
        if name == "e5":                              # ventanas angostas excluyendo LEDs a < 0.006 del borde
            for z in (181.0, 249.0):
                corrida("e5", z, objs, seeds=range(1), excl=0.006)


if __name__ == "__main__":
    main()

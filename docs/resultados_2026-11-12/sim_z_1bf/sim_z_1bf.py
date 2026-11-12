"""sim_z_1bf.py -- matriz 15x15 con UN solo LED en campo claro (z < 85.5 mm) (simulacion, 12/11).
Uso: python sim_z_1bf.py [geo] [e1] [e3] [e2]   (sin argumentos corre todo en ese orden). Semillas fijas.
Reutiliza SIN modificar ../sim_z/sim_z.py y ../sim_z_clave/sim_z_clave.py (modelo directo sin crimen inverso,
ruido, solver ePIE, metricas). Unico cambio: se agrega una exposicion corta de 5 ms a la lista HDR (en memoria),
porque a z < 72 mm el BF central satura con 20 ms. Escribe runs.jsonl y geometria.json.
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z"))
sys.path.insert(0, os.path.join(HERE, "..", "sim_z_clave"))
import sim_z as S                                     # noqa: E402
import sim_z_clave as K                               # noqa: E402

S.EXPOS = [5.0] + list(S.EXPOS)                       # exposicion extra corta (no existe en el HDR real)
T0 = time.time()
ZS = [55.0, 65.0, 73.0]
C0 = (0, 0)


def geo():
    out = []
    for z in ZS + [80.0, 103.0, 135.0, 146.0, 216.0]:
        t = S.geo_table(z)
        g = S.geom(z)
        t["margen"] = K.margen(z, S.NA)[1]
        t["na_anillo1"] = S.ill_na(g, (0, 1))
        t["cabe_en_HR"] = bool(max(abs(g[(7, 7)][0]), abs(g[(7, 7)][1])) / S.DK + S.LR / 2 <= S.HR / 2)
        out.append(t)
    json.dump(out, open(os.path.join(HERE, "geometria.json"), "w"), indent=1)


def log(row):
    row["t"] = round(time.time() - T0, 1)
    with open(os.path.join(HERE, "runs.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    print(row["est"], row["z"], row["var"], row["obj"], row["seed"], round(row["err"], 3), round(row["ph_esf"], 3), row["t"], flush=True)


def corrida(est, z, objs, var="base", seeds=(0, 1), keys=None, **kw):
    g = S.geom(z)
    keys = S.KEYS if keys is None else keys(g)
    nbf = sum(S.ill_na(g, k) < S.NA for k in set(keys))
    for io, (spec, truth, mask) in enumerate(objs):
        I = S.forward(spec, g)
        for s in seeds:
            In, ts = S.add_noise(I, g, z, np.random.default_rng(1000 + s))
            o = S.reconstruct(In, g, keys, **kw)
            log(dict(est=est, z=z, var=var, obj=io, seed=int(s), nbf=int(nbf), t_bf=ts[C0],
                     sat_bf=float(np.mean(In[C0] * S.R0 * (S.Z0 / z) ** 2 * ts[C0] >= S.FW - 1)),
                     **S.metrics(o, truth, mask), **K.extra(o, truth)))


def solo_central(g):                                  # deja 1 BF artificial: quita los demas LEDs BF
    return [k for k in S.KEYS if k == C0 or S.ill_na(g, k) >= S.NA]


def main():
    todo = sys.argv[1:] or ["geo", "e1", "e3", "e2"]
    if "geo" in todo:
        geo()
    objs = [S.make_object(0), S.make_object(1)]
    for name in todo:
        if name == "e1":                              # 1 BF real con margen
            for z in ZS:
                corrida("e1", z, objs)
        if name == "e3":                              # 1 BF artificial a z alto: fase vs solapamiento con 1 BF
            for z in (103.0, 146.0, 216.0):
                corrida("e3", z, objs, var="1bf_artificial", seeds=(0,), keys=solo_central)
        if name == "e2":                              # rescates baratos a z = 73 (1 BF real, mayor solapamiento)
            z = 73.0
            corrida("e2", z, objs, var="bf_x3", seeds=(0,), keys=lambda g: S.KEYS + [C0, C0])
            corrida("e2", z, objs, var="paso_0.1", seeds=(0,), step=0.1)
            corrida("e2", z, objs, var="60_epocas", seeds=(0,), its=60)


if __name__ == "__main__":
    main()

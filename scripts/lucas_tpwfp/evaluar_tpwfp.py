"""Evalúa la copia adaptada del TPWFP de Lucas con los mismos criterios que la reconstrucción del
25/09 (results/captura_2026-09-25_red/criterios.md), para compararla con el método A+init:

  C1  R held-out: 5 folds por anillo (fpm_red.folds), ajuste afín, promedio en anillos < 7
  C2  FRC entre las mitades en damero, promedio en la banda [2NA/lambda, 0.45] 1/um
  C3  lattice_score de la reconstrucción con todos los LEDs
  control sintético (synth.npz): lo mismo más el FRC contra la verdad

    python3 scripts/lucas_tpwfp/evaluar_tpwfp.py [--iteraciones 76] [--procesos 2] [--datos real synth]

Cada tarea se guarda en results/captura_2026-09-25_red/tpwfp_lucas/eval/<nombre>.json (se saltea si ya
existe) y el resumen en .../eval/resumen_it<N>.json.
"""
import argparse
import importlib.util
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("lucas", os.path.join(HERE, "real_images_reconstruction_rojo_2026-09-25.py"))
Lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Lc)
F = Lc.F
OUT = os.path.join(Lc.RED, "tpwfp_lucas", "eval")
BAND = (0.222, 0.45)
_cache = {}


def data(name):
    if name not in _cache:
        if name == "real":
            _cache[name] = F.load_real()
        else:
            import synth
            _cache[name] = synth.load_synth()
    return _cache[name]


def run(t):
    p = os.path.join(OUT, t["name"] + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    D = data(t["data"])
    obj, *_ = Lc.recontruction_pipeline_real_images(None, t["it"], keys_usadas=[tuple(k) for k in t["train"]],
                                                    cobertura=t["cob"], guardar=False, D=D)
    geo = F.geometry(74.0)
    evalk = [k for k in D["keys"] if list(k) not in t["train"]] or D["keys"]
    pred = F.predict(obj, evalk, geo)
    out = {k: v for k, v in t.items() if k != "train"}
    out["per_led"] = {f"{k[0]},{k[1]}": [*F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k]), F.ring(k)]
                      for k in evalk}
    out["lattice"] = F.lattice_score(obj)
    if "truth" in D:
        out["frc_truth_band"] = F.band_mean(F.frc(obj, D["truth"], geo["hrpx"]), *BAND)
    # cambio relativo respecto de la inicialización: si ~0, el solver no se movió
    mid = sorted(k for k in D["keys"] if list(k) in t["train"])[len(t["train"]) // 2]
    out["init_led"] = list(mid)
    if t["kind"] in ("full", "half"):
        np.save(os.path.join(OUT, f"obj_{t['name']}.npy"), obj.astype(np.complex64))
    json.dump(out, open(p, "w"))
    print("listo", t["name"], flush=True)
    return out


def tareas(datos, it, variantes):
    T = []
    for d in datos:
        keys = data(d)["keys"]
        for cob in variantes:
            v = "cob" if cob else "L"
            base = dict(data=d, it=it, cob=cob)
            T.append(dict(base, name=f"{d}_{v}_it{it}_full", kind="full", train=[list(k) for k in keys]))
            for h in (0, 1):
                T.append(dict(base, name=f"{d}_{v}_it{it}_half{h}", kind="half",
                              train=[list(k) for k in keys if (k[0] + k[1]) % 2 == h]))
            if d == "real":
                for i, fo in enumerate(F.folds(keys, 5)):
                    T.append(dict(base, name=f"{d}_{v}_it{it}_f{i}", kind="fold",
                                  train=[list(k) for k in keys if k not in fo]))
    return T


def resumen(res, it):
    S = {}
    for r in res:
        key = f"{r['data']}_{'cob' if r['cob'] else 'L'}"
        s = S.setdefault(key, {"folds": []})
        if r["kind"] == "fold":
            s["folds"].append(float(np.mean([v[0] for v in r["per_led"].values() if v[2] < 7])))
        if r["kind"] == "full":
            s["lattice"] = r["lattice"]
            if "frc_truth_band" in r:
                s["frc_truth_band"] = r["frc_truth_band"]
    for key, s in S.items():
        d, v = key.split("_")
        if s["folds"]:
            s["R_heldout"] = [float(np.mean(s["folds"])), float(np.std(s["folds"]))]
        try:
            a = np.load(os.path.join(OUT, f"obj_{d}_{v}_it{it}_half0.npy"))
            b = np.load(os.path.join(OUT, f"obj_{d}_{v}_it{it}_half1.npy"))
            s["FRC_mitades_banda"] = F.band_mean(F.frc(a, b, F.geometry(74.0)["hrpx"]), *BAND)
        except FileNotFoundError:
            pass
    json.dump(S, open(os.path.join(OUT, f"resumen_it{it}.json"), "w"), indent=1)
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--iteraciones", type=int, default=Lc.iterations)
    ap.add_argument("--procesos", type=int, default=2)
    ap.add_argument("--datos", nargs="+", default=["real", "synth"])
    ap.add_argument("--variantes", nargs="+", default=["L", "cob"])
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    T = tareas(a.datos, a.iteraciones, [v == "cob" for v in a.variantes])
    T.sort(key=lambda t: {"full": 0, "half": 1, "fold": 2}[t["kind"]])
    print(len(T), "tareas", flush=True)
    for d in a.datos:
        data(d)
    with mp.get_context("fork").Pool(a.procesos) as pool:
        res = pool.map(run, T, chunksize=1)
    resumen(res, a.iteraciones)

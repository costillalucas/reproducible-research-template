"""criterios_2110.py -- COPIA 21/10 de octubre_capturas_2026-10-21/eval/criterios_oct.py (DS por env, variante C.VAR).
criterios_oct.py -- C1–C4 de rojo_final sobre el set DS (env, por defecto m2_red), mismas definiciones que
rojo_resolucion_2026-10-20/criterios.py (copiado c4_full), contra rojo_final de 28/09b (criterios.json / resolucion_final.json de
ese directorio). Necesita cv_<DS>_rojo_final.json y resolucion_<DS>_final.json. Uso: DS=m2_red python3 criterios_oct.py 40 [160]"""
import json, os, sys
import numpy as np
import comun as C
from resolucion import objs

H = C.HERE; eps = [int(e) for e in sys.argv[1:]] or [40]
R20 = os.path.join(C.RES, 'rojo_resolucion_2026-10-20')


def c4_full(O, raw, px, F):
    c = C.c4(O["full"], O["half0"], O["half1"], raw, px, F)
    rec = C.blobs(C.rel_phase(O["full"]), px)
    rw = C.blobs(np.real(F.fourier_upsample(np.sqrt(np.clip(raw, 0, None)), O["full"].shape[0] // raw.shape[0])), px)
    new = rec[(rec[:, 2] <= 2.0) & ~C.near(rec, rw, 3.0)]
    sh = np.array([40.0, 25.0, 0.0])
    b0, b1 = C.blobs(C.rel_phase(O["half0"]), px) + sh, C.blobs(C.rel_phase(O["half1"]), px) + sh
    ch = C.near(new, b0, 2.0) & C.near(new, b1, 2.0)
    c["azar_frac"] = float(ch.mean()) if len(new) else 0.0
    c["PASS"] = bool(c["n_new_both_halves"] >= 5 and c["frac"] >= 0.19)
    return c


F, geo, D = C.load()
cv = json.load(open(os.path.join(H, f"cv_{C.DS}_{C.VAR}.json")))
rf = json.load(open(os.path.join(H, f"resolucion_{C.DS}_final.json")))["epocas"]
out = {}
for e in eps:
    i = cv["epocas"].index(e); lat = cv["lattice_full"][str(e)]; c2 = rf[str(e)]["C2"]; rs = rf[str(e)]["res"]
    out[f"{C.DS}_e{e}"] = dict(C1_R=cv["media"][i], C1_sd=cv["sd"][i], C1_sin_fpm=cv["sin_fpm"], C1_PASS=bool(cv["media"][i] <= cv["sin_fpm"] - 0.10),
                               C2_frc=c2["frc"], C2_nulo=c2["nulo"], C2_PASS=c2["PASS"], C3_lattice=lat, C3_PASS=bool(lat <= 0.01),
                               C4=c4_full(objs("final", e), D["I"][(17, 15)], geo["hrpx"], F),
                               periodo_FRC_1_7_um={q: rs[q]["periodo_1_7_um"] for q in rs}, periodo_nulo_um={q: rs[q]["periodo_nulo_um"] for q in rs},
                               crudo_FRC_2BF_k17=rf[str(e)]["crudo_FRC_2BF"]["k_1_7"])
ref = json.load(open(os.path.join(R20, "criterios.json"))); rr = json.load(open(os.path.join(R20, "resolucion_final.json")))["epocas"]
for e in ("40", "160"):
    if f"rojo_final_e{e}" in ref:
        out[f"28b_rojo_final_e{e}"] = {**ref[f"rojo_final_e{e}"], "periodo_FRC_1_7_um": {q: rr[e]["res"][q]["periodo_1_7_um"] for q in rr[e]["res"]},
                                       "periodo_nulo_um": {q: rr[e]["res"][q]["periodo_nulo_um"] for q in rr[e]["res"]},
                                       "crudo_FRC_2BF_k17": rr[e]["crudo_FRC_2BF"]["k_1_7"]}
for k, v in out.items():
    print(k, json.dumps(v, default=float))
json.dump(out, open(os.path.join(H, f"criterios_{C.DS}.json"), "w"), indent=1, default=float)

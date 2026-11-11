#!/usr/bin/env python3
"""R de r20 y n20 evaluado SOLO sobre los LEDs que no cambian BF/DF (para separar el residuo del propio LED cambiado del resto).
Agrega r20_evalsin / n20_evalsin a residuos.json."""
import json, numpy as np, sys
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um/codigo")
import residuos as RS
P0 = RS.P0
out = json.load(open(P0 + "residuos.json"))
J = {p["id"]: p for p in json.load(open(P0 + "particulas.json"))["particulas"]}
for fila in out:
    p = J[fila["id"]]; ruta = P0 + f"runs/_prep_{p['id']}.npz"
    f0, c0 = RS.RC.preparar(p["fila400"], p["col400"], 20, ruta)
    for nom, carpeta, nulo in (("r20", "r20", False), ("n20", "r20_nulo", True)):
        d = np.load(P0 + f"runs/{carpeta}/{p['id']}.npz")
        F, geo, D = RS.geo_y_datos(ruta, f0, c0, 20, nulo); D["bf"] = set(F.BF)
        keys = [k for k in D["keys"] if k not in {tuple(c) for c in d["cambian"]}]
        pred = RS.predecir(F, geo, d["obj"].astype(complex), keys, 20)
        fila[nom + "_evalsin"] = RS.R(pred, D, keys)
    RS.os.remove(ruta)
    print(fila["id"], round(fila["r20_evalsin"], 3), round(fila["n20_evalsin"], 3), round(fila["r20_sincambian"], 3), round(fila["r400"], 3))
json.dump(out, open(P0 + "residuos.json", "w"), indent=1)

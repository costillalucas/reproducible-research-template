"""C2 (FRC complejo mitades, banda [2NA/λ, 0.45] 1/µm) y cruce de 1/7 para la captura roja 03/11 (real y nulo DF)."""
import sys, json, numpy as np
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0]); import comun_plan as C
PX, LAM, NA = 0.43, 0.63, 0.0669
out = {}
for nom, d in [("real", sys.argv[1])] + ([("nulo_df", sys.argv[2])] if len(sys.argv) > 2 else []):
    h0, h1 = np.load(d + "/objeto_mitadA.npy"), np.load(d + "/objeto_mitadB.npy")
    fr = C.frc_fino(h0, h1, PX, ventana=True)
    k = C.cruce(fr, k0=2 * NA / LAM)
    out[nom] = dict(C2=C.c2(h0, h1, PX, NA, LAM), k_cruce_1_7=k, periodo_um=(1 / k if k else None),
                    NA_eff=(k * LAM if k else None))
print(json.dumps(out, indent=1)); json.dump(out, open(sys.argv[-1] if sys.argv[-1].endswith(".json") else "/dev/null", "w"), indent=1)

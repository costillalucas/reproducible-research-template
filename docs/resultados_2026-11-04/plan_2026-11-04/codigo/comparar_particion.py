"""Damero (2026-11-03-red_1311) vs diseño 2 (particion2): C1, C2, cruce 1/7 y volumen de fase por objeto (completo, A, B)."""
import sys, json, importlib.util, numpy as np
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo"); import comun_plan as C
REPO = "/home/chanoscopio/Documents/LucasC/reproducible-research-template"
spec = importlib.util.spec_from_file_location("analisis", REPO + "/results/rojo_fase_2026-10-20/analisis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
R = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/"
PX, LAM, NA, DN = 0.43, 0.63, 0.0669, 0.046
runs = {"damero": R + "2026-11-03-red_1311", "diseno2": R + "plan_2026-11-04/particion2"}
out = {}
for n, d in runs.items():
    o = {t: np.load(f"{d}/objeto_{t}.npy").astype(complex) for t in ("complejo", "mitadA", "mitadB")}
    fr = C.frc_fino(o["mitadA"], o["mitadB"], PX); k = C.cruce(fr, k0=2 * NA / LAM)
    r = dict(C2=C.c2(o["mitadA"], o["mitadB"], PX, NA, LAM), k_cruce=k, periodo_um=(1 / k if k else None))
    for t, ob in o.items():
        ok = A.tabla(A.particulas(ob, PX)[0]); V = np.array([x["V"] for x in ok]); pk = np.array([x["phi"] for x in ok])
        r[t] = dict(N=len(ok), V_med=float(np.median(V)), pico_med=float(np.median(pk)),
                    d_vol=float(np.median(A.dvol(V, DN) / 1.0499)), d_pico=float(np.median(pk * LAM / (2 * np.pi * DN))))
    r["VB_sobre_VA"] = r["mitadB"]["V_med"] / r["mitadA"]["V_med"]
    out[n] = r
json.dump(out, open(R + "plan_2026-11-04/particion2/comparacion.json", "w"), indent=1)
for n, r in out.items():
    print(f"== {n}: C2 {r['C2']:.3f}  cruce {r['periodo_um'] or 0:.2f} µm  VB/VA {r['VB_sobre_VA']:.2f}")
    for t in ("complejo", "mitadA", "mitadB"):
        x = r[t]; print(f"   {t:9s} N {x['N']:3d}  V {x['V_med']:5.1f}  pico {x['pico_med']:.2f}  d_vol {x['d_vol']:.2f}  d_pico {x['d_pico']:.2f}")

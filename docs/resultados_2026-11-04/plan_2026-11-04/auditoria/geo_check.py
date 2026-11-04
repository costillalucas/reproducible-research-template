"""Auditoría: geometría efectiva usada por el solver (lee el código del repo, no lo modifica)."""
import sys, numpy as np
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo")
import comun_plan as C
for na in (C.NA0, 0.072, 0.074):
    print(na, C.k_sint("red", (0.529, -0.041), 3, na=na))
import reconstruir_plan as RP
F, IR = RP.cargar_solver("red", 3)
for z in (102.0, 97.4):
    geo = F.geometry(z, offset_mm=(0.529, -0.041), crop=400)
    print("z", z, "lam", geo["lam"], "lrpx", geo["lrpx"], "hrpx", geo["hrpx"], "na", geo["na"], "factor", geo["factor"])
    for k in [(17,15),(17,22),(24,15),(10,15),(17,8),(24,22),(10,8),(10,22),(24,8),(16,14),(18,14),(16,16),(18,16)]:
        fx, fy = geo["fxy"][k]; f = np.hypot(fx, fy)
        print(k, "fx %.4f fy %.4f |f| %.4f sin %.4f |f|/(NA/lam) %.3f" % (fx, fy, f, f*geo["lam"], f/(geo["na"]/geo["lam"])))
s = F.setup(102.0, (0.529, -0.041), 400)
print(s.led_array)
print(s.objective)

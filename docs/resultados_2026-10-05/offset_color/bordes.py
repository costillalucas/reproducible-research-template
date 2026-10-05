"""bordes.py -- LEDs cuyo borde de pupila pasa cerca de k=0 (|k_LED| - NA/λ en bins de 1/512 µm^-1), nominal vs die,
rojo/verde/azul. Negativo = campo claro."""
import sys; sys.path.insert(0, "../iteraciones_2026-09-30")
import numpy as np, iter_runner as IR
DIE = {"red": 1.06, "green": 0.63, "blue": 0.15}
for ds, c in (("b_red", "red"), ("b_green", "green"), ("b_blue", "blue")):
    F, R = IR._load(ds); keys = F.load_real.__defaults__ and None
    for off in (3.0, 3.0 + DIE[c]):
        g = F.geometry(98, offset_mm=(0, off)); r = g["na"] / g["lam"] * 512
        d = {k: np.hypot(*v) * 512 - r for k, v in g["fxy"].items()}
        near = sorted((round(v, 1), k) for k, v in d.items() if abs(v) < 15)
        print(c, off, "radio pupila %.1f bins" % r, near)
    sys.modules.pop("fpm_red"); sys.path.remove(IR.DATASETS[ds][0])

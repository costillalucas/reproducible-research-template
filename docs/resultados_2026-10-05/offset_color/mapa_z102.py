"""mapa_z102.py -- mapa_bfdf/mapa.py (fuente puntual) para la geometría de trabajo z=102 mm, NA 0.069, lrpx 1.362 µm
(campo 400 px = ±272 µm), offset del die por color. Lista LEDs a horcajadas del borde BF/DF."""
import os, sys, json
import numpy as np
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
from ptyco_full_simulator import config, led_array
Z, NA, LRPX, CROP, N = 102.0, 0.069, 3.2 / 2.35, 400, 201
OFF = {"red": 4.06, "green": 3.63, "blue": 3.15}
half = CROP * LRPX / 2 / 1000.0; u = np.linspace(-half, half, N); X, Y = np.meshgrid(u, u)
print(f"z={Z} NA={NA} R_BF={Z*np.tan(np.arcsin(NA)):.3f} mm, campo ±{half*1000:.0f} µm")
res = {}
for c in OFF:
    cfg = config.default_setup(c, 15, objective="2_5x_na007", resolution_px=(CROP, CROP), row_index_base=11, col_index_base=8,
                               z_distance_mm=Z, led_center_offset_mm=(0.0, OFF[c])).led_array
    st = {}
    for r in range(cfg.row_base, cfg.row_base + cfg.grid_size):
        for cc in range(cfg.col_base, cfg.col_base + cfg.grid_size):
            lx, ly = led_array.led_position_mm(r, cc, cfg); dx, dy = lx - X, ly - Y
            f = float((np.hypot(dx, dy) / np.sqrt(dx**2 + dy**2 + Z**2) < NA).mean())
            if 0 < f < 1: st[f"{r},{cc}"] = round(f, 3)
            if f == 1: st.setdefault("_BF", []).append([r, cc])
    res[c] = st; print(c, st)
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapa_z102.json"), "w"), indent=1)

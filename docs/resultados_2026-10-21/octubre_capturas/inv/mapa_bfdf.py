"""mapa_bfdf.py -- = offset_color_2026-10-02/mapa_z102.py para rojo_final (z 102, NA 0.069·1.25/1.29, lrpx 1.29, recorte 400)
con el offset del dado rojo de 28/09b (3+1.06) y el medido en los flats de octubre (3+dy, frontera_oct.json, R libre).
Lista LEDs a horcajadas del borde BF/DF (fracción del campo dentro de la pupila). Escribe mapa_bfdf.json."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from ptyco_full_simulator import config, led_array
Z, LRPX, CROP, N = 102.0, 1.29, 400, 201; NA = 0.069 * 1.25 / 1.29
fr = json.load(open(f'{HERE}/frontera_oct.json'))['sets']
offs = {'28b_die_1.06': 4.06, **{f'{s}_dy{fr[s]["R_libre"]["dy_mm"]:.3f}': 3 + fr[s]['R_libre']['dy_mm']
                                 for s in ('2026-10-16-luzsinmuestra', '2026-10-20-luzsinmuestra', '2026-10-09-sinmuestra')}}
half = CROP * LRPX / 2 / 1000.0; u = np.linspace(-half, half, N); X, Y = np.meshgrid(u, u)
res = {}
for nm, off in offs.items():
    cfg = config.default_setup('red', 15, objective='2_5x_na007', resolution_px=(CROP, CROP), row_index_base=11, col_index_base=8,
                               z_distance_mm=Z, led_center_offset_mm=(0.0, off)).led_array
    st = {}
    for r in range(cfg.row_base, cfg.row_base + cfg.grid_size):
        for cc in range(cfg.col_base, cfg.col_base + cfg.grid_size):
            lx, ly = led_array.led_position_mm(r, cc, cfg); dx, dy = lx - X, ly - Y
            f = float((np.hypot(dx, dy) / np.sqrt(dx**2 + dy**2 + Z**2) < NA).mean())
            if 0 < f < 1: st[f'{r},{cc}'] = round(f, 3)
            if f == 1: st.setdefault('_BF', []).append([r, cc])
    res[nm] = st; print(nm, st)
json.dump(res, open(f'{HERE}/mapa_bfdf.json', 'w'), indent=1)

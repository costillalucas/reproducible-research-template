#!/usr/bin/env python3
"""redondeo.py -- cuánto error de geometría introduce el redondeo de los k del LED a la grilla de Fourier, según el tamaño del recorte.

[Copia adaptada de plan_2026-11-11/recortes/codigo/redondeo.py.] Usa exactamente las funciones del solver: F.geometry (fxy exactos de cada LED), spectral_ops.led_crop_window (redondeo al bin
HR más cercano, spectral_ops.py:34-35) y optics.circular_pupil (pupila binaria sobre la grilla LR, optics.py:22-27).
Para cada tamaño n (px crudos) con la geometría B (z 102, NA 0.06686, λ 0.63; offset del centro de epocas_200):
  dk = 1/(n·lrpx); radio de la pupila y paso de LED en bins; error de redondeo |f_redondeado - f_exacto| por LED (en bins y en %
  del paso de LED); LEDs cuyo estado BF/DF CAMBIA: exacto |f| < NA/λ vs modelo discreto (el bin DC desplazado cae dentro de la
  pupila binaria); área de la pupila discreta / área continua.
Escribe redondeo.json y lo imprime.
"""
import json
import os
import sys

import numpy as np

for _v in ("Z_MM", "NA_OBJ", "LAM_NM"):
    os.environ.pop(_v, None)   # geometría B: z 102, NA 0.06686, λ 0.63 (defaults del driver)
sys.path.insert(0, "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo")
import reconstruir_plan as RP  # noqa: E402

P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um"
F, IR = RP.cargar_solver("red", 3)
off = (0.529, -0.041)   # offset del centro de los recortes de 200/400 px; casi no cambia el resultado
out = {}
for n in (20, 40, 80, 200, 400):
    geo = F.geometry(RP.Z_MM, offset_mm=off, crop=n)
    H = n * geo["factor"]
    dk = 1 / (H * geo["hrpx"])
    kc = geo["na"] / geo["lam"]
    Pm = F.circular_pupil((n, n), geo["lrpx"], geo["na"], geo["lam"])
    c = n // 2
    keys = sorted(geo["fxy"])
    err, flip, step = [], [], []
    fx_axis = (np.arange(H) - H // 2) * dk
    for k in keys:
        fx, fy = geo["fxy"][k]
        ys, xs = F.led_crop_window((H, H), geo["hrpx"], (n, n), fx, fy)
        cy, cx = ys.start + n // 2, xs.start + n // 2
        fxr, fyr = fx_axis[cx], fx_axis[cy]
        err.append(np.hypot(fxr - fx, fyr - fy))
        bf_exact = np.hypot(fx, fy) < kc
        # en el modelo, el DC del objeto cae en el píxel (c - dy, c - dx) de la ventana LR: BF si ese píxel está en la pupila
        dy, dx = cy - H // 2, cx - H // 2
        iy, ix = c - dy, c - dx
        bf_model = bool(0 <= iy < n and 0 <= ix < n and Pm[iy, ix])
        if bf_exact != bf_model:
            flip.append((k, "BF->DF" if bf_exact else "DF->BF", round(float(np.hypot(fx, fy) / kc), 3)))
    paso = 6.0 / RP.Z_MM / geo["lam"] * np.cos(0)   # paso aproximado de LED en k cerca del eje (6 mm / z / λ)
    paso = abs(geo["fxy"][(16, 15)][1] - geo["fxy"][(17, 15)][1])
    err = np.array(err)
    out[n] = dict(L_um=n * geo["lrpx"], dk=dk, pupila_bins=kc / dk, paso_led_bins=paso / dk,
                  err_med_bins=float(np.median(err / dk)), err_max_bins=float(err.max() / dk),
                  err_med_pct_paso=float(100 * np.median(err) / paso), err_max_pct_paso=float(100 * err.max() / paso),
                  err_max_pct_radio_pupila=float(100 * err.max() / kc),
                  pupila_px=int(Pm.sum()), pupila_area_cont=float(np.pi * (kc / dk) ** 2), leds_cambian=flip)
    o = out[n]
    print(f"n {n:3d} (L {o['L_um']:.0f} µm): dk {dk:.4f} 1/µm, pupila {o['pupila_bins']:.2f} bins ({o['pupila_px']} px vs "
          f"{o['pupila_area_cont']:.1f} continuo), paso LED {o['paso_led_bins']:.2f} bins; error redondeo mediana "
          f"{o['err_med_bins']:.2f} bins = {o['err_med_pct_paso']:.1f} % del paso, max {o['err_max_bins']:.2f} bins = "
          f"{o['err_max_pct_paso']:.1f} % del paso ({o['err_max_pct_radio_pupila']:.1f} % del radio de pupila); "
          f"LEDs que cambian BF/DF: {flip}")
json.dump({str(k): v for k, v in out.items()}, open(os.path.join(P0, "redondeo.json"), "w"), indent=1, default=str)

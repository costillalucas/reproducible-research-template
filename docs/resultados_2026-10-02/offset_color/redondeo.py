"""redondeo.py -- chequeo de código: posiciones espectrales (en píxeles de la grilla HR, dk = 1/512 µm^-1) de las LEDs de la
columna 15, error de redondeo de led_crop_window (round al bin entero) y bordes de pupila que caen cerca de k=0,
para el offset nominal y los del diagnóstico."""
import sys
sys.path.insert(0, "../iteraciones_2026-09-30")
import numpy as np, iter_runner as IR
F, R = IR._load("b_red")
dk = 1 / 512
for z, off in ((98, 3.0), (98, 3.9), (98, 4.06), (98, 4.2), (101, 4.06)):
    g = F.geometry(z, offset_mm=(0, off))
    rows = list(range(14, 22))
    fy = np.array([g["fxy"][(r, 15)][1] for r in rows]) / dk
    na = 0.07 / 0.63 / dk
    print(f"z {z} off {off}: filas {rows}\n  bins {np.round(fy, 2)}\n  err redondeo {np.round(fy - np.round(fy), 2)}"
          f"\n  bordes de pupila |k|<25 bins: {sorted(round(f + s * na, 2) for f in fy for s in (-1, 1) if abs(f + s * na) < 25)}")

"""calibracion_micrometro.py -- píxel en la muestra a partir de la foto de un micrómetro de platina (20/10).

La regla tiene líneas finas cada 0.01 mm dentro de una banda oscura, rayas cada 0.05 mm (cortas/largas alternadas).
Se mide el período de las líneas finas con una FFT 2D (incluye la inclinación de la regla) en la banda entera y en
cada mitad, y el de las rayas como control (debe ser 5 líneas finas). Imprime y guarda JSON.

Uso: python3 scripts/calibracion_micrometro.py IMAGEN.tiff [--banda R0 R1 C0 C1] [--filas-rayas R0 R1] [--sensor-um 3.2] [--out x.json]
Valores por defecto de --banda y --filas-rayas: la de pixelsizecalibracion.tiff (2026-10-16-calibracion/fila18_col15_colorr/5ms).
"""
import argparse
import json

import numpy as np
import tifffile


def periodo_2d(img, lo, hi):
    """Período (px) e inclinación (°) del pico de la FFT 2D con período horizontal entre lo y hi px."""
    c = img - img.mean()
    w = np.outer(np.hanning(c.shape[0]), np.hanning(c.shape[1]))
    n = 4096
    F = np.abs(np.fft.fft2(c * w, (n, n)))
    FX, FY = np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n))
    m = (FX > 1 / hi) & (FX < 1 / lo) & (abs(FY) < 0.03)
    i = np.unravel_index(np.argmax(np.where(m, F, 0)), F.shape)
    return float(1 / np.hypot(FX[i], FY[i])), float(np.degrees(np.arctan2(FY[i], FX[i])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imagen")
    ap.add_argument("--banda", nargs=4, type=int, default=[399, 445, 154, 924], metavar=("R0", "R1", "C0", "C1"))
    ap.add_argument("--filas-rayas", nargs=2, type=int, default=[483, 560], metavar=("R0", "R1"),
                    help="filas debajo de la banda, donde solo hay rayas")
    ap.add_argument("--division-um", type=float, default=10.0)
    ap.add_argument("--sensor-um", type=float, default=3.2)
    ap.add_argument("--out")
    a = ap.parse_args()
    img = tifffile.imread(a.imagen).astype(float)
    r0, r1, c0, c1 = a.banda
    cm = (c0 + c1) // 2
    res = {}
    for nombre, (x0, x1) in {"banda": (c0, c1), "mitad_izq": (c0, cm), "mitad_der": (cm, c1)}.items():
        p, ang = periodo_2d(img[r0:r1, x0:x1], 5, 12)
        res[nombre] = dict(periodo_px=p, inclinacion_grados=ang)
    p_rayas, _ = periodo_2d(img[a.filas_rayas[0]:a.filas_rayas[1], c0:c1], 30, 50)
    p = res["banda"]["periodo_px"]
    res.update(periodo_rayas_px=p_rayas, lineas_por_raya=p_rayas / p, um_por_px=a.division_um / p,
               aumento=a.sensor_um / (a.division_um / p), campo_um=img.shape[1] * a.division_um / p,
               dif_mitades_rel=abs(res["mitad_izq"]["periodo_px"] - res["mitad_der"]["periodo_px"]) / p,
               imagen=a.imagen, banda=a.banda, division_um=a.division_um, sensor_um=a.sensor_um)
    for k, v in res.items():
        print(k, v)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()

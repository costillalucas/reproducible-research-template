# Zonas 3x3 -- 2026-10-20-muestra

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-20-luzsinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-20-muestrasinluz` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-20-muestrasinluz`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-20-muestra | [-1, -1] | A | 9.180 | 7.489 | 6.9 % | 7.97 9.26 8.03 7.97 8.01 | 40.12/49.18 | 0.071 |
| 2026-10-20-muestra | [-1, -1] | B | 12.947 | 7.028 | 4.4 % | 9.19 8.40 9.30 9.32 9.34 | 26.87/49.49 | 0.077 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-20-muestra | (+0.294, -0.002) | 4161 | 1.1760 | 91 | 7.056 | 3440 | 4041 | 1.1746 | 7.048 | 7.03–7.09 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 9.1802 | — | — | 9.1802 | 9.1802 |
| espectral_A_col | 1 | 7.4885 | — | — | 7.4885 | 7.4885 |
| espectral_B_fila | 1 | 12.9466 | — | — | 12.9466 | 12.9466 |
| espectral_B_col | 1 | 7.0281 | — | — | 7.0281 | 7.0281 |
| espectral_A_sd_rel | 1 | 0.0689 | — | — | 0.0689 | 0.0689 |
| espectral_B_sd_rel | 1 | 0.0441 | — | — | 0.0441 | 0.0441 |
| borde_sfijo_NAz | 1 | 7.0562 | — | — | 7.0562 | 7.0562 |
| borde_sfijo_R_pasos | 1 | 1.1760 | — | — | 1.1760 | 1.1760 |
| borde_sfijo_w_px | 1 | 90.6620 | — | — | 90.6620 | 90.6620 |
| borde_slibre_NAz | 1 | 7.0476 | — | — | 7.0476 | 7.0476 |
| borde_slibre_s | 1 | 3440.0431 | — | — | 3440.0431 | 3440.0431 |
| eje_a_fila | 1 | 0.2943 | — | — | 0.2943 | 0.2943 |
| eje_a_col | 1 | -0.0018 | — | — | -0.0018 | -0.0018 |
| contraste_A | 1 | 0.0714 | — | — | 0.0714 | 0.0714 |
| contraste_B | 1 | 0.0770 | — | — | 0.0770 | 0.0770 |

Generado 2026-11-06 13:32 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-20-muestra --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-20-luzsinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-20-muestrasinluz --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-20-muestrasinluz --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-20-muestra`.

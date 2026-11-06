# Zonas 3x3 -- 2026-11-03-red-p1608

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-prueba-1608-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-11-03-red-p1608 | [3968, 1966] | A | 6.952 | 6.918 | 3.3 % | 6.53 7.04 7.01 7.07 7.02 | 50.43/50.68 | 0.110 |
| 2026-11-03-red-p1608 | [3968, 1966] | B | 6.984 | 7.180 | 2.1 % | 6.85 7.06 7.08 7.26 7.15 | 50.37/48.99 | 0.125 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-03-red-p1608 | (+0.076, -0.029) | 4364 | 1.2334 | 222 | 7.400 | 2869 | 3584 | 1.2492 | 7.495 | 7.25–7.46 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 6.9520 | — | — | 6.9520 | 6.9520 |
| espectral_A_col | 1 | 6.9177 | — | — | 6.9177 | 6.9177 |
| espectral_B_fila | 1 | 6.9844 | — | — | 6.9844 | 6.9844 |
| espectral_B_col | 1 | 7.1804 | — | — | 7.1804 | 7.1804 |
| espectral_A_sd_rel | 1 | 0.0326 | — | — | 0.0326 | 0.0326 |
| espectral_B_sd_rel | 1 | 0.0211 | — | — | 0.0211 | 0.0211 |
| borde_sfijo_NAz | 1 | 7.4004 | — | — | 7.4004 | 7.4004 |
| borde_sfijo_R_pasos | 1 | 1.2334 | — | — | 1.2334 | 1.2334 |
| borde_sfijo_w_px | 1 | 222.0527 | — | — | 222.0527 | 222.0527 |
| borde_slibre_NAz | 1 | 7.4953 | — | — | 7.4953 | 7.4953 |
| borde_slibre_s | 1 | 2869.1524 | — | — | 2869.1524 | 2869.1524 |
| eje_a_fila | 1 | 0.0762 | — | — | 0.0762 | 0.0762 |
| eje_a_col | 1 | -0.0293 | — | — | -0.0293 | -0.0293 |
| contraste_A | 1 | 0.1104 | — | — | 0.1104 | 0.1104 |
| contraste_B | 1 | 0.1253 | — | — | 0.1253 | 0.1253 |

Generado 2026-11-06 13:30 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-11-03-red-p1608 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-prueba-1608-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-11-03-red-p1608`.

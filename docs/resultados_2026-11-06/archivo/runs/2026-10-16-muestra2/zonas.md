# Zonas 3x3 -- 2026-10-16-muestra2

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-16-luzsinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-16-muestrasinluz2` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-16-muestrasinluz2`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-16-muestra2 | [-1, -1] | A | 9.864 | 7.363 | 6.5 % | 8.22 9.41 8.14 8.18 8.20 | 37.18/49.80 | 0.145 |
| 2026-10-16-muestra2 | [-1, -1] | B | 8.167 | 7.209 | 1.2 % | 7.77 7.68 7.65 7.66 7.52 | 43.74/49.55 | 0.147 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-16-muestra2 | (+0.355, +0.012) | 4140 | 1.1701 | 82 | 7.020 | 3857 | 4498 | 1.1663 | 6.998 | 6.99–7.04 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 9.8636 | — | — | 9.8636 | 9.8636 |
| espectral_A_col | 1 | 7.3633 | — | — | 7.3633 | 7.3633 |
| espectral_B_fila | 1 | 8.1666 | — | — | 8.1666 | 8.1666 |
| espectral_B_col | 1 | 7.2087 | — | — | 7.2087 | 7.2087 |
| espectral_A_sd_rel | 1 | 0.0652 | — | — | 0.0652 | 0.0652 |
| espectral_B_sd_rel | 1 | 0.0117 | — | — | 0.0117 | 0.0117 |
| borde_sfijo_NAz | 1 | 7.0204 | — | — | 7.0204 | 7.0204 |
| borde_sfijo_R_pasos | 1 | 1.1701 | — | — | 1.1701 | 1.1701 |
| borde_sfijo_w_px | 1 | 82.2359 | — | — | 82.2359 | 82.2359 |
| borde_slibre_NAz | 1 | 6.9978 | — | — | 6.9978 | 6.9978 |
| borde_slibre_s | 1 | 3856.8711 | — | — | 3856.8711 | 3856.8711 |
| eje_a_fila | 1 | 0.3549 | — | — | 0.3549 | 0.3549 |
| eje_a_col | 1 | 0.0119 | — | — | 0.0119 | 0.0119 |
| contraste_A | 1 | 0.1455 | — | — | 0.1455 | 0.1455 |
| contraste_B | 1 | 0.1473 | — | — | 0.1473 | 0.1473 |

Generado 2026-11-06 13:33 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-16-muestra2 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-16-luzsinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-16-muestrasinluz2 --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-16-muestrasinluz2 --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-16-muestra2`.

# Zonas 3x3 -- 2026-10-23-p1326

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-prueba-1326-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-23-p1326 | [4000, 1942] | A | 8.040 | 7.570 | 4.9 % | 7.90 7.52 7.50 7.67 8.41 | 46.24/49.12 | 0.128 |
| 2026-10-23-p1326 | [4000, 1942] | B | 7.173 | 7.200 | 1.2 % | 7.03 7.23 7.23 7.20 7.25 | 49.68/49.49 | 0.117 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-23-p1326 | (+0.093, -0.006) | 4235 | 1.1971 | 226 | 7.183 | 2296 | 2675 | 1.1650 | 6.990 | 6.92–7.25 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 8.0404 | — | — | 8.0404 | 8.0404 |
| espectral_A_col | 1 | 7.5698 | — | — | 7.5698 | 7.5698 |
| espectral_B_fila | 1 | 7.1725 | — | — | 7.1725 | 7.1725 |
| espectral_B_col | 1 | 7.1997 | — | — | 7.1997 | 7.1997 |
| espectral_A_sd_rel | 1 | 0.0486 | — | — | 0.0486 | 0.0486 |
| espectral_B_sd_rel | 1 | 0.0120 | — | — | 0.0120 | 0.0120 |
| borde_sfijo_NAz | 1 | 7.1828 | — | — | 7.1828 | 7.1828 |
| borde_sfijo_R_pasos | 1 | 1.1971 | — | — | 1.1971 | 1.1971 |
| borde_sfijo_w_px | 1 | 226.1568 | — | — | 226.1568 | 226.1568 |
| borde_slibre_NAz | 1 | 6.9901 | — | — | 6.9901 | 6.9901 |
| borde_slibre_s | 1 | 2296.3178 | — | — | 2296.3178 | 2296.3178 |
| eje_a_fila | 1 | 0.0926 | — | — | 0.0926 | 0.0926 |
| eje_a_col | 1 | -0.0064 | — | — | -0.0064 | -0.0064 |
| contraste_A | 1 | 0.1281 | — | — | 0.1281 | 0.1281 |
| contraste_B | 1 | 0.1166 | — | — | 0.1166 | 0.1166 |

Generado 2026-11-06 13:21 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-23-p1326 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-prueba-1326-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-23-p1326`.

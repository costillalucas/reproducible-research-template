# Zonas 3x3 -- 2026-10-30-red-c-flatp1322

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1322`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1322-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1322-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-30-red-c-flatp1322 | [3968, 1966] | A | 6.703 | 5.593 | 4.8 % | 5.93 6.00 6.62 5.93 6.00 | 43.80/52.49 | 0.017 |
| 2026-10-30-red-c-flatp1322 | [3968, 1966] | B | 6.553 | 6.571 | 0.6 % | 6.53 6.61 6.53 6.53 6.61 | 43.80/43.68 | 0.033 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-30-red-c-flatp1322 | (+0.129, -0.015) | 4259 | 1.2038 | 209 | 7.223 | 2043 | 2405 | 1.1772 | 7.063 | 6.96–7.31 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 6.7026 | — | — | 6.7026 | 6.7026 |
| espectral_A_col | 1 | 5.5933 | — | — | 5.5933 | 5.5933 |
| espectral_B_fila | 1 | 6.5525 | — | — | 6.5525 | 6.5525 |
| espectral_B_col | 1 | 6.5713 | — | — | 6.5713 | 6.5713 |
| espectral_A_sd_rel | 1 | 0.0479 | — | — | 0.0479 | 0.0479 |
| espectral_B_sd_rel | 1 | 0.0063 | — | — | 0.0063 | 0.0063 |
| borde_sfijo_NAz | 1 | 7.2228 | — | — | 7.2228 | 7.2228 |
| borde_sfijo_R_pasos | 1 | 1.2038 | — | — | 1.2038 | 1.2038 |
| borde_sfijo_w_px | 1 | 208.7279 | — | — | 208.7279 | 208.7279 |
| borde_slibre_NAz | 1 | 7.0632 | — | — | 7.0632 | 7.0632 |
| borde_slibre_s | 1 | 2042.9780 | — | — | 2042.9780 | 2042.9780 |
| eje_a_fila | 1 | 0.1287 | — | — | 0.1287 | 0.1287 |
| eje_a_col | 1 | -0.0153 | — | — | -0.0153 | -0.0153 |
| contraste_A | 1 | 0.0168 | — | — | 0.0168 | 0.0168 |
| contraste_B | 1 | 0.0326 | — | — | 0.0326 | 0.0326 |

Generado 2026-11-06 13:27 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-30-red-c-flatp1322 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1322 --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1322-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1322-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-30-red-c-flatp1322`.

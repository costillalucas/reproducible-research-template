# Zonas 3x3 -- 2026-10-30-red-c-flatp1331

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1331`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1331-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1331-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-30-red-c-flatp1331 | [3968, 1966] | A | 6.553 | 6.571 | 0.6 % | 6.53 6.61 6.53 6.53 6.61 | 43.80/43.68 | 0.046 |
| 2026-10-30-red-c-flatp1331 | [3968, 1966] | B | 6.553 | 6.571 | 0.6 % | 6.53 6.61 6.53 6.53 6.61 | 43.80/43.68 | 0.076 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-30-red-c-flatp1331 | (+0.117, -0.004) | 4233 | 1.1965 | 217 | 7.179 | 2164 | 2519 | 1.1637 | 6.982 | 6.95–7.23 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 6.5525 | — | — | 6.5525 | 6.5525 |
| espectral_A_col | 1 | 6.5713 | — | — | 6.5713 | 6.5713 |
| espectral_B_fila | 1 | 6.5525 | — | — | 6.5525 | 6.5525 |
| espectral_B_col | 1 | 6.5713 | — | — | 6.5713 | 6.5713 |
| espectral_A_sd_rel | 1 | 0.0063 | — | — | 0.0063 | 0.0063 |
| espectral_B_sd_rel | 1 | 0.0063 | — | — | 0.0063 | 0.0063 |
| borde_sfijo_NAz | 1 | 7.1790 | — | — | 7.1790 | 7.1790 |
| borde_sfijo_R_pasos | 1 | 1.1965 | — | — | 1.1965 | 1.1965 |
| borde_sfijo_w_px | 1 | 217.4345 | — | — | 217.4345 | 217.4345 |
| borde_slibre_NAz | 1 | 6.9824 | — | — | 6.9824 | 6.9824 |
| borde_slibre_s | 1 | 2164.1669 | — | — | 2164.1669 | 2164.1669 |
| eje_a_fila | 1 | 0.1171 | — | — | 0.1171 | 0.1171 |
| eje_a_col | 1 | -0.0039 | — | — | -0.0039 | -0.0039 |
| contraste_A | 1 | 0.0456 | — | — | 0.0456 | 0.0456 |
| contraste_B | 1 | 0.0764 | — | — | 0.0764 | 0.0764 |

Generado 2026-11-06 13:29 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-30-red-c-flatp1331 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1331 --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1331-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-prueba-1331-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-30-red-c-flatp1331`.

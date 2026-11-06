# Zonas 3x3 -- 2026-11-03-red

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-11-03-red | [3968, 1966] | A | 7.007 | 6.938 | 2.1 % | 6.72 7.05 7.00 7.06 7.03 | 50.37/50.87 | 0.108 |
| 2026-11-03-red | [3968, 1966] | B | 6.910 | 7.057 | 0.4 % | 7.01 6.97 6.99 6.94 7.01 | 50.87/49.80 | 0.123 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-03-red | (+0.073, -0.028) | 4364 | 1.2334 | 222 | 7.401 | 2950 | 3682 | 1.2483 | 7.490 | 7.26–7.45 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.0069 | — | — | 7.0069 | 7.0069 |
| espectral_A_col | 1 | 6.9380 | — | — | 6.9380 | 6.9380 |
| espectral_B_fila | 1 | 6.9099 | — | — | 6.9099 | 6.9099 |
| espectral_B_col | 1 | 7.0573 | — | — | 7.0573 | 7.0573 |
| espectral_A_sd_rel | 1 | 0.0206 | — | — | 0.0206 | 0.0206 |
| espectral_B_sd_rel | 1 | 0.0039 | — | — | 0.0039 | 0.0039 |
| borde_sfijo_NAz | 1 | 7.4005 | — | — | 7.4005 | 7.4005 |
| borde_sfijo_R_pasos | 1 | 1.2334 | — | — | 1.2334 | 1.2334 |
| borde_sfijo_w_px | 1 | 221.9440 | — | — | 221.9440 | 221.9440 |
| borde_slibre_NAz | 1 | 7.4895 | — | — | 7.4895 | 7.4895 |
| borde_slibre_s | 1 | 2949.8025 | — | — | 2949.8025 | 2949.8025 |
| eje_a_fila | 1 | 0.0727 | — | — | 0.0727 | 0.0727 |
| eje_a_col | 1 | -0.0282 | — | — | -0.0282 | -0.0282 |
| contraste_A | 1 | 0.1081 | — | — | 0.1081 | 0.1081 |
| contraste_B | 1 | 0.1233 | — | — | 0.1233 | 0.1233 |

Generado 2026-11-06 13:29 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-11-03-red --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-03-red-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-11-03-red`.

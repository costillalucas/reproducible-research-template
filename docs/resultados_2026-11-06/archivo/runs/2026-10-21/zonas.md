# Zonas 3x3 -- 2026-10-21

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-21 | [-1, -1] | A | 7.531 | 6.708 | 7.6 % | 6.40 7.55 7.69 7.12 6.72 | 43.80/49.18 | 0.016 |
| 2026-10-21 | [-1, -1] | B | 10.870 | 8.816 | 9.4 % | 8.60 10.71 10.36 10.05 8.97 | 30.05/37.05 | 0.031 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-21 | (+0.107, -0.019) | 4233 | 1.1964 | 199 | 7.178 | 2156 | 2526 | 1.1713 | 7.028 | 6.96–7.23 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.5312 | — | — | 7.5312 | 7.5312 |
| espectral_A_col | 1 | 6.7081 | — | — | 6.7081 | 6.7081 |
| espectral_B_fila | 1 | 10.8695 | — | — | 10.8695 | 10.8695 |
| espectral_B_col | 1 | 8.8161 | — | — | 8.8161 | 8.8161 |
| espectral_A_sd_rel | 1 | 0.0765 | — | — | 0.0765 | 0.0765 |
| espectral_B_sd_rel | 1 | 0.0935 | — | — | 0.0935 | 0.0935 |
| borde_sfijo_NAz | 1 | 7.1784 | — | — | 7.1784 | 7.1784 |
| borde_sfijo_R_pasos | 1 | 1.1964 | — | — | 1.1964 | 1.1964 |
| borde_sfijo_w_px | 1 | 199.4561 | — | — | 199.4561 | 199.4561 |
| borde_slibre_NAz | 1 | 7.0278 | — | — | 7.0278 | 7.0278 |
| borde_slibre_s | 1 | 2156.3067 | — | — | 2156.3067 | 2156.3067 |
| eje_a_fila | 1 | 0.1072 | — | — | 0.1072 | 0.1072 |
| eje_a_col | 1 | -0.0189 | — | — | -0.0189 | -0.0189 |
| contraste_A | 1 | 0.0164 | — | — | 0.0164 | 0.0164 |
| contraste_B | 1 | 0.0315 | — | — | 0.0315 | 0.0315 |

Generado 2026-11-06 13:38 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-21 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-21`.

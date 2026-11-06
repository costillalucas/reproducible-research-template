# Zonas 3x3 -- 2026-10-02-viejo

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-02_red_sin_muestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-02_red_oscura` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-02_red_oscura`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-02-viejo | [-1, -1] | A | 9.364 | 7.328 | 7.4 % | 7.90 9.31 7.95 7.97 7.98 | 38.93/49.74 | 0.047 |
| 2026-10-02-viejo | [-1, -1] | B | 10.837 | 7.098 | 6.8 % | 7.95 9.54 8.44 8.50 8.46 | 32.99/50.37 | 0.052 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-02-viejo | (+0.247, -0.003) | 4142 | 1.1707 | 99 | 7.024 | 3303 | 3857 | 1.1676 | 7.006 | 7.00–7.05 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 9.3635 | — | — | 9.3635 | 9.3635 |
| espectral_A_col | 1 | 7.3281 | — | — | 7.3281 | 7.3281 |
| espectral_B_fila | 1 | 10.8366 | — | — | 10.8366 | 10.8366 |
| espectral_B_col | 1 | 7.0983 | — | — | 7.0983 | 7.0983 |
| espectral_A_sd_rel | 1 | 0.0741 | — | — | 0.0741 | 0.0741 |
| espectral_B_sd_rel | 1 | 0.0683 | — | — | 0.0683 | 0.0683 |
| borde_sfijo_NAz | 1 | 7.0245 | — | — | 7.0245 | 7.0245 |
| borde_sfijo_R_pasos | 1 | 1.1707 | — | — | 1.1707 | 1.1707 |
| borde_sfijo_w_px | 1 | 99.3680 | — | — | 99.3680 | 99.3680 |
| borde_slibre_NAz | 1 | 7.0057 | — | — | 7.0057 | 7.0057 |
| borde_slibre_s | 1 | 3303.1792 | — | — | 3303.1792 | 3303.1792 |
| eje_a_fila | 1 | 0.2468 | — | — | 0.2468 | 0.2468 |
| eje_a_col | 1 | -0.0032 | — | — | -0.0032 | -0.0032 |
| contraste_A | 1 | 0.0472 | — | — | 0.0472 | 0.0472 |
| contraste_B | 1 | 0.0520 | — | — | 0.0520 | 0.0520 |

Generado 2026-11-06 13:32 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-02-viejo --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-02_red_sin_muestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-02_red_oscura --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-02_red_oscura --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-02-viejo`.

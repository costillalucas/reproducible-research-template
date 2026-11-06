# Zonas 3x3 -- 2026-10-22

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-22 | [4000, 1942] | A | 7.006 | 7.032 | 2.0 % | 6.77 7.03 7.08 7.10 7.11 | 50.93/50.74 | 0.200 |
| 2026-10-22 | [4000, 1942] | B | 7.059 | 7.130 | 1.4 % | 6.93 7.12 7.11 7.17 7.14 | 50.68/50.18 | 0.214 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-22 | (+0.088, +0.001) | 4174 | 1.1797 | 221 | 7.078 | 2462 | 2898 | 1.1769 | 7.061 | 6.93–7.19 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.0057 | — | — | 7.0057 | 7.0057 |
| espectral_A_col | 1 | 7.0316 | — | — | 7.0316 | 7.0316 |
| espectral_B_fila | 1 | 7.0593 | — | — | 7.0593 | 7.0593 |
| espectral_B_col | 1 | 7.1296 | — | — | 7.1296 | 7.1296 |
| espectral_A_sd_rel | 1 | 0.0201 | — | — | 0.0201 | 0.0201 |
| espectral_B_sd_rel | 1 | 0.0135 | — | — | 0.0135 | 0.0135 |
| borde_sfijo_NAz | 1 | 7.0781 | — | — | 7.0781 | 7.0781 |
| borde_sfijo_R_pasos | 1 | 1.1797 | — | — | 1.1797 | 1.1797 |
| borde_sfijo_w_px | 1 | 221.4155 | — | — | 221.4155 | 221.4155 |
| borde_slibre_NAz | 1 | 7.0612 | — | — | 7.0612 | 7.0612 |
| borde_slibre_s | 1 | 2462.0973 | — | — | 2462.0973 | 2462.0973 |
| eje_a_fila | 1 | 0.0879 | — | — | 0.0879 | 0.0879 |
| eje_a_col | 1 | 0.0010 | — | — | 0.0010 | 0.0010 |
| contraste_A | 1 | 0.2001 | — | — | 0.2001 | 0.2001 |
| contraste_B | 1 | 0.2140 | — | — | 0.2140 | 0.2140 |

Generado 2026-11-06 13:15 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-22 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-22`.

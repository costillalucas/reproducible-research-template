# Zonas 3x3 -- 2026-10-09-muestra

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-09-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-09-muestrasinluz` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-09-muestrasinluz`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-09-muestra | [-1, -1] | A | 12.235 | 6.988 | 7.7 % | 9.12 7.67 9.20 9.20 9.29 | 28.05/49.12 | 0.082 |
| 2026-10-09-muestra | [-1, -1] | B | 11.379 | 7.463 | 3.1 % | 9.39 9.24 8.85 8.87 8.73 | 31.93/48.68 | 0.127 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-09-muestra | (+0.384, +0.037) | 4152 | 1.1736 | 88 | 7.042 | 4043 | 4717 | 1.1665 | 6.999 | 7.00–7.06 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 12.2346 | — | — | 12.2346 | 12.2346 |
| espectral_A_col | 1 | 6.9881 | — | — | 6.9881 | 6.9881 |
| espectral_B_fila | 1 | 11.3788 | — | — | 11.3788 | 11.3788 |
| espectral_B_col | 1 | 7.4635 | — | — | 7.4635 | 7.4635 |
| espectral_A_sd_rel | 1 | 0.0774 | — | — | 0.0774 | 0.0774 |
| espectral_B_sd_rel | 1 | 0.0315 | — | — | 0.0315 | 0.0315 |
| borde_sfijo_NAz | 1 | 7.0418 | — | — | 7.0418 | 7.0418 |
| borde_sfijo_R_pasos | 1 | 1.1736 | — | — | 1.1736 | 1.1736 |
| borde_sfijo_w_px | 1 | 87.7065 | — | — | 87.7065 | 87.7065 |
| borde_slibre_NAz | 1 | 6.9991 | — | — | 6.9991 | 6.9991 |
| borde_slibre_s | 1 | 4043.3695 | — | — | 4043.3695 | 4043.3695 |
| eje_a_fila | 1 | 0.3843 | — | — | 0.3843 | 0.3843 |
| eje_a_col | 1 | 0.0368 | — | — | 0.0368 | 0.0368 |
| contraste_A | 1 | 0.0818 | — | — | 0.0818 | 0.0818 |
| contraste_B | 1 | 0.1273 | — | — | 0.1273 | 0.1273 |

Generado 2026-11-06 13:33 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-09-muestra --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-09-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-09-muestrasinluz --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-09-muestrasinluz --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-09-muestra`.

# Zonas 3x3 -- 2026-10-22-p1758

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-prueba-1758-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-22-p1758 | [4000, 1942] | A | 7.011 | 7.063 | 1.9 % | 6.80 7.06 7.12 7.10 7.11 | 50.80/50.43 | 0.204 |
| 2026-10-22-p1758 | [4000, 1942] | B | 7.068 | 7.148 | 1.3 % | 6.94 7.13 7.13 7.18 7.16 | 50.55/49.99 | 0.218 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-22-p1758 | (+0.088, +0.000) | 4172 | 1.1791 | 223 | 7.075 | 2447 | 2879 | 1.1763 | 7.058 | 6.93–7.18 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.0113 | — | — | 7.0113 | 7.0113 |
| espectral_A_col | 1 | 7.0634 | — | — | 7.0634 | 7.0634 |
| espectral_B_fila | 1 | 7.0684 | — | — | 7.0684 | 7.0684 |
| espectral_B_col | 1 | 7.1479 | — | — | 7.1479 | 7.1479 |
| espectral_A_sd_rel | 1 | 0.0189 | — | — | 0.0189 | 0.0189 |
| espectral_B_sd_rel | 1 | 0.0133 | — | — | 0.0133 | 0.0133 |
| borde_sfijo_NAz | 1 | 7.0749 | — | — | 7.0749 | 7.0749 |
| borde_sfijo_R_pasos | 1 | 1.1791 | — | — | 1.1791 | 1.1791 |
| borde_sfijo_w_px | 1 | 222.5171 | — | — | 222.5171 | 222.5171 |
| borde_slibre_NAz | 1 | 7.0579 | — | — | 7.0579 | 7.0579 |
| borde_slibre_s | 1 | 2447.0996 | — | — | 2447.0996 | 2447.0996 |
| eje_a_fila | 1 | 0.0878 | — | — | 0.0878 | 0.0878 |
| eje_a_col | 1 | 0.0001 | — | — | 0.0001 | 0.0001 |
| contraste_A | 1 | 0.2043 | — | — | 0.2043 | 0.2043 |
| contraste_B | 1 | 0.2181 | — | — | 0.2181 | 0.2181 |

Generado 2026-11-06 13:20 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-22-p1758 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-prueba-1758-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-22-p1758`.

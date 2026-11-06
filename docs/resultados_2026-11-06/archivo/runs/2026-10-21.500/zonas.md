# Zonas 3x3 -- 2026-10-21.500

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-21.500 | [-1, -1] | A | 7.061 | 7.122 | 0.3 % | 7.10 7.05 7.10 7.10 7.10 | 50.80/50.37 | 0.210 |
| 2026-10-21.500 | [-1, -1] | B | 7.044 | 7.132 | 1.4 % | 6.91 7.14 7.11 7.14 7.14 | 50.62/49.99 | 0.253 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-21.500 | (+0.074, +0.014) | 4180 | 1.1814 | 236 | 7.088 | 2639 | 3104 | 1.1762 | 7.057 | 6.93–7.14 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.0607 | — | — | 7.0607 | 7.0607 |
| espectral_A_col | 1 | 7.1220 | — | — | 7.1220 | 7.1220 |
| espectral_B_fila | 1 | 7.0443 | — | — | 7.0443 | 7.0443 |
| espectral_B_col | 1 | 7.1324 | — | — | 7.1324 | 7.1324 |
| espectral_A_sd_rel | 1 | 0.0034 | — | — | 0.0034 | 0.0034 |
| espectral_B_sd_rel | 1 | 0.0142 | — | — | 0.0142 | 0.0142 |
| borde_sfijo_NAz | 1 | 7.0884 | — | — | 7.0884 | 7.0884 |
| borde_sfijo_R_pasos | 1 | 1.1814 | — | — | 1.1814 | 1.1814 |
| borde_sfijo_w_px | 1 | 236.1105 | — | — | 236.1105 | 236.1105 |
| borde_slibre_NAz | 1 | 7.0574 | — | — | 7.0574 | 7.0574 |
| borde_slibre_s | 1 | 2638.5210 | — | — | 2638.5210 | 2638.5210 |
| eje_a_fila | 1 | 0.0744 | — | — | 0.0744 | 0.0744 |
| eje_a_col | 1 | 0.0137 | — | — | 0.0137 | 0.0137 |
| contraste_A | 1 | 0.2100 | — | — | 0.2100 | 0.2100 |
| contraste_B | 1 | 0.2530 | — | — | 0.2530 | 0.2530 |

Generado 2026-11-06 13:38 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-21.500 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-21-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-21.500`.

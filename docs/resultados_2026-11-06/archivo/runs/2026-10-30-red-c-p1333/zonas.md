# Zonas 3x3 -- 2026-10-30-red-c-p1333

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-prueba-1333-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-30-red-c-p1333 | [3968, 1966] | A | 7.263 | 7.217 | 1.5 % | 7.42 7.20 7.17 7.15 7.25 | 49.37/49.68 | 0.071 |
| 2026-10-30-red-c-p1333 | [3968, 1966] | B | 7.130 | 7.042 | 1.2 % | 6.99 7.14 7.00 7.15 7.15 | 49.68/50.30 | 0.112 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-30-red-c-p1333 | (+0.117, -0.004) | 4234 | 1.1968 | 217 | 7.181 | 2167 | 2522 | 1.1639 | 6.984 | 6.95–7.23 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.2627 | — | — | 7.2627 | 7.2627 |
| espectral_A_col | 1 | 7.2170 | — | — | 7.2170 | 7.2170 |
| espectral_B_fila | 1 | 7.1303 | — | — | 7.1303 | 7.1303 |
| espectral_B_col | 1 | 7.0417 | — | — | 7.0417 | 7.0417 |
| espectral_A_sd_rel | 1 | 0.0152 | — | — | 0.0152 | 0.0152 |
| espectral_B_sd_rel | 1 | 0.0117 | — | — | 0.0117 | 0.0117 |
| borde_sfijo_NAz | 1 | 7.1809 | — | — | 7.1809 | 7.1809 |
| borde_sfijo_R_pasos | 1 | 1.1968 | — | — | 1.1968 | 1.1968 |
| borde_sfijo_w_px | 1 | 216.8944 | — | — | 216.8944 | 216.8944 |
| borde_slibre_NAz | 1 | 6.9836 | — | — | 6.9836 | 6.9836 |
| borde_slibre_s | 1 | 2167.0554 | — | — | 2167.0554 | 2167.0554 |
| eje_a_fila | 1 | 0.1173 | — | — | 0.1173 | 0.1173 |
| eje_a_col | 1 | -0.0038 | — | — | -0.0038 | -0.0038 |
| contraste_A | 1 | 0.0711 | — | — | 0.0711 | 0.0711 |
| contraste_B | 1 | 0.1124 | — | — | 0.1124 | 0.1124 |

Generado 2026-11-06 13:26 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-30-red-c-p1333 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-prueba-1333-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-30-red-c-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-30-red-c-p1333`.

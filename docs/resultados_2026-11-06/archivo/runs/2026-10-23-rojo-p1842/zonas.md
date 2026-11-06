# Zonas 3x3 -- 2026-10-23-rojo-p1842

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-rojo-prueba-1842-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-23-rojo-p1842 | [4000, 1942] | A | 7.118 | 7.100 | 1.7 % | 6.90 7.13 7.14 7.15 7.22 | 50.30/50.43 | 0.197 |
| 2026-10-23-rojo-p1842 | [4000, 1942] | B | 7.067 | 7.067 | 0.5 % | 7.02 7.10 7.04 7.09 7.09 | 50.55/50.55 | 0.229 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-23-rojo-p1842 | (+0.093, -0.004) | 4187 | 1.1836 | 234 | 7.101 | 2508 | 2928 | 1.1674 | 7.004 | 6.92–7.20 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.1178 | — | — | 7.1178 | 7.1178 |
| espectral_A_col | 1 | 7.1002 | — | — | 7.1002 | 7.1002 |
| espectral_B_fila | 1 | 7.0672 | — | — | 7.0672 | 7.0672 |
| espectral_B_col | 1 | 7.0672 | — | — | 7.0672 | 7.0672 |
| espectral_A_sd_rel | 1 | 0.0170 | — | — | 0.0170 | 0.0170 |
| espectral_B_sd_rel | 1 | 0.0051 | — | — | 0.0051 | 0.0051 |
| borde_sfijo_NAz | 1 | 7.1014 | — | — | 7.1014 | 7.1014 |
| borde_sfijo_R_pasos | 1 | 1.1836 | — | — | 1.1836 | 1.1836 |
| borde_sfijo_w_px | 1 | 234.0554 | — | — | 234.0554 | 234.0554 |
| borde_slibre_NAz | 1 | 7.0042 | — | — | 7.0042 | 7.0042 |
| borde_slibre_s | 1 | 2507.9264 | — | — | 2507.9264 | 2507.9264 |
| eje_a_fila | 1 | 0.0935 | — | — | 0.0935 | 0.0935 |
| eje_a_col | 1 | -0.0044 | — | — | -0.0044 | -0.0044 |
| contraste_A | 1 | 0.1968 | — | — | 0.1968 | 0.1968 |
| contraste_B | 1 | 0.2286 | — | — | 0.2286 | 0.2286 |

Generado 2026-11-06 13:25 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-23-rojo-p1842 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-rojo-prueba-1842-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-23-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-23-rojo-p1842`.

# Zonas 3x3 -- 2026-10-22-p1745

Flat `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra`, oscuros `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-prueba-1745-dark` / `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra-dark`, color `r`. NA·z en mm. Espectral = etapa 1 radio libre (`espectral_zonas.py`); borde = (a) de `centrado.py` (NA·z = R_pasos·6). Recorte A = 360:760, 80:480; B = 360:760, 480:880.

## Espectral

| zona | ROI | rec | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) | paso filas/cols (bins) | contraste rms_hp |
|---|---|---|---|---|---|---|---|---|
| 2026-10-22-p1745 | [4000, 1942] | A | 7.019 | 7.046 | 2.8 % | 6.68 7.09 7.14 7.12 7.12 | 50.62/50.43 | 0.183 |
| 2026-10-22-p1745 | [4000, 1942] | B | 7.086 | 7.210 | 0.6 % | 7.09 7.14 7.19 7.19 7.12 | 50.74/49.87 | 0.201 |

## Borde (a)

| zona | eje (a) (pasos) | s fijo: R px | R pasos | w px | NA·z | s libre: s | R px | R/s pasos | NA·z | LOO NA·z min–max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-22-p1745 | (+0.088, -0.001) | 4181 | 1.1818 | 223 | 7.091 | 2421 | 2845 | 1.1750 | 7.050 | 6.94–7.19 |

## Resumen entre zonas

| métrica | n | media | sd | sd rel | min | max |
|---|---|---|---|---|---|---|
| espectral_A_fila | 1 | 7.0195 | — | — | 7.0195 | 7.0195 |
| espectral_A_col | 1 | 7.0456 | — | — | 7.0456 | 7.0456 |
| espectral_B_fila | 1 | 7.0859 | — | — | 7.0859 | 7.0859 |
| espectral_B_col | 1 | 7.2103 | — | — | 7.2103 | 7.2103 |
| espectral_A_sd_rel | 1 | 0.0278 | — | — | 0.0278 | 0.0278 |
| espectral_B_sd_rel | 1 | 0.0058 | — | — | 0.0058 | 0.0058 |
| borde_sfijo_NAz | 1 | 7.0911 | — | — | 7.0911 | 7.0911 |
| borde_sfijo_R_pasos | 1 | 1.1818 | — | — | 1.1818 | 1.1818 |
| borde_sfijo_w_px | 1 | 223.1967 | — | — | 223.1967 | 223.1967 |
| borde_slibre_NAz | 1 | 7.0503 | — | — | 7.0503 | 7.0503 |
| borde_slibre_s | 1 | 2421.4179 | — | — | 2421.4179 | 2421.4179 |
| eje_a_fila | 1 | 0.0875 | — | — | 0.0875 | 0.0875 |
| eje_a_col | 1 | -0.0015 | — | — | -0.0015 | -0.0015 |
| contraste_A | 1 | 0.1827 | — | — | 0.1827 | 0.1827 |
| contraste_B | 1 | 0.2014 | — | — | 0.2014 | 0.2014 |

Generado 2026-11-06 13:15 por `analizar_zonas.py /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/enlaces/2026-10-22-p1745 --flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra --dark /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-prueba-1745-dark --dark-flat /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-10-22-sinmuestra-dark --procs 1 --out /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo/runs --nombre 2026-10-22-p1745`.

# Experimento A (06/11): ¿el radio de pupila depende de la muestra o de la captura?

**Pregunta.** El método espectral da NA·z ≈ 7.0 y el de borde (a) ≈ 7.4 en la captura roja 03/11. ¿Alguno de los dos
cambia si cambia la muestra? Predicción de Lucas: **ninguno varía**. Vara de comparación: la dispersión del espectral
dentro de una captura, ±2 % (sd del radio sobre los 5 LEDs BF).

**Respuesta corta.** Se cumplió **ninguna de las tres salidas limpias**. Entre 03/11 y 30/10-red-c (mismo ROI, mismo
recorte) **los dos métodos se mueven, más de 2 %, pero en sentidos opuestos**: el espectral sube ≈ +4 % y el borde (a)
baja ≈ −3 %. La brecha borde − espectral pasa de +0.43 mm (03/11) a −0.09 mm (red-c). El par de piso de ruido
(30/10-red y red-b) da el mismo borde dentro de 0.1 %; el espectral **no funciona** en ese par (eje corrido, ver abajo).

## Qué se corrió

- **Espectral.** `score` y `grid` copiados textualmente de `paso_espectral_0311.py`; etapa 1 con radio libre
  (0.92–1.20·rb0) y etapa 2 en 0.88–1.25·rb0, igual que `diag_rb0.espectral_var` modo `etapa1_radio`. Guess nominal sin
  cambios (z 102, +0.529 mm) en todos los recortes. Preprocesado de `scripts/reconstruir.py` (importado, solo lectura):
  oscuro de la misma exposición, flat propio, imagen = S/F·⟨F⟩. Se reporta también el modo `original` en los json.
- **Borde (a).** `centrado.analizar` sin cambios (copia importada); solo cambia la carpeta de salida. Sin flat, como el
  original. NA·z = R_pasos·6 mm (convención de los informes; la corrección tan→sin con z 99.5 resta ≈ 0.02 mm y está en
  los json). Con s libre, R en pasos = R_px / s_libre.
- **Chequeo de cordura (03/11, recorte 360:760, 80:480).** Reproduce exacto: original **6.972 / 6.714**, radio libre
  **7.007 / 6.938** (igual desde `prep.npz`, diferencia relativa de imágenes 1e-7). Borde (a): R 1.2334 pasos → **7.40**,
  w 222 px; con s libre, s 2950, R 1.248 pasos → **7.49**. Coincide con `centrado/tabla.json`.
- **Recortes.** Para elegir, se midió el contraste de partículas (rms de S/F pasa-altos, LED central) en una grilla de
  recortes de 400 px (`resultados/survey_contraste.json`). En 03/11 el recorte A tiene ≈ 0.10–0.11; en red-c el máximo es
  0.11 en (360, 480), y en (360, 80) hay ≈ 0.07–0.08 (menos partículas: PS 500 nm en aire). Se usaron **los mismos dos
  recortes en las dos capturas** (mismo ROI → misma geometría):
  - **A** = filas 360:760, cols 80:480 (el del 03/11);
  - **B** = filas 360:760, cols 480:880 (el de más contraste en red-c).

## Resultados (NA·z en mm)

### Espectral (etapa 1 con radio libre)

| captura | recorte | NA·z filas | NA·z cols | sd radio (5 LEDs) | NA·z por LED (17,15) (16,15) (17,14) (17,16) (18,15) |
|---|---|---|---|---|---|
| 03/11 (esferas 5 µm, DMSO) | A | **7.01** | **6.94** | 2.1 % | 6.72 7.05 7.00 7.06 7.03 |
| 03/11 | B | 6.91 | 7.06 | 0.4 % | 7.01 6.97 6.99 6.94 7.01 |
| 30/10-red-c (PS 500 nm, aire) | A | **7.27** | **7.23** | 1.4 % | 7.40 7.20 7.20 7.14 7.29 |
| 30/10-red-c | B | 7.51 | 7.18 | **3.4 %** | 7.10 7.34 7.20 7.30 7.76 |
| 30/10-red (eje −0.31 paso) | 720:1120, 600:1000 | 7.93 | 7.33 | **5.9 %** | 8.41 7.48 7.41 7.43 7.35 |
| 30/10-red-b (mismo campo) | ídem | 7.53 | 7.42 | **6.9 %** | 8.39 7.19 7.27 7.27 7.24 |

"NA·z por LED" = radio de ese LED / paso medio (filas+cols)/2 · 6 mm; sirve para ver la dispersión, no es otra medida.

### Borde (a)

| captura | eje (a) (pasos) | s fijo 3538: R px | R pasos | w px | **NA·z** | s libre: s | R px | R/s pasos | **NA·z** | LOO NA·z (min–max) |
|---|---|---|---|---|---|---|---|---|---|---|
| 03/11 | (+0.073, −0.028) | 4364 | 1.233 | 222 | **7.40** | 2950 | 3682 | 1.248 | **7.49** | 7.26–7.45 |
| 30/10-red-c | (+0.117, −0.005) | 4222 | 1.193 | 218 | **7.16** | 2278 | 2649 | 1.163 | **6.98** | 6.94–7.20 |
| 30/10-red | (−0.307, +0.013) | 4177 | 1.181 | 99 | **7.08** | 3703 | 4365 | 1.179 | **7.07** | 7.07–7.11 |
| 30/10-red-b | (−0.308, +0.014) | 4179 | 1.181 | 98 | **7.09** | 3670 | 4329 | 1.180 | **7.08** | 7.08–7.12 |

LOO = el ajuste (a) sacando uno de los 8 vecinos por vez (NA·z = R_pasos·6).

### Comparación contra la vara de ±2 %

| comparación | espectral filas | espectral cols | borde (a) s fijo | borde (a) s libre |
|---|---|---|---|---|
| 03/11 → red-c, recorte A | 7.01 → 7.27 (**+3.7 %**) | 6.94 → 7.23 (**+4.2 %**) | 7.40 → 7.16 (**−3.3 %**) | 7.49 → 6.98 (−6.9 %) |
| 03/11 → red-c, recorte B | 6.91 → 7.51 (+8.7 %) | 7.06 → 7.18 (+1.7 %) | (no depende del recorte) | |
| mismo capture, A → B (03/11) | −1.4 % | +1.7 % | — | — |
| mismo capture, A → B (red-c) | +3.3 % | −0.7 % | — | — |
| red → red-b (piso de ruido) | no aplica (método roto) | | +0.06 % | +0.1 % |

## ¿Cuál de las tres salidas ocurrió?

- "Espectral varía y borde no" → **no**: el borde también se mueve 3 %, unas 50 veces su repetibilidad (red vs red-b,
  0.06 %) y más que su LOO dentro de 03/11 (sd 0.8 %).
- "Los dos se corren juntos" → **no**: se corren en **sentidos opuestos**.
- "Ninguno varía" (predicción de Lucas) → **no**: con el recorte A, el espectral se mueve ≈ +4 % (el doble de la vara) y
  el borde ≈ −3 %.

Lo que se observa es una cuarta salida, que el criterio no tenía prevista: **los dos cambian entre capturas y la brecha
casi desaparece en red-c** (7.16 borde contra 7.23–7.27 espectral). La interpretación queda para Lucas.

## Advertencias

- **Muestra y captura están confundidas.** Entre 30/10-red-c y 03/11 cambian la muestra (PS 500 nm en aire contra
  esferas 5 µm en DMSO), el día, posiblemente el foco del objetivo y la exposición del BF (18 contra 17 ms). El
  experimento no separa "muestra" de "captura". El eje (a) también cambia (+0.117 contra +0.073 pasos en filas).
- **El borde (a) no usa flat** y mira el ROI entero; el ancho w de red-c y 03/11 es ≈ 220 px, el del par red/red-b ≈ 99 px
  (otro ROI, eje corrido −0.31 paso). No sé si el w distinto es de la posición del ROI o de otra cosa; no lo investigué.
- **s libre no es estable**: da 2278 (red-c), 2950 (03/11) y ≈ 3700 (red, red-b) contra 3538 nominal. El NA·z con s
  libre se informa, pero cuenta poco.
- **Espectral en red-c recorte B**: la dispersión entre LEDs es 3.4 % (por arriba de la vara), sobre todo por (18,15) con
  7.76. El 8.7 % de filas de ese recorte no es confiable. La comparación limpia es la del recorte A (1.4 % y 2.1 %).
- **Espectral en red / red-b: roto.** Con el eje a −0.31 paso, el círculo del LED (18,15) cae cerca del borde BF/DF en
  todo el ROI (en el recorte usado, el más favorable, el centro del recorte queda ≈ 100 px del lado DF con R 1.18 pasos).
  Resultado: (17,15) lee 8.4, la dispersión es 6–7 % y el paso en filas sale 38–49 bins (contra ≈ 50). **Ese par no da
  piso de ruido para el espectral**; solo lo da para el borde. Se corrió un único recorte.
- El recorte A en red-c tiene menos partículas (contraste ≈ 0.075 contra ≈ 0.10 en 03/11). No sé si el espectral depende
  del contraste; un recorte por captura no alcanza para saberlo.
- Una sola corrida por caso (sin semillas, el método es determinista). El error del espectral se estima solo por la
  dispersión entre LEDs y entre los dos recortes.

## Archivos

- `codigo/espectral_zonas.py`: espectral (score/grid textuales) + preprocesado de `reconstruir.py`. Uso en el docstring.
- `codigo/borde_zonas.py`: borde (a), importa la copia `codigo/centrado.py`.
- `codigo/survey_contraste.py`: contraste por recorte, para elegir recortes.
- `codigo/resumen.py`: arma `resultados/resumen.json`.
- `codigo/paso_espectral_0311.py`, `centrado.py`, `diag_rb0.py`, `real_rb0.py`: copias sin cambios de los originales.
- `resultados/espectral_<etiqueta>.json` (0311_A, 0311_B, redc_A, redc_B, red_A, redb_A; modos `original` y
  `etapa1_radio`, por LED), `resultados/borde_<captura>.json`, `resultados/resumen.json`,
  `resultados/survey_contraste.json`, logs. Los mapas `.npz` de centrado se borraron (se regeneran en ~30 s).
- No se tocó el repo ni se corrieron reconstrucciones.

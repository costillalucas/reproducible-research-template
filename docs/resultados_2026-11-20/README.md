# Resultados 20/11/2026 — esferas 5 µm en rojo (experimento A, parte roja) y "aislar vs recortar"

Estado: **análisis asentado, pendiente de revisión con Lucas.** Las interpretaciones marcadas "hipótesis" no están
verificadas. Todo lo pesado (objetos .npy, datos preprocesados) queda en `~/Documents/AleYLu/reconstrucciones/2026-11-20/`.

Contexto: el 19/11 se resolvió T = 1 µm (red de 1000 l/mm) en azul 29x29. El 20/11 se decidió no medir más redes y
pasar a las esferas de poliamida de 5 µm (en DMSO), experimento A = mismo campo en rojo y azul, para comparar el volumen
de fase por partícula entre colores. Hoy se tomó **solo el rojo**; el azul no se capturó.

Contenido:

| carpeta | qué hay |
|---|---|
| `red_a/` | toma red.a: QC, centrado, problema del flat, paralaje, reconstrucción 29x29 completa |
| `red_b_qc/` | toma red.b (17:43–18:15): QC y centrado de sus dos flats. **No reconstruida** |
| `aislar_vs_recortar/` | comparación A (reconstruir 200 px y recortar) vs B (recortar 20/40 px crudos y reconstruir), sobre la toma del 18/11 |

---

## 1. Toma `2026-11-20.2048ms-red.a`

- 29x29 = 841 LEDs, rojo, z 143.5 en la config (z medido por el borde BF: ver abajo), ROI centrado **4064, 842**.
  Exposiciones 34 / 482 / 1405 / 2048 ms (804 LEDs a 2048), 4 oscuros por exposición.
- Centrado: prueba-1204 empezó en 4160,1008 (ROI del azul del 19/11) con desvío 0.084 pasos → ROI movido −96/−166 px;
  prueba-1209 desvío (+0.030, +0.006). Toma completa: (+0.033, +0.010). Estable.
- QC (`red_a/qc.txt`): oscuros OK; 4 LEDs con unos pocos píxeles saturados (0.000 %, despreciable); SNR de pico ≥ 3 en
  todos los anillos.
- **z por el radio del borde BF** (R en pasos de LED): hoy 1.751–1.781 contra 1.768 de las esferas del 18/11 a 143.5
  y 1.795 de la red del 18/11 con separador (145.6) → **z ≈ 142–144.5 mm**, misma altura que el 18/11 sin separador.
  Reconstrucción con z 142.1 (R 1.753 de la toma completa).

### 1.1 Corrección de una afirmación anterior: el salto de ROI 18/11 → 19/11 no era el color

El 19/11 a la mañana yo había interpretado que el ROI centrado del rojo (4160,**1626**, 18/11) y el del azul
(4160,**1008**, 19/11) diferían por el corrimiento de dado entre colores. Hoy el **rojo** quedó centrado cerca de la
posición del azul del 19/11. Entonces el salto de ~618 px (~0.3 pasos de LED) no es un efecto de color: algo cambió en
el camino óptico entre el 18/11 15:30 y el 19/11 13:00. **No se pueden usar ROIs de días distintos para inferir offsets
de dado entre colores.** El offset rojo/azul real hay que medirlo el mismo día sin tocar nada.

### 1.2 El flat tiene el eje corrido: la muestra desvía la luz

- Flat `red.a-sinmuestra` (platina corrida a un costado, camino vacío): centrado **−0.228 filas / +0.047 col** contra
  **+0.033 / +0.010** con la muestra. Diferencia ~0.23–0.26 pasos ≈ 1.3–1.5 mm equivalentes en la matriz.
- Control independiente (`red_a/arcos.py`, cociente de los LEDs de borde en los bordes del ROI): con muestra el arco
  del LED (19,15) aparece abajo (0.10) y el (15,15) arriba casi nada (0.01); en el flat se invierte ((15,15) 0.12,
  (19,15) 0.00). Confirma el corrimiento con un método que no usa el ajuste de borde.
- Segundo flat `red.b-sinmuestra` (14:51, mismo procedimiento): **−0.223 / +0.049**, igual al primero → el corrimiento
  es **reproducible**.
- Vuelta de la platina con la muestra (`red.b-prueba-1405`): **+0.040 / +0.007** → el eje vuelve con la muestra.
- Lucas: la matriz y la platina son independientes; para el flat solo se corrió la platina.
- **Hipótesis (no verificada):** el conjunto de la muestra (portaobjetos + DMSO + cubre) actúa como una cuña: caras
  externas no paralelas → desvía el haz. El desvío necesario es ~0.23 pasos · 6 mm / 143 mm ≈ 0.55°. Esto también
  explicaría el salto de ROI entre el 18/11 y el 19/11 (muestras distintas, con y sin separador).
  Prueba pendiente: medir con un portaobjetos vacío, o en una zona limpia de la misma muestra.

**Impacto en la reconstrucción de red.a** (`red_a/afectados.py`, recorte 285:685 / 344:744, anillos 1.2–3.3):
`reconstruir.py` usa el flat **píxel a píxel** (BF = S/F·⟨F⟩, DF = S − gauss(F, 8)). Con el eje corrido, el único LED
cuyo flat difiere dentro del recorte es el **(15,15)**: cociente del flat con mediana 0.10 (p5–p95 0.03–0.12) contra
0.00 en la muestra → en ese LED la resta DF sobrecorrige. Los BF (16,14), (16,16), (18,14) y (18,16) coinciden dentro
de ~0.03. **Afecta a 1 de 841 LEDs.** `reconstruir.py` no tiene una opción para excluir LEDs. La prueba empírica (con y
sin ese LED) no se hizo.

### 1.3 Qué se ve en la imagen cruda: esferas, discos de polvo y paralaje

- Imagen del LED del eje (`red_a/eje.png`): puntos oscuros chicos y nítidos de ~7–10 px (compatibles con esferas de
  5 µm a 1.29 µm/px), con forma de estrella de 4 brazos (origen sin explicar). También discos anulares grandes y
  borrosos de ~120–150 px; dos caen dentro del recorte central de 400 px.
- Los discos sobreviven a la división por el flat (`red_a/cruda_sobre_flat.png`).
- **Desplazamiento de mosaicos entre red.a y red.b** (`red_a/mismo_campo.py`; la platina se movió −87, −3 px):
  - hay dos poblaciones;
  - los mosaicos con estrellas se mueven **con la platina** → están en el portaobjetos (son muestra);
  - los discos grandes quedan en **(0,0)** → están fijos a la óptica: polvo o defectos en el camino óptico, desenfocados.
  - Los discos sobreviven al flat porque el eje del flat está corrido 0.23 pasos y por eso la sombra se mueve.
- **Paralaje** (`red_a/paralaje.py`, LEDs BF a ±1 paso del (17,15)): las estrellas y el disco grande se mueven
  ~6–7 px/paso, y otro objeto abajo a la derecha ~28 px/paso. Con 1 paso = 6/142 rad y 1 px = 1.29 µm, la primera
  lectura daba Δz ≈ 200 µm y ≈ 870 µm.
  **Retractado para las esferas:** esa medida estaba dominada por los discos fijos a la óptica. Los picos de
  correlación eran débiles (0.02–0.04). La profundidad de las esferas no quedó medida por paralaje.
- Me corrijo: "mínimo contraste en foco" vale para objetos de fase **débil**. Las esferas (φ ~ 2.5 rad esperado)
  no son débiles, así que ese criterio no sirve para enfocarlas.

### 1.4 Reconstrucción red.a, los 841 LEDs (`red_a/resumen.txt`, `red_a/reconstruccion.png`)

Comando en `red_a/correr_red_a.sh`: flat red.a-sinmuestra, z 142.1, NA 0.0747, factor 5 (píxel reconstruido
0.258 µm), 160 épocas, `--validar`, recorte de 400 px 285:685 / 343:743 (sobre el eje). Tardó 55.9 min con 3 núcleos.

| métrica | valor | criterio |
|---|---|---|
| C1 (R held-out, mitades) | **0.733** (A 0.726 / B 0.741) | pasa (≤ 0.867; sin FPM 0.967) |
| R de ajuste | 0.755 | — |
| C3 (artefacto de grilla) | 5.2e-3 | pasa (≤ 0.01) |

**Fase de las partículas** (desenvuelta, fondo restado, umbral 0.06 rad; el análisis se hizo en la sesión y el script
no se conservó):

- Volúmenes de fase de objetos aislados: **31–47 rad·µm²**. Lo esperado para UNA esfera de 5 µm con Δn 0.05 en rojo es
  ~32.6 rad·µm².
- Pero cada objeto se reparte en un diámetro de 15–20 µm, con picos de 0.4–1 rad (se esperaba ~2.5 rad).
- El objeto más grande da 175 rad·µm² (pico 3.1 rad): probablemente un agregado.
- Reenfoque digital de ±600 µm (n del DMSO 1.48): los picos son algo mejores entre 0 y −200 µm y nunca se afinan.
  → el ensanchamiento **no** se explica por un desenfoque grande.
- **Hipótesis abiertas:** límite de resolución del rojo, error de modelo, esferas no ancladas que se mueven durante la
  toma, o esferas a distintas profundidades.

### 1.5 Preguntas físicas sobre la muestra (números a verificar por Lucas)

- Las esferas están en **DMSO** (se sabía desde septiembre), con Δn ≈ 0.05 → φ ≈ 2.5 rad en rojo.
- Sedimentación (Stokes) con ρ_PA ≈ 1.14 contra ρ_DMSO 1.10 y η ≈ 2 mPa·s: ~0.3 µm/s, unos 0.5 mm en 30 min.
- Browniano: ~12 µm laterales en 30 min para una esfera libre.
- → una toma de ~30 min solo funciona con esferas **pegadas a una superficie**. Las estrellas se correlacionan a lo
  largo de ~2 h, así que al menos esas están pegadas.
- Con Δn chico, la **dispersión** de n(λ) del DMSO y de la poliamida puede cambiar Δn(λ) en decenas de %. Es una causa
  candidata del viejo déficit de volumen G/B. Para predecir V_B/V_R hacen falta n(λ) de los dos materiales.

---

## 2. Toma `2026-11-20.2048ms-red.b` (QC; sin reconstruir)

Captura 17:43–18:15, mismo ROI 4064,842; centro de `red.b-prueba-1405` (+0.040, +0.007).

- QC con oscuros (`red_b_qc/qc_red_b.txt`): **841/841** LEDs, 1 frame por LED, exposiciones 37 / 545 / 1691 / 2048 ms
  (804 a 2048), oscuros de 4 frames que cubren todas las exposiciones, SNR de pico ≥ 3 en todos los anillos.
- Saturación: 9 LEDs con píxeles saturados (el peor, (17,16), 0.004 %). Es despreciable, pero hay más que en red.a
  (4 LEDs).
- SNR por frame en los anillos exteriores (18–20): 11–14 (con nivel de oscuro fijo da ~48, que es falso → **siempre
  correr el QC con `--dark`**).
- Comparado con red.a: anillo 0 más brillante (95.9 contra 82.6 c/ms) y anillos ≥ 15 más débiles (anillo 18: 0.006
  contra 0.010 c/ms). Sin explicar: ¿otro campo o el cambio de posición?
- **Flats disponibles para red.b:**

| flat | centrado (fila, col) | R borde | sirve para el borde |
|---|---|---|---|
| `red.b-sinmuestra` (14:31, completo, camino vacío) | **−0.223, +0.049** | 1.766 (w 70 px) | **no**: mismo problema que red.a |
| `red.b-sinmuestra-prueba-1636` (prueba, solo LEDs centrales) | **−0.044, −0.017** | 1.749 (w 99 px) | más cerca (diferencia de 0.08 pasos con la muestra) pero solo es una prueba |

Que el flat de las 16:36 quede mucho más cerca del eje de la muestra (y con un borde más ancho, w 99 contra 70) va a
favor de la hipótesis de que **la muestra en el camino cambia el eje**. Preguntar a Lucas dónde se tomó (¿zona limpia
del mismo portaobjetos?). Falta el flat completo en esa posición.

---

## 3. Aislar vs recortar (toma del 18/11, rojo 21x21)

Pregunta de Lucas: ¿reconstruir una ventana chica aislada alrededor de una partícula (B) da lo mismo que reconstruir un
campo de 200 px y recortar después (A)?

Métodos y desvíos del plan: `aislar_vs_recortar/README_agente_pre_B40.md`, escrito antes de correr B40. Lo importante:

- 15 partículas en 5 recortes A de 200 px.
- B = 20x20 o 40x40 px crudos centrados en cada partícula, mismas opciones (NA 0.0747, factor 3, 160 épocas, `--validar`).
- Diferencia real entre los caminos: en B cada ventana tiene su propio offset de LED por posición (0.14–0.43 mm); en
  A hay uno solo por recorte.
- El volumen de fase de octubre **no sirve** acá: en A la amplitud es ≈ 0 en el centro de las partículas, lo que da
  vórtices de fase.
- Se usaron medidas complejas: S = ∫(o/fondo − 1), correlación compleja ρ_c, ρ_c tras un pasa-altos (σ 3 µm) = ρ_c_hp,
  Pearson de amplitud y de fase, error relativo y desplazamiento.
- Control A vs A' = misma partícula en dos recortes A distintos (solo 2 pares: P03, P06).

### 3.1 Resultados (medianas sobre 15 partículas, [p25–p75])

| medida | B20 | **B40** | control A–A' (N=2) |
|---|---|---|---|
| fondo B/A | 0.24 [0.23–0.26] | **1.00** [0.99–1.00] | — |
| \|S\| B/A | 5.9 [3.7–10.7] | **0.98** [0.91–1.02] | 0.95 |
| error relativo ‖A−B‖/‖A‖ | 0.77 | **0.051** [0.042–0.057] | 0.043 |
| ρ_c (complejo) | 0.49 [0.37–0.65] | **0.76** [0.63–0.84] | 0.92 |
| ρ_c_hp (pasa-altos) | 0.66 [0.55–0.71] | **0.68** [0.60–0.81] | 0.91 |
| Pearson de amplitud | 0.02 | **0.71** [0.50–0.82] | 0.83 |
| Pearson de fase | 0.38 | **0.77** [0.69–0.88] | — |
| desplazamiento A↔B | 0.13 µm | **0.06 µm** | — |
| C1 de B | 0.57 (sin FPM 0.93) | 0.57 (sin FPM 0.91) | — |
| C2 en la ventana, A / B | 0.65 / 0.54 | 0.51 / 0.51 | — |

Por tamaño: ρ_c_hp B40 en las 10 partículas grandes (manchas de 11–21 µm) = **0.80**; en las 5 chicas y redondas
(3–5 µm: P08, P10, P12, P13, P15) = **0.65**. En B20: 0.67 y 0.63.

Tabla completa por partícula: `aislar_vs_recortar/tabla.csv`. Figuras: `fig_grilla_B20.png`, `fig_grilla_B40.png`,
`fig_dispersion.png`.

### 3.2 Qué dicen los números (sin ir más allá)

1. **B20 pierde el fondo y las bajas frecuencias.** El fondo queda en 0.24× el de A en las 15 partículas, y por eso las
   partículas normalizadas aparecen claras donde en A son oscuras. La energía de la estructura fina se conserva (0.96×)
   y la posición coincide (0.1 µm).
2. **Con B40 las bajas frecuencias vuelven del todo:** fondo 1.00, |S| 0.98, error relativo 0.051 (≈ control 0.043),
   Pearson de amplitud 0.71. Las bajas frecuencias de B20 eran un problema de tamaño de ventana.
3. **La concordancia en altas frecuencias casi no mejora** (ρ_c_hp 0.66 → 0.68) y queda lejos del control (0.91).
   Mejora en las partículas grandes (0.80) y no en las chicas (0.65).
4. **C1 no ve nada de esto:** da 0.57 en B20 y en B40, aunque B20 tiene el fondo mal en un factor 4. C1 está dominado
   por los anillos BF/DF bajos y no detecta este error. No sirve como control de calidad por partícula.
5. El volumen de fase "de octubre" en B40 sigue a A cuando no hay vórtice (V_B/V_A sin vórtice: mediana 0.94, N = 5).

### 3.3 Hipótesis para la discrepancia en altas frecuencias (para discutir; ninguna probada)

- **Offset de LED por posición:** en B cada ventana usa su offset (0.14–0.43 mm) y en A uno solo para todo el recorte.
  Si la corrección no telecéntrica está bien, B debería ser *más* correcto en esas frecuencias, no menos; si está mal,
  es una fuente de diferencia. El control A–A' (offsets distintos ±0.24 mm) da 0.91, lo que sugiere que el offset solo
  no alcanza a explicarlo.
- **Pupila menos restringida:** en A hay muchas partículas para fijar la pupila/fase global; en una ventana de 40 px
  con una sola partícula, la ambigüedad pupila–objeto es mayor.
- **Estadística:** las partículas chicas tienen poca energía de altas frecuencias, así que el ρ_c_hp es más ruidoso. El
  control tiene N = 2.
- **Borde periódico:** a 40 px la partícula ocupa una fracción menor de la ventana, pero el borde sigue a ~13 µm.
- Prueba posible: B40 con el offset de A forzado (`--offset-roi`) → si ρ_c_hp sube hacia 0.9, el offset era la causa.

---

## 4. Otros cambios del día

- `imagenes_recorta_cuadradas.py` (repo de captura): CLI
  `python imagenes_recorta_cuadradas.py <captura|captura/organizado/color> ... [--side] [--centro]`; cada toma usa el
  centro de su propio `captura.json` (antes apuntaba a un chequeo que no existe). Recorta sobre el eje con el mismo
  redondeo que `reconstruir.py`.
- Diferencia de 1 px en columnas (343 en `reconstruir.py` contra 344 en el script de recorte): los dos usan el mismo
  redondeo, pero el eje sale de caminos distintos (`centro.json` → col 543; desvío × px/paso → ~543.5) y cae justo en
  el borde del redondeo. Son 1.3 µm, con un offset de LED de +0.001 mm: **despreciable**.
- Gotcha operativo: si un script de espera usa `pgrep -f "<patrón>"` y ese patrón aparece en su propia línea de
  comando, se encuentra a sí mismo y no termina nunca (pasó el 19/11 y otra vez hoy).
- Gotcha: un chequeo de centrado del azul antes del flat rojo sobrescribe `chequeos/centro_actual.json` → el flat queda
  con el centro del azul.

## 5. Pendiente

1. **Flat válido** para red.a/red.b: completo, en la posición de la prueba de las 16:36 (o en una zona limpia de la
   misma muestra). Después, reconstruir red.b y comparar con red.a.
2. Experimento A, **parte azul**: no capturada. Antes, escribir la predicción V_B/V_R (necesita n(λ) del DMSO y de la
   poliamida).
3. Probar si la muestra desvía la luz (portaobjetos vacío / cuña).
4. Aislar vs recortar: probar B40 con el offset de A forzado; más pares de control A–A'.
5. LED (15,15) en red.a: reconstrucción con y sin ese LED (hay que agregar una opción de exclusión).
6. Ancho de 15–20 µm de las esferas en la fase: ¿resolución, modelo o movimiento?

---
**Trazabilidad.** De Lucas: el diseño del experimento A (rojo+azul, mismo campo), la captura y el procedimiento de los
flats, la observación de que las partículas no estaban del todo enfocadas, la hipótesis de que la matriz y la platina
son independientes, el dato del DMSO, la pregunta aislar-vs-recortar y el pedido de 40 px. De Claude (con agentes):
las mediciones de centrado, arcos, mosaicos y paralaje; el cálculo del impacto del flat; la hipótesis de la cuña;
Stokes/Browniano; las reconstrucciones; las métricas complejas y esta redacción. Las interpretaciones de §3.3 son
sugerencias sin revisar.

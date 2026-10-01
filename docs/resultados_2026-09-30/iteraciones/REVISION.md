# Revisión adversarial independiente del INFORME (iteraciones, 28/09 b), 2026-09-30

Código propio en `revision/` (no usa `analizar.py`): `rev_c1.py` (C1, train, brecha, por anillo y por LED desde
`metrics.jsonl`), `rev_obj.py` (`c2`: C2 con `F.frc` y con una FRC propia, C2 por teselas 3×3 con ventana de Hann;
`stab`: estabilidad de bajas y descomposición espectral del cambio; `col`: colores con corrimiento medido en cada
snapshot), `rev_c2b.py` (tendencias pareadas por tesela y C2 con ventana de Hann sobre el interior). Logs y json al lado.
Todo con `nice -n 19`, un proceso. No se tocó el barrido s3_red.

## 1. Reproducción a 40 épocas: CONFIRMADA

- C1: rojo 0.46127, verde 0.61526, azul 0.59584. Coincide al último dígito con los tasks oficiales del 28/09 b
  (`captura_2026-09-28b/*/out/tasks/*_f*.json`). La media propia sobre `per_led` (no entrenados, anillo < 7) coincide
  con `heldout_R_ring_lt7` (diferencia 0).
- La sd de la tabla es la poblacional (ddof = 0), igual que en `criterios_b.py`. Con ddof = 1 es ~10 % mayor
  (rojo 0.008, verde 0.008, azul 0.011 a 40). Conviene decirlo.
- C2 (nulo): rojo 0.0828 (0.0141), verde 0.0429 (0.0078), azul 0.0986 (0.0071). Coincide `F.frc` con mi FRC propia
  (bincount) en todas las épocas.
- Sin FPM: 0.977 / 0.984 / 0.978.

## 2. Tabla a 0/20/40/120/400 y mínimos: CONFIRMADA, con una corrección

Todos los C1 ± sd, C2 y nulos de la tabla clave coinciden con mi cálculo a 3 decimales. También coinciden los mínimos:

| color | mínimo de C1 | máximo de C2 |
|---|---|---|
| rojo | 0.3955 (400) | 0.1050 (400) |
| verde | 0.6003 (5) | 0.0486 (20) |
| azul | 0.5753 (5) | 0.1123 (320) |

Los dos sets de números citados abajo también coinciden:
- las diferencias pareadas por fold;
- las de la segunda tabla (train, brecha, BF full, por anillo con cortes 1.3-4 / 4-7, lattice, solver_err).

**Corrección:** el INFORME dice que el BF del rojo a 40 es "el peor de toda la corrida (R = 0.93)". Es falso. El
máximo es a 60 épocas (0.947). Y algo más fuerte que el INFORME no dice: a 30-80 épocas el BF del rojo ajusta **peor
que el objeto inicial**. Serie (BF, tarea full):

| época | 0 | 5 | 30 | 40 | 60 | 80 | 120 | 400 |
|---|---|---|---|---|---|---|---|---|
| R | 0.725 | 0.699 | 0.857 | 0.928 | 0.947 | 0.892 | 0.763 | 0.638 |

Texto propuesto: "El ajuste de los 6 LEDs de campo claro empeora de 0.70 (5) a 0.95 (60), peor que el objeto inicial
(0.73), y recién a 160-240 vuelve por debajo de él."

## 3. Mínimo de C1 a 5 épocas en verde y azul: CONFIRMADA dentro de esta captura, MATIZAR su lectura

**Independencia de los folds.**
- Los held-out son disjuntos: 30/30/30/29/29 LEDs, sin solapamiento, y juntos cubren los 148 LEDs no-BF con anillo < 7.
- Los entrenamientos **no** son independientes: Jaccard medio entre pares de folds 0.61, y los 6 BF están en todos.
- Por eso la sd entre folds (0.007 / 0.005) no es un error estándar de 5 réplicas independientes.

**Prueba alternativa, a nivel de LED.** Cada LED no entrenado aparece en un solo fold, así que se puede emparejar
R(5) − R(40) LED por LED (n = 148) y hacer bootstrap sobre los LEDs. El bootstrap supone LEDs independientes, que
tampoco es del todo cierto, porque los vecinos se correlacionan.

| color | media | IC 95 % | LEDs que mejoran a 5 |
|---|---|---|---|
| verde | −0.015 | [−0.023, −0.007] | 61 % |
| azul | −0.021 | [−0.027, −0.014] | 67 % |

Los dos métodos (folds y LEDs) coinciden: el efecto existe en esta captura.

**De qué anillos viene** (contribución a la media).

| anillo | verde | azul |
|---|---|---|
| 5.5-7 (n = 60) | −0.015 (77 % de los LEDs mejora a 5) | −0.015 (75 %) |
| 4-5.5 | −0.005 | −0.006 |
| 1.3-2.5 (n = 10) | **peor** a 5 épocas: +0.045, 9/10 LEDs | +0.010 |

La "U" es casi toda del borde exterior del conjunto evaluado, el campo oscuro más lejano dentro de anillo < 7. No es
una mejora general.

**¿Es un artefacto de "objeto ≈ inicial"?** No en el sentido trivial.
- A 5 épocas C1 ya es 0.60 / 0.58, contra 0.99 del objeto inicial.
- El piso de ruido de los LEDs evaluados es ~0.05 (máximo 0.21). R ~0.6 está muy por encima: el residuo es error de
  modelo, no ruido.

Lectura compatible con los datos: parada temprana como regularización de las frecuencias altas. Más épocas meten en
los LEDs exteriores contenido que el modelo no predice bien. Que "favorezca la métrica afín" (s ≥ 0 y offset libres
por LED) **no se pudo descartar** con lo guardado.
- Prueba: recalcular R(5) y R(40) para los LEDs 5.5-7 con s fijo (sin offset) o con correlación cruda, regenerando las
  predicciones desde `obj` de los folds. Los folds no guardaron `obj`: habría que rehacer 2 snapshots × 5 folds.

**Tamaño del efecto.** 0.015-0.021, frente a una mejora de ~0.38 sobre sin FPM. Una sola captura y una sola zona.

Texto propuesto: "En verde y azul C1 es mínimo a 5-8 épocas. Entre 5 y 40 sube 0.015 (verde) y 0.021 (azul): los 5
folds en la misma dirección e IC 95 % por LED [−0.023, −0.007] y [−0.027, −0.014]. La diferencia viene casi toda de
los LEDs de anillo 5.5-7; en el anillo 1.3-2.5 del verde, 40 épocas es mejor. Los folds comparten el 61 % del
entrenamiento, así que la sd entre folds no es un error de réplicas independientes."

## 4. Rojo en transitorio a 40 épocas: CONFIRMADA en lo numérico, MATIZAR "fondo lento"

**Números.**
- Error interno del solver: 0.189 (40) → 0.117 (60) → 0.060 (80) → 0.027 (120) → 0.018 (400). Correcto.
- Correlación de la amplitud de bajas (≤ NA/λ) con 400: 0.106 a 40. Correcto.
- Esa correlación es **no monótona**: 0.60 (5), 0.27 (20), 0.11 (40), 0.24 (60), 0.75 (120). La amplitud de bajas a 5
  épocas se parece más a la final que la de 40. Es una excursión que va y vuelve, no un avance lento. Eso refuerza que
  40 cae en el peor punto del rojo.

**¿Es "del fondo lento"?** Solo en parte. Fracción de la energía del cambio de amplitud 40 → 120 (interior) por banda
de frecuencias:

| banda (1/µm) | rojo | verde | azul |
|---|---|---|---|
| ≤ 0.02 (escalas > 50 µm) | 25 % | 0.07 % | 0.01 % |
| 0.02 a NA/λ | 23 % | 2 % | 2 % |
| NA/λ a 2NA/λ | 18 % | 28 % | 31 % |
| banda de C2 | 24 % | 39 % | 30 % |
| > 0.45 | 9 % | 30 % | 37 % |

Cambio relativo 40 → 120: rojo 0.17, verde 0.08, azul 0.07.

- Lo distintivo del rojo es que la mitad del cambio está por debajo de NA/λ. En verde y azul eso es ~2 %.
- La otra mitad está en NA/λ-0.45 1/µm, incluida la banda de C2 (24 %). El rojo cambia en todas las bandas.
- La correlación muy lenta (≤ 0.02) con 400 es −0.01 a 40 y 0.74 a 120: el fondo de muy baja frecuencia se reacomoda
  por completo.

Texto propuesto: "Entre 40 y 120 épocas el rojo cambia la amplitud un 17 % (verde 8 %). La mitad de ese cambio está
por debajo de NA/λ: el fondo lento se reacomoda por completo (correlación con 400 de −0.01 a 40 y 0.74 a 120). La
otra mitad está en frecuencias altas, incluida la banda de C2. No es solo el fondo."

## 5. Tendencias de C2: verde REFUTADA como hecho robusto, rojo MATIZAR, azul CONFIRMADA

Con una sola partición en mitades no hay réplica. Hice dos pruebas de robustez con los mismos objetos.

**(a) C2 en 9 teselas** (3×3 del interior, Hann, cada una de 140-150 µm de lado): da réplicas espaciales, no
independientes de la partición.

| color, intervalo | cambio medio ± ee | teselas que suben | cambio del nulo |
|---|---|---|---|
| azul, 40 → 400 | +0.018 ± 0.006 | 8/9 | ~0 |
| rojo, 40 → 400 | +0.007 ± 0.035 | 3/9 (dominado por 2 teselas) | — |
| verde, 20 → 400 | +0.009 ± 0.014 | 4/9 | — |

- En verde la media por tesela **sube**: 0.101 → 0.110. El campo entero baja: 0.049 → 0.036.

**(b) Campo entero con ventana de Hann** sobre el interior:

| color | 20 | 40 | 120 | 400 |
|---|---|---|---|---|
| verde | 0.054 | 0.056 | 0.059 | 0.092 |
| rojo | 0.131 | 0.146 | 0.150 | 0.154 |
| azul | 0.052 | 0.056 | 0.058 | 0.080 |

- Verde: la tendencia **se invierte** frente a la definición oficial.
- La caída del verde tras 20 depende de cómo se tratan bordes y fondo. No es una propiedad robusta de la
  reconstrucción.
- Rojo: sube, pero el valor absoluto con ventana (0.146 a 40) ya supera 0.143. Los umbrales están calibrados para la
  definición sin ventana, así que no se puede decir "pasa". Sí muestra que "nunca llega a 0.143" depende de la
  definición.
- Variabilidad espacial grande: sd entre teselas 0.05-0.16. El rojo va de 0.07 a 0.39 según la tesela a 40.

**Textos propuestos.**
- Verde: "C2 del campo entero baja de 0.049 (20) a 0.036 (400), pero con ventana de Hann o por teselas no baja (sube
  0.009 ± 0.014 por tesela). No hay evidencia de que C2 empeore con las épocas."
- Rojo: "sube en el campo entero, no en la mayoría de las teselas (3/9)."
- Azul: "sube 0.018 ± 0.006 por tesela (8/9), robusto."
- "Nunca llega a 0.143" debe decir "con la definición oficial (sin ventana)".

**Cómo cuantificarlo bien.**
- Repetir la partición en mitades con K ≥ 5 particiones aleatorias de los LEDs (estratificadas por anillo) a pocas
  épocas clave (20/40/400). Costo: 2K reconstrucciones por color.
- Mientras tanto: bootstrap por teselas o por anillos de Fourier, e informar C2 con y sin ventana.

## 6. Sobreajuste: CONFIRMADA la brecha, MATIZAR la palabra

Brecha C1 − train (folds):

| color | 2 | 5 | 40 | 400 |
|---|---|---|---|---|
| verde | 0.078 | 0.107 | 0.187 | 0.205 |
| azul | 0.084 | 0.110 | 0.198 | 0.221 |

- Monótona en verde y azul.
- Rojo: máximo 0.125 a 12-20, luego 0.084 a 400.
- Lattice (full) ≤ 0.0064 en todas las épocas. El máximo es el azul a 400 (0.00638); el rojo llega a 0.0024 y el verde
  a 0.0026.
- Como el residuo está muy por encima del piso de ruido (~0.05), lo que se sobreajusta es **error de modelo**, no
  ruido. El propio INFORME ya lo matiza en la interpretación. Está bien que la palabra "sobreajuste" no aparezca como
  hecho.

## 7. Coherencia entre colores con corrimiento fijo: CONFIRMADA la conclusión, REFUTADO el control

Recalculé el corrimiento en cada snapshot (correlación de fase sobre la amplitud sin fondo, con refinamiento
subpíxel). Comparé con el verde, amplitud en "banda_objetivo" (≤ 0.111 1/µm):

| época | 5 | 12 | 20 | 40 | 60 | 80 | 120 | 400 |
|---|---|---|---|---|---|---|---|---|
| corr. rojo-verde, corrimiento fijo | 0.395 | — | — | 0.109 | 0.034 | 0.161 | 0.254 | 0.265 |
| corr. rojo-verde, corrimiento propio | 0.300 | 0.208 | 0.232 | 0.109 | 0.033 | 0.161 | 0.228 | 0.270 |
| corrimiento rojo (px HR) | — | ~3 | ~2 | 6.1 | 6.7 | — | 2.9 | 7.1 |

- Corrimiento rojo-verde por snapshot: salta entre ~3 y ~6-7 px HR sin tendencia (4, 12, 20 y 120-160 cerca de 3; el
  resto cerca de 6).
- Rojo-azul con corrimiento propio: 0.45 (5), 0.024 (40), 0.14 (60), 0.50 (120), 0.60 (400).
- **El mínimo a 40-60 se mantiene.**
- Pero el INFORME dice que "con corrimiento fijo las correlaciones del rojo fuera de 40 están algo subestimadas". Con
  el corrimiento propio dan **igual o menos**, nunca más. El corrimiento que mide el registro es inestable: dos picos
  de ~3 px, es decir ~1.3 µm.
- Texto propuesto: "El registro rojo-verde es ambiguo (3 o 6 px según el snapshot). Con el corrimiento medido en
  cada snapshot las correlaciones no suben y el mínimo a 40-60 se mantiene."

**Además:** la "banda del objetivo" es un pasabajos ≤ 0.11 1/µm. El mínimo rojo-verde a 40-60 es el **mismo
fenómeno** que el transitorio de bajas del rojo (punto 4). No es evidencia independiente, y el INFORME debería
decirlo.

## 8. Lenguaje y limitaciones

**Bien.** Hechos e interpretación están separados en secciones. Las limitaciones incluyen: sin verdad de referencia,
C1 no mide resolución y excluye el BF, una zona y una captura, rampa del paso y época 1 = 0, folds que comparten el BF.

**Más fuerte que los datos.**
1. "C2 tiene su máximo a 20 en verde (después baja)" está en la respuesta corta y la "regla con C2 elegiría ~20 para
   verde" depende de eso. Ninguna de las dos es robusta (punto 5): hay que quitarlas o condicionarlas.
2. "Las dos reglas no coinciden": para el verde se apoya en la tendencia no robusta de C2.
3. "El peor de toda la corrida (R = 0.93)": falso (60, 0.947). Ver el punto 2.
4. "Las 2 primeras épocas hacen casi todo": como la época 1 es nula, es **una** época efectiva (la 2).
5. "Margen sobre el nulo 5-15 veces": es un cociente sobre un nulo chico. En absoluto, el margen (0.07-0.10) no
   alcanza el criterio nulo + 0.068 en verde (0.029-0.042).
6. "En el montaje se ve como un cambio del fondo lento": corregir a "la mitad del cambio es fondo lento" (punto 4).

**Faltan en las limitaciones.**
- (a) C2 depende de la definición: ventana y bordes. Puede invertir la tendencia del verde y pasar el umbral en rojo.
- (b) Una sola partición en mitades, sin réplica.
- (c) sd poblacional.
- (d) La U de C1 viene del anillo exterior 5.5-7 y no se descartó un efecto de la métrica afín.
- (e) Una sola z (98 mm) y un solo método (A+init) con paso 0.3: la convergencia del rojo puede depender del paso.

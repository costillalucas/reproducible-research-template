# Recortes chicos (20 px) contra reconstrucción normal (200 px): 2026-10-30-red-c (11/11)

Pregunta: si se reconstruye un recorte de 20×20 px crudos alrededor de una partícula aislada, ¿el spot se achica igual que
en una reconstrucción de 200 px? ¿El recorte de 20 px se comporta como el de 200 px?
Predicción previa (del investigador): con L = 20 px · 1.29 µm ≈ 26 µm la grilla de Fourier es gruesa (pupila ~3 bins,
paso de LED ~2.5 bins). Si el solver redondea los k de los LEDs a bins enteros, el error de geometría puede llegar a ~20–27 %,
así que el recorte de 20 px debería salir degradado o poco confiable.

## 0. ¿El solver redondea los k de los LEDs? Sí, al bin entero más cercano

* `src/ptyco_full_simulator/spectral_ops.py:34-35` (repo `reproducible-research-template`):
  `cx = int(round((fx_led - fx_axis[0]) / df_x))`, `cy = int(round(...))`. La ventana del espectro HR de cada LED se centra en
  el **bin entero** más cercano a (fx, fy). No hay rampa de fase ni interpolación sub-píxel. El lazo la usa así:
  `scripts/fpm_solver/iter_runner.py:82` (`win = {k: F.led_crop_window(...)}`) y `spec[ys, xs] = ...` (`:105`); también
  `fpm_red.py:137` y `predict` en `fpm_red.py:197`.
* La pupila es una máscara binaria sobre la grilla LR discreta: `optics.py:22-27` (`circular_pupil`, `(FX²+FY²) <= cutoff²`).
* ¿Acepta 20 px? Sí. No hay un tamaño mínimo ni un assert. La única condición es que la ventana entre en el arreglo HR
  (`spectral_ops.py:40-46`), y eso depende del factor, no de n (`optics.py:75-95`). El driver fija el factor en 3
  (`reconstruir_plan.py:261`). Con `--tam 20` el driver correría. Igual usé un envoltorio propio (§2) para que los píxeles
  sean exactamente los de la referencia.
* Hay un desajuste adicional. El driver clasifica BF/DF con el |f| **exacto** (`reconstruir_plan.py:547`), y esa clasificación
  decide el preprocesado del blanco (`fpm_red.py:80`: BF = S/F·⟨F⟩, DF = S − gauss(F, 8)). El modelo directo, en cambio, usa
  el k **redondeado** y la pupila discreta. Si el redondeo mete el DC de un LED DF dentro de la pupila discreta, el modelo
  predice para ese LED una imagen de campo claro, mientras que el dato es una imagen de campo oscuro (unas 250 veces más débil).

Error de redondeo medido con las mismas funciones (`codigo/redondeo.py` → `redondeo.json`; geometría de §1):

| n (px) | L (µm) | Δk (1/µm) | radio pupila (bins) | paso LED (bins) | error mediana / máx (% del paso) | máx (% radio pupila) | LEDs que cambian BF/DF |
|---|---|---|---|---|---|---|---|
| 20 | 26 | 0.0388 | 3.0 (29 px) | 2.5 | 15 % / **27 %** | 23 % | 1 (DF→BF) |
| 40 | 52 | 0.0194 | 6.0 | 5.0 | 7 % / 13 % | 11 % | 0 |
| 80 | 103 | 0.0097 | 12.0 | 10.1 | 4 % / 7 % | 6 % | 0 |
| 200 | 258 | 0.0039 | 30.1 | 25.2 | 1.7 % / 2.6 % | 2.2 % | 0 |

La cuenta numérica de la predicción se confirma: el error máximo es 27 % del paso de LED a 20 px. A 20 px, en **20 de las 25**
partículas un LED diagonal del anillo 1 ((16,14), (18,14) o (18,16), con |f| ≈ 1.15·NA/λ) pasa de DF a BF en el modelo. Cuál
LED cambia depende del offset de cada recorte. En las otras 5 no cambia ninguno.

## 1. Geometría y brazo de referencia

* Geometría (igual en todos los brazos): z 99.5 mm, λ 0.617 µm, **NA 0.0720** (NA·z = 7.16 = borde (a) s fijo de red-c,
  `plan_2026-11-06/archivo/runs/2026-10-30-red-c/zonas.md`), píxel crudo 1.290 µm, factor 3 → píxel HR **0.430 µm**
  (verificado en los logs). Offset del LED según la posición de cada recorte en el sensor (fórmula del driver). Son 160 épocas
  con A+init y paso 0.3 con rampa. La reconstrucción vieja de 400 px (`2026-10-30-red-c`, NA 0.0669, z 102, λ 0.63) no se
  reusó porque tiene otra geometría y otro tamaño.
* Referencia: `reconstruir_plan.py` sin modificar (env `Z_MM=99.5 NA_OBJ=0.0720 LAM_NM=617`, `--tam 200 --epocas 160
  --offset-roi 3968,1966`). Hay **tres** recortes de 200 px (filas,col del ROI): A 440,380; B 770,460; C 520,180.
  * R de ajuste: A 0.405, B 0.453, C 0.392. Lattice C3 OK (≤ 3.8e-3).
  * Hacen falta tres porque con la regla de aislamiento ningún recorte de 200 px junta 15 partículas (máximo ~11). La muestra
    es densa.
* Nulo DF (`NULO_DF=1`, ya existía en el driver: fxy permutadas entre los 220 LEDs DF, seed 0) con los mismos tres recortes.
  R de ajuste 0.62 / 0.65 / 0.59; lattice ALTO (0.15–0.29).

## 2. Partículas y recortes chicos

* Selección (`codigo/seleccionar.py` → `particulas.json`) sobre la imagen BF cruda del LED (17,15) dividida por el flat.
  * En BF cada perla se ve como un lóbulo claro con dos oscuros al costado. Un primer detector por mínimos los contaba como
    dos partículas y lo descarté. El detector final usa la energía local del contraste.
  * Criterios: sin otro candidato (e > 0.10) a menos de 20 px = **25.8 µm**; sin manchas grandes a menos de 20 px; a ≥ 20 px
    del borde del recorte de 200 px.
  * Resultado: **25 partículas** (A 9, B 5, C 11). Vecino más cercano entre 26 y 69 µm, mediana 35 µm.
* Recortes chicos (`codigo/recortes_chicos.py`). Los datos de cada recorte son el **sub-arreglo** del `prep.npz` de 200 px de
  su región: mismo oscuro, flat, exposición, máscara y varianza. Después siguen el mismo `load_real`, la misma geometría (con el
  offset recalculado para el centro del recorte chico), el mismo lazo y las mismas 160 épocas. Variantes:
  * 20 px;
  * 20 px nulo DF (la misma permutación);
  * 20 px **sin el LED que cambia BF/DF** (diagnóstico);
  * 40 px (las 25 partículas) y 80 px (las 16 que entran en su recorte de 200 px).

## 3. Medición

`codigo/medir.py` → `medidas.json/.csv`, `fondo.json`; tabla en `tabla.txt` (`codigo/tabla.py`).

* Normalización local: b = media compleja en el anillo de 7.5–11 µm; amplitud = |o/b|, fase = arg(o/b). Para el LR se usa √I
  dividido por la mediana del anillo.
* Ajuste gaussiano 2D isótropo más una constante, con signo libre, en r < 7 µm. Después se reajusta en r < max(2 µm,
  1.5·FWHM).
* Chequeos:
  * perfil radial (en `medidas.csv`; para la fase falla a menudo porque el spot tiene anillo);
  * similitud con la referencia: correlación de la amplitud y |correlación compleja| en r < 8 µm contra la misma zona de 200 px;
  * control de fondo: el mismo ajuste en 24 posiciones sin partícula.
* En la tabla, × marca un ajuste que tocó el límite de σ (sin spot).

## 4. Resultados

Mediana [Q1–Q3] (n):

| brazo | FWHM amplitud (µm) | FWHM fase (µm) | corr. amplitud con 200 px | \|corr. compleja\| con 200 px |
|---|---|---|---|---|
| LR BF crudo (√I) | 5.29 [5.09–5.39] (25) | — | — | — |
| **200 px** | **3.09 [2.55–3.56] (25)** | 3.99 [3.43–4.35] (24) | 1 | 1 |
| **20 px** (todas) | **3.38 [2.88–4.10] (24)** | 4.42 [3.43–6.97] (24) | 0.74 [0.56–0.79] | 0.79 [0.74–0.86] |
| 20 px, sin LED que cambia (5) | 3.31 [3.28–4.06] | 4.21 [3.95–4.40] | 0.86 [0.86–0.89] | 0.88 [0.87–0.88] |
| 20 px, con LED que cambia (20) | 3.46 [2.84–4.09] (19) | 4.57 [3.43–7.82] (19) | 0.72 [0.55–0.78] | 0.78 [0.73–0.81] |
| 20 px, quitando ese LED (25) | 3.28 [2.76–3.45] | 4.19 [3.35–4.59] | 0.87 [0.84–0.89] | 0.87 [0.85–0.90] |
| 40 px | 3.19 [2.62–3.60] (24) | 4.07 [3.59–4.51] | 0.92 [0.90–0.93] | 0.93 [0.91–0.95] |
| 80 px | 3.04 [2.55–3.72] (16) | 3.87 [2.29–4.27] | 0.94 [0.92–0.95] | 0.94 [0.93–0.95] |
| nulo DF 200 px | 0.92 [0.72–1.24] (24)* | 0.84 [0.55–2.18]* | 0.16 [0.13–0.21] | 0.21 [0.16–0.23] |
| nulo DF 20 px | 0.88 [0.80–1.34] (23)* | 1.79 [0.70–6.56]* | 0.15 [0.12–0.21] | 0.23 [0.20–0.25] |
| fondo sin partícula, 200 px | 2.00 [1.40–2.82] (22) | 2.27 [1.89–2.70] | — | — |
| fondo sin partícula, nulo 200 | 1.67 [0.60–5.24] (19) | 4.39 [0.52–13.6] | — | — |

\* En los nulos no hay spot (fig.). El ajuste se engancha en un grano de speckle de ~2 px HR, igual que en el fondo. Ese número
**no es** el ancho de una partícula.

Razones por partícula (mediana [Q1–Q3]):
* 200 px / LR (amplitud): **0.60** [0.50–0.67].
* 20 px / 200 px: 1.08 [1.00–1.22] en amplitud y 1.09 [1.02–1.81] en fase.
* 20 px sin el LED que cambia / 200 px: 1.03 [0.99–1.05].
* 40 px / 200 px: 1.01 [0.99–1.03].

Error final del solver a 20 px:
* ~0.50 en las 20 partículas con un LED que cambia, contra ~0.01 en las 5 sin cambio.
* Quitando ese LED baja a 0.006–0.024. El residuo de ese único LED (DF tratado como BF) domina la suma.
* Referencia a 200 px: 0.006–0.010.

Tabla por partícula (FWHM en µm; corr = amplitud / compleja contra 200 px):

| id | vecino µm | LR | 200 amp | 200 fase | 20 amp | 20 fase | 20 corr | LED que cambia (20 px) | 20 sin ese LED amp / corr cplx | 40 amp | 80 amp | nulo 200 amp / fase | nulo 20 amp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A01 | 47 | 5.3 | 3.1 | 6.2 | 3.6 | 3.4 | 0.79 / 0.74 | (16,14) | 3.3 / 0.85 | 3.1 | — | 1.2 / 0.8 | 0.8 |
| A02 | 43 | 5.1 | 3.1 | 3.9 | 3.3 | 2.9 | 0.80 / 0.72 | (16,14) | 3.1 / 0.90 | 3.0 | 3.1 | 1.3 / 0.3 | 6.8 |
| A03 | 37 | 5.4 | 1.1 | 3.9 | 5.6 | 13.5 | 0.73 / 0.70 | (16,14) | 7.3 / 0.81 | 1.5 | — | 0.5 / 1.7 | 0.3 |
| A04 | 35 | 5.3 | 3.1 | 4.2 | 3.2 | 4.4 | 0.79 / 0.77 | (16,14) | 3.2 / 0.82 | 3.0 | 3.0 | 0.8 / 0.5 | 0.5 |
| A05 | 51 | 5.3 | 6.8 | 4.2 | 4.3 | 4.4 | 0.86 / 0.88 | ninguno | 4.3 / 0.88 | 3.8 | 3.7 | 0.7 / 2.7 | 0.7 |
| A06 | 33 | 5.4 | 3.8 | 4.5 | 4.1 | 4.6 | 0.83 / 0.85 | ninguno | 4.1 / 0.85 | 4.1 | 4.0 | 1.1 / 2.1 | 0.8 |
| A07 | 30 | 5.4 | 3.4 | 4.1 | 3.3 | 4.2 | 0.86 / 0.87 | ninguno | 3.3 / 0.87 | 3.5 | 3.4 | 2.8 / 2.9 | 0.9 |
| A08 | 30 | 5.1 | 1.0 | 18.8× | 1.6 | 11.9 | 0.56 / 0.59 | (18,14) | 3.3 / 0.86 | 1.0 | 1.3 | 18.8× / 2.8 | 3.6 |
| A09 | 69 | 5.3 | 3.3 | 4.3 | 3.8 | 4.6 | 0.74 / 0.78 | (18,14) | 3.2 / 0.91 | 3.3 | — | 0.9 / 0.3 | 0.8 |
| B01 | 55 | 5.5 | 2.1 | 1.5 | 2.5 | 1.7 | 0.77 / 0.89 | (18,14) | 2.2 / 0.87 | 2.1 | 2.1 | 0.7 / 0.7 | 1.4 |
| B02 | 30 | 5.1 | 2.5 | 1.7 | 2.5 | 3.4 | 0.89 / 0.88 | ninguno | 2.5 / 0.88 | 2.5 | 2.5 | 0.4 / 0.8 | 0.8 |
| B03 | 40 | 5.2 | 3.5 | 4.6 | 3.5 | 4.6 | 0.78 / 0.79 | (18,16) | 3.5 / 0.86 | 3.5 | — | 1.1 / 0.5 | 0.6 |
| B04 | 33 | 13.1 | 0.9 | 3.3 | 18.8× | 12.8 | 0.30 / 0.44 | (18,14) | 0.9 / 0.84 | 18.8× | 0.9 | 3.1 / 0.8 | 18.8× |
| B05 | 29 | 4.9 | 2.6 | 3.9 | 13.8 | 18.8× | 0.14 / 0.17 | (18,14) | 2.8 / 0.76 | 2.7 | 2.7 | 0.4 / 18.8× | 15.2 |
| C01 | 26 | 5.3 | 3.2 | 3.9 | 3.3 | 3.9 | 0.90 / 0.92 | ninguno | 3.3 / 0.92 | 3.2 | — | 0.7 / 0.8 | 0.9 |
| C02 | 60 | 5.2 | 2.7 | 3.5 | 2.9 | 3.3 | 0.72 / 0.77 | (18,14) | 2.7 / 0.82 | 2.6 | 2.7 | 0.7 / 0.8 | 0.8 |
| C03 | 46 | 7.2 | 4.1 | 2.0 | 2.5 | 8.2 | 0.52 / 0.81 | (18,14) | 3.0 / 0.86 | 3.5 | 3.8 | 4.5 / 3.4 | 3.5 |
| C04 | 30 | 5.1 | 2.5 | 1.5 | 2.8 | 3.4 | 0.78 / 0.82 | (18,14) | 2.6 / 0.85 | 2.5 | 2.6 | 1.1 / 0.7 | 0.9 |
| C05 | 30 | 5.1 | 3.8 | 4.7 | 6.0 | 7.5 | 0.49 / 0.76 | (18,14) | 3.9 / 0.90 | 3.8 | 3.8 | 1.9 / 0.3 | 18.8× |
| C06 | 29 | 6.3 | 1.4 | 0.3 | 1.4 | 1.5 | 0.73 / 0.85 | (18,14) | 2.1 / 0.87 | 2.3 | — | 1.0 / 0.6 | 4.1 |
| C07 | 39 | 4.9 | 4.0 | 4.2 | 3.9 | 6.8 | 0.42 / 0.86 | (18,14) | 4.3 / 0.96 | 4.5 | — | 0.9 / 1.6 | 1.3 |
| C08 | 29 | 5.4 | 3.8 | 4.6 | 3.6 | 5.6 | 0.55 / 0.79 | (18,14) | 3.8 / 0.90 | 3.9 | 3.8 | 0.7 / 0.3 | 0.8 |
| C09 | 30 | 5.1 | 3.6 | 6.0 | 4.6 | 9.7 | 0.57 / 0.86 | (18,14) | 3.3 / 0.91 | 3.8 | 3.6 | 0.6 / 7.2 | 0.9 |
| C10 | 49 | 5.4 | 3.3 | 4.1 | 4.2 | 4.2 | 0.72 / 0.81 | (18,14) | 3.4 / 0.92 | 3.4 | — | 2.2 / 2.5 | 0.9 |
| C11 | 35 | 5.0 | 3.0 | 3.6 | 3.2 | 4.2 | 0.74 / 0.73 | (18,14) | 3.1 / 0.91 | 3.0 | — | 1.0 / 0.6 | 1.0 |

### Artefactos cualitativos (`fig_recortes.png`: A01, A05, B02, C01, C05, C08)

* Las reconstrucciones de 20 px **no salen en blanco** ni muestran wrap-around evidente. La partícula aparece en el mismo
  lugar, con la misma forma que en 200 px: núcleo oscuro con anillo claro en amplitud, y spot de fase negativo.
* Cuando hay un LED que cambia BF/DF:
  * aparece una rampa o un fondo de fase de baja frecuencia que cruza el recorte (A01, C05, C08);
  * hay más anillos y lóbulos alrededor de la partícula (C05 amplitud, C08);
  * en B04 y B05 la partícula se pierde (corr 0.30 y 0.14).
* Sin ese LED (o en las 5 partículas sin cambio), el recorte de 20 px es casi indistinguible a ojo del de 200 px.
* En los nulos DF (200 y 20 px) no aparece ninguna partícula reconocible. Queda un speckle de grano fino orientado en
  horizontal, y la correlación con la referencia es de 0.15–0.23.

## 5. Lectura (sin ir más allá de los datos)

1. **Redondeo: confirmado.** Los k de los LEDs se redondean al bin entero (`spectral_ops.py:34-35`). A 20 px el error llega a
   27 % del paso de LED, como predecía la cuenta.
2. **La degradación predicha se ve, pero no por la vía esperada.** A 20 px la similitud con la referencia cae de forma marcada:
   compleja 0.79 contra 0.93–0.94 a 40–80 px. El ancho del spot crece poco (+8 % en la mediana) pero se dispersa mucho más
   (Q3 1.22 contra 1.03 a 40 px), con 3 de 25 partículas rotas (A03, B04, B05). La mayor parte de esta degradación viene de un
   solo efecto discreto: el LED diagonal que pasa de DF a BF por el redondeo. El error de posición de los demás LEDs aporta poco.
   * Quitando ese LED, el recorte de 20 px queda en 1.03 [0.99–1.05] de la FWHM de 200 px, con correlación compleja 0.87.
   * Eso es similar a las 5 partículas donde no hay cambio, aunque peor que 40 px (0.93).
   * **Esto contradice en parte la predicción**: un error de redondeo de 15–27 % del paso, por sí solo, no rompe el recorte de
     20 px en estos datos.
3. **¿El spot se achica?** En 200 px la FWHM de amplitud es 0.60 veces la del LR crudo (3.1 contra 5.3 µm), y el recorte de
   20 px da lo mismo (3.3–3.4 µm). Dos salvedades importantes:
   * en el LR la gaussiana ajusta el lóbulo **claro** central, y en la reconstrucción ajusta un núcleo **oscuro** rodeado de
     anillo; no es la misma estructura;
   * el ajuste en fondo sin partícula ya da ~2 µm.

   La razón 0.60 no se debe leer como un factor de resolución.
4. **Nulo DF:** el spot **no** se achica en el nulo, desaparece. El ~0.9 µm del ajuste es el mismo grano que aparece en el
   fondo del nulo. La forma de la partícula en 200 px y en 20 px depende de que los LEDs DF estén en su lugar (corr 0.8–0.9
   contra 0.2 en el nulo). Con este control no aparece un afinamiento genérico que dé la misma forma sin la geometría correcta.
   Que haya o no super-resolución no se decide con estos números: el spot de 3 µm sigue siendo mucho mayor que la perla de 0.5 µm.

## 6. Salvedades

* La regla de aislamiento original no se pudo cumplir con un solo recorte de 200 px: la densidad no lo permite. Por eso hay tres
  recortes de referencia (A, B, C). Varias partículas tienen un vecino a 26–30 µm.
* La FWHM gaussiana es frágil cuando el spot tiene anillos. Hay ajustes malos en las tres columnas (A03, A08, B04, C06). El
  perfil radial de fase falla en ~40 % de los casos. Por eso conviene mirar las medianas y las correlaciones, no las filas
  sueltas.
* En el recorte chico, el fondo DF (`gauss(F, 8)`) y ⟨F⟩ se calculan sobre 20 px. Es lo mismo que haría el driver, pero no es
  idéntico a la referencia. La variante "sin el LED que cambia" no separa este efecto del redondeo.
* Hay una sola corrida (semilla y permutación del nulo fijas), una sola geometría y 160 épocas. No probé k sub-píxel (por
  ejemplo, una rampa de fase), así que no está medido cuánto del 0.87 restante se debe al redondeo y cuánto a los bordes o la
  periodicidad del recorte.
* La clasificación BF/DF exacta contra la discreta depende del offset de cada recorte. Con otra geometría (z, NA) los LEDs que
  cambian serían otros.

## 7. Tiempos (4 núcleos compartidos con Chrome)

* 200 px: 6 corridas en paralelo, ~14 min cada una (C y nulo C: ~9 min).
* Recortes chicos (2 procesos):
  * 20 px: 10–42 s por partícula según la carga (8.4 min las 25 con carga; 2.7–3 min sin carga);
  * 40 px: 19 s;
  * 80 px: 44 s.
* Total de pared: ~1 h 20 min, incluida la selección y la medición.

## Archivos

* `codigo/`:
  * `explorar_bf.py`, `seleccionar.py`: selección de partículas;
  * `correr_ref.sh`, `correr_ref_C.sh`: referencias y nulos;
  * `recortes_chicos.py`, `correr_chicos.sh`: brazo de recortes chicos;
  * `redondeo.py`, `medir.py`, `tabla.py`, `figura.py`.
* Datos de partículas y regiones: `particulas.json`, `datos/q_bf_roi.npy`.
* Corridas: `runs/ref_{A,B,C}`, `runs/nulo_{A,B,C}` (salida estándar del driver) y
  `runs/chicos_{20,20_nulo,20_sincambian,40,80}/<id>.npz`.
* Resultados: `medidas.json/.csv`, `fondo.json`, `redondeo.json`, `tabla.txt`, `resumen_medidas.txt`, `fig_recortes.png`.

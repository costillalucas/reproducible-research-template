# Glosario y preguntas de la revisión

Preguntas que fueron saliendo al revisar la presentación, con la respuesta corta
y dónde vive cada cosa en el repo. Sirve para dos cosas: contestar en la sala si
alguien pregunta, y como material para la segunda presentación.

---

## Contraste de amplitud

El objeto sintético es `o(x) = A(x)·exp(iφ(x))`, y la amplitud se arma así
(`scripts/plan_common.py`, `src/ptyco_full_simulator/test_objects.py`):

```
A = min_amp + (1 − min_amp) · (imagen normalizada a [0,1])
```

`A` vive en `[min_amp, 1]`, y el contraste es **`1 − min_amp`**: cuánto varía la
amplitud transmitida entre puntos, con el máximo normalizado a 1.

- contraste 20 % → `min_amp` 0.8 (transmite entre 80 % y 100 %)
- contraste 5 % → `min_amp` 0.95
- contraste 0 % → `min_amp` 1.0: amplitud uniforme, **objeto de fase pura**

Importa porque las muestras biológicas casi transparentes están en ese régimen de
pocos por ciento, que es justo donde el solver se rompe (fig01).

---

## Fase débil (y fase máxima del objeto)

La otra mitad del objeto complejo. Si el contraste de amplitud es cuánto **atenúa**
la muestra, la fase es cuánto **retrasa** la luz que la atraviesa:

```
φ(x) = (2π/λ) · (n − n_medio) · t(x)
```

"Fase débil" = la excursión máxima de fase del objeto es chica. En los barridos el
parámetro es `phase_max` y el régimen que no se recupera es **φ_max ≤ 0.1π** (≈ 0.31 rad).

Para dimensionarlo: a 530 nm, φ_max = 0.1π equivale a `(n − n_medio)·t ≈ 26 nm`.
Con un contraste de índice típico de tejido en medio acuoso (Δn ≈ 0.05), eso es una
muestra de ~0.5 µm de espesor. Es decir, exactamente el objeto biológico fino y casi
transparente que el proyecto declara como objetivo.

Los dos límites son independientes y la muestra objetivo cae en los dos: **poco
contraste de amplitud** (casi no absorbe) y **fase débil** (casi no retrasa). Por eso
las dos primeras figuras de validación sintética son las que más condicionan el
proyecto.

Medido: con φ_max ≤ 0.1π ningún solver pasa de ~0.25 de correlación, en todo objeto y
nivel de fotones; y a 0.05π el RMSE del resultado (0.097) es **peor** que el de no
poner fase (0.022) — es decir, la correlación sobrestima lo recuperado.

---

## TIE (Transport of Intensity Equation)

Método clásico de recuperación de fase **no iterativo**: con la intensidad en foco
`I` y su derivada axial `∂I/∂z` (diferencia finita entre una captura en foco y otra
levemente desenfocada), la fase sale de resolver

```
∇·( I ∇φ ) = −k · ∂I/∂z
```

una ecuación de Poisson con peso, que se resuelve de una. En el repo es
`propagation.solve_tie` (con regularización donde `I ≈ 0`).

No lo usamos como reconstructor sino como **inicialización**: en vez de arrancar
con fase cero, se arranca con la fase de TIE. Eso saca al solver de la cuenca mala
en objetos de bajo contraste: **0.39 → 0.99** de correlación de fase.
Cableado como `--tie-defocus-um`.

Caveats: TIE da fase de baja frecuencia (aproximación de desenfoque chico). La
ganancia sobrevivió a la re-medición con el paso descongelado, pero el mecanismo
no es el que decía el registro original: no destraba un punto de silla, el arranque
por defecto cae en un **mínimo local que ya ajusta bien los datos**.

---

## La métrica de fase y el "techo de π"

La métrica es `phase_correlation`: Pearson entre la fase reconstruida y la
verdadera, píxel a píxel (`src/ptyco_full_simulator/metrics.py`). Antes de
correlacionar, ambas pasan por `_normalize_phase`:

```python
wrapped = np.angle(np.exp(1j * phase))   # envuelve a (−π, π]
return wrapped - wrapped.mean()          # saca el pistón global
```

Sacar el pistón es correcto: FPM recupera la fase salvo una constante aditiva.

El problema es el envolvimiento: si la fase verdadera pasa de π en valor absoluto,
**la verdad también se envuelve**, así que la referencia contra la que puntuás ya
no es la fase real sino una versión envuelta y discontinua. A partir de ahí la
métrica premia reproducir los saltos de envolvimiento y castiga una reconstrucción
desenvuelta correcta: deja de medir calidad.

Métricas hermanas en el mismo módulo: `phase_rmse_rad` (misma normalización),
`amplitude_rmse`, `amplitude_correlation`; y para datos reales
`correlate_against_hr_reference` (Pearson tras z-scorear las dos imágenes y probar
las 4 combinaciones de espejado).

---

## Fase inyectada

Validar la cadena de acople RGB (desenvolvimiento multi-λ + ajuste de Cauchy)
**sin pasar por el solver**: en vez de simular las 81 capturas y reconstruir φ(λ)
en cada canal, se le entregan a la cadena los mapas de fase construidos a partir
de un espesor y una dispersión conocidos.

Se hace porque el aporte novedoso necesita fase > π para tener sentido, y el solver
no llega a ese régimen. Por eso los tests están separados a propósito:

- **con el solver real y fase chica** → correlación de espesor **0.88**, end-to-end de verdad;
- **con fase inyectada y señal de dispersión grande** → el factor **183x** contra el
  baseline ingenuo.

Consecuencia para lo que se dice en voz alta: el 183x es un resultado **sobre el paso
de desenvolvimiento**, no sobre el pipeline completo.

---

## Desenvolver, y "envolvimiento espurio"

La fase se mide módulo 2π: lo que se recupera es φ envuelta en (−π, π]. La real es

```
φ_real(x) = φ_medida(x) + 2π·k(x)
```

con `k(x)` entero: el **número de envolvimiento**. Desenvolver es recuperar ese
entero. Físicamente, cada unidad de `k` es un camino óptico entero (un salto de una
longitud de onda completa en el espesor).

El truco multiespectral: la diferencia de fase entre dos canales se comporta como si
midieras con una **longitud de onda sintética** (de batido)

```
Λ = λ₁·λ₂ / |λ₁ − λ₂|
```

Con 530 y 470 nm, Λ ≈ 4.1 µm: envuelve mucho más lento, así que sirve para estimar
`k` y después desenvolver cada canal.

**Envolvimiento espurio** = un píxel donde ese `k` sale mal (típicamente ±1), porque
el ruido o el error de reconstrucción lo cruzó de frontera. No es un error chico: es
un salto de un camino óptico entero en ese píxel, un outlier gigante. Un puñado de
esos píxeles dominaba el Pearson sobre toda la imagen y hacía parecer que acoplar
empeoraba.

---

## Qué gana el acople de los tres canales

Lo que se compara es un **mapa de espesor**, no fase ni resolución. La métrica del
eje y de fig02 es la correlación de Pearson con el espesor verdadero
(`corr_coupled_masked`, `corr_naive`, `corr_coupled` en
`data/coupled_opl_ceiling_sweep*.json`).

- **Ingenua**: la fase envuelta de cada canal tomada como si ya fuera camino óptico.
- **Acoplada**: fase por canal → pistón → desenvolvimiento multi-λ → Cauchy → espesor.

Ganancia medida en escalas 1/2/4: **0.80 / 0.88 / 0.93** (acoplada + máscara) contra
**0.66 / 0.82 / 0.89** (ingenua). Sin filtrar, la acoplada cae a 0.11/0.30/0.35.

A partir de escala 8 la fracción enmascarada salta a 68–93 %: el filtro deja de ser
filtrado de outliers y pasa a tirar señal real. Mejora más barata pendiente: usar
`pair_disagreement` (confianza por píxel, ya calculada, sin usar).

Dos precisiones: la correlación de Pearson es insensible a escala y offset, así que
el 183x (reducción de **error** de espesor, con fase inyectada) es el número
complementario; y acoplar **no** gana resolución ni mejora la fase de cada canal:
es un post-procesado que resuelve la ambigüedad de 2π.

---

## Grilla HR común

Cada canal tiene su propio factor de sobremuestreo, porque depende de λ: sin hacer
nada, las reconstrucciones de rojo, verde y azul caen en grillas de distinto paso y
distinto tamaño, y no se pueden apilar ni comparar píxel a píxel.

El arreglo es `optics.shared_upsampling_factor(setups)`: toma el **máximo** de los
factores por canal (manda el de menor λ, típicamente el azul), de modo que ningún
canal quede submuestreado y los tres compartan exactamente el mismo
`hr_pixel_um` y el mismo `hr_shape`. Los tres objetos salen apilables en un array
`(3, H, W)` sin ningún resize.

Probado en `tests/test_multispectral_registration.py`. Caveat de procedencia: se
validó contra objeto sintético, no contra las capturas reales del laboratorio
(roadmap, hito 1).

---

## Ajuste de Cauchy

Modelo de dispersión: el índice de refracción de un material transparente se
aproxima con `n(λ) = A + B/λ²`. Como el camino óptico es `OPL(λ) = n(λ)·t`,

```
OPL(λ) = A·t + (B·t)/λ² = C + D/λ²,   con   C := A·t,  D := B·t
```

`fit_cauchy_dispersion` (en `multispectral.py`) ajusta ese modelo de 2 parámetros
por píxel a los mapas de OPL desenvueltos de 2 o más canales: con 2 canales es un
sistema 2×2 exacto, con 3 es mínimos cuadrados sobre-determinado (ahí está el
beneficio de promediar ruido usando los tres RGB en vez de elegir dos). Devuelve
`C`, `D` y los **residuos por píxel**, que son un diagnóstico útil: un residuo
grande significa que el modelo de Cauchy no describe ese píxel (absorción o
resonancia cerca de esas longitudes de onda), independiente del ruido de medición.

**El hallazgo teórico propio del proyecto está acá**: de fase multi-λ sola se miden
`C` y `D`, es decir los **productos** `A·t` y `B·t`, nunca `A`, `B` y `t` por
separado. Una muestra más gruesa con menos dispersión es indistinguible de una más
fina con más dispersión. No es una limitación del método de ajuste: el modelo tiene
solo 2 grados de libertad identificables, y agregar longitudes de onda no rompe la
degeneración — hace falta un dato externo (`resolve_thickness_and_dispersion`).

El roadmap original decía "3 incógnitas, 3 ecuaciones, exactamente determinado" con
3 canales; eso subestimaba la degeneración y quedó corregido.

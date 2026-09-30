# Reconstrucción conjunta de tres colores con un espesor compartido — informe

**Resultado: NEGATIVO, y el negativo es sólido.** El método se construyó entero, el gradiente está
verificado a 1e-8, las corridas llegaron a 240 épocas y bajaron el costo **por debajo del piso de ruido
de la simulación** — y aun así el espesor que encuentran **no tiene ninguna relación con el verdadero**
(correlación −0.09, donde 1 sería perfecto y la línea base que hay que superar vale 0.94). No es que
falten épocas ni que se haya caído en un mínimo local feo: el mínimo del costo especificado **no está
donde está la verdad**. Por esa razón, y siguiendo la regla del propio plan, **no se pasó a datos reales**.

Todos los números de este informe salen de `resultados.json` (mismo directorio), que es el archivo
citable; las figuras están en `figs/` y los números que dibujan en `figs/datos_figuras.json`.

---

## 1. Qué se hizo

Se escribió desde cero `joint.py`: un solver que ajusta **un solo mapa de espesor** `t(x)` común a los
tres colores, en vez de reconstruir rojo, verde y azul por separado y después combinarlos. Se corrió
sobre la simulación de `results/sim_multiespectral_2026-09-29/`, cuya verdad se conoce, con las cuatro
variantes del plan (amplitud por color A1 o compartida A2; dispersión fija D1 o ajustada D2) y con dos
puntos de partida distintos. Se implementaron **las dos** variantes de algoritmo que permite el plan
(gradiente de lote completo, y ePIE por color + proyección al modelo conjunto) y se ejecutó su regla de
selección sobre un recorte chico, que es lo que el plan manda (sección 10). Las métricas S1, S2 y S3 se calcularon con `metricas.py`, **el mismo código**
que se usó para recalcular las referencias, todo sobre una grilla común de 1600 px a 0.32 µm (el "factor
4" del plan: con factor 3 se caerían fuera 5 ventanas de LED en verde y 49 en azul; con factor 4 entran
las 225 en los tres colores).

Antes de correr nada se comprobó que el gradiente analítico es correcto: `gradcheck(seed=0) = 1.03e-8`
contra diferencias finitas centrales (el umbral pedido era 1e-5), y el verificador lo rehízo con su
propio código y obtuvo 6.0e-9. O sea: **lo que sigue no es un error de programación del gradiente.**

## 2. El modelo, en dos párrafos

La idea física es que la muestra es un objeto de fase: una partícula de espesor `t(x)` y una diferencia
de índice `Δn(λ) = A + B/λ²` respecto del medio. Un haz que la atraviesa acumula un retardo de fase que
depende del color, `κ_c·t(x)` con `κ_c = 2π·Δn(λ_c)/λ_c`. Entonces el objeto complejo que ve cada color es

    O_c(x) = g_c · a_c(x) · exp( i · κ_c · t(x) )

con `a_c(x)` la amplitud (la absorción) y `g_c` una ganancia escalar por color. La ventaja esperada es
doble: (a) los tres colores comparten **una sola** incógnita de espesor, así que hay tres veces más datos
para la misma cantidad de parámetros; (b) como `κ_c` es distinto en cada color, la ambigüedad de "vueltas
de fase" (el espesor sólo se conoce módulo λ/Δn) se rompe sola — es el mismo truco del desenvolvimiento
multicolor, pero hecho **dentro** del ajuste en lugar de después.

El ajuste minimiza la diferencia entre las fotos medidas y las predichas por el modelo directo de FPM
(recortar la ventana del LED en el espectro, multiplicar por la pupila, antitransformar, tomar el módulo),
sumando sobre los 225 LEDs y los tres colores. Las incógnitas son `t(x)` (2.56 millones de píxeles),
`a_c(x)` (uno o tres mapas más), `g_c` y, en la variante D2, también `B`. Se optimiza con Adam de lote
completo; `g_c` tiene mínimo cerrado y se resuelve exactamente en cada época en vez de darle pasos.

## 3. Los números, contra sus referencias

| criterio | qué mide | valor obtenido | referencia | ¿pasa? |
|---|---|---|---|---|
| **S1** | correlación del espesor con la verdad | **−0.0915** | 0.9449 (mejor línea base) / umbral 0.90 | **NO** |
| **S2** | error de fase conjunta − independiente (rad) | **+0.669** | 0.0 (pasa si es negativo) | **NO** |
| **S3** | FRC entre mitades, conjunta − independiente | +0.0675 | 0.0 (pasa si es positivo) | sí, *pero ver §5* |
| **B** | dispersión ajustada (variante D2) | **−0.002341** | +0.0015 (tolerancia ±0.0005) | **NO** |

S1 por corrida, **todas a 240 épocas**: A1_D1 −0.0915, A1_D2 −0.0912, A2_D1 −0.0259, A1_D1_cad +0.4385†.
**Ninguna se acerca al umbral.** Las cuatro corridas, más las dos mitades, terminaron las 240 épocas
pedidas; todas están convergidas según la regla del propio plan (menos del 1 % de caída de costo en las
últimas 10 épocas) **salvo A1_D1_cad**.

† **`A1_D1_cad` no está convergida:** su costo todavía cae **3.54 %** entre la época 230 y la 240 (el plan considera
convergida una corrida cuando cae menos del 1 %), y su historia de costo ni siquiera es monótona. Su S1 = +0.4385 es
un valor **en tránsito**, no final — y la tendencia es a **bajar** (0.557 → 0.456 → 0.440 → 0.4385). Cada vez que
aparece el +0.4385 en este informe hay que leerlo así.

Para poner el −0.09 en escala: reconstruir cada color por separado y combinarlos con la cadena
de tres colores da 0.115; con el par verde+azul y dispersión conocida da **0.945**. La conjunta no sólo no
mejora la línea base: queda por debajo de todas, incluso de la peor.

**A1 contra A2, ahora sí a igual número de épocas (240 las dos).** El plan elige "la mejor" por menor
costo final, y eso da A1_D1: 4.0016e5 contra 8.8930e5 de A2_D1, un factor **2.2**. Y A1 le ganaba ya en
todas las épocas intermedias medidas (80: 5.86e5 contra 1.033e6; 105: 5.02e5 contra 9.99e5; 120: 4.72e5
contra 9.82e5). La elección no era un artefacto de épocas desiguales — ése era el único reparo que
quedaba abierto y **queda cerrado**.

Lo interesante es el contraste: **A2 nunca baja del piso de ruido** (se queda en 2.15 × el piso), porque
suponer una sola amplitud para los tres colores le quita dos tercios de los grados de libertad de
amplitud. **Y aun así A2 tampoco recupera el espesor**, y también empeora al optimizar: S1 = −0.0155 a
las 80 épocas, −0.0233 a las 120, **−0.0259 a las 240**; su S2 pasa de +0.425 a **+0.730**. Es decir: el
fracaso de S1 **no se explica sólo por tener demasiados grados de libertad en la amplitud.** La variante
más restringida, la que ni siquiera consigue ajustar las fotos hasta el ruido, falla igual en el espesor.
El problema está en cómo entra `t`, no en cuánta libertad tiene `a`.

`B` no sólo falla su tolerancia por un factor ~8: sale con **el signo contrario** al verdadero. El ajuste
arranca en B = 0 (no se le da la verdad), y ya en la primera época está en −5e−5; de ahí baja de forma
**monótona** durante las 240 épocas hasta −0.002341, sin pasar nunca por el lado positivo (figura 4). No es
que el ajuste no encuentre la dispersión: es que le conviene ir para el otro lado. Deja de ser un ajuste
de dispersión física y pasa a ser un parámetro más con el que absorber el desajuste del modelo.

## 4. Por qué falla (esto es lo importante)

**El costo llega al piso de ruido con un espesor que no es el verdadero.** Se midió el piso de ruido de
la simulación evaluando el costo en el objeto exactamente limitado en banda que generó las fotos:
**4.1283e5**. El costo del objeto verdadero paramétrico es 4.1403e5 (0.3 % más). A 240 épocas:

- A1_D2 llega a **3.9418e5** = 0.955 × el piso de ruido,
- A1_D1 llega a **4.0016e5** = 0.969 × el piso de ruido,

es decir, **las dos ajustan las fotos mejor que la verdad misma**, y sin embargo su S1 es −0.09. Eso es la
definición operativa de un problema no identificable: hay configuraciones `(t, a, g)` completamente
distintas de la verdadera que explican los datos igual de bien o mejor. Con ~10 millones de parámetros
libres contra 108 millones de mediciones ruidosas, y con `t` entrando sólo a través de exponenciales
complejas que dan vueltas, el modelo se come el ruido. Esto **refuta** lo que se había supuesto en la
ronda 1 ("la verdad todavía tiene el costo más bajo de todos, así que el mínimo global está en el lugar
correcto"): no lo está. Figura 1.

**Optimizar más lo empeora, de forma monótona.** S1 de la época 80 → 180 → 240:

| corrida | ép. 0 | ép. 80 | ép. 180 | ép. 240 |
|---|---|---|---|---|
| A1_D1 | −0.152 | −0.037 | −0.079 | **−0.0915** |
| A1_D2 | −0.152 | −0.043 | −0.077 | **−0.0912** |
| A1_D1_cad | +0.557 | +0.456 | +0.440 | **+0.4385** (en tránsito, sin converger) |
| A2_D1 (ép. 120 en vez de 180) | −0.152 | −0.015 | −0.023 | **−0.0259** |
| mitad 0 del damero | −0.152 | −0.068 | — | **−0.112** |
| mitad 1 del damero | −0.152 | +0.035 | — | **−0.027** |

En las seis, más ajuste = peor espesor. No hay ninguna cantidad de épocas que rescate S1, y esto ya no es
una tendencia leída en tránsito: cinco de las seis corridas están convergidas según la regla del plan.
Figura 2.

**El caso más elocuente es A1_D1_cad.** Esa corrida *arranca* del espesor que da la cadena multicolor,
que ya tiene S1 = +0.557. El ajuste la empuja **a abandonarlo** (baja a +0.4385, y sigue bajando: la corrida
no llegó a converger, ver † en §3) mientras el costo cae de
1.79e7 a 6.11e5. Y al final esa corrida, que es la que tiene el mejor espesor de todas, es también la que
tiene **el peor costo** (6.11e5 contra 4.00e5 de A1_D1). Dicho de otro modo: **el costo y la calidad del
espesor apuntan en direcciones opuestas.** Cualquier regla que elija por costo — y el plan elige por costo,
porque con datos reales no hay otra cosa — elegirá la peor reconstrucción de espesor. Figura 3: el mapa de
`t` de A1_D1 es una textura de contraste bajo sin relación con las partículas, mientras el de A1_D1_cad
todavía las muestra.

## 5. Dos criterios que resultaron mal planteados (se informan, no se retocaron)

El spec ordena informar los criterios mal planteados en lugar de ajustarlos. Hay dos.

**S3 no mide el espesor.** Aparece como "pasa" (**+0.0675**) y no significa nada. Ahora está medido con
**las dos mitades y la corrida completa a las mismas 240 épocas**, las tres convergidas según la regla del
plan (caída de costo en las últimas 10 épocas: 0.75 %, 0.87 % y 0.65 %), así que ya no queda ninguna
salvedad de épocas desiguales. Y el resultado es peor de lo que parecía:

| | época 80 | época 240 |
|---|---|---|
| S3 (min sobre colores, conjunta − independiente) | +0.0559 | **+0.0675** (mejora) |
| S1 de la mitad 0 | −0.068 | **−0.112** (empeora) |
| S1 de la mitad 1 | +0.035 | **−0.027** (empeora) |
| FRC entre mitades (rojo / verde / azul) | 0.939 / 0.985 / 0.982 | **0.967 / 0.989 / 0.993** |

Es decir: **al optimizar más, S3 mejora mientras el espesor que S3 debería certificar empeora, en las dos
mitades a la vez.** Las dos mitades del damero se parecen cada vez más entre sí y cada vez menos a la
verdad. La razón es que la FRC se calcula sobre el objeto complejo `O_c`, que está dominado por la
amplitud `a_c` — y la amplitud **sí** se reconstruye bien. Las dos mitades coinciden entre sí en algo que
no es el espesor. S3 nunca podría haber detectado este fracaso: es un criterio de *autoconsistencia*, y el
modo de falla de este problema es justamente que el ajuste es autoconsistente y equivocado.

**El umbral de S1 quedó por debajo de su propia línea base.** El plan fija "pasa si S1 ≥ 0.90" y anota
0.80 como referencia de la cadena verde+azul con dispersión conocida. Al recalcularla con este código da
**0.9449**. El 0.80 del plan salía de `couple_rgb_channels` de *tres* colores, donde el rojo se cuela igual
por `opl["green"] = ½(par rojo-verde + par verde-azul)` (`multispectral.py:393`). Con el par verde-azul
genuinamente limpio de rojo, la línea base es 0.9449 — **más alta que el umbral**. Un método con S1 = 0.92
habría "pasado" siendo peor que lo que ya existe. Se informa y se deja la clave `supera_referencia` al
lado de `pasa`; no cambia nada acá, porque el valor medido es −0.09.

Un corolario incómodo para el *motivo* del trabajo: la premisa "reconstruir por color y después combinar
falla" es cierta para la cadena libre de tres colores (S1 = 0.115) pero **no** para el par verde+azul con
dispersión conocida (S1 = 0.945, error cuadrático medio 0.62 µm sobre una muestra de hasta 21 µm). En
simulación esa cadena ya casi resuelve el problema. La conjunta tenía que competir contra 0.94, no contra
0.11.

**Un cambio de número que conviene no malinterpretar:** el "techo" de la cadena libre (lo que daría la
cadena si las fases por color fueran perfectas) subió de 0.587 a 0.704 al recalcularlo. Se separaron las
dos causas posibles con un solo código: grilla 1200→1600 aporta **+0.01**; margen 60→100 px aporta
**+0.09 a +0.11**. Es decir, **fue el margen, no la grilla**: el error de la cadena libre está concentrado
en el borde del campo. No hay ningún cambio de comportamiento del desenvolvimiento.

## 6. Datos reales: omitidos, por regla

**No se corrieron los datos reales de la captura 2026-09-28 (b).** El plan (línea 74) dice: *si S1 falla
para todas las variantes, no se pasa a datos reales.* S1 falla en las cuatro corridas evaluadas. Correr el
método sobre datos reales, donde no hay verdad para compararlo, sólo produciría un mapa de espesor sin
manera de saber si significa algo — y en simulación ya está medido que no significa nada. **La omisión es
por regla, no por falta de tiempo de cómputo.** Queda registrada así en `resultados.json` → `real.omitido`.

## 7. Una desviación del plan, declarada

El costo del plan pesa cada LED con 1. Acá se agregó un escalar `s_ck` por (color, LED), ajustado en forma
cerrada. Motivo: el generador de las fotos reescala **cada LED por su propio factor**
(`sim.py:79`), con un rango de 0.093 a 0.919 en rojo — un factor 9.9 entre LEDs que una sola ganancia por
color no puede absorber. Sin ese escalar el costo literal del plan **ni siquiera tiene su mínimo en la
verdad**: la verdad cuesta 1.0949e7 y 15 épocas de Adam ya bajan a 1.0141e7. La desviación está autorizada
por el PI y anotada en `resultados.json` → `desviaciones_del_plan`.

## 8. Figuras

- `figs/fig1_costo_vs_epoca.png` — costo contra época. Panel izquierdo: las cuatro corridas en escala
  logarítmica, con el piso de ruido medido marcado. Panel derecho: las últimas 60 épocas en escala lineal,
  que es donde se ve lo importante — las dos corridas **cruzan hacia abajo** el piso de ruido y el costo en
  la verdad, y no vuelven a subir: **A1_D2 en la época 175 y A1_D1 en la 195** (cruce permanente, leído del
  `hist` guardado; corrección del verificador — antes decía 181 y ~193).
- `figs/fig2_S1_vs_epoca.png` — S1 contra época para las **cuatro** corridas (A2_D1 incluida, con sus
  puntos en 0/80/120/240), con el umbral 0.90, la mejor línea base 0.9449 y la cadena libre 0.115. Se ve
  que las curvas bajan en vez de subir, y que ninguna se acerca ni de lejos a las dos rayas de arriba. La
  curva de A1_D1_cad va en trazo cortado y con una flecha, porque es la que no convergió.
- `figs/fig3_mapas_t.png` — el espesor: verdad filtrada a la banda, conjunta A1_D1, conjunta desde la
  cadena, y cadena libre. Comparar el primero con el segundo.
- `figs/fig4_B_vs_epoca.png` — `B` contra época en la variante D2, con el valor verdadero +0.0015.
- `figs/fig5_variante_algoritmo.png` — la regla de selección de variante del plan (sección 10).
  Izquierda: la historia de costo de (i) y (ii) en el recorte, con los cortes de 80 y 240 épocas; las
  curvas **se cruzan** cerca de la época 135. Derecha: el S1 de cada variante en esos dos cortes,
  contra el umbral 0.90 — las cuatro barras son indistinguibles de cero, y el ganador por costo
  cambia de lado entre un corte y el otro.

## 9. Muestra con amplitud distinta por color (el último ítem del plan que faltaba)

El plan (línea 72) pedía repetir la prueba sobre una muestra en la que la **amplitud dentro de la
partícula sea distinta en cada color** — rojo 0.95, verde 0.90, azul 0.85, en vez de 0.9 en los tres.
El motivo: la variante **A2** supone una única amplitud compartida por los tres colores, y en esta
muestra esa suposición es **falsa**; **A1** (una amplitud por color) sí puede representarla. Como el
espesor no queda identificado por el ajuste (sección 4), la amplitud es el único diagnóstico que
distingue de verdad una variante de la otra. Se corrió en la ronda 4 y **el resultado también es
negativo, y de una manera que no esperábamos**.

**Cómo se hizo la muestra** (`amp_gen.py`). Se regeneró la verdad con el mismo generador y la misma
semilla que `sim.py`, se verificó que el espesor es **idéntico** al de `verdad.npz` (máxima diferencia
0.0 µm, 0 píxeles de máscara distintos) y se generaron las fotos con el mismo modelo directo, el mismo
brillo por LED y el mismo ruido medido. Prueba de que es exactamente la misma cadena: como el verde
nominal de esta muestra (0.90) coincide con el 0.9 de `sim.py`, el archivo `datos_amp_green.npz` sale
**idéntico bit a bit** al `datos_z98_green.npz` original, y la reconstrucción independiente del verde
sale idéntica bit a bit a `obj_z98_green_full.npy`. Las independientes de los tres colores se
recalcularon sobre estas fotos (40 iteraciones, `fourier_avg`, la receta de `sim.py`) y son las que dan
el inicio de la conjunta; la verdad no se usó para ninguna decisión.

**Las dos corridas, con el mismo número de épocas (80) y los mismos hiperparámetros** (`lr_t` 0.2,
`lr_a` 0.01, ganancia por LED exacta, `B` fijo en el valor verdadero, inicio elegido por costo — las dos
eligieron "verde"):

| | A1 (una amplitud por color) | A2 (amplitud compartida) |
|---|---|---|
| costo final (80 épocas) | **5.8046e5** | 1.0408e6 |
| S1 (espesor) | −0.0522 | −0.0242 |
| amplitud recuperada (rojo/verde/azul) | 0.826 / **1.161** / 0.930 | 0.803 (una sola) |
| error máximo de amplitud | **0.261** | 0.147 |

Las referencias de amplitud, medidas con el mismo código y la misma máscara: la verdad remuestreada a la
grilla común da 0.9505 / 0.9006 / 0.8504 (o sea, la máscara reproduce el nominal), y las
reconstrucciones **independientes** dan 0.855 / 0.750 / 0.668.

**Qué dice esto, en castellano.**

1. **A1 le vuelve a ganar a A2 en costo** (factor 1.79 a igual número de épocas), igual que en la muestra
   principal. Si uno eligiera la variante por costo, como manda el plan, elegiría A1.
2. **Y sin embargo A1 estima la amplitud peor que A2.** A1 devuelve 0.826 / 1.161 / 0.930 y su peor
   error es 0.261, contra 0.803 y 0.147 de A2, que usa un solo número para los tres colores. Para el
   verde da **1.16, es decir más transparente que el fondo**, que es físicamente al revés de lo que es
   una partícula absorbente.

   **Cuidado con el titular del orden.** La métrica de amplitud es nuestra, no del plan, así que el
   verificador la midió de tres formas sobre los mismos arreglos guardados:

   | definición | error máx. A1 | error máx. A2 | ¿A1 acierta el orden rojo > verde > azul? |
   |---|---|---|---|
   | mediana, núcleo erosionado 3 px (la declarada) | 0.2605 | 0.1471 | **no** (0.8264 / 1.1611 / 0.9301) |
   | mediana, máscara `dentro` sin erosionar | **0.1317** | 0.1508 | **sí** (1.0496 / 1.0426 / 0.9720) |
   | media, núcleo erosionado 3 px | 0.2417 | **0.0712** | no (0.8513 / 1.1420 / 0.8804) |

   O sea: "A1 estima la amplitud peor que A2" aguanta en dos de las tres definiciones y se da vuelta por
   poco en la tercera (0.132 contra 0.151). En cambio **"A1 se equivoca del orden de colores" NO es
   robusta**: vale sólo con el núcleo erosionado de 3 px; con la máscara sin erosionar el orden le sale
   bien. Lo que sí aguanta las tres definiciones —y por eso es el hecho que se usa más abajo— es que
   **el verde de A1 sale por encima de 1** (1.1611 / 1.0426 / 1.1420), que no es físico.
3. **Las independientes, que ni siquiera comparten el espesor, aciertan el orden** (0.855 > 0.750 >
   0.668) aunque todas sesgadas hacia abajo. Es decir: la información de "qué color absorbe más" está en
   los datos, y el ajuste conjunto **la pierde**.
4. La lectura es la misma de la sección 4, ahora vista desde la amplitud: los grados de libertad extra
   de A1 no se usan para describir la muestra, se usan para **absorber el error de fase**. El ajuste
   compra costo pagándolo con la física. Que el criterio del plan (menor costo) elija justo la variante
   que peor estima la amplitud es la señal más clara de que **el costo no sirve como criterio de
   selección en este problema**.
5. El espesor sigue sin recuperarse (S1 = −0.05 y −0.02, contra −0.037 y −0.043 de las corridas
   principales a la misma época 80): cambiar la amplitud de la muestra **no cambia nada** del diagnóstico
   central.
6. **S2 también falla en esta muestra, y también es peor en A1.** Las reconstrucciones independientes de
   estas mismas fotos dan un error de fase de 0.537 / 0.175 / 0.174 rad (rojo/verde/azul); la conjunta da
   0.807 / 0.526 / 0.716 con A1 y 0.671 / 0.498 / 0.646 con A2. El criterio S2 (pasa si la conjunta es
   mejor que la independiente en los tres colores) da **+0.543 con A1 y +0.472 con A2**: no pasa ninguna,
   y la que gana en costo es la peor de las dos.

Los números están en `resultados.json → sim.muestra_amplitud_distinta_por_color` (y en crudo en
`out/amplitud_variable.json` y `out/eval_amp_A1_D1.json` / `out/eval_amp_A2_D1.json`). Los scripts son
`amp_gen.py`, `amp_indep.py`, `amp_correr.py`, `amp_eval.py` y `amp_pipeline.sh`.

### 9.1 El control con la cota física `a_c ≤ 1`: no arregla el verde, mueve el error al fondo

La pregunta que dejó abierta la ronda 4 era directa: el solver deja la amplitud libre en `[0, 2]` y
nada en el costo penaliza `a_c > 1`, así que el 1.161 del verde es admisible para el costo aunque no
sea físico. **¿Imponer la cota física arregla la amplitud o sólo mueve el error a otro lado?**

Se repitió la corrida A1 cambiando **una sola cosa**: `joint.resolver(a_rango=(0, 1))` en vez de
`(0, 2)`, y recortando el punto inicial al mismo intervalo (un punto inicial fuera del conjunto
admisible no es un punto inicial). Todo lo demás idéntico: mismas fotos, mismas independientes de
arranque, mismas 80 épocas, mismos `lr_t` 0.2 / `lr_a` 0.01 / `lr_B` 2e-4, `B` fijo en +0.0015,
ganancia por LED exacta, inicio elegido por costo (volvió a ganar "verde", 2.043e6 contra 1.848e7).
Script: `amp_cota.py`; evaluación: `amp_cota_eval.py`; resultado en
`resultados.json → sim.cota_amplitud_fisica` y en crudo en `out/cota_amplitud.json`.

| | con cota `a ≤ 1` | sin cota (`a ≤ 2`) | verdad en la grilla |
|---|---|---|---|
| época alcanzada | 80 / 80 | 80 / 80 | — |
| costo final | 6.8745e5 | **5.8046e5** | — |
| S1 (espesor) | −0.0496 | −0.0522 | 1 |
| S2 valor (rad) | +0.4617 | +0.5427 | 0 |
| amplitud r/v/a (mediana, núcleo erosionado) | 0.7468 / **1.1222** / 0.9119 | 0.8264 / **1.1611** / 0.9301 | 0.9505 / 0.9006 / 0.8504 |
| error máx. — mediana, núcleo erosionado | 0.2216 | 0.2605 | — |
| error máx. — mediana, `dentro` sin erosionar | 0.1218 | 0.1317 | — |
| error máx. — media, núcleo erosionado | **0.2686** | 0.2417 | — |
| ¿acierta el orden r > v > a? (las tres definiciones) | no / no / no | no / **sí** / no | — |

**La respuesta es "sólo mueve el error", y se ve exactamente dónde lo mueve.** Con la cota, el
`a_verde` en bruto satura: el 6.8 % de los píxeles del verde (7.6 % del rojo, 10.3 % del azul) quedan
pegados al tope `a = 1`, y la partícula verde es justamente una de esas zonas. Pero la métrica —y la
física— comparan la partícula **con el fondo**, y el fondo del verde baja a 0.891 (sin cota estaba en
0.900). Resultado: la partícula verde sigue saliendo **1.12 veces más transparente que su propio
fondo**. El ajuste no puede subir la partícula por encima de 1, así que baja el fondo: el cociente
no físico sobrevive casi intacto (1.1611 → 1.1222).

Lo demás que dice el control:

1. **El espesor no se mueve**: S1 pasa de −0.0522 a −0.0496. La cota no toca el problema central.
2. **El error de amplitud mejora en dos definiciones de máscara y empeora en la tercera** (la media
   en el núcleo, 0.2417 → 0.2686). No es una mejora robusta.
3. **El orden de colores no se recupera en ninguna definición**, y de hecho se pierde el único caso
   en que salía bien (máscara `dentro` sin erosionar): con cota da 1.0320 / 1.0327 / 0.9536, que ya
   no es decreciente.
4. **Y la regla del plan volvería a elegir mal**: el costo final con la cota es 1.18 veces **mayor**
   que sin ella, así que "menor costo final" elegiría la variante sin cota, es decir la que produce
   la amplitud no física. Es la cuarta cosa (después del inicio, la dispersión y A1 contra A2) sobre
   la que el criterio del costo se pronuncia y se equivoca.

## 10. La variante (ii) del algoritmo, y qué pasa cuando se aplica la regla de selección del plan

Éste era el único paso **ordenado por el plan** que seguía sin ejecutarse. El plan permite dos
algoritmos y manda elegir uno *por el costo final sobre un recorte chico de la simulación*:

- **(i)** gradiente de lote completo sobre `t`, `a_c` (y `g_c`, `B`), con Adam. Es la que se usó en
  todas las corridas grandes de este informe.
- **(ii)** por vuelta: **un paso ePIE en cada color** (el bucle de `fpm_red.reconstruct`, paso 0.3,
  sin EPRY) partiendo del `O_c` del modelo conjunto, y después **proyectar** los tres `O_c` sobre el
  modelo conjunto, minimizando `Σ_c ‖O_c − a_c exp(i κ_c t)‖²` con `a_c` en forma cerrada y `t` por
  gradiente desde el `t` anterior (sin desenvolver). Código nuevo: `variante_ii.py`.

**El recorte.** El cuarto central del campo: **128 µm de lado** (contra 512 µm), grilla de **400 px**
a los mismos 0.32 µm, cámara de **100 px**, los **225 LEDs** de siempre en los tres colores, margen de
25 px en la métrica (los mismos 32 µm de siempre). Las fotos se **regeneraron** con el mismo generador
de `sim.py` (objeto en la grilla del factor propio de cada color, brillo por LED igualado al medido,
ruido gaussiano con la varianza medida por LED, semilla 1): recortar las fotos del problema grande no
habría servido, porque el modelo directo no es local (la PSF de NA 0.07 mide ~9 µm). Código:
`recorte.py`. El gradiente de la proyección se verificó contra diferencias centrales:
**4.49e−8** (umbral 1e−5).

Las dos variantes corren con **el mismo recorte, el mismo inicio, el mismo número de épocas y el mismo
costo de evaluación**. El inicio lo eligió el costo, como manda el plan: entre la cadena de dispersión
conocida (costo 9.364e5) y la fase del verde sola (1.250e5) **ganó el verde**.

**Los resultados, con las dos cosas separadas como corresponde:**

| corte | costo final (i) | costo final (ii) | **gana por costo** | S1 de (i) | S1 de (ii) | gana por S1 |
|---|---|---|---|---|---|---|
| 80 épocas | 37 826.7 | **30 010.7** | **(ii)** | **+0.0653** | +0.0011 | (i) |
| 240 épocas | **25 598.6** | 28 950.7 | **(i)** | **−0.0018** | −0.0315 | (i) |

Hay dos cosas acá, y las dos son malas para la regla del plan:

1. **A 80 épocas —el número por defecto del plan— la regla elige (ii), y (ii) es la peor por S1.** El
   ganador por costo es el que menos se parece a la verdad. Es exactamente lo que ya se veía dentro de
   una sola corrida (el costo baja por debajo del piso de ruido mientras S1 empeora), ahora *entre*
   algoritmos.
2. **La regla ni siquiera es estable.** El propio plan dice seguir más allá de 80 épocas "si el costo
   sigue bajando > 1 % en las últimas 10": a 80 bajaba 6.35 % (i) y 1.27 % (ii), o sea que seguir es lo
   que el plan manda, y esa decisión se tomó mirando **sólo** la historia de costo. A 240 épocas las dos
   están convergidas (0.67 % y 0.03 %) y **el orden está dado vuelta**: las curvas se cruzan cerca de la
   época 135 (figura 5). Quién gana depende de dónde se pare, y el único criterio de parada que da el
   plan es el mismo costo.

**Lo que de verdad importa: no cambia nada.** Las cuatro mediciones de S1 del recuadro están entre
−0.032 y +0.065, contra un umbral de 0.90. **El algoritmo no es la causa del fracaso**: cambiarlo por el
otro que permite el plan no recupera el espesor. Y el mismo fenómeno aparece en la elección del inicio,
que el plan también manda hacer por costo: el costo eligió el verde, cuyo S1 de partida es **−0.0545**,
por encima de la cadena, cuyo S1 de partida es **+0.6597**. El criterio de selección elige el peor punto
de partida disponible.

**Qué queda seleccionado.** En el punto de corte válido (240 épocas, las dos convergidas) la regla
selecciona la **variante (i)**, que es la de todas las corridas grandes de este informe: el cuerpo de
resultados es consistente con la selección. No se rehicieron las corridas grandes con la (ii) porque en
el recorte las dos dan S1 ≈ 0 y el veredicto NEGATIVO no cambiaría. Aviso menor: la historia de costo de
(ii) a 240 épocas **no es monótona** (tiene subidas chicas); la de (i) sí.

Los números están en `resultados.json → sim.variante_de_algoritmo_ii` y en crudo en
`out/variante_algoritmo.json` (80) y `out/variante_algoritmo_240.json` (240). Los scripts son
`recorte.py`, `variante_ii.py`, `correr_recorte.py` y `fig_variante.py`; los registros, en
`logs/recorte.log` y `logs/recorte_240.log`.

## 11. Qué probaría después (en orden)

1. **Continuación por longitud de onda.** Empezar con el rojo solo (que es el que menos vueltas de fase
   da), converger, y recién ahí agregar verde y azul usando el resultado como punto de partida. Ataca
   directamente el modo de falla — que `t` se acomoda en una vuelta de fase equivocada — sin tocar ningún
   criterio. Es lo único de esta lista con chance real de dar vuelta el resultado. ~3 h.
2. **Regularizar `t`** (variación total o suavidad). El otro candidato para sacar al ajuste del mínimo
   aliasado: hoy nada impide que `t` tenga estructura de alta frecuencia que sólo sirve para comerse el
   ruido. Habría que declararlo como desviación, igual que `s_ck`. ~1 h por corrida.
3. ~~Muestra con amplitud distinta por color~~ y ~~la cota física `a_c <= 1`~~ — **las dos se
   corrieron**, secciones 9 y 9.1. La cota **no** arregla el verde: lo baja de 1.161 a 1.122 y el
   resto lo compensa bajando el fondo. Lo que queda abierto, y es distinto: **anclar el fondo**. Si
   el problema es que la escala de cada color es libre (sólo el producto `g_c · a_c` está
   determinado), la prueba siguiente es fijar `a_c = 1` en la máscara de fondo estimada de los datos
   —no de la verdad— en vez de acotar `a_c` globalmente. ~40 min, y es la continuación natural de
   9.1.
4. ~~Variante (ii) del algoritmo~~ — **ya se corrió**, sección 10: implementada, comparada contra la
   (i) en el recorte chico y seleccionada con la regla literal del plan. Lo que dejó abierto es más
   grave que lo que cerró: la regla del plan elige (ii) a 80 épocas y (i) a 240, y a 80 el ganador por
   costo es el peor por S1. Lo que faltaría es correr la (ii) en la grilla completa de 1600 px (~30 min),
   aunque con S1 ≈ 0 en el recorte no se espera que cambie nada.
5. **Barrido de `z` en la conjunta**: la pregunta de fondo del proyecto, fuera de este plan.

Y una observación de método que vale para todo lo que siga: **hace falta un criterio de parada que no sea
el costo**. Acá el costo bajó del piso de ruido mientras la respuesta empeoraba, y con datos reales no
habría manera de darse cuenta. Un conjunto de LEDs reservado (no usado en el ajuste) y evaluado época a
época es lo mínimo indispensable antes de volver a intentar esto sobre la captura real.

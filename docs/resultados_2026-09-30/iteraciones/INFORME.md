# ¿Cómo cambian amplitud y fase con las épocas? Datos reales, 28/09 (b), 2026-09-30

Revisado por un verificador independiente: ver `REVISION.md` (scripts en `revision/`).

**Pregunta (Lucas):** hasta ahora se usaron 40 épocas sin justificación (ver `ANTECEDENTES.md`). ¿Cómo evolucionan las
reconstrucciones reales de amplitud y fase con el número de épocas?

**Qué se corrió:** el mismo pipeline que dio los números del 28/09 (b): A+init, paso 0.3 con rampa
`0.3·(1 − e^(−0.3·it))`, z = 98 mm, mismas tareas (full, mitades, mitades con geometría mezclada, 5 folds). La única
diferencia es que se guardó el estado en 17 épocas entre 0 y 400 (`iter_runner.py`, `ESTADO.md`). El solver es
bit-idéntico al original (`smoke.json`).

**Verificación a 40 épocas:** `analisis/analizar.py` reproduce el INFORME del 28/09 (b) y `criterios_b.json`.
- C1: diferencia 0 en los tres colores (rojo 0.461, verde 0.615, azul 0.596).
- C2: diferencias < 3e-9 (rojo 0.083, verde 0.043, azul 0.099). El nulo y el lattice coinciden igual que C1 y C2.
- Coherencia de amplitud entre colores: coincide con `comparar_colores.json` (0.109 / 0.559 / 0.022 en la banda del objetivo).

## Respuesta corta

- **No hay una sola cantidad de épocas óptima. Depende del color y de la métrica.**
  - Rojo: C1 (fotos no vistas) mejora de forma monótona hasta 400 épocas. C2 (coincidencia entre mitades) también,
    pero solo en el campo entero: por teselas sube en 3 de 9.
  - Verde y azul: C1 tiene su mínimo a **5 épocas**, y a 40 está apenas peor (+0.015 en verde, +0.021 en azul). De ahí
    a 400 queda plano.
    - El efecto es real en esta captura: IC 95 % emparejado por LED de [−0.023, −0.007] en verde y [−0.027, −0.014] en
      azul (`REVISION.md` §3).
    - Pero viene casi todo de los LEDs del anillo 5.5-7. En el anillo 1.3-2.5 del verde, 40 épocas es mejor que 5.
    - No se descartó que sea un efecto de la métrica afín.
  - C2 (definición oficial, sin ventana): sube de forma robusta solo en azul, +0.018 ± 0.006 por tesela entre 40 y 400,
    con 8 de 9 teselas en la misma dirección.
    - En rojo sube en el campo entero, pero solo en 3 de 9 teselas.
    - En verde no hay una tendencia robusta: la caída después de 20 épocas se invierte con ventana de Hann o por teselas.
- **Umbral de C2 (0.143):** con la definición oficial (sin ventana), ningún color lo alcanza en ninguna época. El máximo
  es 0.112, en azul a 320-400.
  - Con ventana de Hann el rojo ya da 0.146 a 40 épocas. El umbral está calibrado para la definición sin ventana, así
    que eso no quiere decir que "pase", pero sí que "no llega" depende de la definición.
- **A 40 épocas el rojo está en mitad de un transitorio:**
  - El ajuste de los 6 LEDs de campo claro empeora de 0.70 (5 épocas) a 0.95 (60), peor que el objeto inicial (0.73), y
    recién vuelve por debajo de ese valor a 160-240.
  - La correlación de la amplitud de bajas frecuencias con la de 400 no es monótona: 0.60 (5), 0.11 (40), 0.75 (120).
- **40 épocas:** es corto para el rojo, algo largo para verde y azul según C1, y corto para C2 en azul.

## Tabla clave

C1 es la media de 5 folds ± sd poblacional entre folds (ddof = 0, como `criterios_b.py`; con ddof = 1 es ~10 % mayor) (menor es mejor; sin FPM: rojo 0.977, verde 0.984, azul 0.978). C2 es la FRC
entre mitades en [2NA/λ, 0.45] 1/µm (mayor es mejor; umbral 0.143). El nulo de C2 va entre paréntesis.

| color | métrica | 0 | 20 | **40** | 120 | 400 | mejor (época) |
|---|---|---|---|---|---|---|---|
| rojo | C1 | 0.987 ± 0.002 | 0.482 ± 0.009 | **0.461 ± 0.007** | 0.421 ± 0.009 | 0.396 ± 0.021 | 0.396 (400) |
| rojo | C2 (nulo) | 0.214 (0.214)* | 0.077 (0.015) | **0.083 (0.014)** | 0.095 (0.013) | 0.105 (0.011) | 0.105 (400) |
| verde | C1 | 0.993 ± 0.001 | 0.612 ± 0.004 | **0.615 ± 0.007** | 0.613 ± 0.009 | 0.610 ± 0.010 | 0.600 (5) |
| verde | C2 (nulo) | 0.172 (0.172)* | 0.049 (0.007) | **0.043 (0.008)** | 0.037 (0.005) | 0.036 (0.007) | 0.049 (20)† |
| azul | C1 | 0.989 ± 0.002 | 0.589 ± 0.010 | **0.596 ± 0.010** | 0.597 ± 0.009 | 0.597 ± 0.007 | 0.575 (5) |
| azul | C2 (nulo) | 0.190 (0.190)* | 0.094 (0.006) | **0.099 (0.007)** | 0.103 (0.009) | 0.112 (0.010) | 0.112 (320-400) |

\* A 0 épocas, C2 no tiene sentido. El objeto inicial (`fourier_avg`) sale de los mismos LEDs de campo claro en las dos
mitades y en el nulo: C2 coincide exactamente con el nulo, y la FRC tiene un pico espurio en 0.57 1/µm (`figs/frc_curvas.png`).
La época 1 es idéntica a la 0 porque la rampa da paso 0 en la primera época.

† El máximo del verde a 20 épocas no es robusto: con ventana de Hann o por teselas, C2 no baja después de 20
(`REVISION.md` §5).

Diferencia pareada por fold, C1(e) − C1(40), media ± sd entre folds:
- rojo: +0.053 ± 0.007 (5), −0.025 ± 0.009 (80), −0.041 ± 0.012 (120), −0.066 ± 0.025 (400);
- verde: −0.015 ± 0.007 (5), −0.003 ± 0.003 (120), −0.005 ± 0.005 (400);
- azul: −0.021 ± 0.005 (5), +0.002 ± 0.002 (120), +0.001 ± 0.005 (400).

Otras magnitudes (`analisis/b_*.json`):

| | rojo 5 / 40 / 400 | verde 5 / 40 / 400 | azul 5 / 40 / 400 |
|---|---|---|---|
| R de entrenamiento (folds) | 0.410 / 0.348 / 0.311 | 0.493 / 0.428 / 0.406 | 0.465 / 0.398 / 0.376 |
| brecha C1 − entrenamiento | 0.105 / 0.113 / 0.084 | 0.107 / 0.187 / 0.205 | 0.110 / 0.198 / 0.221 |
| R entrenamiento, campo claro (full)‡ | 0.699 / **0.928** / 0.638 | 0.776 / 0.744 / 0.764 | 0.699 / 0.637 / 0.619 |
| C1 campo oscuro cercano (anillo 1.3-4) | 0.633 / 0.607 / 0.590 | 0.658 / 0.642 / 0.635 | 0.650 / 0.651 / 0.657 |
| C1 campo oscuro lejano (anillo 4-7) | 0.467 / 0.404 / 0.318 | 0.577 / 0.605 / 0.601 | 0.546 / 0.574 / 0.573 |
| lattice (full) | 0.0008 / 0.00002 / 0.0010 | 0.0017 / 0.0006 / 0.0015 | 0.0060 / 0.0036 / 0.0064 |
| error interno del solver (full) | 0.199 / 0.189 / 0.018 | 0.115 / 0.116 / 0.114 | 0.054 / 0.048 / 0.047 |
| corr. amplitud bajas (≤ NA/λ) con 400 | 0.60 / **0.11** / 1 | 0.77 / 0.91 / 1 | 0.84 / 0.95 / 1 |
| corr. amplitud banda C2 con 400 | 0.14 / 0.22 / 1 | 0.30 / 0.59 / 1 | 0.39 / 0.68 / 1 |
| corr. fase relativa bajas con 400 | 0.56 / 0.36 / 1 | 0.58 / 0.82 / 1 | 0.74 / 0.95 / 1 |
| corr. fase relativa banda C2 con 400 | 0.22 / 0.21 / 1 | 0.38 / 0.59 / 1 | 0.58 / 0.76 / 1 |

‡ Rojo, campo claro, todas las épocas: 0.725 (0), 0.699 (5), 0.857 (30), 0.928 (40), **0.947 (60)**, 0.892 (80),
0.763 (120), 0.638 (400).

## Hechos medidos

1. **C1 (fotos no vistas, anillo < 7)**
   - **Una sola época efectiva** (la 2; la 1 es nula por la rampa) hace casi todo: R cae de ~0.99 a 0.55-0.63 en los tres colores.
   - **Rojo:** sigue bajando de forma monótona hasta 400 (0.396). La sd entre folds crece de 0.007 (40) a 0.021 (400).
     4 de 5 folds mejoran de 120 a 400; el fold f4 empeora (0.425 → 0.433).
   - **Verde y azul:** mínimo a 5-8 épocas. De 5 a 40 suben (verde 0.600 → 0.615, azul 0.575 → 0.596; los 5 folds suben
     en los dos colores) y después quedan planos (±0.005) hasta 400.
   - Es una U poco profunda: 0.015-0.021, del orden de 1-2 sd entre folds y de 2-4 sd en la diferencia pareada.
     - Los folds **no** son réplicas independientes: comparten en promedio el 61 % del entrenamiento (Jaccard) y los 6
       LEDs de campo claro.
     - El revisor la confirmó con bootstrap emparejado por LED (n = 148): verde −0.015 [−0.023, −0.007], con 61 % de los
       LEDs mejor a 5 épocas; azul −0.021 [−0.027, −0.014], con 67 %.
     - La empuja el anillo 5.5-7: −0.015 de la media en los dos colores, con 75-77 % de los LEDs mejor a 5. En el anillo
       1.3-2.5 del verde es al revés: +0.045, 9 de 10 LEDs peor a 5.
     - No se descartó un efecto de la métrica afín (s y offset libres por LED). Para probarlo hay que rehacer los folds
       guardando `obj`.
2. **Por anillo** (`figs/c1_por_anillo.png`). Los 6 LEDs de campo claro nunca quedan fuera de un fold, así que C1 no los mide.
   - Rojo: la mejora tardía viene casi toda del campo oscuro lejano (anillo 4-7): 0.404 → 0.318 de 40 a 400. El campo
     oscuro cercano cambia poco (0.607 → 0.590).
   - Verde: la U está en el campo oscuro lejano (mínimo 0.577 a 5, 0.605 a 40).
   - Azul: en los dos grupos (cercano 0.646 a 8 contra 0.651 a 40; lejano 0.546 a 5 contra 0.574 a 40).
3. **Brecha entre entrenamiento y no vistos** (`figs/curvas_metricas.png`, abajo a la derecha)
   - Verde y azul: crece de forma monótona, de ~0.08 a 2 épocas a 0.205-0.221 a 400. Entre 40 y 400 se agranda 0.02.
   - Rojo: sube a 0.125 (12-20 épocas) y después **baja** a 0.084 (400).
4. **C2 (mitades)**
   Todo lo de este punto usa la definición oficial: campo entero, sin ventana.
   - Rojo: sube de forma monótona desde 3 épocas (0.044) hasta 400 (0.105).
     - Por teselas (3×3, Hann) el cambio de 40 a 400 es +0.007 ± 0.035, y sube solo en 3 de 9: no es robusto.
   - Verde: el campo entero baja de 0.049 (20) a 0.036 (400).
     - Con ventana de Hann sube (0.054 → 0.092), y por teselas sube +0.009 ± 0.014.
     - **No hay evidencia de que C2 empeore con las épocas en verde.**
   - Azul: sube hasta 320-400 (0.112). Por teselas, +0.018 ± 0.006 con 8 de 9 en la misma dirección: robusto.
   - El nulo baja con las épocas en los tres (0.011, 0.007 y 0.010 a 400).
   - **Umbral:** con la definición oficial, ningún color llega a 0.143 en ninguna época.
     - Con ventana de Hann sobre el interior, el rojo da 0.146 (40) y 0.154 (400). El umbral no está calibrado para esa
       definición.
     - Hay variabilidad espacial grande: según la tesela, el rojo a 40 épocas va de 0.07 a 0.39.
   - **Margen sobre el nulo:** en absoluto es 0.03-0.10, y en verde (0.029-0.042) no alcanza el criterio nulo + 0.068.
   - Fuera de la banda (FRC media en [0, NA/λ), informativa), la coincidencia entre mitades a bajas frecuencias **baja**
     con las épocas: rojo 0.69 (5) → 0.28 (40) → 0.12 (400), verde 0.31 → 0.34 → 0.12, azul 0.44 → 0.51 → 0.36. El nulo
     baja igual. Las mitades divergen en lo lento.
5. **Lattice (C3):** en los tres colores queda chico en todas las épocas (≤ 0.0064). Solo en azul tiene una suba leve
   (0.0036 a 40, 0.0064 a 400). No hay crecimiento apreciable de la red.
6. **Estabilidad del objeto completo** (`figs/estabilidad.png`). Los intervalos entre snapshots crecen con la época, así
   que el cambio por intervalo no es por época.
   - **Verde y azul:** cambio relativo de amplitud de 0.02-0.04 por intervalo desde ~8 épocas, y cambio de fase rms de
     0.04-0.09 rad.
     - Las bajas frecuencias de la amplitud se estabilizan pronto: correlación con 400 de 0.91 (verde) y 0.95 (azul) a 40.
     - La banda de C2 sigue cambiando: correlación con 400 de 0.59 en amplitud y fase en verde, y 0.68 (amplitud) / 0.76 (fase) en azul.
   - **Rojo: transitorio grande entre 40 y 120 épocas.**
     - Cambio de amplitud de 0.10-0.18 por intervalo y cambio de fase de 0.29-0.66 rad rms.
     - El error interno del solver cae de 0.19 a 0.027 entre 40 y 120.
     - El residuo de los LEDs de campo claro (tarea full) sube de 0.70 (5) a 0.95 (60), peor que el objeto inicial (0.73),
       y baja a 0.64 (400).
     - La correlación de la amplitud de bajas frecuencias con 400 no es monótona: 0.60 (5), 0.27 (20), 0.11 (40),
       0.24 (60), 0.75 (120). Es una excursión que va y vuelve.
     - Entre 40 y 120 épocas la amplitud cambia un 17 % (verde 8 %, azul 7 %).
       - Cerca de la mitad de ese cambio está por debajo de NA/λ: 25 % con ≤ 0.02 1/µm y 23 % entre 0.02 1/µm y NA/λ. En
         verde y azul eso es ~2 %.
       - El fondo muy lento se reacomoda por completo: correlación con 400 de −0.01 a 40 y 0.74 a 120.
       - La otra mitad está en frecuencias altas: ~24 % en la banda de C2.
       - **No es solo el fondo lento.** En el montaje lo más visible es el fondo (gradiente o franjas de brillo y de fase).
7. **Amplitud contra fase:** con correlación contra el snapshot de 400 como medida de "llegar al final" (valores a 40 épocas):
   - bajas frecuencias: en verde la fase va detrás de la amplitud (0.82 contra 0.91); en azul van igual (0.95 y 0.95);
   - banda de C2: en verde van igual (0.59 y 0.59); en azul la fase va algo adelante (0.76 contra 0.68);
   - en las dos bandas, la banda alta va muy detrás de las bajas, en amplitud y en fase;
   - en rojo, amplitud y fase tienen el mismo transitorio (bajas: amplitud 0.11, fase 0.36).
8. **Montaje** (`figs/montaje_b_*.png`: amplitud y fase en 0/5/20/40/120/400 épocas, zona de 128 µm del deck).
   - Las partículas y su posición se fijan a las 5 épocas. De 5 a 400 cambian el contraste, los anillos y el fondo.
   - En verde y azul, la fase dentro de la partícula grande cambia después de 40-120 épocas: el centro pasa de saturado
     (> 3 rad) a ~2 rad. Puede ser un salto del desenrollado o un cambio real; con esto no se distingue.
   - En rojo el desenrollado falla en una región a 40 épocas, como ya estaba documentado en `make_fig_fase_2809b.py`.
9. **Coherencia entre colores** (`figs/colores.png`, `analisis/colores.json`). Se usaron corrimientos fijos medidos a 40 épocas.
   - A 0 épocas la amplitud coincide 0.92-0.96 entre colores: es el objeto inicial suave, no cuenta.
   - **azul-verde:** amplitud en la banda del objetivo 0.72 (5) → 0.56 (40) → 0.52 (400); fase 0.55 → 0.56 → 0.50.
   - **rojo-verde / rojo-azul:** mínimo a 40-60 épocas (amplitud 0.11/0.02 a 40), recuperación a 400 (0.26/0.61). La
     fase en la banda del objetivo es máxima a 8-12 épocas (0.69/0.64) y baja a 0.47/0.35 a 40.
     - La "banda del objetivo" es un pasabajos ≤ 0.11 1/µm. Por eso este mínimo es **el mismo fenómeno** que el
       transitorio de bajas frecuencias del rojo (punto 6), no evidencia independiente.
   - **Registro:** el corrimiento rojo-verde es ambiguo, ~3 o ~6-7 px HR según el snapshot y sin tendencia.
     - Con el corrimiento medido en cada snapshot (revisor, refinamiento subpíxel) las correlaciones no suben: dan igual o
       menos que con el fijo.
     - El mínimo a 40-60 se mantiene.

## Interpretación (no es un hecho medido)

- **Verde y azul muestran semi-convergencia leve en C1**, concentrada en el campo oscuro exterior (anillo 5.5-7). Más
  épocas ajustan algo que no generaliza a esos LEDs:
  - la brecha entre entrenamiento y no vistos crece de forma monótona;
  - el entrenamiento sigue bajando mientras C1 no se mueve.

  **Lo que se sobreajusta es error de modelo, no ruido.** El residuo (R ~0.4-0.6) está muy por encima del piso de ruido
  de esos LEDs (~0.05). La parada temprana actúa como regularización de las frecuencias altas.

  El daño es chico: C1 queda plano después de 40, y el lattice no crece. En azul, C2 sube de forma robusta hasta 400
  mientras C1 empeora un poco: C1 y C2 miden cosas distintas. C1 mide la predicción de LEDs cercanos (anillo < 7); C2,
  la repetibilidad en alta frecuencia.
- **El rojo no tiene un óptimo dentro de 400 épocas.** El transitorio de 40-120 coincide con el reacomodo del fondo de
  baja frecuencia, que es la mitad del cambio, con un cambio en todas las bandas y con la caída del error interno. Leído así, el rojo a 40 épocas no está convergido. Los números
  "oficiales" del rojo a 40 (C1 0.461) son un punto de un transitorio, no un estado estable. A 400, C1 es 0.396 y C2 0.105.
- **Lo que separa los ritmos es la frecuencia, más que amplitud contra fase.** Lo grueso (posición de las partículas,
  bajas frecuencias) se fija en 5-20 épocas en verde y azul. La banda alta, en amplitud y en fase, sigue moviéndose
  hasta 400 sin estabilizarse del todo (correlación de 240 contra 400: 0.76-0.96). La fase de bajas frecuencias va algo
  detrás de la amplitud solo en verde.
- **¿40 estaba bien?**
  - Para verde y azul es un punto aceptable de una meseta, a 0.015-0.021 del mínimo de C1.
  - Para el rojo es corto.
  - Para C2 en azul y rojo es corto, pero subir las épocas no lleva a ningún color al umbral: la mejora máxima de C2 es
    0.083 → 0.105 en rojo y 0.099 → 0.112 en azul.
  - Una regla por color con C1 elegiría ~5-8 épocas para verde y azul (con los matices del punto 1), y ≥ 240 para rojo.
  - Con C2 solo el azul da una señal robusta: más épocas, ≥ 320. El verde no tiene tendencia robusta y el rojo sube solo
    en el campo entero.
  - En azul, C1 y C2 apuntan en direcciones opuestas: C1 a ~5 épocas, C2 a ≥ 320.

## Limitaciones

- **No hay verdad de referencia.** Todas las métricas son indirectas. La correlación con el snapshot de 400 mide si la
  corrida se estabilizó, no si la reconstrucción es buena.
- **C1 no mide resolución.** Mide la predicción de LEDs no vistos con anillo < 7 (casi todo campo oscuro cercano o
  intermedio). No incluye el campo claro.
- **C2 queda bajo el umbral en todas las épocas, con la definición oficial.**
  - Sus variaciones (0.04-0.11) son chicas en términos absolutos: el margen sobre el nulo es 0.03-0.10, aunque como
    cociente sea 5-15 veces.
  - C2 depende de la ventana y de los bordes: con ventana de Hann la tendencia del verde se invierte y el rojo supera
    0.143.
  - Hay una sola partición en mitades, sin réplica. Para cuantificar la incertidumbre convendría repetir con K ≥ 5
    particiones aleatorias de los LEDs, estratificadas por anillo, a 20, 40 y 400 épocas (2K reconstrucciones por color).
    También informar C2 con y sin ventana.
- **Umbrales sin recalibrar:** son los del set 3, sin simulación de esta geometría a cada número de épocas
  (ANTECEDENTES, pregunta 8).
- **Una sola zona y una sola captura:** 28/09 (b). El set 3 del 25/09 (rojo, otro campo) está en la sección "Rojo 25/09 set 3".
- **El paso tiene rampa** (`0.3·(1 − e^(−0.3·it))`). La forma de las curvas en las primeras épocas depende de ella y del
  paso 0.3; no se barrió el paso. La época 1 es igual a la 0.
- **Los folds comparten los LEDs de campo claro y el 61 % del entrenamiento.** La sd (poblacional, ddof = 0) entre
  folds no es un error estándar de réplicas independientes. Las diferencias pareadas, y el bootstrap por LED del revisor,
  son más informativas.
- **El origen de la U de C1 no está aclarado.** Viene del anillo 5.5-7, y no se descartó un efecto de la métrica afín.
- **Una sola z (98 mm), un solo método (A+init) y un solo paso (0.3).** La convergencia del rojo puede depender del paso.
- **Coherencia entre colores:** el registro rojo-verde es ambiguo (3 o 6 px). El mínimo rojo a 40-60 no es
  independiente del transitorio del rojo.
- **Fase:** el desenrollado y el polinomio de orden 2 de `make_fig_fase_2809b.py` fallan en rojo, por las franjas de
  fondo. La escala satura en 3 rad y recorta los valores negativos.

## Qué cambió tras la revisión (`REVISION.md`)

**Confirmado:** la reproducción a 40 épocas, la tabla clave, los mínimos y las diferencias pareadas.

**Corregido o matizado:**
- **Campo claro del rojo:** el peor punto es a 60 épocas (0.947), no a 40, y entre 30 y 80 épocas es peor que el objeto
  inicial (0.725).
- **Mínimo de C1 a 5 en verde y azul:**
  - se agregaron el IC por LED y la dependencia entre folds (61 % del entrenamiento compartido);
  - viene del anillo 5.5-7, y en el anillo 1.3-2.5 del verde es al revés;
  - no se descartó un efecto de la métrica afín.
- **Rojo, "fondo lento":** es solo la mitad del cambio entre 40 y 120 (~24 % está en la banda de C2), y la correlación
  de bajas frecuencias no es monótona.
- **C2:**
  - se quitó "verde máximo a 20" como hecho, y la regla C2 ~20 (refutadas por teselas y por la ventana de Hann);
  - el rojo sube solo en 3 de 9 teselas;
  - el azul queda confirmado;
  - "nunca llega a 0.143" vale solo para la definición oficial, sin ventana.
- **Colores:**
  - el mínimo rojo a 40-60 es el mismo transitorio del rojo, no evidencia independiente;
  - se reemplazó la frase sobre correlaciones "subestimadas", que quedó refutada.
- **Otros:**
  - la sd es poblacional;
  - "2 primeras épocas" pasa a "una época efectiva";
  - el sobreajuste es de error de modelo, no de ruido;
  - se agregaron limitaciones: dependencia de C2 de la ventana, una sola partición en mitades, una sola z, un solo
    método y un solo paso.

## Rojo 25/09 set 3 (z 74 mm)

Barrido lanzado el 2026-09-30 21:24:48 (`setsid nohup ./run_all.sh 3 400 s3_red`), terminó a las 22:55:01 (10/10 FIN,
"TODO TERMINADO"). Mismo pipeline (A+init, paso 0.3 con rampa, 17 snapshots), z = 74 mm, otro campo y otra geometría
(2 LEDs de campo claro). Análisis: `analisis/analizar.py s3_red` → `analisis/s3_red.json`; figuras: `figuras.py s3_red`
(`figs/montaje_s3_red.png` y la serie s3_red en `curvas_metricas.png`, `c1_por_anillo.png`, `estabilidad.png`,
`frc_curvas.png`). C2 con ventana de Hann: misma función que `revision/rev_c2b.py` (vía `analisis/particiones_c2.py`).

**Verificación a 40 épocas contra el 25/09** (`captura_2026-09-25_red/out/tasks/real_A+init_z74.0_f*.json` y
`out/obj_real_A+init_z74.0_half*.npy`): **reproduce exactamente.**
- C1 0.5172 ± 0.0215 (sd poblacional, como la referencia 0.517 ± 0.022); R por LED de cada fold idéntico (diferencia 0).
- Los objetos half0, half1, half0_scr, half1_scr a 40 épocas son bit a bit los del 25/09 (diferencia máxima 0).
- C2 0.0255 (referencia 0.026), nulo 0.0135 (referencia 0.013).
- Sin FPM: el archivo `real_nofpm_z74.0.json` da 0.984 (incluye los LEDs de campo claro); el 0.991 del 25/09 coincide
  con C1 a 0 épocas (0.991).

### Tabla (misma convención que la tabla clave)

C1: media de 5 folds ± sd poblacional (ddof = 0). C2 oficial: campo entero, sin ventana; nulo entre paréntesis. C2 Hann:
variante (interior, ventana de Hann), nulo entre paréntesis. Una sola partición en mitades (damero).

| métrica | 0 | 20 | **40** | 120 | 400 | mejor (época) |
|---|---|---|---|---|---|---|
| C1 s3 | 0.991 ± 0.001 | 0.530 ± 0.023 | **0.517 ± 0.022** | 0.484 ± 0.023 | 0.438 ± 0.022 | 0.438 (400) |
| C2 oficial s3 (nulo) | 0.300 (0.300)* | 0.026 (0.010) | **0.026 (0.013)** | 0.027 (0.017) | 0.027 (0.017) | ninguna (ver †) |
| C2 Hann s3 (nulo) | — | 0.033 (0.014) | **0.026 (0.015)** | 0.021 (0.023) | 0.034 (0.031) | — |
| C1 b_red (para comparar) | 0.987 ± 0.002 | 0.482 ± 0.009 | **0.461 ± 0.007** | 0.421 ± 0.009 | 0.396 ± 0.021 | 0.396 (400) |
| C2 oficial b_red (nulo) | 0.214 (0.214)* | 0.077 (0.015) | **0.083 (0.014)** | 0.095 (0.013) | 0.105 (0.011) | 0.105 (400) |
| C2 Hann b_red | — | 0.131 | **0.146** | 0.150 | 0.154 | — |

\* Época 0 = objeto inicial, igual en mitades y nulo: no cuenta (como en b).
† C2 oficial es 0.025-0.036 desde 5 épocas, sin tendencia útil. A 2-3 épocas (0.101 / 0.048) está por **debajo** de su
nulo (0.199 / 0.099): domina el objeto inicial. El máximo de C2 − nulo es 0.019 (12 épocas); a 40, 0.012; a 400, 0.010.

Diferencias pareadas por fold, C1(e) − C1(40), media ± sd entre folds: −0.033 ± 0.007 (120), −0.079 ± 0.012 (400);
+0.055 ± 0.003 (5), +0.013 ± 0.004 (20). Los 5 folds en la misma dirección en 5 → 40, 20 → 40, 40 → 400 y 120 → 400.

### Hechos medidos (s3)

1. **C1 mejora de forma monótona hasta 400**, como en b_red: 0.517 (40) → 0.484 (120) → 0.438 (400), sin mínimo
   interior. La caída no se detiene: de 320 a 400 baja todavía 0.008. La sd entre folds se queda
   en ~0.022 (en b_red crecía de 0.007 a 0.021).
   - Por anillo: campo oscuro cercano (1.3-4) 0.607 (40) → 0.535 (400); lejano (4-7) 0.469 → 0.384. Mejoran los dos
     grupos (en b_red el cercano casi no se movía: 0.607 → 0.590).
2. **No hay transitorio.** En b_red, a 40 épocas el campo claro empeoraba hasta peor que el objeto inicial y la
   amplitud de bajas frecuencias hacía una excursión. En s3 nada de eso:
   - R de campo claro (tarea full) baja de forma monótona: 0.705 (0) → 0.501 (5) → 0.376 (40) → 0.350 (120) → 0.324 (400).
   - Correlación de amplitud de bajas (≤ NA/λ) con 400: 0.72 (5), 0.87 (20), 0.89 (40), 0.95 (120): monótona.
   - Error interno del solver: 0.049 (5), 0.023 (40), 0.019 (400): sin la caída tardía 0.19 → 0.03 del rojo b.
   - Cambio de amplitud por intervalo 0.02-0.03 y de fase 0.04-0.08 rad rms desde 12 épocas (b_red: 0.10-0.18 y
     0.29-0.66 rad entre 40 y 120).
3. **C2 no mejora con las épocas y queda en el nivel del nulo.**
   - Oficial: 0.036 (5), 0.026 (20-40), 0.027 (120-400). El nulo sube de 0.010 (20) a 0.017 (400), así que el margen
     sobre el nulo baja de 0.016 (20) a 0.010 (400); su máximo es 0.019, a 12 épocas.
   - Con Hann: 0.033 (20), 0.026 (40), 0.021 (120), 0.034 (400), con nulo Hann 0.014-0.031; a 120 el real queda
     **por debajo** del nulo.
   - Ninguna época, con ninguna de las dos definiciones, se acerca al umbral 0.143 ni al criterio nulo + 0.068.
4. **Brecha C1 − entrenamiento**: 0.231 (20), 0.237 (40), 0.222 (120), 0.191 (400). Baja desde 30-40, como en b_red,
   pero es el doble (b_red 0.084 a 400).
5. **Lattice** ≤ 0.0061 en todas las épocas, sin crecimiento (0.0052 a 40, 0.0006 a 400).
6. **Montaje** (`figs/montaje_s3_red.png`; mismas coordenadas de píxel que el deck, pero es otro campo): partículas
   fijas desde 5 épocas; de 120 a 400 aparece y crece un patrón de franjas en el borde inferior de la zona, en amplitud
   y en fase.

### Comparación con b_red (hechos)

- **Igual que b_red:** C1 mejora de forma monótona hasta 400, con los 5 folds en la misma dirección; 40 épocas es corto
  para C1 en los dos sets rojos (−0.066 en b_red, −0.079 en s3 de 40 a 400).
- **Distinto de b_red:**
  - no hay transitorio en 40-120 (campo claro, bajas frecuencias y error del solver son monótonos);
  - C2 no sube (b_red: 0.083 → 0.105 oficial, 0.146 → 0.154 Hann); en s3 queda en ~0.026 con nulo ~0.015;
  - la variante de Hann no cambia el veredicto en s3 (no supera nada), mientras que en b_red llegaba a 0.146.

### Interpretación (no es un hecho medido)

- La mejora de C1 hasta 400 aparece en los dos sets rojos, con geometrías y campos distintos: es razonable leer que
  el rojo necesita más épocas que verde y azul con este paso, y no un accidente de la captura b.
- El transitorio del rojo b (40-120) **no** se reproduce en s3. Lo más probable es que dependa de esa captura o
  geometría (6 LEDs de campo claro, z 98, franjas de fondo), no del color. Con dos sets no se puede separar.
- En s3, más épocas mejoran la predicción de LEDs no vistos pero no la repetibilidad en alta frecuencia: C2 sigue sin
  evidencia de detalle más allá de 2NA/λ, igual que el veredicto del 25/09 (C2 FAIL). Las épocas no cambian ese
  veredicto. Las franjas que crecen a 120-400 sugieren que parte de la mejora tardía de C1 es ajuste de fondo.

### Limitaciones (s3)

Las mismas que en b (una zona, sin verdad, umbrales sin recalibrar, una sola partición en mitades, paso 0.3, sd
poblacional entre folds que comparten entrenamiento), más: el nulo de s3 está cerca del valor real en todas las
épocas, así que diferencias de C2 de 0.001-0.01 entre épocas no son interpretables.

## Archivos

- `analisis/analizar.py`: métricas por época.
  - Escribe `analisis/b_red.json`, `b_green.json`, `b_blue.json` y `colores.json`.
  - El log está en `analisis/analizar.log`.
  - Cada json tiene todas las épocas, los C1 por fold, las curvas FRC completas a 0/5/20/40/120/400 y la verificación a e = 40.
- `analisis/figuras.py`: figuras en `analisis/figs/`.
  - `curvas_metricas.png`: C1 con sin FPM, entrenamiento contra no vistos, C2 con nulo y umbral, y brecha.
  - `c1_por_anillo.png`, `estabilidad.png`, `frc_curvas.png` y `colores.png`.
  - `montaje_b_red.png`, `montaje_b_green.png` y `montaje_b_blue.png`.
- Set 3: `analisis/s3_red.json` (log `analisis/analizar_s3.log`), `figs/montaje_s3_red.png`; la serie s3_red está en
  las figuras de curvas.
- Fase B (particiones aleatorias): `particiones.py` (importa `iter_runner`, mismo solver; `check` verifica la partición
  oficial a 20 épocas: diferencia 0), `run_part.sh` (lanzador resumible), log `particiones.log`, objetos en
  `out_part/<DS>/p<s>_h<h>/`; análisis `analisis/particiones_c2.py` → `analisis/particiones_<DS>.json`.

## C2 con 5 particiones aleatorias (rojo 28/09 b) — escrito por la sesión coordinadora, 01/10 00:25

Particiones: LEDs de campo claro fijos en damero (como `run.half_tasks`), 219 de campo oscuro repartidos al azar 50/50 estratificado por anillo, semillas 0..4 (`particiones.py`, check bit-idéntico contra la partición oficial). C2 en banda [2NA/λ, 0.45] 1/µm, sin ventana (oficial) y con ventana de Hann. Datos: `analisis/particiones_b_red.json` (salida de `particiones_c2.py b_red`). sd muestral (ddof=1). Azul: en curso.

| época | C2 oficial, media ± sd (min–max) | n > 0.143 | C2 Hann, media ± sd (min–max) | n > 0.143 | damero oficial / Hann |
|---|---|---|---|---|---|
| 20 | 0.059 ± 0.009 (0.044–0.068) | 0/5 | 0.084 ± 0.021 (0.059–0.105) | 0/5 | 0.077 / 0.131 |
| 40 | 0.070 ± 0.010 (0.056–0.082) | 0/5 | 0.101 ± 0.023 (0.071–0.127) | 0/5 | 0.083 / 0.146 |
| 120 | 0.088 ± 0.011 (0.073–0.101) | 0/5 | 0.130 ± 0.047 (0.062–0.191) | 2/5 | 0.095 / 0.150 |
| 400 | 0.115 ± 0.025 (0.091–0.147) | 1/5 | 0.160 ± 0.065 (0.079–0.254) | 3/5 | 0.105 / 0.154 |

Cambio pareado respecto de 40 (oficial): 20 → −0.012 ± 0.002; 120 → +0.017 ± 0.003; 400 → +0.045 ± 0.025 (las 5 particiones positivas, mínimo +0.009).

**Hechos.**
- En el rojo, C2 oficial sube con las épocas en las 5 particiones aleatorias (y en la oficial): es robusto a la partición.
- La partición damero da C2 más alto que todas las aleatorias a 20 y 40 épocas (0.083 vs máx 0.082 a 40; con Hann 0.146 vs máx 0.127).
- El cruce del umbral NO es robusto: con la métrica oficial, 1 de 5 particiones lo supera y solo a 400 épocas (0.147); con Hann, 0/5 a 40, 2/5 a 120 y 3/5 a 400, con dispersión grande (0.079–0.254).

**Interpretación.**
- El "0.146 con Hann a 40 épocas" de REVISION.md era propio de la partición damero; con particiones aleatorias a 40 ninguna llega.
- Más épocas aumentan la coincidencia entre mitades en el detalle fino del rojo, pero con 400 épocas la media sigue bajo el umbral con la métrica oficial. No hay todavía evidencia robusta de ganancia de resolución.
- Limitación: no se calculó un nulo (_scr) por partición aleatoria; la comparación con el azar se apoya en el nulo de la partición oficial (≈0.011–0.015).

### Azul (28/09 b), 5 particiones aleatorias — 01/10 01:30

Datos: `analisis/particiones_b_blue.json`. Por partición (oficial / Hann):

| partición | 20 | 40 | 120 | 400 |
|---|---|---|---|---|
| p0 | 0.073 / 0.109 | 0.075 / 0.124 | 0.072 / 0.131 | 0.073 / 0.147 |
| p1 | 0.055 / 0.068 | 0.052 / 0.077 | 0.048 / 0.074 | 0.057 / 0.072 |
| p2 | 0.065 / 0.058 | 0.069 / 0.062 | 0.069 / 0.062 | 0.076 / 0.069 |
| p3 | 0.082 / 0.071 | 0.086 / 0.083 | 0.088 / 0.089 | 0.081 / 0.087 |
| p4 | 0.070 / 0.088 | 0.070 / 0.091 | 0.065 / 0.091 | 0.065 / 0.090 |
| media aleatorias | 0.069 / 0.079 | 0.071 / 0.087 | 0.069 / 0.090 | 0.071 / 0.093 |
| damero (oficial) | 0.094 / 0.052 | 0.099 / 0.056 | 0.103 / 0.058 | 0.112 / 0.080 |

**Hechos.**
- Con particiones aleatorias, C2 oficial del azul es plano con las épocas (media 0.071 a 40 y 0.071 a 400; cambio pareado 40→400 ≈ 0.000, signos mixtos 2+/3−).
- La subida 0.099 → 0.112 del azul solo aparece en la partición damero, que además da C2 oficial más alto que todas las aleatorias en todas las épocas.
- Umbral 0.143: oficial 0/5 en todas las épocas; Hann 1/5 (p0, 0.147) solo a 400.

**Interpretación y corrección a lo anterior.**
- La afirmación "solo el azul sube de forma robusta (+0.018 ± 0.006, 8/9 teselas)" (INFORME y REVISION) dependía de la partición damero: no se sostiene con particiones aleatorias. En el rojo, en cambio, la subida sí es robusta a la partición.
- En ambos colores la partición damero da C2 oficial más alto que las aleatorias a 40 épocas (rojo 0.083 vs 0.056–0.082; azul 0.099 vs 0.052–0.086). Posible causa (no verificada): en damero cada LED de una mitad tiene vecinos inmediatos en la otra, así que las dos mitades cubren el espacio de frecuencias de forma más pareja; una partición aleatoria deja huecos locales. Esto importa para el umbral 0.143, que se fijó con la partición damero: hay que reportar qué partición se usa, o promediar varias.

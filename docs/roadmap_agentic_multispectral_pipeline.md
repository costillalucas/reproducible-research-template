# Roadmap: Pipeline de microscopía FPM multiespectral asistido por agentes

Objetivo final del proyecto: un pipeline de Fourier Ptychographic
Microscopy (FPM) que reconstruye objetos **multiespectrales** (RGB, dado el
hardware real del laboratorio) orquestado por **agentes de IA** (tipo
Claude Code) que deciden parámetros, calibran, disparan reconstrucciones,
evalúan calidad/convergencia y reintentan/ajustan automáticamente sobre el
código físico ya existente en `src/ptyco_full_simulator/`.

Este documento es solo de planificación — no toca código ni la parte de
procedencia (`structure/`, `data/numbers.json`).

## 0. Qué significa "multiespectral" acá, concretamente

`src/ptyco_full_simulator/config.py` ya lo define: el hardware real es un
**arreglo LED RGB secuencial** — `CHANNEL_WAVELENGTH_NM = {"red": 630,
"green": 530, "blue": 470}`. El propio comentario del archivo lo deja
explícito: *"each grid position is captured once per color, one channel
reconstructed at a time for now (...) combining all 3 channels into one
solid reconstruction is a later goal, not implemented yet"*. Los datos
reales ya están organizados por canal en disco
(`data/<channel>/<N>x<N>_recortada_<crop>/fila<row>_columna<col>.tiff`,
ver `io_utils.py`), así que no es un problema de captura sino de
**reconstrucción conjunta**: hoy `reconstruct()` corre tres veces
independientes (una por canal) y nunca comparte información entre ellas.

## 1. Análisis de brechas

**Lo que existe hoy** (confirmado leyendo `reconstruction.py`,
`forward_model.py`, `optics.py`, `spectral_ops.py`,
`tests/test_ptyco_simulator.py`):

- Forward model + reconstructor Wirtinger flow (Bian et al. 2015,
  `bian2015`) **monocromático**: una longitud de onda por corrida, pasada
  como escalar (`wavelength_um`) a `circular_pupil`, `led_crop_window`,
  `illumination_spatial_freq`.
- Pupila NA-limitada **estática** (sin recuperación de aberraciones — gap
  #1 de `priority_focus`, paper `ou2014`).
- Sin auto-calibración de ángulos LED (gap #2, `eckert2018`).
- Step size con rampa fija, no adaptativa (gap #3, `zuo2016`).
- Tests (`test_ptyco_simulator.py`) prueban que la reconstrucción
  multi-LED recupera fase (`phase_correlation > 0.85`) y que un control
  negativo de un solo LED falla (`< 0.3`) — sigue vigente, sin cambios
  desde que se implementó. El bug de normalización 1/N en el adjunto de
  `ifft2` (línea 87 de `reconstruction.py`, comentario explícito) sigue
  corregido y documentado ahí mismo.
- Limitación documentada en `README.md` y en el docstring del test: un
  objeto de fase grande/alta frecuencia en grilla LED chica puede
  converger a un mínimo local — propiedad conocida del Wirtinger flow
  vanilla, no un bug.

**Lo que falta para multiespectral real:**

1. **Reconstrucción conjunta RGB**, no tres corridas independientes. Cada
   canal ve una escena físicamente idéntica (mismo objeto, distinta
   longitud de onda) — hoy no se comparte nada entre las tres
   reconstrucciones, tirando información redundante que podría acelerar
   convergencia o mejorar SNR.
2. **Geometría dependiente de λ**: `optics.upsampling_factor` y
   `hr_pixel_size_um` dependen de `wavelength_um`, así que cada canal
   produce naturalmente una grilla HR de tamaño/paso distinto — hay que
   resolver el registro/alineación entre los tres antes de poder fusionar
   nada (no está implementado ni testeado).
3. **Aberración cromática de la pupila**: `circular_pupil` usa `na` y
   `wavelength_um` para el corte, pero no hay ningún término de
   aberración dependiente de λ — si el objetivo real tiene dispersión
   cromática, el modelo actual no la captura.
4. La bibliografía tiene un paper directamente sobre esto que **no** está
   en `priority_focus` (el ranking de notebook.md se hizo contra el gap
   monocromático, antes de que "multiespectral" fuera el objetivo
   declarado): `chen2022b`, *"Rapid Full-Color FPM via Spatially Filtered
   Color Transfer"* (Photonics Research, 2022,
   `references/papers/2022/2410.pdf`), notado en `bibliography.yaml` como
   *"Relevante solo si el sensor/pipeline es a color"* — que es
   exactamente este caso ahora. **Importante:** leyendo la nota completa,
   `chen2022b` resuelve un problema distinto (velocidad de reconstrucción
   a color vía transferencia de color desde una banda reconstruida rápido,
   no un solver que acopla físicamente los tres canales). No sirve como
   receta lista para el punto 5 de abajo — solo como referencia de qué NO
   estamos haciendo.
5. **Explotar la tripleta (fase, λ) de los 3 canales, no solo fusionar
   colores — esta es la línea que el usuario identificó como el aporte
   potencialmente novedoso del proyecto.** Ninguno de los 37 papers de
   `bibliography.yaml` cubre esto (búsqueda por "unwrap", "dispersion",
   "refractive index", "multi-wavelength" sin resultados) — es una brecha
   real en la bibliografía curada, no solo un gap de prioridad. Dos frentes
   concretos, ambos habilitados por tener φ_red(x,y), φ_green(x,y),
   φ_blue(x,y) del mismo objeto físico:
   - **Multi-wavelength phase unwrapping**: la fase reconstruida por FPM es
     módulo 2π; la ambigüedad de desenvolvimiento depende de λ. Con 2+
     longitudes de onda distintas se puede resolver el entero de
     desenvolvimiento vía "beat wavelength" (técnica clásica de
     interferometría de dos/múltiples longitudes de onda, p. ej. Cheng &
     Wyant 1984). **[Actualizado tras chequeo de literatura externa,
     2026-09-17, ver `docs/literature_check_multispectral_dispersion.md`]**
     no está publicado aplicado a FPM propiamente dicho, pero sí a la
     técnica hermana Fourier Ptychographic Topography: `shen2025`
     ("Dual-wavelength Fourier Ptychographic Topography", Shen/Li/.../Tian,
     arXiv:2512.08883, dic-2025 — agregado a `references/bibliography.yaml`).
     Calcula una **longitud de onda sintética ("batido") λ_s =
     λ1·λ2/|λ1−λ2|**, que amplía el rango sin ambigüedad a λ_s/2, y resuelve
     el número de envolvimiento por píxel con búsqueda robusta a ruido +
     regularización TV circular global — validado en silicio, no en fase de
     objeto transparente ni con 3 canales (ellos usan 2 λ). Es el algoritmo
     a adaptar para el milestone 2b: aplicar el mismo batido de a pares
     entre los 3 canales RGB (red-green, green-blue, y opcionalmente
     red-blue como chequeo cruzado) en vez de partir de cero.
   - **Recuperación de la curva de dispersión n(λ) de la muestra**: si el
     camino óptico OPL(λ) = n(λ)·t no es constante en λ (dispersión
     normal), las tres φ(λ) más un modelo paramétrico de dispersión (p.
     ej. Cauchy de 2 parámetros: n(λ) = A + B/λ²) dan un sistema resoluble.
     **[Corregido en milestone 2b.ii, ver más abajo]**: NO son "3
     incógnitas, 3 ecuaciones, exactamente determinado" como decía esta
     misma línea originalmente — OPL(λ) solo depende de los productos
     A·t y B·t, nunca de A, B, t por separado (degeneración física real).
     Con 3 canales el sistema para esos 2 productos queda
     sobre-determinado, lo que sí ayuda a promediar ruido. **Precondición:
     requiere resuelto el punto de unwrapping anterior**, porque φ debe
     estar desenvuelta antes de que la ecuación OPL = φ·λ/2π tenga sentido
     físico.

   Esto no está en el roadmap original como milestone propio — se agrega
   como milestone 2b más abajo. Antes de implementarlo vale una búsqueda
   externa puntual (fuera de los 37 papers ya curados) por
   "multi-wavelength phase unwrapping ptychography" / "refractive index
   dispersion quantitative phase imaging", porque la técnica en sí no es
   nueva en QPI/holografía — lo que podría ser nuevo es aplicarla sobre
   una reconstrucción FPM.

6. **[NUEVO — encontrado 2026-09-17 al integrar milestone 2 de punta a
   punta, no en el análisis original] Objetos de amplitud uniforme (fase
   pura) rompen el solver actual.** `reconstruction.py`'s
   `initial_hr_guess` arranca del amplitud de la imagen del LED central;
   con amplitud uniforme esa imagen no tiene estructura espacial alguna, y
   el solver no tiene de dónde agarrarse — `phase_correlation` se vuelve
   *negativa* (peor que ruido) incluso con fase mínima (0.2 rad), muy por
   debajo del límite de 0.08π que ya documentaba milestone 2a para
   objetos CON contraste de amplitud. Con apenas 5-10% de contraste de
   amplitud la calidad se recupera dramáticamente.

   **Por qué importa más que un detalle técnico:** el objetivo declarado
   de este proyecto son muestras biológicas ("digital pathology" en la
   nota de `chen2022b`), que suelen ser casi transparentes — exactamente
   el régimen de bajo contraste de amplitud donde el solver de hoy es más
   débil.

   **[ACTUALIZADO — 2026-09-17, sesión de investigación dedicada, ver
   `tests/test_weak_phase_object_limitation.py`]** Se investigó a fondo
   la causa raíz, no solo el síntoma:

   1. **Es un punto silla degenerado, no un objeto irrecuperable en
      principio.** La inicialización estándar (amplitud del LED central,
      fase exactamente cero) hace que la reconstrucción *empeore* de
      forma monótona y determinista con más iteraciones (no aleatorio,
      reproducible). Pero perturbaciones chicas alrededor de la solución
      *verdadera* (no del punto degenerado) convergen de forma confiable
      y estable — la dinámica del gradiente está bien cerca de la
      respuesta correcta; el problema es específicamente que la
      inicialización arranca justo en el punto degenerado.
   2. **Se descartó una solución barata**: reintentar con varias
      inicializaciones de fase aleatoria y quedarse con la de menor
      `recovery_error` (la métrica interna que ya calcula
      `reconstruction.reconstruct`, exactamente el tipo de decisión que
      el agente de milestone 3 ya sabe tomar) — **no funciona**, porque
      `recovery_error` no está correlacionado con la precisión real para
      este tipo de objeto (en un experimento con 10 semillas, la corrida
      con el `recovery_error` *más bajo* tuvo la *peor* precisión real).
      Es decir: las mediciones de intensidad son casi insensibles a la
      fase acá, así que un buen ajuste a los datos no implica una fase
      correcta.
   3. **Coincide exactamente con un paper ya citado en la bibliografía,
      leído recién después de encontrar el hallazgo empíricamente**:
      `rogalski2025` ("FPM Aided with Transport of Intensity Equation")
      — su abstract dice literalmente que FPM está "fundamentally
      limited in retrieving low spatial frequency phase information due
      to the absence of phase encoding in all on-axis and slightly-off-
      axis (brightfield) illumination angles" — exactamente el mecanismo
      medido acá (el LED central casi no tiene contraste de amplitud
      para este tipo de objeto: std/mean=0.0008). Su arreglo: una imagen
      extra desenfocada on-axis + Transport of Intensity Equation para
      recuperar específicamente la fase de baja frecuencia espacial que
      FPM no puede ver. Reclasificado en `bibliography.yaml`
      (`applicable_to_gap: true`) y agregado como rank 7 de
      `priority_focus` (no estaba en el análisis original de
      notebook.md).

   **Implicación práctica**: este gap es candidato serio a atacar antes
   que pupil recovery (`ou2014`) o adaptive step size (`zuo2016`) —
   posiblemente más urgente que ambos para que este proyecto sirva con
   muestras reales cuasi-transparentes. Implementar FPM+TIE
   (`rogalski2025`) es el siguiente paso concreto y bien fundamentado,
   no una exploración a ciegas.

   **[HECHO parcialmente — 2026-09-17, misma sesión de seguimiento]
   Las dos piezas de física de TIE, implementadas y validadas por
   separado — la fusión con FPM todavía no.** Nuevo módulo
   `src/ptyco_full_simulator/propagation.py`:
   - `angular_spectrum_propagate`: propagación de campo por desenfoque
     (método del espectro angular, exacto, no la aproximación paraxial de
     Fresnel). Ida y vuelta (+d luego -d) recupera el campo original a
     precisión de punto flotante (~1e-16).
   - `solve_tie`: la ecuación de transporte de intensidad clásica
     (Teague 1983, aproximación de absorción débil), resuelta en el
     dominio de Fourier. Probado recuperando un objeto de fase débil
     conocido (el mismo tipo de objeto que rompe el solver FPM en
     `tests/test_weak_phase_object_limitation.py`) con correlación
     >0.99 a partir de dos capturas desenfocadas simuladas — exactamente
     la fase de baja frecuencia que FPM no puede ver.

   **[ACTUALIZADO — 2026-09-17, misma sesión, fusión FPM+TIE probada] La
   fusión post-hoc NO funciona de forma confiable; inicializar FPM con la
   fase de TIE sí.** Se probaron dos estrategias:
   - **Empalme espectral post-hoc** (`propagation.merge_low_and_high_frequency_phase`,
     bajo+TIE / alto+FPM combinados después de que ambos terminaron): **no
     superó de forma confiable usar TIE solo** en los objetos de prueba —
     la recuperación de alta frecuencia de FPM se degrada cuando también
     hay una componente de baja frecuencia mal manejada en el mismo
     objeto (el solver acopla frecuencias de forma no lineal a través del
     estimado de amplitud compartido; no son canales independientes como
     asumía el diseño original). Queda implementada como utilidad general
     pero con esta salvedad documentada en su propio docstring.
   - **Inicializar el solver FPM con la fase de TIE** (en vez de fase
     cero) — `reconstruction.reconstruct` ahora acepta un parámetro
     `initial_object` para esto. **Funciona de forma mucho más
     confiable**: en los 3 objetos de prueba, siempre superó
     dramáticamente a la inicialización estándar (ej. 0.99 vs -0.01,
     0.85 vs 0.66, 0.99 vs -0.008). Tiene sentido con el hallazgo del
     punto silla de la sección 1.6: TIE le da a FPM un punto de partida
     que no es el punto degenerado, y desde ahí el propio gradiente de
     FPM funciona bien (como ya se había probado con perturbaciones
     chicas alrededor de la verdad).

     **Salvedad honesta, no oculta**: si seguir iterando FPM después de
     partir de TIE *mejora* o *empeora* el resultado más allá de lo que
     TIE ya dio, es inconsistente entre objetos — en un caso mejoró de
     forma monótona en las 40 iteraciones (0.976→0.986), en otro empeoró
     de forma igual de monótona (0.925→0.850). Ambas tendencias son
     suaves dentro de su propia corrida (no ruido), pero la dirección no
     se puede predecir de antemano sin verdad conocida. No hay un punto
     de corte universal seguro ("pocas iteraciones" no alcanza en el caso
     que mejora gradualmente).

     **[ACTUALIZADO — 2026-09-17, se probaron 3 diagnósticos candidatos,
     ninguno sirve todavía]** Antes de dejarle esto al agente de
     milestone 3 sin más, se probó si existía algún diagnóstico interno
     (sin verdad conocida) que distinguiera el caso que mejora del que
     empeora:
     1. **Residuo en LEDs de validación** (dejar ~15% de LEDs fuera del
        ajuste, medir el error solo ahí — validación cruzada clásica):
        en el caso que empeora, el residuo de validación *mejora* de
        forma monótona (0.64→0.23) mientras la precisión real de fase
        *empeora* (0.92→0.85) — va en la dirección **contraria**. No
        sirve.
     2. **Correlación de la componente de baja frecuencia actual contra
        la fase de TIE** (ya confiable, fija): en ambos casos se
        mantiene altísima y casi constante (0.994-1.0) — hay una
        diferencia real pero mínima (el caso que empeora se aleja un
        poco más de TIE), demasiado chica para ser un umbral práctico
        sin más ruido de por medio.
     3. `recovery_error` (ya descartado antes, sección 1.6).

     **Por qué importa que los tres fallen de la misma manera**: todos
     se derivan de mediciones de **intensidad/amplitud** — exactamente
     lo que ya se estableció como casi insensible a la fase en el
     régimen de fase débil (sección 1.6). Ningún diagnóstico construido
     *solo* a partir de ese mismo tipo de medición va a poder discriminar
     bien acá, sin importar cuán ingenioso sea el diseño (entrenamiento,
     validación, comparación con un prior externo) — es una limitación de
     información, no de falta de una métrica más inteligente. Vale
     intentar algo que traiga información genuinamente nueva (ej. una
     segunda medición de TIE a mitad de la corrida de FPM, no solo al
     principio) en vez de seguir buscando un diagnóstico más clever sobre
     los mismos datos de intensidad. Sigue sin resolver — sigue siendo un
     candidato para el agente de milestone 3, pero con el espacio de
     soluciones ya acotado por estos tres intentos fallidos.

   Probado en `tests/test_tie_informed_initialization.py` (2 tests): la
   mejora de TIE-informado sobre el arranque estándar, y que
   `initial_object=None` no cambia el comportamiento existente
   (`reconstruction.reconstruct` sigue siendo retrocompatible).

   **[HECHO — 2026-09-17] Conectado a `pipelines/`.**
   `simulate_and_reconstruct.py` ahora acepta `--tie-defocus-um`: simula
   el par de capturas on-axis desenfocadas del mismo objeto conocido,
   resuelve TIE, y usa esa fase para inicializar el solver en vez de
   cero. Probado end-to-end vía CLI real (no solo llamando a las
   funciones de librería) en
   `tests/test_simulate_and_reconstruct_tie.py`: mismo objeto,
   `phase_correlation` pasa de <0.3 (roto) a >0.8 con el flag. El JSON
   de métricas guarda `tie_defocus_um` para que quede trazable qué
   corrida usó qué inicialización.

   **[HECHO — 2026-09-17] También conectado al pipeline multiespectral
   real** (`reconstruct_multispectral_independent.py`), no solo al de un
   canal simulado. Como acá se usan capturas reales (no un objeto
   conocido para simular el desenfoque), se definió una convención nueva
   de archivo — `io_utils.load_defocus_pair` espera
   `defocus_plus.tiff`/`defocus_minus.tiff` junto al escaneo normal de
   cada canal (no es algo que el laboratorio ya capture hoy; queda
   propuesta para quien agregue ese paso de captura). Con `--tie-defocus-um`,
   cada canal usa su propia fase de TIE para inicializar. Probado en
   `tests/test_reconstruct_multispectral_tie.py` con capturas falsas
   generadas del mismo objeto para los 3 canales — mejora en los 3, en
   distinta magnitud por canal (consistente con que cada longitud de
   onda tiene su propia sensibilidad, ya visto en milestone 2a).

   **Sigue sin resolver (ver arriba)**: la política de cuántas
   iteraciones correr después de la inicialización con TIE. Los CLIs hoy
   simplemente corren `--iterations` completas con la advertencia impresa
   de revisar `metrics.json`'s history a mano — no deciden nada todavía.

7. **[NUEVO — 2026-09-17, investigado en vivo con el usuario a partir de
   un análisis propio suyo] Altura del arreglo de LEDs (`z_distance_mm`):
   dos óptimos distintos, uno de amplitud y uno de fase — no confundirlos.**
   El usuario había encontrado empíricamente (variando la altura y
   midiendo con `mse_complejo_alineado` y `recovery_error`, fuera de este
   repo) que z≈51mm da mejor reconstrucción que otras alturas para el
   objetivo `"current"` (NA=0.07). Se reprodujo acá, con hallazgos más
   precisos:
   - **z≈51mm es un óptimo real, pero de AMPLITUD**, no de fase
     (`amp_corr` pico ~0.39 ahí, mejor que z=70mm en adelante). El MSE
     complejo alineado hereda ese pico porque, al ser la fase del objeto
     chica, |campo|≈|amplitud| domina la magnitud del error — esconde que
     la fase sigue siendo mala en ese punto (`phase_corr`≈0.03,
     prácticamente ruido).
   - **`recovery_error` tampoco sirve acá**: en el mismo rango donde
     `amp_corr` mejora hacia 51mm, `recovery_error` se mantiene chato o
     empeora levemente — mismo patrón de desconexión entre esa métrica
     interna y la precisión real ya encontrado en el punto 6/`recovery_error`.
   - **La fase tiene su propio umbral, en otro punto geométrico**: se
     encontró (y se agregó a `led_array.py` como
     `adjacent_led_overlap_ratio`, con test dedicado en
     `tests/test_led_overlap_ratio.py`) que `phase_correlation` salta de
     forma abrupta (~0.04 → ~0.52) justo cuando el solapamiento en
     Fourier entre sub-aperturas de LEDs vecinos cruza **~28%** — en la
     configuración por defecto de este proyecto (pitch=6mm, z=70mm), ese
     cruce ocurre muy cerca de z=70mm. Esto es del mismo orden que el
     mínimo de "35% overlap" que cita `eckert2018` en su introducción
     para que la recuperación de fase funcione en absoluto — no es una
     coincidencia exacta de número (formas de definir "overlap" difieren
     entre papers/sistemas), pero sí confirma que este simulador
     reproduce una restricción física real de ptychography, no un
     artefacto del solver.

   **Implicación práctica para el usuario**: si su barrido de alturas se
   hizo con una métrica dominada por amplitud (`mse_complejo_alineado`)
   y el objetivo del proyecto es recuperar **fase** (dispersión, espesor
   — todo el punto de este proyecto), esa altura óptima probablemente no
   es la correcta. Vale rehacer ese análisis mirando `phase_correlation`
   por separado, o usando `adjacent_led_overlap_ratio` directamente como
   criterio de diseño en vez de barrer alturas a ciegas.

## 2. Diseño de la capa de agentes

Principio guía: un agente LLM solo tiene sentido donde hace falta
**juicio/adaptación bajo incertidumbre**; un paso determinista (cargar un
TIFF, correr una FFT, comparar contra ground truth) sigue siendo código
plano, no un agente. Mapeando contra `priority_focus` y el pipeline
actual:

| Agente | Qué decide | Por qué es agent-shaped |
|---|---|---|
| **Capture/LED-selection agent** | Qué subconjunto de LEDs/canales priorizar dado tiempo/SNR disponible (gap #5, `tian2014` multiplexado) | Trade-off sin regla fija: depende de objeto, ruido observado, tiempo disponible |
| **Calibration agent** | Corrige ángulos LED asumidos vs. reales a partir de los propios datos (gap #2, `eckert2018`); decide cuándo la auto-calibración convergió vs. cuándo hace falta intervención manual | Requiere leer residuales y decidir "¿esto es ruido o desalineación sistemática?" |
| **Reconstruction-orchestration agent** | Dado `metrics.convergence_summary()` (ya existe), decide: seguir iterando, bajar `step_max`/reintentar con otra inicialización (gap #3, `zuo2016`), o declarar la corrida como estancada en mínimo local (limitación ya documentada) | Es exactamente el tipo de decisión "¿reintento con otros parámetros o no?" que hoy un humano hace leyendo `history` a mano |
| **Cross-channel consistency agent** | Una vez resuelto el registro geométrico (punto 1.2), decide si las tres reconstrucciones RGB son consistentes (mismos bordes de amplitud en los tres canales) o si una divergió y hay que re-lanzarla con otra semilla/paso | No existe hoy ningún chequeo de consistencia cruzada; es nuevo, no una migración de código existente |
| **Confidence/QC agent** | Sobre datos reales (sin ground truth), estima si una reconstrucción es confiable antes de reportarla (gap #6, `chen2025`, Uncertainty-Aware FP) | Sin ground truth, es juicio sobre calidad, no una comparación numérica directa como `compare_to_ground_truth` (que solo aplica a `simulate_and_reconstruct.py`) |
| **Report/provenance agent** | Redacta `report/report.md` con tags `[src:]`/`[srcnum:]` y actualiza `structure/claims.yaml` a partir de una corrida terminada | Tarea de síntesis en lenguaje natural + mapeo a un esquema estructurado — no un cálculo |

**Explícitamente NO agent-shaped** (quedan como código determinista, no
delegar a un LLM): `forward_model.simulate_lr_stack`, el propio bucle de
gradiente en `reconstruction.reconstruct`, `metrics.compare_to_ground_truth`,
la carga de TIFFs en `io_utils`. Ninguno de estos requiere juicio — son
cálculo numérico puro, y ya están implementados y testeados.

## 3. Milestones por fases

Orden pensado para validar barato primero (datos/código que ya existen)
antes de construir la capa de orquestación, y siguiendo el ranking de
`priority_focus` donde aplica.

1. **[HECHO — 2026-09-17] [Físico, sin agentes] Registro geométrico entre
   canales.** Definición de listo: dado un mismo objeto simulado, las tres
   reconstrucciones (red/green/blue) quedan expresadas en una grilla HR
   común (mismo `hr_pixel_um`, mismo `hr_shape`) — hoy no lo están, porque
   `upsampling_factor` depende de λ.

   Implementado: `optics.shared_upsampling_factor(setups)` en
   `src/ptyco_full_simulator/optics.py` — toma el `max()` de
   `upsampling_factor` por canal (el canal de menor λ, típicamente blue,
   manda), garantizando que ningún canal quede sub-muestreado y que los
   tres compartan `actual_hr_pixel_size_um`/`hr_shape` exactamente (no
   solo aproximado). Probado en
   `tests/test_multispectral_registration.py`: (a) confirma que el gap es
   real (factores por canal difieren sin el fix, con cuidado de no caer en
   una coincidencia de redondeo), (b) confirma que el factor compartido
   iguala pixel/shape entre los 3 canales, (c) corrida end-to-end
   simulate→reconstruct por canal produce tres objetos `stack`-eables en
   un array `(3, H, W)` sin ningún resize.

   **Nota/desviación del plan original**: no se validó contra
   `data/<channel>/9x9_recortada_*` reales — esos datos del laboratorio no
   están en este Codespace (`data/` sin capturas, ver `.gitignore`). Se
   validó contra el objeto sintético determinista (mismo patrón que
   `tests/test_ptyco_simulator.py`), que es lo que el texto original del
   milestone también permitía ("dado un mismo objeto simulado"). Repetir
   la validación con capturas reales cuando estén disponibles.

2. **[Físico, sin agentes] Ambas reconstrucciones, para comparar (decisión
   del usuario — se hacen las dos, no una u otra).**
   - **2a — [HECHO — 2026-09-17] Independiente (baseline, barato):** correr
     `reconstruct()` tres veces (una por canal, ya funcionaba) sobre la
     grilla HR común del paso 1, sin compartir nada entre canales.

     Implementado en `pipelines/reconstruct_multispectral_independent.py`
     (función reusable `reconstruct_all_channels()` + CLI, mismo patrón que
     `reconstruct_real_images.py` pero iterando los 3 canales con
     `optics.shared_upsampling_factor`). Devuelve φ_red, φ_green, φ_blue
     alineadas (mismo `hr_pixel_um`/`hr_shape`, aserción explícita en el
     código); guarda amplitud/fase por canal, un compuesto RGB de amplitud
     (solo visualización, no la fusión real de 2b), y un `.npz` con los 3
     objetos complejos crudos — insumo directo para 2b.i (unwrapping).
     Probado en `tests/test_reconstruct_multispectral_pipeline.py`
     sintetizando capturas TIFF falsas con la convención real del
     laboratorio (mismo motivo que milestone 1: no hay datos reales en
     este Codespace) y corriendo el pipeline completo contra ellas.

     **Hallazgo nuevo, no anticipado en el roadmap original:** con el
     mismo objeto de fase (magnitud 0.15π) que ya usaba
     `test_ptyco_simulator.py` para el canal green, el canal **red
     (630nm, la longitud de onda más larga)** cae de forma reproducible en
     un mínimo local en esta grilla LED chica (9x9, `objective="current"`)
     — `phase_correlation` ≈0.64 y sin mejorar con más iteraciones (hasta
     300 probadas), mientras green/blue convergen bien (≥0.95) con las
     mismas 40 iteraciones. Es una instancia dependiente de canal de la
     limitación de mínimos locales ya documentada para Wirtinger flow
     vanilla en grillas LED chicas (`reconstruction.py`, `README.md`), no
     un bug nuevo — pero antes no se sabía que fuera *peor para red*
     específicamente. A magnitud de fase 0.08π los 3 canales convergen
     bien; el test usa ese valor. **Implicación para datos reales:** si el
     objeto real tiene excursión de fase comparable a 0.15π o mayor, el
     canal red puede necesitar más iteraciones, un `step_max` distinto, o
     ya requerir el pupil recovery/adaptive step size de `priority_focus`
     antes de confiar en su reconstrucción — vale chequear esto temprano
     con datos reales del laboratorio, no asumir que las 3 bandas se
     comportan igual de bien.
   - **2b — Acoplada (la parte novedosa, punto 1.5):** un solver que además
     de reconstruir explota la tripleta (φ, λ) por píxel, en dos etapas:
     - **2b.i — [HECHO — 2026-09-17] Unwrapping por batido (adaptado de
       `shen2025`).** Implementado en
       `src/ptyco_full_simulator/multispectral.py`:
       `synthetic_wavelength`, `search_wrap_numbers` (la búsqueda del par
       (k1,k2) que minimiza el desacuerdo de OPL entre canales — el núcleo
       del método, fiel a las ecuaciones del paper), y `refine_opl_tv`
       (versión simplificada de su refinamiento convexo — TV suavizada +
       cota blanda por descenso de gradiente en vez de ADMM/solver convexo
       exacto, porque solo se tuvo acceso a las ecuaciones vía WebFetch,
       no al algoritmo/pseudocódigo completo del paper). Adaptación
       reflexión→transmisión: su relación es φ=4π/λ·h (ida y vuelta); la
       nuestra es φ=2π/λ·OPL (paso único) — el código generaliza con un
       parámetro `path_factor` para no hardcodear ninguna de las dos.

       Probado en `tests/test_multispectral_unwrapping.py` (5 tests): (a)
       fórmula del batido, (b) recupera un OPL que excede varias veces el
       rango sin ambigüedad de un solo canal (con k≠0 confirmado, no un
       acierto de k=0), (c) control negativo — mismo objeto, `k_range`
       angosto a propósito, falla como se espera, (d) robustez a ruido de
       fase moderado (mediana del error <10nm con ruido de 0.05 rad), (e)
       `refine_opl_tv` reduce la variación total de una estimación ruidosa.

       **Dos hallazgos no anticipados:** (1) el `step_size` por defecto
       inicial (0.2) hacía que el refinamiento *aumentara* la variación
       total en vez de reducirla — el subgradiente de la cota blanda tiene
       magnitud constante (±1) sin importar la distancia al límite, así
       que un paso grande hace oscilar los píxeles cerca del borde; bajado
       a 0.05, estable. (2) El "rango sin ambigüedad" ±λ_s/2 no es un
       corte duro en el caso sin ruido con `k_range` suficientemente
       ancho — la búsqueda recuperó OPL exacto incluso a 3x ese rango; la
       degradación real depende de ruido + cobertura de `k_range`, no de
       un límite físico estricto. No se caracterizó rigurosamente dónde
       empieza a fallar con ruido realista — pendiente si hace falta más
       adelante.
     - **2b.ii — [HECHO — 2026-09-17] Ajuste de dispersión.** Implementado
       en `src/ptyco_full_simulator/multispectral.py`:
       `fit_cauchy_dispersion` y `resolve_thickness_and_dispersion`. Sigue
       sin precedente publicado encontrado (ver
       `docs/literature_check_multispectral_dispersion.md`) — es la parte
       más nueva del proyecto.

       **Corrección a esta misma entrada del roadmap, encontrada al
       implementarla:** el texto original decía "A, B, t: 3 incógnitas, 3
       ecuaciones, exactamente determinado". Eso está mal — es una
       degeneración real, no un error de conteo menor. Físicamente
       OPL(λ) = n(λ)·t = (A + B/λ²)·t = A·t + (B·t)/λ² — el modelo solo
       depende de los **productos** C:=A·t y D:=B·t, nunca de A, B, t por
       separado. Cualquier (A', B', t') con A'·t'=C y B'·t'=D da exactamente
       el mismo OPL(λ) en cualquier longitud de onda — una muestra más
       gruesa con dispersión más débil es indistinguible de una más fina
       con dispersión más fuerte, sin importar cuántos canales se midan.
       Con 3 canales el sistema para (C, D) queda **sobre-determinado**
       (2 incógnitas, 3 ecuaciones) — eso sí es real y sí ayuda: promedia
       ruido (confirmado en test, ver abajo), pero no rompe la
       degeneración A/B/t. Recuperar A, B, t individuales requiere un dato
       externo (p. ej. un índice base A conocido de la literatura para el
       material/medio de la muestra) — `resolve_thickness_and_dispersion`
       lo hace dado ese dato, y devuelve silenciosamente un (t, B)
       autoconsistente pero incorrecto si el A asumido está mal (no hay
       forma de detectar un A equivocado solo con estos datos).

       Probado en `tests/test_dispersion_fit.py` (6 tests): recupera C, D
       exactos (escalar y por-píxel), 2 canales da ajuste exacto (2x2,
       sin redundancia), 3 canales es más robusto a ruido que cualquier
       par de 2 (comparado explícitamente), la degeneración A/B/t es real
       (dos ternas físicas distintas dan el mismo OPL(λ)), y
       `resolve_thickness_and_dispersion` con un A incorrecto devuelve un
       resultado autoconsistente pero equivocado sin señal de error.

     Definición de listo (2b completo): 2a + 2b.i + 2b.ii implementados y
     testeados de forma independiente (arriba). **Pendiente, no hecho
     todavía:** ~~correr la cadena completa 2a→2b.i→2b.ii de punta a
     punta...~~ **[HECHO — 2026-09-17].**

     Implementado `src/ptyco_full_simulator/multispectral.py`'s
     `couple_rgb_channels` (referencia de pistón por canal + unwrapping
     red-green/green-blue + fit de dispersión, todo en una función) y
     `pipelines/reconstruct_multispectral_coupled.py` (CLI sobre datos
     reales del lab, construido sobre `reconstruct_all_channels` de 2a).
     Probado en `tests/test_multispectral_end_to_end.py` con dos tests
     distintos a propósito (no confundir uno con el otro):
     - Uno corre la cadena completa a través del solver Wirtinger flow
       **real** (no fase inyectada) y confirma que recupera la forma del
       campo de espesor (correlación >0.5 con la verdad).
     - Otro aísla el valor de 2b.i/2b.ii inyectando fase directamente
       (sin pasar por el solver) con una señal de dispersión grande que
       *sí* requiere desenvolvimiento real, y confirma que el pipeline
       acoplado le gana por mucho (<5% del error) a la alternativa
       ingenua de tratar la fase cruda envuelta como si ya fuera el OPL
       (k=0 en todos lados) — la comparación que pedía originalmente esta
       misma entrada del roadmap.

     **Por qué dos tests separados, no uno solo:** al intentar construir
     un único test de punta a punta con una señal de dispersión grande
     (que sí necesite desenvolvimiento) PASANDO por el solver real,
     apareció un límite del solver mucho más severo de lo esperado — ver
     el hallazgo nuevo abajo. La fase que el solver actual puede
     reconstruir de forma confiable (aun en el mejor caso) queda muy por
     debajo de lo necesario para generar ambigüedad de envolvimiento real
     (necesita exceder π rad; el solver ya sufre bastante por debajo de
     0.3 rad). Separar los dos tests es la forma honesta de probar cada
     cosa: que el software está bien cableado (test 1, con el solver
     real), y que la lógica de desenvolvimiento/dispersión en sí misma
     tiene valor (test 2, con fase inyectada) — sin fingir que el solver
     de hoy ya puede generar el caso de prueba ideal para el test 2.

     **Hallazgo nuevo, el más importante encontrado en toda esta
     integración:** el solver Wirtinger flow actual (`reconstruction.py`)
     **falla casi por completo en objetos de amplitud uniforme (fase
     pura)** — `phase_correlation` se volvió *negativo* (peor que ruido)
     incluso con magnitud de fase mínima (0.2 rad), muy por debajo del
     límite de 0.08π ya documentado en el milestone 2a. La causa:
     `initial_hr_guess` arranca del amplitud de la imagen del LED central
     — con amplitud uniforme esa imagen no tiene ninguna estructura
     espacial, y el solver no tiene de dónde agarrarse para localizar
     correcciones de fase. Con apenas 5-10% de contraste de amplitud, la
     calidad se recupera dramáticamente (de correlación negativa a
     ~0.6-0.9 según el resto de la geometría). **Esto importa mucho más
     que un detalle de test**: el objetivo declarado del proyecto son
     muestras biológicas cuasi-transparentes (ver `chen2022b`,
     "digital pathology" en la bibliografía) — exactamente el régimen de
     bajo contraste de amplitud/fase-dominante donde el solver de hoy es
     más débil. No estaba documentado antes de esta integración. Vale
     agregarlo a `priority_focus` o al menos a la lista de gaps a atacar
     junto con pupil recovery/adaptive step size — puede que sea más
     urgente que ambos para el objetivo real del proyecto.

     También se confirmó, ahora con un modelo de dispersión físicamente
     consistente (no solo la misma magnitud de fase artificial en los 3
     canales como en milestone 2a): el canal más débil para converger
     depende de la magnitud de OPL, no es siempre red — con OPL
     compartido entre canales, **blue** (la λ más corta) recibe la mayor
     magnitud de fase (φ=2π·OPL/λ) y es sistemáticamente el más difícil de
     los tres, consistente con y extendiendo el hallazgo de canal-dependiente
     de milestone 2a.

   - Métrica de comparación 2a vs 2b: **[HECHO]** ver el segundo test de
     `tests/test_multispectral_end_to_end.py` arriba — con una señal de
     dispersión grande, el pipeline acoplado (2b) recupera el espesor con
     <5% del error de la alternativa ingenua (2a + asumir k=0). Con una
     señal chica (dentro del rango de un solo canal, sin necesidad real de
     desenvolvimiento) ambos son equivalentes, como es de esperar.

3. **[Agente #1 — HECHO 2026-09-17] Reconstruction-orchestration agent.**
   Implementado en `agents/reconstruction_orchestrator.py`:
   `orchestrate_reconstruction` corre `reconstruction.reconstruct`, arma
   un prompt con `metrics.convergence_summary` (`build_decision_prompt`) y
   se lo pasa a `claude -p --restricted --json-schema ...` pidiendo una
   decisión estructurada: `accept` / `retry` (con `new_step_max` sugerido)
   / `give_up`. Reintenta hasta `max_attempts`, con auditoría completa de
   qué decidió el agente y por qué en cada intento.

   Probado en `tests/test_reconstruction_orchestrator.py` (6 tests) **sin
   llamar a la API real** — se inyecta un `agent_fn` stub (decisiones
   canned) para probar la lógica de reintentos (para en `accept`, aplica
   `new_step_max` en el siguiente intento, para inmediato en `give_up`,
   nunca reintenta más allá de `max_attempts` aunque el agente siga
   pidiendo `retry`) sin gastar dinero real en cada corrida de tests.

   **Hallazgo de costo/latencia, medido con 2 llamadas reales en vivo
   durante el desarrollo:** una llamada sin restringir y sin modelo fijado
   costó **$0.13 y tardó ~9s**, con turnos de uso de herramientas
   inesperados (exploró el filesystem del proyecto sin que hiciera falta
   para una decisión tan simple). Con `--restricted` (sin Bash/tools) y
   `--model claude-haiku-4-5-20251001` fijado, bajó a **~$0.03-0.04 y
   ~10-11s**, igual más lento/caro de lo que uno esperaría para una
   decisión de "¿reintento o no?". **Implicación práctica:** este patrón
   (invocar `claude -p` como subproceso) no es gratis ni instantáneo — no
   conviene llamarlo en cada iteración del solver, solo en checkpoints
   (p. ej. al final de una corrida completa, como está armado acá), y
   vale la pena seguir explorando si un modelo más chico/rápido o un
   prompt más acotado lo abarata más. Ningún test de la suite regular hace
   esta llamada real — queda documentado acá como referencia de costo.

4. **[Agente #2 — núcleo numérico HECHO 2026-09-17, capa de agente
   todavía no] Calibration agent** (gap #2, `eckert2018`) — el gap de
   mayor impacto en datos reales según notebook.md, porque hoy
   `reconstruct_real_images.py` no corrige nada de error de posición LED.

   Implementado en `src/ptyco_full_simulator/led_calibration.py`, leyendo
   el PDF completo del paper (no solo notas/abstract):
   `spectral_correlation_correction` (Eq. 7 del paper — búsqueda local en
   grilla de enteros por LED que refina la posición contra el espectro de
   objeto actual) y `fit_similarity_transform`/`apply_similarity_transform`
   (regularización "Rigid Source Projection" de la Fig. 3a — ajuste
   cerrado por mínimos cuadrados de una transformación de similitud
   rotación+escala+traslación, en vez de RANSAC como el paper).
   **Explícitamente NO implementado**: la etapa de calibración brightfield
   (Algorithm 1 del paper — detección de círculos por gradiente radial en
   el espectro de Fourier de cada imagen brightfield, que da el bootstrap
   inicial). Ver el docstring del módulo para el detalle completo de qué
   se adaptó y qué no.

   Probado en `tests/test_led_calibration.py` (3 tests, dos historias
   distintas):
   - **Resultado positivo**: dado un buen estimado del espectro del
     objeto (el que tendría una reconstrucción ya bien calibrada),
     `spectral_correlation_correction` + el ajuste de transformación
     recupera con precisión una desalineación LED inyectada
     (rotación+escala+shift conocidos) — la matemática del método
     funciona.
   - **Resultado negativo, no anticipado**: bootstrapear la calibración
     desde una reconstrucción cruda usando la grilla nominal (equivocada)
     **no funciona de forma confiable**, ni siquiera para una
     desalineación chica — el estimado de objeto ya sale tan distorsionado
     (`phase_correlation` negativo, peor que ruido) que no hay información
     útil de la que la búsqueda espectral pueda partir. Confirma
     exactamente por qué el paper necesita su etapa de calibración
     brightfield: sin un bootstrap inicial razonable, la calibración
     SC-sola no rescata una reconstrucción ya rota. **Esto degrada la
     prioridad de este gap**: implementarlo bien en datos reales
     probablemente requiere primero portar (aunque sea de forma
     simplificada) la etapa brightfield del paper — no es un simple
     "agregar corrección de LED encima de lo que ya hay".

   **[ACTUALIZADO — 2026-09-17, sesión de seguimiento] Etapa brightfield
   (BF) implementada — resultado honesto: funciona parcialmente, no
   cierra el loop todavía.** `led_calibration.py` ahora tiene
   `find_circle_center` (detección circular por gradiente radial, Fig. 2
   del paper) y `brightfield_calibration` (la corre en todos los LEDs
   brightfield, ajusta una transformación de similitud, la aplica a
   todos incluyendo darkfield — Algorithm 1 completo, simplificado).

   **Hallazgo sólido y reproducible**: sin el paso de normalización del
   paper (Algorithm 1 línea 1, dividir por el espectro promedio entre
   imágenes) la detección de círculos da sistemáticamente mal —
   dominada por la caída genérica tipo 1/f del espectro de cualquier
   imagen natural, no por el borde de la pupila. Implementado
   (`mean_spectrum_magnitude`) y confirmado en test: sin normalizar, el
   centro encontrado se va sistemáticamente al borde de la ventana de
   búsqueda; normalizando, mejora claramente.

   **Hallazgo negativo, abierto, no resuelto**: con la geometría real de
   este laboratorio (pitch=6mm, z=70mm) el objetivo `"current"` (NA=0.07)
   tiene **un solo LED brightfield** — no alcanza ni para ajustar una
   transformación. El objetivo `"future"` (NA=0.10) tiene 5, en cruz
   alrededor del eje óptico — geométricamente pobre para estimar
   escala/rotación con precisión (config de pocos puntos, casi simétrica).
   Con esos 5 puntos y la métrica simplificada de este proyecto, la
   calibración BF **no mejora la reconstrucción de forma confiable** —
   en un caso de prueba concreto la empeoró (`phase_correlation` de 0.58
   a -0.07). No es un bug puntual arreglable rápido: es una limitación
   real de precisión dada la escasez geométrica de LEDs brightfield en
   este montaje, documentada explícitamente en
   `tests/test_brightfield_calibration.py` (sin aserción de "BF mejora
   las cosas" a propósito, porque no es cierto de forma confiable
   todavía).

   **[HECHO — 2026-09-17, sesión de seguimiento] RANSAC agregado, pero no
   ataca este problema específico.** `fit_similarity_transform_ransac`
   (nuevo, `tests/test_ransac_similarity_fit.py`, 3 tests) reemplaza el
   ajuste por mínimos cuadrados simple cuando se le pasa
   `ransac_inlier_threshold` a `calibrate_led_grid`/`brightfield_calibration`
   — recupera la transformación correcta incluso con ~10% de LEDs
   corregidos a posiciones muy erróneas, donde el ajuste simple se
   desviaba por completo (probado: signo de rotación invertido sin
   RANSAC, exacto con RANSAC). **Pero esto no es lo que le falla a BF con
   la geometría real de este lab** — ahí el problema no son unos pocos
   LEDs corregidos mal (outliers), es que *todos* los ~5 LEDs brightfield
   disponibles están dispuestos en una cruz geométricamente pobre para
   estimar rotación/escala — RANSAC no puede inventar información
   geométrica que no está. Sigue siendo un problema abierto, con RANSAC
   como mejora real pero para un modo de falla distinto (outliers
   puntuales, no escasez geométrica sistemática).

   **Capa de agente (la decisión "¿esto es ruido o desalineación
   sistemática?" de la sección 2) todavía no está implementada** — lo que
   existe es la matemática determinística de corrección (SC + ahora
   también BF); falta el wrapper tipo
   `agents/reconstruction_orchestrator.py` que decida cuándo confiar en
   la transformación ajustada. Dado que ni BF ni SC solos cierran el loop
   de forma confiable todavía con la geometría real de este lab, ese
   agente hoy tendría poco de valor para decidir — el problema previo es
   de precisión numérica, no de juicio/decisión.

5. **[Agente #3 — HECHO 2026-09-17] Cross-channel consistency +
   Confidence/QC agent**, fusionados en uno solo (`agents/qc_agent.py`) —
   ambas decisiones se responden con el mismo diagnóstico
   (`pair_disagreement` que `couple_rgb_channels` ya calculaba, más
   `metrics.convergence_summary` por canal), y sin datos reales acá no
   hay forma de tratarlas por separado con casos de prueba distintos de
   todas formas.

   `qc_agent.summarize_run_diagnostics` reduce los arrays por-píxel a
   estadísticos (media/p95/max de desacuerdo por par, mejora relativa por
   canal) — código plano, testeado sin agente. `qc_agent.qc_review` arma
   el prompt con esos números y pide veredicto estructurado
   (`confidence`, `recommendation`, `flagged_issues`) al mismo patrón
   `claude -p --restricted` de `reconstruction_orchestrator.py`. Integrado
   como `--qc`/`--qc-live` en `pipelines/reconstruct_multispectral_coupled.py`
   (`--qc` sin `--qc-live` usa un veredicto dry-run enlatado, no gasta
   dinero real — probado end-to-end así contra datos falsos, CLI completo
   incluyendo `qc_review.json`). 4 tests en `tests/test_qc_agent.py`, sin
   llamadas reales a la API, mismo criterio de costo que milestone 3.

6. **[Agente #4] Capture/LED-selection agent** (gap #5, `tian2014`,
   multiplexado) — último porque implica cambiar el propio protocolo de
   captura en el laboratorio (hardware/software fuera de este repo), no
   solo el pipeline de reconstrucción.

7. **[Integración — cableado determinístico HECHO 2026-09-17, el agente
   en sí todavía no] Report/provenance agent** — una vez que hay corridas
   reales que reportar, automatizar lo que hoy sería llenar
   `structure/claims.yaml` y `report/report.md` a mano.

   Lo que se hizo: reemplazado el placeholder `template_wired` por 4
   reclamos reales de todo lo construido en esta sesión —
   `scripts/compute_numbers.py` ahora recomputa 5 números reales
   (correlación de espesor multiespectral, factor de reducción de error
   del unwrapping vs. ingenuo, correlación de fase con/sin contraste de
   amplitud, error de recuperación de escala de calibración LED) llamando
   directamente al código de `src/ptyco_full_simulator/` y
   `agents/led_calibration.py`/`multispectral.py` — deterministamente
   (verificado corriendo dos veces, output idéntico). `scripts/checks.py`
   tiene 4 checks reales incluyendo un control negativo (el hallazgo de
   objeto de fase pura). `structure/claims.yaml`/`outputs.yaml` y
   `report/report.md` están reescritos con los 4 reclamos reales, y
   `scripts/reproduce.sh` corre compute → check → gate de punta a punta
   sin fallar (`all checks pass — 6 \src tag(s), 5 \srcnum tag(s), 6
   registry entry(ies), 4 claim(s)`).

   **[HECHO — 2026-09-17, sesión de seguimiento] El agente en sí,
   construido.** `agents/report_agent.py`: dado un hallazgo (números ya
   en el registro + una descripción) y los ids de reclamos existentes,
   `draft_claim_and_report` pide al agente un borrador estructurado —
   `claim_id`, `claim_statement`, `depends_on`, `report_markdown` (con
   los tags `[srcnum:]`/`[src:]` ya insertados), y `worth_reporting`
   (puede decidir que no vale la pena reportarlo). **No escribe los
   archivos reales** — el borrador se valida a mano (o con
   `scripts/check_provenance.py`) antes de aplicarlo, mismo criterio de
   "no confiar ciegamente" que el resto de los agentes de este proyecto.

   Probado con 3 tests con stub (`tests/test_report_agent.py`, sin gasto
   real) más **una llamada real** de validación (mismo criterio que los
   otros 2 agentes): pedí un borrador para el hallazgo de RANSAC de esta
   misma sesión — devolvió un `claim_statement` razonable, un
   `report_markdown` con los tags bien formados, y hasta una nota honesta
   sobre que el valor 0.0 "parece sospechosamente perfecto" pero refleja
   lo que se computó — buen indicio de que el agente entiende el estilo
   de honestidad que este proyecto viene manteniendo. Tardó ~15s (un poco
   más que los otros dos agentes, prompt más largo).

   Con esto, los 3 agentes de la sección 2 (orquestación de
   reconstrucción, QC/consistencia, reporte) existen y están probados.

   **[HECHO — 2026-09-17] Conectados en un solo flujo, al menos QC→reporte.**
   `pipelines/reconstruct_multispectral_coupled.py --qc` ahora, si el
   agente de QC recomienda `"report"`, llama automáticamente a
   `report_agent.draft_claim_and_report` con las estadísticas de
   desacuerdo entre canales y el espesor medio, y guarda el borrador en
   `report_draft.json` — **no lo aplica solo**, queda explícito en el
   output que un humano debe formalizarlo en `compute_numbers.py`/
   `claims.yaml` (los números de una corrida real con datos del lab no
   están en el registro automáticamente; ese paso sigue siendo manual a
   propósito). Probado end-to-end con datos falsos en
   `tests/test_reconstruct_multispectral_coupled_cli.py`.

   **[HECHO — 2026-09-17, mismo día] El tercer agente, conectado.**
   `orchestrate_reconstruction` ahora acepta `initial_object` (pasante,
   sin cambiar su lógica de decisión) para poder combinarse con la
   inicialización de TIE. `simulate_and_reconstruct.py` tiene
   `--use-reconstruction-agent` (+ `--agent-live`, `--max-attempts`) que
   lo usa en vez de una llamada directa a `reconstruction.reconstruct` —
   guarda el log completo de intentos/decisiones en `metrics.json`.
   Probado en `tests/test_simulate_and_reconstruct_tie.py`: en modo
   dry-run (decisión enlatada "accept" en el primer intento) el resultado
   es idéntico a no usar el agente, como corresponde. **Nota honesta**:
   pasar `initial_object` no le da al agente ninguna información nueva
   sobre si TIE se usó — sigue sin resolverse cómo decidir cuántas
   iteraciones correr después de un arranque informado por TIE (ver más
   arriba, los 3 diagnósticos descartados), esto solo deja la tubería
   lista para cuando eso se resuelva.

   Con esto, los 3 agentes están conectados a pipelines reales: QC→reporte
   en el pipeline multiespectral acoplado, y orquestación de
   reconstrucción en `simulate_and_reconstruct.py` — aunque los dos
   flujos siguen siendo independientes entre sí (no hay un único pipeline
   que use los 3 agentes juntos todavía).

   **[HECHO — 2026-09-18] Los dos flujos, unificados en un solo
   pipeline.** `reconstruct_all_channels()` (usada tanto por
   `reconstruct_multispectral_independent.py` como por
   `reconstruct_multispectral_coupled.py`) ahora acepta
   `use_reconstruction_agent`/`agent_live`/`max_attempts`: cuando está
   activo, corre `agents/reconstruction_orchestrator.py` (agente #1)
   por canal en vez de una llamada directa a `reconstruction.reconstruct`,
   guardando el log de intentos/decisiones por canal
   (`channels[canal]["agent_attempts"]`). Con esto,
   `reconstruct_multispectral_coupled.py --use-reconstruction-agent --qc`
   corre los 3 agentes del proyecto (orquestación de reconstrucción → QC
   → reporte, encadenado cuando QC recomienda reportar) en una sola
   invocación real, no dos flujos separados. Probado en
   `tests/test_reconstruct_multispectral_coupled_cli.py::test_all_three_agents_chained_dry_run`
   (dry-run, sin gasto real, mismo criterio de costo que el resto de los
   agentes) — 64 tests pasando.

8. **[HECHO — 2026-09-18] Solver monocromático: gaps #1 (pupil recovery)
   y #3 (adaptive step size) implementados.** No es un milestone
   multiespectral en sí (mejora `reconstruction.reconstruct`, usado por
   los tres canales por igual) pero el CAVEAT al inicio de
   `pipelines/reconstruct_multispectral_coupled.py` los marcaba
   explícitamente como PREREQUISITOS, no nice-to-haves, para que el
   pipeline acoplado sirva en muestras reales de fase grande — sin esto,
   el solver satura mucho antes de necesitar el unwrapping multiespectral
   que es el corazón del proyecto.

   **Pupil recovery (rank 1, `ou2014`, EPRY)**: `reconstruct()` gana
   `recover_pupil` — alterna la actualización del parche de espectro del
   objeto y una estimación de pupila compleja por LED (Eq. 2-4 del paper,
   leído completo, no solo el abstract). Necesitó agregar infraestructura
   de testing que no existía: `forward_model.simulate_lr_stack` ahora
   acepta `pupil_override` (antes siempre usaba la pupila ideal, sin forma
   de simular una aberración conocida) y `optics.add_defocus_aberration`
   genera una aberración de defocus sintética (Zernike modo 4, la misma
   que el paper encontró dominante en un microscopio real) para validar
   contra verdad de referencia. **Resultado honesto**: en el objeto
   sintético chico ya usado por `test_ptyco_simulator.py`, con
   `defocus_rad_amplitude=2.0`, EPRY mejora de forma real pero modesta
   (correlación de fase 0.687→0.793, correlación de la fase de pupila
   recuperada con la aberración real inyectada: 0.648) — lejos del arreglo
   dramático que fue la inicialización TIE para objetos de fase débil. Con
   aberración mayor (4.0, explorado pero no aserteado en el test) tanto la
   reconstrucción corregida como la no corregida fallan del todo en este
   problema chico — EPRY no es una bala de plata sin más imágenes/píxeles,
   consistente con que el paper mismo necesitó 225 imágenes en su demo real.

   **Adaptive step size (rank 3, `zuo2016`)**: `reconstruct()` gana
   `adaptive_step`, implementando la Ec. 16 del paper tal cual (no
   aproximada): mantiene el step mientras la mejora relativa del error
   global por época supere η=0.01 (el default que el propio paper
   recomienda), si no lo achica a la mitad — nunca lo vuelve a crecer,
   arrancando en `step_max` (la convención α⁰=1 del paper). `history`
   ahora también guarda el `step` usado cada época. **Resultado honesto,
   a diferencia de EPRY**: no se encontró una ventaja limpia de calidad
   de reconstrucción sobre la rampa fija ya existente en los problemas
   sintéticos chicos de este proyecto, probado con varios niveles de
   ruido Poisson (correlación de fase dentro de pocos puntos porcentuales
   en cualquier dirección) — la rampa fija ya alcanza un step moderado y
   sin oscilación en estos tamaños de grilla/iteración chicos, así que el
   modo de falla por oscilación inducida por ruido que ataca el paper
   puede no ser lo bastante pronunciado acá para mostrar su beneficio. Lo
   que sí se verificó: el mecanismo de la Ec. 16 está bien implementado
   (test unitario directo) y una corrida real con ruido fuerte efectivamente
   achica el step con el tiempo sin diverger.

   Ambos son opt-in (`recover_pupil`/`adaptive_step` default `False`),
   comportamiento previo sin cambios (regresión testeada, incluye los
   valores de `step` por época coincidiendo exactamente con la fórmula
   cerrada de la rampa fija). 70 tests pasando (eran 64 antes de estos
   dos).

   **[HECHO — 2026-09-18] Cableados como CLI** en
   `pipelines/simulate_and_reconstruct.py` (`--recover-pupil`,
   `--adaptive-step`, mismo patrón que `--tie-defocus-um`), mutuamente
   excluyentes entre sí y con `--use-reconstruction-agent` (combinarlos
   con el agente de orquestación de reconstrucción es una pregunta de
   diseño real, no resuelta acá — su lógica de decisión está armada
   alrededor de reintentos de `step_max`, que EPRY directamente ignora y
   que `adaptive_step` ya gestiona por su cuenta). Probado end-to-end a
   mano contra PNGs sintéticos (no es parte de la suite regular — es
   plomería de CLI, el algoritmo en sí ya está cubierto por
   `tests/test_epry_pupil_recovery.py`/`test_adaptive_step_size.py`).
   Los dos siguen sin estar expuestos en `reconstruct_multispectral_*.py`
   (los pipelines multiespectrales) — quedan solo en el pipeline
   mono-objeto por ahora.

   **[HECHO — 2026-09-18] Cableados también en los pipelines
   multiespectrales.** `reconstruct_all_channels()` (compartida por
   `reconstruct_multispectral_independent.py` y
   `reconstruct_multispectral_coupled.py`) gana `recover_pupil`/
   `adaptive_step`, aplicados por canal, con la misma exclusión mutua con
   `use_reconstruction_agent` que ya tenía `simulate_and_reconstruct.py`
   (ahora vive como un `ValueError` dentro de la función compartida, no
   duplicado en cada CLI). `channels[canal]["pupil"]` guarda la pupila
   recuperada por canal cuando corresponde (`None` si no). Ambos CLI
   multiespectrales ganan `--recover-pupil`/`--adaptive-step`. Nuevos
   tests en `tests/test_reconstruct_multispectral_pipeline.py`: wiring
   check de cada modo por separado (no re-derivan la calidad de EPRY/
   step-size, ya probada a nivel de librería — solo confirman que corren
   por canal y no rompen nada) más un test de la exclusión mutua. 73 tests
   pasando (eran 70).

   **[HALLAZGO NEGATIVO — 2026-09-18] `recover_pupil=True` no es seguro
   prender siempre.** Explorando los 3 canales reales juntos con fase
   0.15π (el caso que ya hacía caer a red en mínimo local, milestone 2a):
   `recover_pupil` mejora red modestamente (0.641→0.672) pero **hunde
   blue** (0.951→0.526) — sin ninguna aberración real presente (pupila
   ideal). Investigado a fondo: la fase de pupila recuperada queda casi
   plana (std <0.003 rad, no "inventa" una aberración grande), pero la
   calidad real empeora monótonamente con más iteraciones (0.625 a 5
   iters → 0.526 a 40 iters) mientras `recovery_error` mejora todo el
   tiempo — la propia normalización del update de EPRY (dividir por
   `max(|P|²)`/`max(|S|²)` en vez del paso de gradiente fijo) puede
   sobreajustar un canal que ya converge bien, y el `recovery_error` no lo
   detecta (misma patología que `test_weak_phase_object_limitation.py`,
   disparada acá por una vía distinta). **Implicación práctica**: no
   activar `recover_pupil` a ciegas para los 3 canales RGB en la misma
   corrida — puede ayudar a uno y arruinar a otro simultáneamente, y no
   existe todavía ningún diagnóstico por canal para distinguir los casos
   de antemano (mismo tipo de problema abierto que la pregunta de
   continuar iterando después de TIE). Formalizado en
   `tests/test_epry_pupil_recovery.py::test_recover_pupil_can_regress_an_already_well_converging_channel`
   y en el docstring de `reconstruction.reconstruct`. 74 tests pasando.

   **[FOLLOW-UP — 2026-09-18, mismo día] ¿Está mal implementado EPRY, o
   es un artefacto del testbed chico de este proyecto? Lo segundo,
   confirmado con evidencia.** Investigación en 3 pasos, hecha fuera del
   código del proyecto (scripts sueltos) antes de formalizar nada:
   1. **Se descartó "normalización mal regularizada"**: se probó el fix
      estándar de la literatura para inestabilidad de este tipo en la
      familia PIE (denominador regularizado per-píxel/global, estilo
      rPIE — Maiden/Muller/Rodenburg 2017) fuera del código principal, y
      casi no cambió los números a escala chica (blue seguía ~0.57-0.59
      con cualquier valor de regularización). Bajar `epry_alpha`/
      `epry_beta` sí mitiga parcialmente (blue mejora a ~0.63 con
      alpha=beta≈0.1) pero nunca cierra la brecha con el baseline sin
      corrección (~0.94), y a más iteraciones (160) vuelve a degradarse
      incluso con el paso chico — confirma que es una dirección de
      update genuinamente inestable, no solo "el paso por defecto es muy
      grande".
   2. **Réplica a escala cercana a la demo real del paper** (225 LEDs =
      grilla 15x15, imágenes de 64x64px en vez de 12x12px, manteniendo
      la frecuencia espacial física del objeto comparable — un primer
      intento sin ese cuidado confundió el resultado empujando el
      objeto al régimen ya conocido de fase casi-uniforme degenerada).
      **El colapso catastrófico desaparece por completo a esta escala**
      (0.840→0.836, estable incluso hasta 300 iteraciones) — confirma
      que el hallazgo negativo es un artefacto de poca redundancia de
      datos en los problemas sintéticos chicos de este proyecto (12px,
      81-441 LEDs), no una falla general de EPRY ni un bug de esta
      implementación (que además recupera aberraciones reales
      correctamente, ver el primer test del archivo).
   3. **Pregunta que quedó abierta, no resuelta**: si EPRY recupera bien
      una aberración real a esa escala grande. Un primer intento pareció
      un fallo limpio (correlación de pupila ~0.03 vs. 0.648 a escala
      chica), pero resultó estar confundido también — el baseline SIN
      ninguna corrección de pupila tampoco converge en el mismo
      presupuesto de iteraciones a esta escala más grande y compleja
      (phase_correlation sigue subiendo a 600 iteraciones: 0.466→0.623,
      `recovery_error` sigue bajando) — la comparación no fue justa y no
      se formalizó como test. Requeriría correr ambos casos hasta
      convergencia real (varios minutos por corrida a esta escala), no
      hecho todavía.

   Formalizado el paso 2 (el que sí tiene una conclusión sólida) en
   `tests/test_epry_pupil_recovery.py::test_recover_pupil_regression_is_a_small_testbed_artifact_not_reproduced_at_paper_scale`,
   con nota honesta sobre el paso 3 en su docstring. **Conclusión
   práctica actualizada**: `recover_pupil=True` no es "peligroso en
   general" — es específicamente arriesgado en los problemas sintéticos
   chicos que usa la suite de tests de este proyecto (que además son más
   parecidos en tamaño a las grillas reales del labo, 81-441 LEDs, que a
   las 225+ imágenes de mayor resolución de la demo real del paper). 75
   tests pasando (eran 74).

9. **[HECHO — 2026-09-18, sesión autónoma] Step-size adaptativo
   (`zuo2016`, rank 3): se le aplicó la misma ablación de escala que a
   EPRY, con resultado distinto — no era un artefacto de escala, era un
   artefacto de ruido/iteraciones insuficientes.** El hallazgo original
   (`tests/test_adaptive_step_size.py`, mismo día temprano) decía "sin
   diferencia limpia" probado con `peak_photon_count` hasta 20 y hasta 60
   iteraciones. Releyendo la Sección 4 del paper (Property A): el modo de
   falla que ataca es de **muchos ciclos bajo ruido fuerte** (el paso
   constante "deshace" el progreso del ciclo anterior y vuelve a
   introducir el ruido completo), no de escala del problema (LEDs/píxeles)
   — esa era la pista equivocada a seguir, distinta de la de EPRY.

   Reprobado con `peak_photon_count=3` (mucho más ruido que antes) y 400
   iteraciones: **sí aparece una ventaja real y reproducible**. Validado
   con comparación pareada (mismos datos ruidosos para ambos métodos, 8
   semillas distintas): adaptive_step gana en 8/8, con ganancia media
   pareada de 0.060 ± 0.012 SE de `phase_correlation` — no es ruido,
   es una diferencia real. A `peak_photon_count=1` (ruido extremo) la
   ventaja desaparece (ambos métodos fallan por igual), así que el efecto
   tiene un régimen específico: ruido pesado pero no extremo, con
   suficientes iteraciones — no es una mejora universal como la
   inicialización TIE.

   A diferencia del hallazgo de EPRY (donde a escala pequeña el resultado
   era "malo" y a escala grande resultó ser "artefacto, no problema
   real"), acá el patrón es inverso: el hallazgo original ("sin
   diferencia") seguía siendo cierto en su régimen (ruido leve, pocas
   iteraciones), y lo que cambió fue encontrar el régimen correcto donde
   el efecto real sí se manifiesta — ambos resultados (el nulo y el
   positivo) quedan documentados, no se descarta el primero.

   Formalizado en el registro de procedencia por primera vez para un
   hallazgo de step-size (antes excluido a propósito por no ser
   cuantitativo limpio): `structure/claims.yaml`'s
   `adaptive_step_helps_under_heavy_noise`, con el punto exacto de
   semilla=0 como número determinístico reproducible, y la estadística
   multi-semilla (8/8, 0.060±0.012) documentada en
   `tests/test_adaptive_step_size.py::test_adaptive_step_beats_fixed_ramp_under_heavy_noise_across_seeds`
   sin forzarla al registro (no es un número único determinístico).
   `scripts/reproduce.sh` pasa completo (19 tags `\src`, 18 `\srcnum`, 19
   entradas, 10 claims). 81 tests pasando (eran 80 tras la tarea 2 de
   esta misma sesión autónoma).

10. **[HECHO — 2026-09-18, sesión autónoma] Resuelta la exclusión mutua
    `recover_pupil`/`adaptive_step` vs. `--use-reconstruction-agent` —
    parcialmente, con una razón mucho más precisa para la parte que
    sigue excluida.**

    **`adaptive_step` + agente de orquestación: SÍ se pueden combinar,
    ya cableado.** Análisis: incluso bajo `adaptive_step=True`,
    `step_max` sigue jugando un rol real y bien definido (es α⁰, el
    punto de partida del que la Ec. 16 arranca a achicar el paso) — así
    que cuando el agente sugiere un `new_step_max` en un reintento,
    sigue siendo una palanca con sentido, no un parámetro ignorado como
    pasa con `recover_pupil`. `agents/reconstruction_orchestrator.py`'s
    `orchestrate_reconstruction` gana el parámetro `adaptive_step`
    (pasado a cada intento), y `build_decision_prompt` ahora avisa
    explícitamente al agente cuándo está activo (mostrando el trace de
    `step` real por iteración, no solo el `step_max` inicial, para que
    no confunda "paso fijo" con "punto de partida de un paso que se
    autoajusta"). Cableado en los 3 pipelines
    (`simulate_and_reconstruct.py`,
    `reconstruct_multispectral_independent.py`/`coupled.py` vía
    `reconstruct_all_channels`). Tests nuevos (dry-run, sin costo real,
    mismo criterio que el resto de los agentes de este proyecto):
    `tests/test_reconstruction_orchestrator.py` (prompt correcto,
    `adaptive_step` llega a cada intento), CLI end-to-end en
    `tests/test_simulate_and_reconstruct_tie.py` y
    `tests/test_reconstruct_multispectral_pipeline.py`.

    **`recover_pupil` + agente de orquestación: sigue excluido, pero
    ahora con una razón verificada, no solo "pregunta de diseño
    abierta".** Análisis honesto (no se forzó una combinación falsa):
    `reconstruction.reconstruct` ignora `step_max` por completo cuando
    `recover_pupil=True`, así que la única palanca del agente (reintentar
    con otro `step_max`) no tiene nada que ajustar. La palanca que sí
    tendría sentido (`epry_alpha`/`epry_beta`, que esta misma sesión
    encontró que mitiga parcialmente — no arregla — la regresión de
    EPRY a escala chica) no se le puede dar al agente de forma segura
    tampoco, porque la única señal que el agente ve (`recovery_error`)
    está **probada como ciega** exactamente al modo de falla que
    necesitaría detectar: en el hallazgo de milestone 8, `recovery_error`
    mejoraba todo el tiempo mientras la precisión real empeoraba. Un
    agente que solo ve `recovery_error` no puede detectar el problema que
    necesitaría detectar para decidir algo útil acá — es un déficit de
    información real, no una funcionalidad faltante, y forzar la
    combinación igual blanquearía una señal ciega conocida como si fuera
    seguridad automatizada. Documentado explícitamente en el docstring de
    `orchestrate_reconstruction` y en los mensajes de error de los 3
    CLIs — queda como pendiente genuino, a revisar solo si aparece una
    señal de diagnóstico nueva específica para `recover_pupil` (mismo
    tipo de problema abierto que la pregunta de continuar iterando
    después de TIE).

    86 tests pasando (eran 81 antes de esta tarea).

11. **[HECHO — 2026-09-21, primera sesión en PC local] Autocalibración
    conjunta objeto + posiciones LED (AD-SC, You & Liang 2025).**
    `src/ptyco_full_simulator/joint_calibration.py`, leído el paper
    completo (`references/papers/complementarios/`). Sin PyTorch (el
    proyecto es numpy-only): el gradiente del grafo de la Fig. 2 se
    derivó a mano y se verificó contra diferencias finitas (coincide a
    ~1e-4 relativo, objeto y posiciones). Modelo directo con k continuo
    (tilt en espacio real, no recorte a bin entero) — idéntico al modelo
    de recorte cuando k cae justo en un bin (1e-15). Optimizador Adam
    como en el paper. `led_model="rigid"` (rotación+escala+traslación,
    4 parámetros, misma regularización de `eckert2018`) o `"per_led"`
    (2 parámetros libres por LED, como el paper).

    **Hallazgos** (`tests/test_joint_calibration.py`, 5 tests):
    - `per_led` **sobreajusta** en crops chicos (16px): con la grilla ya
      correcta derivó 0.27 bins, y con desalineación rígida no recuperó
      las posiciones. `rigid` es el modo usable acá.
    - Dado un buen objeto, una desalineación chica (~0.25 bins de error
      medio) se recupera **exacta** (<0.01 bins).
    - Arrancando solo desde la imagen del LED central (sin buen
      objeto), calibrar mejora frente a fijar las posiciones nominales:
      `phase_correlation` 0.485→0.861, error de posición 0.248→0.079 bins.
    - **Límite negativo**: una desalineación de ~0.8 bins **no** se
      recupera ni siquiera con el objeto verdadero — cae en un mínimo
      local (terminó peor que al inicio, 1.26 vs 0.80). La cuenca de
      atracción es menor a ~medio bin en este testbed. Refina una grilla
      más o menos bien; no arregla una grosera. Esto es consistente con
      el resultado de `led_calibration.py` (etapa brightfield).
    - **Efecto lateral, investigado de forma controlada** (mismos datos,
      k alineado a bin, posiciones conocidas, sin ruido,
      `tests/test_gradient_descent_vs_wirtinger.py`): el descenso de
      gradiente Adam reconstruye mejor que el Wirtinger flow del repo en
      los 3 canales (`phase_correlation`, WF400 vs GD100): green 0.981 vs
      0.990, red 0.928 vs 0.992, **blue -0.056 vs 0.878** (el Wirtinger
      flow no converge nunca en blue, ni con 400 épocas). Sirve como
      referencia para la pregunta abierta de 2a (¿por qué un canal se
      queda en mínimo local?): en este testbed es propiedad del solver,
      no del problema. **Salvedades**: un solo objeto/geometría; más costo por
      iteración. **Con ruido la ventaja NO se sostiene** (barrido pareado,
      8 semillas × 3 canales × pico de fotones 100/20/5, WF 200 épocas vs
      GD 100 iteraciones, `scripts/sweep_gd_vs_wf_noise.py`; diferencia
      media GD−WF de `phase_correlation` ± error estándar): GD gana solo
      en red con pico 100 (+0.090 ± 0.018, 8/8). En red con pico 20 pierde
      (−0.114 ± 0.039, 1/8); green empata a pico 100 (−0.016 ± 0.021) y
      tiende a perder a pico 20 (−0.062 ± 0.032); blue falla en los dos
      métodos con ruido (WF ≈ 0, GD muy inestable, sd 0.23-0.41 entre
      semillas). La ventaja sin ruido en blue (0.878 vs −0.056) es real
      pero no transfiere a datos ruidosos, que es lo que habrá en el
      laboratorio. No se probó si regularizar o cortar antes el GD (la
      pérdida L2 sobre intensidad no es la adecuada para ruido de Poisson)
      recupera la ventaja — **[probado después, ver abajo]**.
      **[ACTUALIZADO — misma sesión] Con la pérdida de AMPLITUD la ventaja
      sí sobrevive al ruido.** `joint_calibration.loss_and_gradients` /
      `reconstruct_and_calibrate` ganan `loss="amplitude"`
      (Σ(|f|−√M)², ruido gaussiano en amplitud, la que Yeh 2015 reporta
      más robusta) y `loss="poisson"` (log-verosimilitud de Poisson), con
      gradiente analítico verificado contra diferencias finitas. Mismo
      barrido pareado (8 semillas, GD 100 iteraciones vs WF 200 épocas,
      diferencia media de `phase_correlation` ± error estándar, victorias
      de GD): **amplitud** gana en 8/8 semillas en green (+0.128 ± 0.007
      a pico 100, +0.462 ± 0.026 a pico 20, +0.108 ± 0.015 a pico 5) y en
      red (+0.230 ± 0.008, +0.472 ± 0.013, +0.052 ± 0.019, 7/8 a pico 5), y
      **rescata blue a pico 100** (+0.695 ± 0.051, 8/8: 0.708 vs 0.013).
      **Poisson** es mixta: gana en green/red a pico 100 y 20 pero con
      más varianza (e.g. red pico 100 +0.115 ± 0.114) y no rescata blue.
      **Cortar antes** (Poisson, 30 iteraciones) no ayuda: pierde a pico
      100 (−0.348 green, −0.231 red). **Sigue sin resolverse:** blue a
      pico ≤ 20 falla con todos los métodos y pérdidas probados (mejor
      caso ≈ 0, peores ≈ −0.37). Todavía **no** se cambió el solver de los
      pipelines: falta probar con más objetos/geometrías y con datos
      reales antes de reemplazar `reconstruction.reconstruct`, pero ya es
      un candidato serio (`loss="amplitude"`), no solo una curiosidad de
      testbed sin ruido. Test:
      `tests/test_gradient_descent_vs_wirtinger.py` (amplitud, green y
      red, pico 20, 4 semillas).
      **No arregla** el punto silla de fase pura (sección 1.6): GD
      -0.215 vs WF -0.044, eso requiere información nueva (TIE), no otro
      optimizador.
    - No formalizado en el registro de procedencia
      (`compute_numbers.py`/`claims.yaml`) ni cableado a los pipelines
      CLI todavía.

12. **[NEGATIVO — 2026-09-21] Diagnóstico de "cuántas iteraciones de FPM
    correr tras el arranque con TIE": el residuo del par desenfocado tampoco
    discrimina.** Idea (la que sugería el punto 6 de la sección 1: traer
    información genuinamente nueva, no otro derivado de las intensidades
    brillantes): el par de capturas desenfocadas es sensible a la fase,
    así que comparar el par que *predice* la reconstrucción actual
    (LED central, banda limitada por la pupila, propagada ±30µm) contra el
    par *medido* no repite la ceguera de `recovery_error`/validación
    cruzada. Probado en 6 objetos de fase mixta con FPM continuando 0/5/10/
    20/40 iteraciones desde el arranque de TIE
    (`scripts/explore_tie_continuation_diagnostic.py`; residuo invariante a
    ganancia global — una primera versión sin eso dio números sin sentido,
    ~79, por unidades de amplitud del solver):
    - **Residuo con campo completo:** *sube* con las iteraciones en los 6
      objetos, incluso donde la fase real *mejora* (obj0 0.979→0.989,
      obj4 0.580→0.671). Mide distancia al arranque de TIE, no calidad.
    - **Variante solo-fase** (amplitud medida del LED central + fase de la
      estimación, para aislar lo que se quiere juzgar): *baja* siempre,
      incluso donde la fase real *empeora* (obj1 0.998→0.987, obj2, obj5).
    - En ambas, la dirección del residuo es la misma en todos los objetos,
      así que no separa los casos que mejoran de los que empeoran; la
      política "quedarse con el k de menor residuo" da 0.909 (=TIE solo)
      con campo completo y 0.919 (=40 iteraciones fijas) con solo-fase,
      contra 0.926 del oráculo.
    - Interpretación: lo que separa "mejora" de "empeora" son componentes
      de alta frecuencia que un defocus de 30µm limitado por la pupila casi
      no ve. Cuarto y quinto diagnóstico descartados de este tipo.
      Sigue abierto para el agente de orquestación.

13. **[HECHO — 2026-09-21] Objeto real (Lena amplitud + Map fase): más LEDs
    NO rescatan la fase con ruido; la pérdida de amplitud sí gana sin
    ruido y en recuperación de amplitud.** Nuevo
    `src/ptyco_full_simulator/test_objects.py` (`lena_map_object`, imágenes
    512×512 fuera del repo en `/home/chanoscopio/Documents/LucasC/code/
    data_source`, o `PTYCO_DATA_SOURCE`). Green, objetivo "current", recorte
    32px, fase máx 0.3π, WF 200 épocas vs GD 100 iteraciones con
    `loss="amplitude"` (`scripts/sweep_lena_map_grid_size.py`):

    | Grilla (LEDs) | Lienzo HR | Ruido | corr. fase WF | corr. fase GD-amp | corr. amp WF / GD-amp |
    |---|---|---|---|---|---|
    | 9×9 (81) | 96² | ninguno | 0.160 | 0.675 | 0.726 / 0.970 |
    | 15×15 (225) | 160² | ninguno | 0.074 | 0.637 | 0.470 / 0.966 |
    | 21×21 (441) | 160² | ninguno | 0.082 | 0.608 | 0.473 / 0.955 |
    | 9×9 | 96² | pico 20 (4 sem.) | 0.023 | 0.033 | 0.267 / 0.733 |
    | 15×15 | 160² | pico 20 (4 sem.) | 0.023 | −0.040 | 0.058 / 0.742 |
    | 21×21 | 160² | pico 20 (2 sem.) | 0.020 | 0.005 | 0.126 / 0.748 |

    - **Sin ruido**, GD-amp gana por ~0.5 de fase en todas las grillas
      (una sola corrida por celda, sin barrido multi-semilla), y la
      amplitud queda en ~0.96-0.97 contra 0.47-0.73 del Wirtinger flow.
    - **Con ruido a pico 20, la fase no se recupera con ningún método a
      ningún tamaño de grilla** (|corr| ≤ 0.04). Lo que sí se conserva es
      la amplitud: GD-amp ~0.73-0.75 contra 0.06-0.27 del WF.
    - **Más LEDs no ayudó a la fase con ruido.** Contra la hipótesis de
      "faltan datos": el lienzo HR también crece con la grilla (96²→160²),
      así que la redundancia (LEDs×píxeles LR / píxeles HR) es 9.0 en 9×9,
      9.0 en 15×15 y 17.6 en 21×21 — subir de 9×9 a 15×15 no agrega
      redundancia por píxel, solo 21×21 la duplica, y ahí tampoco mejoró
      (n=2 semillas, no concluyente). Falta probar subir la redundancia a
      lienzo fijo, o subir el pico de fotones (100, 1000) para ver dónde
      la fase empieza a ser recuperable.
    - Costo: ~40s (9×9), ~260s (15×15), ~480s (21×21) por corrida
      (WF + GD, un núcleo).

    **[SEGUIMIENTO — misma sesión] La conclusión de arriba ("más LEDs no
    ayudan") estaba confundida y se corrige: sí ayuda subir la
    redundancia si el lienzo HR se mantiene fijo, y la fase pasa a ser
    recuperable con más fotones.** Barrido en
    `scripts/sweep_lena_map_noise_and_redundancy.py` (mismo objeto/canal/
    solvers; `corr. fase`, GD-amp vs WF; n semillas entre paréntesis):

    | Experimento | LEDs (redundancia) | Pico | WF | GD-amp | GD−WF |
    |---|---|---|---|---|---|
    | A: ruido, 9×9 | 81 (9.0) | 100 (4) | 0.051 | 0.186 | +0.135 ± 0.021, 4/4 |
    | | | 1000 (4) | 0.122 | 0.524 | +0.402 ± 0.010, 4/4 |
    | | | 10000 (4) | 0.112 | 0.593 | +0.481 ± 0.021, 4/4 |
    | B: lienzo fijo 96², misma extensión física (48 mm) | 225 (25.0) | 20 (2) | 0.108 | 0.279 | +0.171 ± 0.023, 2/2 |
    | | | 1000 (2) | 0.262 | 0.725 | +0.463 ± 0.029, 2/2 |
    | | 441 (49.0) | 20 (2) | 0.138 | 0.338 | +0.200 ± 0.014, 2/2 |
    | | | 1000 (2) | 0.288 | 0.758 | +0.470 ± 0.004, 2/2 |

    - **Fotones:** con 81 LEDs la fase de GD-amp sube 0.19 → 0.52 → 0.59 de
      pico 100 → 1000 → 10000, contra 0.05-0.12 del WF; llega a 0.675 sin
      ruido. El WF apenas se mueve. Para un objeto con este detalle, la fase
      empieza a recuperarse de forma útil desde pico ≈ 1000.
    - **Redundancia a lienzo fijo:** a pico 20, la fase de GD-amp pasa de
      0.033 (9×9, del barrido anterior, 4 sem.) a 0.279 (225 LEDs) y 0.338
      (441 LEDs); a pico 1000 de 0.524 a 0.725 y 0.758. El WF también sube
      (0.12 → 0.26 → 0.29 a pico 1000) pero ~0.4-0.5 por debajo.
    - **Salvedades:** 2 semillas en B; el pitch más chico también aumenta
      el solapamiento entre LEDs vecinos (que ya se vio que importa,
      `adjacent_led_overlap_ratio`) — redundancia y solapamiento están
      confundidos y no se separaron; un solo objeto, canal green, LEDs
      alineados a bin. Costo GD+WF por corrida: ~45 s (81 LEDs), ~120 s
      (225), ~340 s (441).

14. **[HECHO — 2026-09-21] Solver de descenso de gradiente con pérdida de
    amplitud, cableado como opción `--solver gd-amplitude` (default sigue
    siendo `wirtinger`).** `joint_calibration.reconstruct_gradient_descent`
    devuelve lo mismo que `reconstruction.reconstruct` (`object`, `history`
    con `recovery_error`), así que `metrics.convergence_summary` y el resto
    de los pipelines funcionan sin cambios. Disponible en
    `simulate_and_reconstruct.py`, `reconstruct_real_images.py` y los dos
    pipelines multiespectrales (vía `reconstruct_all_channels(solver=...)`).
    Normaliza la escala de intensidad (las capturas reales tienen escala
    arbitraria) dividiendo por la media de la imagen del LED central, y
    reescala un `initial_object` (p. ej. de TIE) en consecuencia.
    Mutuamente excluyente con `--recover-pupil`, `--adaptive-step` y
    `--use-reconstruction-agent` (ajustan partes internas del Wirtinger
    flow). Sin validar con capturas reales; blue con ruido moderado/fuerte
    falla con todos los solvers; usar ~100 iteraciones (pasos de lote
    completo, no épocas por LED). 9 tests en
    `tests/test_gd_solver_pipelines.py`.

    **Hallazgo importante al cablearlo — el modelo de k es lo que importa,
    y las pruebas viejas lo escondían.** Las capturas falsas de todo el
    resto de la suite se generan con `forward_model.simulate_lr_stack`, que
    redondea k a un bin del espectro: exactamente el modelo que el Wirtinger
    flow invierte (un "crimen inverso"). Con capturas de k *exacto* (lo que
    produce el hardware real), a igual dato, recorte de 16 px:
    Wirtinger flow (modelo de bin redondeado, ~0.4 bin de error medio)
    **0.076** de correlación de fase vs. descenso de gradiente (modelo
    continuo) **0.995**. Recíprocamente, darle al gradiente una grilla
    redondeada a bin sobre datos de k exacto da **0.092**: el modelo
    continuo exige posiciones LED bien conocidas (bien por debajo de un bin;
    ver milestone 11, la corrección `rigid` de `reconstruct_and_calibrate`
    ayuda solo si el error inicial es menor a ~0.5 bin). Con datos reales
    ni el redondeo ni las posiciones nominales son exactas, así que la
    posición real de los LED del laboratorio es probablemente el factor
    que más pese en cualquier solver — a medir con datos reales.
    Implicación para comparaciones anteriores (milestones 11 y 13): se
    hicieron con k alineado a bin a propósito (igualdad de condiciones para
    ambos solvers), lo que es justo pero no realista.

15. **[HECHO — 2026-09-21] Redundancia vs solapamiento entre LEDs a
    lienzo HR fijo (96²): con solapamiento fijo, más LEDs no mejoran la
    fase frente a lo que la apertura sintética permite; el solapamiento
    ayuda a igual cantidad de LEDs.** Lena+Map, green, recorte 32px, fase
    máx 0.3π, pico 1000 fotones, GD-amp 100 iteraciones (sin WF),
    3 semillas, `scripts/sweep_lena_map_redundancy_vs_overlap.py`. Todos
    los brazos son grillas uniformes sobre 48 mm (U) o subconjuntos de la
    de 21×21 (paso 2.4 mm): R = subconjunto aleatorio (centro incluido),
    C = 9×9/15×15 central (mismo solapamiento que U21, apertura menor).
    "corr. fase (pasabajos)" compara contra la verdad filtrada al corte de
    cada brazo (NA objetivo + NA del LED más externo), para no penalizar a
    C por resolución que su apertura no puede tener:

    | Brazo | LEDs | Solap. vecino mediano | corr. fase | corr. fase (pasabajos) | corr. amp |
    |---|---|---|---|---|---|
    | U9 (uniforme) | 81 | 0.33 | 0.526 ± 0.003 | 0.547 | 0.954 |
    | R81 (aleatorio) | 81 | 0.65 | 0.462 ± 0.070 | 0.478 | 0.928 |
    | C9 (central) | 81 | 0.77 | 0.573 ± 0.008 | 0.750 | 0.915 |
    | U15 (uniforme) | 225 | 0.65 | 0.719 ± 0.025 | 0.745 | 0.964 |
    | R225 (aleatorio) | 225 | 0.77* | 0.700 ± 0.010 | 0.724 | 0.963 |
    | C15 (central) | 225 | 0.77 | 0.659 ± 0.015 | 0.724 | 0.948 |
    | U21 (uniforme) | 441 | 0.77 | 0.758 ± 0.006 | 0.785 | 0.966 |

    - **Misma cantidad de LEDs, distinto solapamiento (81):** el 9×9
      compacto (0.77) supera al uniforme espaciado (0.33) en fase contra
      la verdad filtrada (0.750 vs 0.547) pero solo un poco contra la
      verdad completa (0.573 vs 0.526), porque su apertura es la mitad de
      grande. El aleatorio (R81) es el peor (0.462, la mayor varianza):
      huecos y grupos no ayudan.
    - **Mismo solapamiento, distinta cantidad (C9→C15→U21, 0.77):** la
      fase contra la verdad completa sube 0.573 → 0.659 → 0.758, pero contra
      la verdad filtrada queda ~plana (0.750 → 0.724 → 0.785). Es decir,
      la mejora al agregar LEDs a solapamiento fijo viene de ampliar la
      apertura (más frecuencias), no de la redundancia en sí; a apertura
      fija (dentro de cada corte) más LEDs no aportó de forma clara.
    - **Misma cantidad (225), solapamiento distinto:** U15 0.719, R225
      0.700, C15 0.659 (0.724 filtrada): diferencias chicas, del orden de
      1-2 desviaciones estándar salvo C15 en la métrica completa.
    - **Conclusión matizada:** la ganancia por "más redundancia a lienzo
      fijo" del milestone 13 (0.524 → 0.725 → 0.758) queda explicada
      sobre todo por solapamiento y apertura, no por redundancia pura.
      Redundancia pura (cuadros repetidos, mismo k) no se probó.
    - **Salvedades:** 3 semillas, un solo pico (1000), un objeto, sin WF;
      (*) la métrica "solapamiento vecino mediano" usa el vecino más
      cercano y no distingue el R225 (muchos pares adyacentes a paso
      mínimo, pero con huecos) del uniforme; la comparación filtrada
      depende de definir el corte como NA_obj + NA del LED más externo; el
      C9 no separa del todo "solapamiento" de "tamaño de apertura".
      Costo por corrida (un núcleo): ~35-45 s (81), ~95-110 s (225), ~205 s
      (441).

- **Milestone 16 — error de posición de los LEDs con k exacto (2026-09-21):**
  `scripts/plan_p4_led_position_error.py` (experimentos P1 y P3 del plan
  `docs/plan_experimentos_punto3_y_hardware_real.md`); JSON crudo en
  `data/plan_p1_led_position_error.json` (22 jobs) y
  `data/plan_p3_led_position_error.json` (10 jobs). Lena+Map, green, 9×9 LEDs
  sobre 48 mm, recorte de 32 px, HR 96², fase máx 0.3π, Poisson pico 1000,
  **2 semillas por celda**. Los datos se generan con las posiciones
  *verdaderas* (perturbadas físicamente: mm/grados/fracción de pitch) y todos
  los solvers reciben la grilla *nominal*; `gd_true` es el oráculo con las
  posiciones verdaderas. Correlación de fase, media de 2 semillas (`k_err` =
  RMS del error de k en bins del espectro HR):

  | error (k_err bins) | WF | GD nominal | GD rígido | GD per-LED | GD oráculo |
  |---|---|---|---|---|---|
  | ninguno (0.00) | 0.03 | 0.435 | 0.414 | 0.370 | 0.435 |
  | jitter 0.05 mm (0.07) | 0.03 | 0.355 | 0.358 | 0.439 | 0.504 |
  | pitch +1 % (0.20) | 0.05 | 0.431 | 0.441 | 0.405 | 0.455 |
  | jitter 0.2 mm (0.27) | 0.04 | 0.182 | 0.179 | 0.357 | 0.501 |
  | rot 1° (0.40) | 0.03 | 0.359 | 0.424 | 0.396 | 0.449 |
  | z +2 mm (0.56) | 0.03 | 0.152 | 0.185 | 0.208 | 0.535 |
  | offset 0.5 mm (0.59) | 0.05 | −0.003 | 0.101 | 0.049 | 0.499 |
  | rot 3° (1.19) | 0.03 | 0.096 | 0.388 | 0.281 | 0.464 |
  | combinado (1.49) | 0.02 | 0.034 | 0.023 | 0.023 | 0.527 |
  | z +7 mm (1.86) | 0.04 | 0.255 | 0.115 | 0.076 | 0.538 |
  | offset 2 mm (2.36) | −0.02 | −0.007 | −0.022 | −0.041 | 0.563 |

  P3 (error "combinado" × multiplicador; k_err 0.15 / 0.38 / 0.76 / 1.49 /
  2.89 bins): GD nominal 0.348 / 0.144 / 0.059 / 0.034 / 0.015; GD rígido
  0.433 / 0.259 / 0.122 / 0.023 / −0.004; oráculo 0.52-0.56 en todos.

    - **El error de posición es el cuello de botella, no el solver.** Con
      las posiciones verdaderas la fase se recupera a 0.43-0.56 en todas las
      filas; con la grilla nominal cae a ~0.0-0.2 apenas el error supera
      ~0.3-0.6 bin (offset 0.5 mm, z +2 mm, jitter 0.2 mm ya pierden 0.2-0.5
      de correlación). Un error "combinado" plausible (jitter 0.1 mm, offset
      ~1 mm, rot 1.5°, z +3 mm, pitch +0.5 %) mide 1.5 bins a 32 px y deja
      el resultado en ~0.03 para todos los solvers. Con hardware real esto
      es lo que hay que medir primero (calibración de posiciones de LEDs
      con campo brillante, `led_calibration.py`).
    - **La calibración rígida (AD-SC) rescata solo errores con estructura
      global y pequeños.** Rescata claramente rot 3° (0.096 → 0.388;
      `k_err` 1.19 → 0.03) y ayuda en offset 0.5 mm (+0.10) y en el
      "combinado" ×0.1-×0.5 (+0.04 a +0.13, mismo signo en ambas semillas; el
      de ×0.5 es el más flojo); no ayuda con
      jitter, pitch ni z +2 mm (dentro del ruido o +0.03), y empeora z +7 mm
      (0.255 → 0.115). No rescata nada del "combinado" ×1 (1.49 bins) ni
      del offset de 2 mm: `k_err` tras la calibración queda igual que
      antes (1.59 y 2.33). Ni siquiera donde el `k_err` baja (×0.5: 0.76 →
      0.22) la fase llega al oráculo (0.12 vs 0.50): la posición recuperada
      sigue sin alcanzar. **Acantilado:** entre ~0.8 y ~1.5 bins para el
      error combinado; pero depende del tipo (una rotación de 3° con 1.19
      bins sí se recupera, un offset de 2 mm con 2.4 no), así que "0.5 bin"
      del milestone 11 es una guía, no un umbral.
    - **Per-LED:** es lo único que ayuda con jitter (0.2 mm: 0.182 → 0.357;
      0.05 mm: 0.355 → 0.439) aunque `k_err_after_perled` no baja (0.27 →
      0.35): compensa el efecto sin recuperar la posición. Sobreajusta o
      empata en los demás casos.
    - **Contra el criterio de refutación del plan:** (a) `gd_nominal` no
      supera de forma consistente a WF con `k_err` ≥ 0.5 (sí en z +2, rot 3°
      y z +7; no en offset 0.5, combinado y offset 2); (b) `gd_rigid` no
      supera a `gd_nominal` con `k_err` < 0.5 (rot 1° +0.06, pitch +0.01,
      jitter ±0.00): ahí no hay nada que rescatar porque el nominal ya está
      cerca del oráculo. La hipótesis de P3 "rígido ≈ oráculo debajo del
      acantilado" **no se cumple** (0.433 vs 0.519 a 0.15 bin; 0.259 vs 0.531
      a 0.38).
    - **Salvedades (importantes):** (1) **2 semillas**: las diferencias
      menores de ~0.05 están dentro del ruido (en la fila "ninguno" GD rígido
      − nominal da −0.01 y −0.03); solo tomo como robustas las de >0.1 en
      ambas semillas. (2) **El WF da ~0.03 hasta sin error de posición**, es
      decir, está en su piso incluso en la fila de control; con 200 épocas
      sin afinar, la comparación con WF no es informativa (ver auditoría A2)
      y no se debe leer como "GD le gana a WF". (3) **El operador que genera
      los datos es el mismo que usa GD** (`jc.simulate_lr_stack_continuous`):
      lo independiente es la posición (verdadera vs nominal), no el modelo
      directo, así que el 0.435 de la fila de control es un techo optimista
      (hallazgo A1 solo parcialmente atendido). (4) Fase máx 0.3π, pico 1000
      y Lena/Map: el techo del oráculo es ~0.5, no 1. (5) Los errores son
      una parametrización inventada, no medidos. (6) A 32 px los bins escalan
      con el recorte: el mismo error físico mide menos bins a 16 px.
      No se ejecutaron P2 (ruido × canal) ni P4 (recorte). Costo real: P1
      ~33 min (22 jobs, 2 procesos, PC cargada), P3 ~14 min (10 jobs);
      ~160-190 s por job.

    - **Ampliación a 4 semillas (2026-09-21) de las celdas más ambiguas con
      2:** `jitter 0.2 mm`, `offset 0.5 mm` y `z +2 mm` de P1, y `combinado
      ×0.25` y `×0.5` de P3 — 10 jobs nuevos (seeds 2-3), datos crudos en
      `data/plan_p1_p3_extra_seeds.json`, combinados con las semillas 0-1 de
      arriba. Mismo objeto/configuración; media ± desviación estándar de las
      4 semillas:

      | condición | k_err (bins) | GD nominal | GD rígido | GD per-LED | GD oráculo |
      |---|---|---|---|---|---|
      | jitter 0.2 mm | 0.27 | 0.19±0.09 | 0.16±0.06 | **0.32±0.05** | 0.51±0.02 |
      | offset 0.5 mm | 0.59 | −0.00±0.01 | 0.10±0.01 | 0.05±0.01 | 0.52±0.03 |
      | z +2 mm | 0.56 | 0.16±0.03 | 0.20±0.04 | 0.21±0.02 | 0.54±0.01 |
      | combinado ×0.25 | 0.38 | 0.13±0.01 | **0.26±0.01** | 0.25±0.01 | 0.53±0.01 |
      | combinado ×0.5 | 0.76 | 0.06±0.02 | 0.12±0.02 | 0.10±0.01 | 0.52±0.02 |

      Confirma con menos incertidumbre lo que ya sugerían las 2 semillas: (1)
      **per-LED sigue siendo lo único que rescata jitter** (0.32 contra
      0.16-0.19 de nominal/rígido, sd baja); (2) **offset 0.5 mm es un caso
      raro y estable**: la calibración rígida baja `k_err` pero la fase
      recuperada (0.10±0.01) queda muy por debajo del oráculo (0.52±0.03) —
      no es ruido de 2 semillas, hay un mínimo local o una ambigüedad
      estructural en la calibración conjunta ante offset puro que no se
      investigó más; (3) **z +2 mm sigue sin que ninguna variante de GD
      ayude claramente** (0.16-0.21, todas dentro de la sd de las otras);
      (4) el **acantilado de P3 se confirma entre 0.38 y 0.76 bins**: a
      ×0.25 el rígido casi duplica al nominal (0.26 contra 0.13), a ×0.5 el
      margen se estrecha (0.12 contra 0.06) y ambos ya están lejos del
      oráculo. Sigue siendo n=4, no un intervalo de confianza; P2 y P4 del
      plan continúan sin correr.

- **Milestone 17 — E1 (objeto × fase × fotones) y E3b (span fijo, cantidad
  de LEDs), 2 seeds (2026-09-21):** `scripts/plan_p3_object_phase_geometry.py`
  (agregué `--where`, guardado incremental y `*_phase_rmse`/`flat_phase_rmse`
  a la salida); datos en `data/plan_e1_object_phase.json` (36 jobs) y
  `data/plan_e3b_fixed_span_leds.json` (32 jobs). Datos alineados a bin (la
  vara justa de los hitos 11-15, no la realista del hito 16), green, recorte
  32 px, GD-amplitud 100 iter contra WF 200 épocas sin afinar (ver A2), 1
  proceso. **Diseño recortado** respecto del plan: E1 sin `map_lena` ni
  `siemens_star` y sin fase 0.2π (3 objetos × {0.05, 0.1, 0.3}π × pico
  {100, 1000}); E3b sin la grilla 21×21. Solo n=2: en las tablas cuento
  como diferencia real solo lo que se repite en ambas seeds y pasa de ~0.1.
  - **E1, GD > WF:** en `lena_map` y `blob` GD gana a WF en las 12
    condiciones y WF queda cerca de 0 casi siempre. A 0.3π y pico 1000, GD
    da 0.528 (`lena_map`) y 0.772 (`blob`), contra WF 0.111 y −0.115.
    Ojo con A2: WF sin afinar, así que esto no mide "algoritmo contra
    algoritmo".
  - **E1, fase débil no es recuperable:** para fase ≤ 0.1π GD queda por
    debajo de 0.5 en todo objeto y pico (máximo 0.253 en `lena_map`
    0.1π/1000; `blob` 0.235). Es el resultado negativo esperado. En RMSE,
    GD queda peor que "no poner fase" para fase débil en `lena_map` (0.097
    contra 0.022 a 0.05π, pico 1000) y solo iguala la referencia a 0.3π
    (0.124 contra 0.131), aunque la correlación suba a 0.53: **la
    correlación sobrestima lo recuperado en radianes** (M1 del auditor).
    Solo `blob` a 0.3π/1000 mejora de verdad el RMSE (0.161 contra 0.219).
  - **E1, `phase_only` no confirma la hipótesis:** a 0.3π y pico 1000 GD
    da −0.239 en ambas seeds (con pico 100: 0.335, no monótono en los
    fotones), y a 0.1π/1000 las dos seeds dan −0.34 y +0.35. La amplitud
    es plana, así que la inicialización desde el LED central no aporta
    nada (la advertencia de E2): puede ser un problema de inicialización y
    no del solver, y con n=2 no lo puedo separar. Esta es la celda donde
    la ventaja de GD **se refuta** (GD < WF a 0.3π/1000, ambas seeds).
  - **E3b, más LEDs ayudan a canvas fijo:** `current`, pico 1000, GD:
    0.177 → 0.528 → 0.693 → 0.725 con 49/81/121/225 LEDs; `future`:
    0.454 → 0.594 → 0.636 → 0.682. A pico 100: 0.058 → 0.214 → 0.473 →
    0.554 (`current`) y 0.202 → 0.333 → 0.424 → 0.477 (`future`). Las seeds
    coinciden (±0.05) salvo 7×7. El HR es constante dentro de cada objetivo
    (96² para `current`, 160² para `future`), como debía. **No refuta**
    nada: la mejora es mayor a ±0.05 entre 7 y 15 en ambos objetivos. La
    ganancia se achata con las grillas grandes (11 → 15: +0.03 a +0.05 a
    pico 1000).
  - **E3b no separa redundancia de solapamiento:** a span fijo suben
    juntos (overlap 0.096 → 0.564 y redundancia 5.4 → 25 en `current`).
    Es exactamente lo que ya separó el hito 15, que atribuyó la mejora
    sobre todo al solapamiento y a la apertura. Leer los dos juntos.
  - **E3b, `future` contra `current` no es una comparación limpia:** el
    canvas HR es distinto (160² contra 96²), así que "future mejor por más
    overlap" queda confundido con el tamaño del canvas y con la
    resolución. A pico 100 `future` gana con pocos LEDs (0.202 contra
    0.058 con 7×7); a pico 1000 y grillas de 9 o más `current` es igual o
    mejor. Sin veredicto.
  - **E3b, WF:** 0.04-0.30 en todo el barrido y RMSE de fase de hasta
    1.4 rad en `future` (más que la referencia sin fase, 0.139): WF queda
    en su piso, así que nada de lo medido dice algo de WF.
  - **Salvedades:** n=2 y una sola vara de fase (0.3π) en E3b; solo canal
    green; ruido Poisson puro; los datos son de k redondeado a bin (la
    ventaja de GD acá no se traslada a datos con posiciones exactas y
    grilla nominal: ver hito 16, donde todos los solvers caen a ~0.0-0.2
    con error de posición > ~0.5 bin); no se corrieron E2, E3a ni E4.
    Costo real: E1 ~30 min (36 jobs, ~25 s cada uno) y E3b ~30 min (32
    jobs), con la PC compartida con otros jobs.

- **Auditoría A2/A3 — Wirtinger flow afinado y ablación pérdida × esquema
  (2026-09-21, `scripts/audit_wf_tuning_and_gd_ablation.py`; sin número de
  hito para no chocar con los que agregan otros agentes):** responde a los
  hallazgos A2 ("el baseline WF nunca se afinó") y A3 ("la pérdida de
  amplitud mezcla pérdida, optimizador y lote") de la auditoría adversarial
  a los hitos 11-14.
  - **Diseño:** green, 9×9 LEDs, crop 16 (HR 48×48), datos con k redondeado
    a bin (justo para ambos, NO el régimen de k exacto de hardware real),
    ruido Poisson pico 20/100/1000, objetos: fantasma sintético y Lena/Map
    (fase máx. 0.3π). **6 semillas de evaluación (0-5) por condición**, 36
    problemas, pareadas por semilla. Presupuesto: 100 evaluaciones de
    gradiente por LED para todas las celdas de Adam y para WF
    (`wf_*` = 100 épocas); `wf_s20_200` es WF con el ajuste de los hitos
    11-14 (200 épocas, `step_max=20`). WF: `step_max` 1, 2, 5, 10, 20, y
    `adaptive_step` (zuo2016) con `step_max` 20 y 5. 2×2 de GD: pérdida
    (intensidad | amplitud) × esquema (Adam de lote completo | Adam
    incremental por LED, gradiente reponderado por su norma para
    conservar los pesos por LED de la pérdida global). Los `lr` de Adam se
    eligieron con **una** semilla de ajuste (100, disjunta) por objeto a
    pico 100, sobre una grilla de 3 valores por celda: `full_int` 0.01,
    `full_amp` 0.01, `incr_int` 0.001, `incr_amp` 0.005.
  - **Línea base de inicialización** (amplitud del LED central, fase 0): la
    correlación de fase es indefinida (fase constante), así que la
    referencia es su `phase_rmse_rad` (**0.236** fantasma, **0.137**
    Lena/Map) y su correlación de amplitud (fantasma 0.57/0.75/0.83,
    Lena/Map 0.40/0.49/0.51 a pico 20/100/1000).
  - **A2 — WF afinado (correlación de fase, media de 6 semillas):**
    `step_max=20` (el default) NO es el mejor a pico bajo ni en Lena/Map.
    Mejor `step_max` fijo por condición: fantasma 20→0.377 (`s1`),
    100→0.745 (`s20`; 0.840 con 200 épocas), 1000→0.951 (0.974 con 200);
    Lena/Map 20→0.114 (`s1`), 100→0.265 (`s5`/`adapt5`), 1000→0.286
    (`s5`). Afinar sube a WF (fantasma pico 20: 0.224→0.377; Lena/Map
    pico 100: 0.179→0.265) pero no cierra la brecha. `adaptive_step` no
    mejora lo que ya da el mejor `step_max` fijo. **Con `step_max` ≥ 10 y
    pico ≤ 100 WF queda PEOR que su propia inicialización:** `phase_rmse`
    0.60-0.70 rad contra 0.236 (fantasma pico 20) y 0.57-0.70 contra 0.137
    (Lena/Map pico 20), y su correlación de amplitud (0.25-0.5) cae por
    debajo de la de la inicialización (0.57-0.75) en todos los niveles de
    ruido del fantasma; la correlación de fase no delata esto.
  - **¿GD sigue ganando con WF afinado?** Sí en casi todo, pero menos que
    en los hitos 11-14 (mejor WF por condición, elegido con las mismas
    semillas de evaluación, o sea a favor de WF; GD = `full_amp`; entre
    paréntesis semillas ganadas de 6 y diferencia media de correlación de
    fase): fantasma pico 20 +0.40 (6/6), 100 +0.13 (6/6, contra WF de 200
    épocas), 1000 +0.02 (6/6); Lena/Map pico 20 +0.07 (5/6), 100 +0.08
    (6/6), **1000 +0.001 (3/6, empate)**. En Lena/Map pico 1000 el GD de
    lote completo con `lr` 0.01 queda en 0.289 con `phase_rmse` 0.211,
    peor que WF (0.131); la ventaja ahí solo aparece con el esquema
    incremental (ver A3).
  - **A3 — pérdida contra esquema:** la **pérdida es el factor grande y
    consistente**: amplitud > intensidad en las 6 condiciones y en ambos
    esquemas (fantasma pico 20: 0.775 contra 0.292 con lote completo;
    Lena/Map pico 100: 0.350 contra 0.128); GD con pérdida de intensidad
    NO le gana al mejor WF afinado (0-3 de 6 semillas por condición,
    diferencia media ≤ 0). El **esquema no importa en el fantasma** (|Δ|
    ≤ 0.02 salvo pico 20, donde el incremental tiene sd 0.18 con
    intensidad), **pero sí en Lena/Map**: incremental+amplitud 0.394 contra
    0.350 a pico 100 y **0.649 contra 0.289 a pico 1000** (con el `lr`
    afinado, que cayó en el borde de la grilla, 0.005). Es decir que el
    veredicto del hito 14 "GD con pérdida de amplitud gana" se sostiene
    por la pérdida, y la elección lote-completo vs incremental cambia el
    resultado en el objeto real.
  - **Lo que debilita la conclusión del hito 14:** (1) el baseline WF
    del hito 14 estaba mal afinado (ver A2), y la ventaja se reduce de
    ~+0.4 a ~+0.1 en varias condiciones; (2) a pico alto en Lena/Map el
    GD "estándar" (lote completo, `lr` 0.01) empata con WF y solo el
    incremental gana claro, así que la ventaja depende de un
    hiperparámetro de esquema que el hito 14 no exploró; (3) la etiqueta
    "amplitud" no es específica de GD: WF ya usa esa pérdida, y
    intensidad+Adam pierde contra WF afinado, así que lo que gana es la
    combinación pérdida de amplitud + Adam (hipótesis: el paso
    normalizado de Adam frente al paso fijo de WF; no se probó WF con
    Adam de forma aislada más allá de esta celda).
  - **Salvedades de este barrido:** solo 1 semilla y 3 valores de `lr` por
    celda para ajustar Adam (y el mejor `lr` de `incr_amp` en Lena/Map en
    el borde de la grilla: el techo del incremental puede ser mayor); el
    mejor WF se elige por condición con las semillas de evaluación (sesgo
    a favor de WF, conservador para GD); comparaciones a 100 épocas de
    gradiente por LED, y GD no se corrió con 200; datos de k redondeado a
    bin, crop 16, un solo canal y una sola geometría; ruido Poisson puro;
    el fantasma viene de `tests/test_joint_calibration.py::_synthetic_object`
    y Lena/Map de imágenes fuera del repo. Costo: ~58 min de un core
    (36 problemas, ~100 s cada uno, más ~7 min de ajuste de `lr`).

- **Milestone 18 — P2 (canal × ruido) y P4 (tamaño de recorte), 2 semillas
  (2026-09-21):** completa el plan de error de posición de LEDs iniciado en
  el hito 16. `scripts/plan_p4_led_position_error.py --exp P2` (18 jobs,
  `data/plan_p2_channel_noise.json`) y `--exp P4` (6 jobs,
  `data/plan_p4_crop_size.json`). Mismo objeto Lena/Map, error "combinado"
  de P1/P3, sin escalar (×1). **Bug de portabilidad arreglado antes de
  correr**: `_job_star` leía una variable global `_opts` que solo existía
  dentro del bloque `if __name__ == "__main__":`; en Windows
  `multiprocessing.Pool` usa `spawn` (no `fork`), así que los procesos hijos
  reimportan el módulo sin ejecutar ese bloque y `_opts` no existe ahí →
  `NameError` en todo trabajo con `--procs > 1`. Corregido con
  `functools.partial(job, **opts)`, sin variable global; probado con un job
  chico real (no solo `--dry-run`, que no pasa por `Pool`) antes de la
  corrida completa.

  P2 (`k_err_bins` ya fijo por canal, ya que k escala con 1/λ para el mismo
  error físico):

  | canal | pico | k_err | WF | GD nominal | GD rígido | GD per-LED | GD oráculo |
  |---|---|---|---|---|---|---|---|
  | azul | 100 | 1.68 | −0.02 | 0.01 | 0.01 | 0.01 | 0.25 |
  | azul | 1000 | 1.68 | −0.01 | 0.02 | 0.02 | 0.00 | 0.54 |
  | azul | 10000 | 1.68 | −0.02 | 0.02 | 0.02 | 0.00 | 0.77 |
  | verde | 100 | 1.49 | 0.02 | 0.02 | 0.02 | −0.00 | 0.20 |
  | verde | 1000 | 1.49 | 0.02 | 0.03 | 0.02 | 0.02 | 0.53 |
  | verde | 10000 | 1.49 | 0.01 | 0.03 | 0.02 | 0.03 | 0.72 |
  | rojo | 100 | 1.26 | 0.03 | 0.12 | 0.05 | 0.07 | 0.26 |
  | rojo | 1000 | 1.26 | 0.03 | 0.12 | 0.06 | 0.08 | 0.46 |
  | rojo | 10000 | 1.26 | 0.02 | 0.11 | 0.09 | 0.07 | 0.54 |

  P4 (crop 16/32/48; `k_err` es el mismo error "combinado" físico, pero
  escala con el recorte):

  | crop | k_err | k_err tras rígido | WF | GD nominal | GD rígido | GD per-LED | GD oráculo |
  |---|---|---|---|---|---|---|---|
  | 16 | 0.75 | 0.68 | 0.03 | −0.14 | −0.02 | −0.02 | 0.40 |
  | 32 | 1.49 | 1.59 | 0.02 | 0.03 | 0.02 | 0.02 | 0.53 |
  | 48 | 2.24 | 2.22 | −0.01 | −0.00 | −0.00 | −0.01 | 0.56 |

    - **P2 no puede probar su hipótesis: el error "combinado" a ×1 ya está
      muy por encima del acantilado (1.26-1.68 bins, contra el ~0.4-0.8
      bin del hito 16) en los tres canales.** Por eso ningún solver (WF,
      nominal, rígido, per-LED) recupera nada en ningún pico —quedan todos
      pinneados entre −0.02 y 0.12 sin importar si hay 100 o 10000 fotones—
      mientras el oráculo (posiciones verdaderas) sí mejora con los fotones
      (0.20→0.72 en verde, 0.25→0.77 en azul). El criterio de refutación
      ("`gd_rigid` ≈ `gd_true` a pico 100 en verde → el ruido no limita la
      calibración") ni siquiera llega a evaluarse: rígido nunca se acerca
      al oráculo en ningún pico, así que el cuello de botella es
      enteramente la posición, no el ruido fotónico — el diseño del
      experimento reutilizó el error a magnitud completa en vez de una
      escala parcial (como el ×0.25/×0.5 de P3), y ahí no queda nada que
      el ruido pueda seguir rompiendo.
    - **Sí aparece una señal de canal, chica pero consistente en ambas
      semillas: rojo (menos bins de error, 1.26) queda menos roto que
      verde y azul** (nominal 0.11-0.12 contra 0.02-0.03 y 0.01-0.02).
      Coincide con el patrón ya visto en P1/P3 ("menos bins, menos
      catástrofe"), no con la hipótesis original de "el azul falla primero
      por peor SNR" — acá lo que manda es que el mismo error físico mide
      menos bins en rojo (λ mayor), no el ruido.
    - **P4 confirma la propia advertencia del plan: crop y `k_err_bins` están
      confundidos** (el error físico "combinado" mide 0.75 bins a crop 16 y
      2.24 a crop 48), así que 32 y 48 ya están muy pasados el acantilado y
      no hay nada que comparar ahí. El único punto con señal es crop 16
      (0.75 bins, cerca del umbral), y ahí el resultado va en contra de la
      hipótesis del plan ("crops chicos dan poca señal y `per_led` sobreajusta
      peor que `rigid`"): las tres variantes de GD quedan mal, pero
      **`gd_nominal` es la peor y va a negativo (−0.14)**, peor que
      `gd_rigid` y `gd_perled` (−0.02 ambos) — a recorte chico, no calibrar
      es peor que calibrar de cualquier forma, no al revés. El criterio de
      refutación ("`gd_rigid` no cambia con el crop, ±0.05") tampoco se
      puede evaluar limpiamente por la misma confusión: los tres valores
      (−0.02 / 0.02 / −0.00) están dentro del ruido entre sí, pero
      corresponden a tres severidades de error distintas, no a la misma.
    - **No se amplió a 4 semillas**: a diferencia del hito 16, acá ninguna
      celda queda en una zona ambigua (~0.05-0.1) que dependa de la
      elección — todo está claramente cerca de cero o claramente cerca del
      oráculo, salvo la señal roja-contra-verde/azul de P2, que ya es
      consistente en las 2 semillas.
    - **Salvedades:** (1) 2 semillas, igual que el resto del plan hasta
      ahora. (2) Ninguno de los dos experimentos prueba realmente lo que se
      propuso: P2 necesitaría un error a escala parcial (no ×1) para
      separar el efecto del ruido/canal del acantilado ya cruzado; P4
      necesitaría mantener el error en bins constante entre recortes (no el
      error físico) para aislar el efecto del tamaño de recorte del
      acantilado. Quedan como diseños a corregir si se retoma este punto,
      no como resultados negativos definitivos. (3) Mismo objeto Lena/Map,
      geometría "current", fase 0.3π, calibración conjunta de 150
      iteraciones. Costo real: P2 ~40 min (18 jobs, 2 procesos, PC
      cargada), P4 ~16 min (6 jobs, el crop 48 domina el costo).

- **Milestone 19 — techo de fase y contraste de amplitud para retomar 2b
  (2026-09-22):** antes de intentar construir el tercer test de punta a
  punta que faltaba en `tests/test_multispectral_end_to_end.py` (solver
  real + señal de dispersión grande + sin fase inyectada), dos chequeos
  baratos para saber si es siquiera posible. **Bug de portabilidad
  arreglado en el camino** (mismo patrón que el hito 18, otro archivo):
  `scripts/plan_p3_object_phase_geometry.py` tenía el mismo `_job_star`/
  `_opts` global roto bajo `spawn` en Windows — mismo fix con
  `functools.partial`.

  **Techo de fase (`data/phase_ceiling_sweep_blue.json`, 28 jobs):**
  `search_wrap_numbers` solo hace algo real cuando la fase absoluta supera
  **π rad** (envuelve a `(-π, π]`, ver `wrap_phase` en `multispectral.py`)
  — GD-amplitude nunca se había probado más allá de 0.3π (~0.94 rad,
  hitos 11-18). Barrido en **azul** (el canal con más fase a OPL
  compartido, hito 2b), `lena_map`, crop 32, 9×9, pico 1000 y sin ruido, 2
  semillas, RMSE de fase en radianes (no correlación — M1 del auditor: la
  correlación sobrestima lo recuperado):

  | fase máx | RMSE GD (rad) | RMSE "sin fase" | correlación GD |
  |---|---|---|---|
  | 0.3π | 0.11 | 0.13 | 0.62-0.71 |
  | 0.5π | 0.15-0.16 | 0.22 | 0.74-0.76 |
  | 0.75π | 0.22-0.24 | 0.33 | 0.73-0.76 |
  | 1.0π | 0.30-0.36 | 0.44 | 0.67-0.74 |
  | **1.5π** | **2.63** | 2.30 | **−0.40 a −0.45** |
  | 2.0π | 1.49 | 1.20 | −0.02 a −0.05 |
  | 3.0π | 1.33 | 1.12 | 0.28 |

  **Corrección (revisión del advisor, misma noche):** las filas de 1.5π en
  adelante **no son una curva de degradación confiable**. `metrics.py`'s
  `compare_to_ground_truth` calcula `truth_phase = _normalize_phase(np.angle(truth))`
  — envuelve la fase *verdadera* a `(-π, π]` antes de comparar, y además
  compara wrapped-contra-wrapped con una resta ingenua (sin
  `wrap_phase(recon − truth)` circular). Con `phase_max` > π la propia
  verdad de referencia queda con discontinuidades de envolvimiento
  artificiales, y por eso `flat_phase_rmse` (la referencia "sin fase") es
  **no monótono** con la fase (0.13→0.22→0.33→0.44→**2.30→1.20→1.12**): no
  es que "sin fase" se vuelva una mejor referencia a fases más altas, es
  que la métrica ya no mide lo mismo por encima de π. **Conclusión
  corregida: GD-amplitude no es medible de forma confiable por encima de
  π con la métrica actual** (no "colapsa entre 1.0π y 1.5π" con precisión
  — esa lectura punto por punto no sobrevive). Lo que sí se sostiene: hasta
  1.0π le gana claro a la referencia "sin fase" con una métrica que ahí sí
  es válida (fase todavía < π, sin envolver), y **el tercer test tampoco
  se puede construir hoy** — si la métrica de este repo no puede siquiera
  puntuar una reconstrucción por encima de π, la conclusión de más abajo
  (que no hay wrap ambiguity utilizable con ningún solver actual) se
  sostiene igual o más fuerte, solo que por una razón distinta (límite de
  medición, no necesariamente solo de solver). No se tocó `metrics.py`
  para arreglar esto — cambiar una función compartida por tantos hitos
  pasados invalidaría la comparabilidad histórica; queda documentado como
  limitación conocida, a evaluar aparte si hace falta medir fase > π de
  verdad en el futuro.

  La separación en dos tests de `test_multispectral_end_to_end.py` (uno
  con el solver real y fase chica, otro con fase inyectada para aislar
  2b.i/2b.ii) **no es una rareza de Wirtinger flow** como sugería el
  hallazgo del hito 2b — es una
  propiedad de esta familia de solvers (ninguno probado hasta ahora
  reconstruye de forma útil por encima de ~π rad de fase absoluta). No se
  intentó forzar el tercer test con fase inyectada disfrazada de
  "punta a punta"; se registra el nulo como resultado.

  **Contraste de amplitud (`data/amplitude_contrast_sweep.json`, 20
  jobs):** el hallazgo del hito 2b decía que el solver (WF) falla en
  objetos de amplitud uniforme (fase pura) — justo el régimen de muestras
  biológicas casi transparentes que motiva el proyecto. `lena_map`,
  verde, fase fija 0.3π (zona segura del barrido de arriba), crop 32,
  9×9, 2 semillas, contraste = `1 - min_amplitude`:

  | contraste | pico | corr WF | corr GD | RMSE WF | RMSE GD |
  |---|---|---|---|---|---|
  | 20% | 100 | 0.06 | 0.28 | 0.131 | 0.126 |
  | 20% | 1000 | 0.32 | **0.75** | 0.124 | 0.086 |
  | 10% | 100 | 0.09 | 0.25 | 0.130 | 0.127 |
  | 10% | 1000 | 0.09 | **0.58** | 0.131 | 0.106 |
  | 5% | 100 | 0.03 | 0.01 | 0.132 | 0.138 |
  | 5% | 1000 | 0.09 | **0.42** | 0.131 | 0.122 |
  | 2% | 100 | 0.01 | 0.12 | 0.132 | 0.133 |
  | 2% | 1000 | 0.02 | 0.15 | 0.132 | 0.138 |
  | 0% (fase pura) | 100 | 0.10 | 0.34 | 0.130 | 0.123 |
  | 0% (fase pura) | 1000 | 0.00 | **−0.24** | 0.133 | **0.166** |

    - **GD-amplitude sí ayuda con poco contraste, pero no en cero exacto.**
      Desde 2% de contraste hacia arriba, a pico 1000, gana claro a WF (de
      0.15 a 0.75 de correlación, contra 0.02-0.32 de WF) y con RMSE por
      debajo de WF en casi todos los casos. **En contraste cero exacto
      (fase pura) a pico 1000, GD-amplitude se vuelve inestable y queda
      peor que WF** (correlación −0.24, RMSE 0.166 — peor que "sin fase",
      0.131): no resuelve el caso límite que motivó el hallazgo del hito
      2b, solo lo mueve. WF en cambio se queda plano cerca de cero en todo
      el barrido, sin colapsar nunca a negativo.
    - **A pico 100 (menos fotones) la ventaja de GD se erosiona y en 5% se
      invierte** (corr 0.01 contra 0.03 de WF) — con ruido moderado y poco
      contraste, ninguno de los dos solvers sirve de mucho (todas las
      correlaciones ≤0.34).
    - **No confirma "dramáticamente" la recuperación con 5-10% de contraste
      del hito 2b para WF específicamente** — acá WF se queda en 0.09-0.32
      en ese rango, no cerca de los 0.6-0.9 que mencionaba esa entrada
      (que viene de otra geometría/objeto, la del test de punta a punta
      inyectado, no de este barrido); no se reconcilian ambos números en
      esta sesión.
  - **Salvedades:** 2 semillas; un solo canal (verde) para el contraste,
    uno solo (azul) para el techo de fase; un solo objeto (`lena_map`),
    geometría y crop fijos; posiciones de LEDs exactas (sin el error de
    los hitos 16-18); Poisson puro. El techo de fase es una medición de
    reconstrucción monocanal aislada, no de la cadena acoplada completa
    (`couple_rgb_channels`) — sirve como cota superior barata, no como
    medición directa de dónde falla el pipeline de 2b entero. Costo real:
    ~35 min (barrido de fase, 28 jobs) + ~25 min (contraste, 20 jobs), 2
    procesos.

- **Milestone 20 — techo de la cadena acoplada completa con el solver real
  (2026-09-22, sesión nocturna autónoma):** el hito 19 solo midió un canal
  aislado; esto corre `couple_rgb_channels` de punta a punta (extensión de
  `test_full_pipeline_through_real_reconstruction_recovers_thickness_shape`)
  con WF y GD-amplitude, barriendo la magnitud de OPL. `data/coupled_opl_ceiling_sweep.json`
  (48 jobs), crop 16, 9×9, pico 1000, 4 semillas, objeto/geometría de ese
  test (bump de amplitud + espesor oscilante `sin·cos`, A=1.34/B=0.004),
  script en el scratchpad de la sesión (no versionado — extensión ad hoc
  del test existente, no un script de `scripts/`). **Bug encontrado y
  arreglado antes de confiar en el resultado**: la primera corrida
  alimentaba `jc.reconstruct_and_calibrate` con imágenes generadas por
  `forward_model.simulate_lr_stack` (la convención de unidades de WF) sin
  la conversión `/sc**2` que `plan_p3_object_phase_geometry.job()` sí
  aplica entre esa convención y la que espera `jc` (documentado en el
  propio docstring de `initial_object_from_center_led`); GD salía
  uniformemente roto en todas las escalas. Corregido y re-corrido
  completo; la corrección mejoró GD pero no cambió la conclusión (ver
  abajo). Correlación con el espesor verdadero (no la fase — sin el
  problema de envolvimiento del hito 19), media±sd de 4 semillas:

  | escala | fase máx azul | corr. acoplada WF | corr. ingenua WF | corr. acoplada GD | corr. ingenua GD | frac. k≠0 |
  |---|---|---|---|---|---|---|
  | 1 | 0.14π | 0.11±0.04 | **0.66±0.03** | −0.05±0.03 | 0.07±0.01 | 0.00 (WF) / 0.45 (GD) |
  | 2 | 0.28π | 0.30±0.02 | **0.82±0.01** | −0.03±0.04 | 0.08±0.01 | 0.00 / 0.43 |
  | 4 | 0.55π | 0.35±0.21 | **0.89±0.01** | −0.20±0.01 | 0.04±0.01 | 0.03 / 0.35 |
  | 8 | 1.11π | −0.04±0.07 | −0.69±0.01 | −0.35±0.07 | 0.20±0.01 | 0.40 / 0.56 |
  | 16 | 2.22π | 0.04±0.01 | −0.45±0.01 | −0.28±0.03 | −0.35±0.04 | 0.50 / 0.56 |
  | 24 | 3.33π | 0.01±0.02 | −0.21±0.02 | −0.15±0.03 | −0.26±0.03 | 0.65 / 0.76 |

    - **Con WF, acoplar (2b.i+2b.ii) es una pérdida neta cuando NO hace
      falta desenvolver, y solo un rescate parcial cuando sí hace falta.**
      A escala 1-4 (`frac_k`≈0, el desenvolvimiento no debería tocar nada)
      el ingenuo ya reconstruye bien el espesor (0.66-0.89) y **acoplar lo
      empeora** (0.11-0.35) — el ajuste de dispersión + el refinamiento TV
      de `refine_opl_tv` distorsionan la señal incluso con k=0 en todos
      lados, no solo cuando corrigen wraps reales. A escala 8 (fase azul
      1.11π, `frac_k`=0.40, ahí sí hace falta desenvolver) el ingenuo
      colapsa (−0.69) y acoplar lo mitiga (−0.04) pero **sin llegar a un
      resultado útil** — sigue cerca de cero, no una reconstrucción de
      espesor confiable. A escala 16-24 el patrón se repite (ingenuo muy
      negativo, acoplado cerca de cero).
    - **Con GD-amplitude, acoplar es un problema en todas las escalas,
      incluso ya con el fix de unidades.** El ingenuo de GD (0.04-0.20 en
      casi todo, sin colapsar del todo) es sistemáticamente mejor que el
      acoplado (−0.03 a −0.35, siempre negativo o cerca). La causa
      aparece en `frac_k`: a escala 1 (fase azul 0.14π, donde NO debería
      hacer falta ningún wrap real) el 45% de los píxeles ya reciben un
      número de envolvimiento distinto de cero — la fase cruda de GD trae
      suficiente ruido/estructura espuria como para que
      `search_wrap_numbers` "corrija" con saltos de 2π donde no los hay,
      metiendo ruido nuevo en vez de sacarlo. La robustez al ruido de
      `search_wrap_numbers` está validada en
      `tests/test_multispectral_unwrapping.py` con 0.05 rad de ruido
      gaussiano sintético — el ruido real de una reconstrucción GD parece
      tener una estructura (espacialmente correlacionada, no gaussiano
      i.i.d.) que rompe ese supuesto de robustez.
    - **Contraste con el hito 2b/la prueba de fase inyectada:** con fase
      inyectada limpia, acoplar le gana al ingenuo por >20x de error
      (`test_unwrapping_beats_naive_phase_on_a_large_dispersion_signal`).
      Acá, con fase real (de cualquier solver), la ventaja de acoplar
      **nunca aparece como una mejora neta útil** — en el mejor caso
      (WF, fases grandes) pasa de catastrófico a mediocre, no a bueno. La
      cadena 2b.i+2b.ii tal como está calibrada hoy (parámetros por
      defecto de `refine_opl_tv`, `k_range`) está afinada para fase
      limpia/inyectada, no para el nivel de ruido de una reconstrucción
      real — esto es un hallazgo nuevo y más importante que el bug de
      unidades: **incluso arreglado, 2b no produce un resultado
      cuantitativo utilizable a través del solver real, con ningún
      solver de este repo.**
    - **Salvedades:** 4 semillas, un solo objeto/geometría (crop 16, 9×9,
      el del test existente, no `lena_map`), un solo pico (1000), un solo
      `k_range` y una sola configuración de `refine_opl_tv` (los
      parámetros por defecto de `couple_rgb_channels`); no se probó
      desactivar el refinamiento TV (`refine=False`) para ver si la
      pérdida neta a escala baja viene de ahí específicamente en vez del
      ajuste de dispersión en sí — sería el primer lugar a mirar si se
      retoma esto. Posiciones de LEDs exactas (sin el error de los hitos
      16-18, que ya se sabe que domina sobre esto en la práctica). Script
      guardado en `scripts/coupled_opl_ceiling_sweep.py` (vivió en el
      scratchpad de la sesión durante el desarrollo; copiado al repo
      recién al final para que quede reproducible) — es una extensión
      directa de `tests/test_multispectral_end_to_end.py`'s primer test,
      barriendo `t_scale` y agregando la rama `gd-amplitude`. Costo real:
      ~20 min (primera corrida, con el bug) + ~20 min (corrida
      corregida), 2 procesos.

  - **CORRECCIÓN IMPORTANTE (misma noche, después de seguir la sugerencia
    del advisor de aislar el mecanismo):** la lectura de arriba ("acoplar
    es una pérdida neta cuando no hace falta desenvolver") está **mal
    diagnosticada para WF** — el mecanismo real es otro y bastante más
    interesante. Se probaron los dos sospechosos obvios y ninguno explica
    nada:
    1. **`refine_opl_tv` no tiene ningún efecto en `couple_rgb_channels`,
       nunca.** Comparar `refine=True` (default) contra `refine=False` en
       el mismo job da **resultados idénticos, bit a bit** (0.115 en
       ambos, escala 1, WF). Razón, ya documentada en el propio docstring
       de `couple_rgb_channels` pero que se me había pasado: el
       diccionario `opl` que alimenta `fit_cauchy_dispersion` se arma con
       `rg["opl1"]`/`rg["opl2"]`/`gb["opl1"]`/`gb["opl2"]` —las
       candidatas CRUDAS de `search_wrap_numbers`— nunca con `rg["opl"]`/
       `gb["opl"]` (la salida refinada de `refine_opl_tv`). El
       refinamiento TV se calcula (dentro de `unwrap_two_channel`) pero
       su resultado **no se usa en ningún lado que afecte el espesor
       final**. No es un bug — el docstring explica por qué (promediar
       antes de ajustar borraría la señal de dispersión) — pero sí
       significa que "afinar `refine_opl_tv`" no es una vía de mejora
       disponible hoy para este pipeline específico, contra lo que
       sugería la salvedad original.
    2. **El pistón (`reference_phase_to_background`) tampoco es la
       causa**: a escala 1, el pistón aritmético y el circular coinciden
       hasta la 6ª cifra decimal en los tres canales, y el fondo nunca
       cruza ±π (`straddles_pi=False`). Descartado.
    - **El mecanismo real: unos pocos píxeles con número de envolvimiento
      erróneo, y una métrica (correlación de Pearson) sin ninguna
      robustez a outliers.** A escala 1 (WF), 7 de 2304 píxeles (0.3%)
      reciben `k≠0` cuando la verdad es `k=0` en todos lados; cada uno de
      esos píxeles mete un error de OPL de hasta 1.26 (la señal real
      completa mide ~0.012). **Excluir esos 7 píxeles sube la correlación
      de 0.115 a 0.79** —mejor que el ingenuo (0.65), no peor—. A escala 2
      (WF), 58/2304 píxeles (2.5%) están mal; excluirlos da 0.88 contra
      0.33 con ellos (ingenuo: 0.82). **La conclusión "acoplar empeora"
      del texto original es en gran parte un artefacto de la métrica, no
      una falla real del pipeline**: para el 97-99.7% de los píxeles
      restantes, acoplar sí ayuda.
    - **Para GD-amplitude el diagnóstico es distinto, y ahí la conclusión
      original sí se sostiene.** A escala 1, GD tiene **2084/2304 píxeles
      (90%)** con `k≠0` —no es un puñado de outliers, es la mayoría de la
      imagen—. Excluir esos píxeles solo sube la correlación de −0.09 a
      0.29, lejos de ser buena. Para GD el problema no es un artefacto de
      métrica: la fase cruda que entrega tiene demasiado ruido por
      píxel, en todas partes, como para que la búsqueda de número de
      envolvimiento funcione en absoluto.
    - **A escalas altas (8+), donde sí hace falta desenvolver de verdad,
      este diagnóstico deja de ser limpio**: la fracción de píxeles con
      `k≠0` ahí mezcla correcciones genuinamente necesarias con errores
      residuales, así que "excluir los píxeles con k≠0" ya no separa
      "ruido espurio" de "señal real" (a escala 8/WF, excluirlos da
      **peor** correlación, −0.29, que no excluirlos, 0.02 — consistente
      con estar tirando la mayoría de la información real). La lectura
      original del hito 20 para esas escalas (ingenuo colapsa, acoplado
      lo mitiga sin llegar a bueno) no se revisó de nuevo y puede seguir
      siendo válida.
    - **Salida constructiva que el propio código ya deja preparada y sin
      usar:** `couple_rgb_channels` ya devuelve `pair_disagreement`
      (`|opl1-opl2|` en el par ganador), documentado explícitamente en su
      docstring como "diagnóstico de confianza por píxel" — exactamente
      la señal que habría marcado los 7/58 píxeles problemáticos de
      arriba. Hoy nada en el pipeline lo usa para filtrar o ponderar el
      ajuste de dispersión ni el mapa de espesor final. Enmascarar o
      down-weight-ear por `pair_disagreement` alto antes de calcular
      correlación/ajustar dispersión es la mejora concreta más barata
      que se identificó en toda la sesión — no probada todavía, es
      trabajo a futuro, no un resultado.
    - **Conclusión revisada del hito 20**: para WF, acoplar (2b.i, la
      parte de desenvolvimiento) **funciona razonablemente bien** una vez
      que se controla por el puñado de píxeles con número de
      envolvimiento mal asignado — el problema no es 2b.i/2b.ii en sí,
      es la ausencia de un paso de filtrado/robustez que use la señal de
      confianza que el código ya calcula. Para GD, el problema es más
      profundo (ruido de fase por píxel demasiado alto) y no se resuelve
      con un filtro de outliers.

    - **Confirmado con el barrido completo de 4 semillas** (mismo diseño
      de 48 jobs de arriba, `corr_coupled_masked` agregado a
      `scripts/coupled_opl_ceiling_sweep.py`, `data/coupled_opl_ceiling_sweep_masked.json`):
      el diagnóstico de una semilla se sostiene entero y se ve más nítido
      con más datos.

      | escala | frac. enmascarada | acoplada WF | **enmascarada WF** | ingenua WF | acoplada GD | **enmascarada GD** | ingenua GD |
      |---|---|---|---|---|---|---|---|
      | 1 | 0.4% (WF) / 91% (GD) | 0.11±0.04 | **0.80±0.01** | 0.66±0.03 | −0.05±0.03 | 0.20±0.10 | 0.07±0.01 |
      | 2 | 1.9% / 91% | 0.30±0.02 | **0.88±0.01** | 0.82±0.01 | −0.03±0.04 | 0.33±0.18 | 0.08±0.01 |
      | 4 | 20% / 88% | 0.35±0.21 | **0.93±0.01** | 0.89±0.01 | −0.20±0.01 | 0.34±0.07 | 0.04±0.01 |
      | 8 | 68% / 89% | −0.04±0.07 | −0.46±0.10 | −0.69±0.01 | −0.35±0.07 | 0.42±0.08 | 0.20±0.01 |
      | 16 | 82% / 93% | 0.04±0.01 | −0.48±0.09 | −0.45±0.01 | −0.28±0.03 | −0.08±0.39 | −0.35±0.04 |
      | 24 | 93% / 97% | 0.01±0.02 | −0.24±0.09 | −0.21±0.02 | −0.15±0.03 | 0.21±0.36 | −0.26±0.03 |

      - **Para WF, enmascarar da el mejor resultado de las tres métricas
        en escala 1, 2 y 4** (0.80, 0.88, 0.93 — todas mejores que
        ingenuo, que a su vez ya era razonable ahí). La fracción
        enmascarada se mantiene chica hasta escala 4 (≤20%), consistente
        con "son outliers, no señal real perdida". **En escala 8 en
        adelante la fracción enmascarada salta a 68-93%** — ahí enmascarar
        ya está descartando la mayoría de la imagen (donde el
        desenvolvimiento real sí hace falta, no es espurio) y por eso
        la métrica enmascarada se vuelve la peor de las tres, no la
        mejor. El punto de quiebre (entre escala 4 y 8) coincide con
        donde la fase azul cruza ~0.5-1.0π (ver hito 19/20) — justo donde
        empieza a hacer falta desenvolver de verdad.
      - **Para GD, enmascarar ayuda pero nunca llega a bueno** (0.20-0.42
        en el mejor caso, contra 0.80-0.93 de WF a las mismas escalas
        bajas) y la fracción enmascarada es enorme en todas las escalas
        (88-97%, sin la caída abrupta que muestra WF entre escala 4 y 8).
        Esto descarta que el problema de GD sea "unos pocos outliers
        además de los reales" — es ruido de fase por píxel extendido a
        casi toda la imagen incluso donde no debería hacer falta ningún
        wrap. **Salvedad nueva**: la reconstrucción ingenua de GD en este
        objeto/geometría (crop 16, bump oscilante, grid 9×9) ya es mucho
        peor que la de WF en las mismas condiciones (ingenua GD 0.04-0.20
        contra ingenua WF 0.66-0.89 a escala 1-4) — algo no visto en los
        hitos 11-19, donde GD solía ganarle a WF en objetos con
        estructura. No se investigó a fondo si esto es específico de este
        objeto/crop (16, más chico que el crop 32 de los hitos anteriores).
        **Corrección**: un chequeo de una sola celda (escala 8, semilla 0)
        que se mencionó más arriba como "crop 32 mejora algo" en realidad
        dio **mixto, no una mejora limpia**: crop 32 mejoró lo acoplado
        (−0.227→0.054) pero **empeoró lo ingenuo** (0.198→0.094) respecto
        de crop 16. No alcanza para concluir que crop 32 arregla nada acá;
        sería el primer lugar a mirar con más semillas si se
        retoma esto.
      - Esto reemplaza el diagnóstico de una sola semilla de arriba, que
        queda como registro de cómo se llegó al hallazgo, no como el
        resultado final.

- **Milestone 21 — diagnóstico de inicialización para el colapso a
  contraste 0% (2026-09-22, sesión nocturna autónoma):** el hito 19
  encontró que GD-amplitude, a contraste de amplitud exactamente cero
  (fase pura) y pico 1000, da correlación de fase **negativa** (−0.24,
  peor que WF). ¿Es un problema de inicialización (`initial_hr_guess`/
  `initial_object_from_center_led` arrancan de una imagen sin estructura)
  o del paisaje de optimización en sí (el "saddle de fase débil" ya
  documentado en `c566d85`)? `reconstruct_and_calibrate` ya acepta
  `initial_object` como parámetro arbitrario, así que esto no tocó
  `src/`.

  **Falso comienzo, corregido antes de confiar en el resultado:** la
  primera versión del diagnóstico usó el modelo directo de k continuo de
  `plan_common.simulate_exact_k` (la convención de los hitos 16+), NO la
  grilla alineada a bin + `forward_model.simulate_lr_stack` que el hito 19
  realmente usó — con esa mezcla, el init "default" daba correlación
  **positiva** (0.75±0.01 a pico 1000), sin relación con la anomalía
  original. Corregido para replicar exactamente el `job()` de
  `plan_p3_object_phase_geometry.py` (grilla alineada a bin, conversión
  `/sc**2` para GD); con eso, "default" reprodujo la anomalía casi exacto
  en la prueba de una semilla (−0.27 contra el −0.24 original) antes de
  correr las 4 semillas completas.

  `data/init_diagnosis_pure_phase.json` (32 jobs, 4 inits × 2 picos × 4
  semillas), `lena_map`, verde, `min_amp=1.0` (fase pura), fase 0.3π,
  crop 32, 9×9, GD-amplitude 100 iteraciones, posiciones exactas:

  | init | pico 100 | pico 1000 |
  |---|---|---|
  | default (centro-LED, el que falla) | 0.242±0.117 | **−0.338±0.165** |
  | oráculo amplitud (=1 exacto, fase 0) | 0.096±0.064 | 0.191±0.325 |
  | fase aleatoria chica (σ=0.3 rad) | 0.029±0.019 | 0.032±0.063 |
  | **oráculo completo (objeto verdadero)** | 0.601±0.020 | **0.913±0.000** |

    - **Es un problema de cuenca de atracción, no del paisaje de
      optimización.** Arrancar exactamente en la respuesta verdadera
      (`oracle_full`) converge casi perfecto y con desviación
      prácticamente nula entre semillas (0.913±0.000 a pico 1000) — el
      optimizador no se aleja de un buen óptimo una vez que llega ahí. El
      problema es puramente de **alcanzabilidad** desde un arranque plano
      típico, no de que no exista un buen óptimo o de que el gradiente
      empuje activamente lejos de él.
    - **Un arreglo barato y genérico (romper la simetría con fase
      aleatoria chica) no rescata nada** — 0.03 a ambos picos,
      indistinguible de ruido. No es un saddle simétrico que cualquier
      perturbación resuelve; el arranque plano cae en (o cerca de) un
      atractor malo específico, no en un punto de equilibrio inestable
      genérico.
    - **El init "default" es *peor* que el init con amplitud oráculo
      (ambos son "planos"), y con menos variabilidad entre semillas**
      (sd 0.165 contra 0.325) — el ruido de conteo de fotones en la
      imagen del LED central (que en teoría no debería aportar ninguna
      estructura útil a contraste 0%) parece empujar de forma consistente
      hacia un atractor malo específico, mientras el init perfectamente
      uniforme (sin ese ruido) es más errático semilla a semilla —a veces
      cae mejor, a veces peor, con muchísima más varianza. No se investigó
      por qué el ruido de conteo tiene un efecto direccional consistente
      en vez de puramente aleatorio; sería el siguiente paso si se retoma
      esto.
    - **Implicación práctica:** ni con este solver ni con una
      inicialización barata hay hoy una forma de manejar el caso 0% de
      contraste con muchos fotones. Un arreglo real necesitaría o (a) una
      inicialización más informada (p. ej. desde un espectrograma de fase
      débil o desde un modelo TIE aproximado, no probado acá), o (b) un
      cambio de esquema de optimización (scheduling del learning rate,
      annealing, o el "saddle de fase débil" de `c566d85` sugiere que
      podría hacer falta una estrategia de escape de saddle específica),
      ninguno de los cuales se probó en esta sesión.
    - **Salvedades:** 4 semillas; una sola celda (contraste exacto 0%,
      `lena_map`, verde, fase 0.3π); no se probó a otros niveles de
      contraste bajo (2%/5%) si el mismo problema de cuenca aparece ahí
      también o si es específico del contraste exactamente cero; solo GD-
      amplitude (no se repitió el diagnóstico con WF, que a esta celda ya
      se sabe que se queda cerca de cero sin volverse negativo). Script
      en el scratchpad de la sesión (extensión directa de
      `plan_p3_object_phase_geometry.job()`, variando solo `initial_object`
      — no copiado a `scripts/` por brevedad, dado que es un diagnóstico
      puntual, no un experimento a repetir). Costo real: ~2 min (prueba de
      una semilla, ya con el bug corregido) + ~13 min (barrido completo),
      2 procesos.

(Gap #4 FPM-INR/`zhou2023` queda fuera de este roadmap por ahora —
mejora calidad/velocidad del solver monocromático en general por una vía
de aprendizaje profundo mucho más grande, no es específico de
"multiespectral asistido por agentes"; se puede intercalar en cualquier
fase si conviene.)

## 4. Preguntas abiertas / riesgos

1. **[RESUELTO — 2026-09-17]** "Reconstrucción conjunta" se hace de las
   **dos formas, para comparar** (ver milestone 2a/2b arriba): independiente
   como baseline barato, acoplada vía unwrapping multi-wavelength +
   ajuste de dispersión n(λ) como la línea novedosa. La comparación entre
   ambas es en sí misma un resultado a reportar.

2. **¿El objetivo real (`ObjectiveConfig` en `config.py`) tiene corrección
   acromática, o hay que esperar dispersión notable entre 470-630 nm?** No
   hay ningún dato en el repo sobre esto — `OBJECTIVES["current"]` solo
   define NA y magnificación, sin curva de aberración cromática.
   **Plan acordado**: antes de pedir ficha técnica o medir con target físico,
   diagnóstico gratis con los datos reales ya existentes en
   `data/<channel>/...` — comparar registro/foco entre los 3 canales de un
   mismo target; si hay corrimiento lateral o de foco entre red/green/blue,
   ahí está medida la aberración cromática directamente. Si no alcanza,
   recurrir a auto-calibración vía pupil recovery (`ou2014`, gap #1) por
   canal, o a ficha técnica/target físico como último recurso.

   **[HERRAMIENTA CONSTRUIDA — 2026-09-18, sesión autónoma] Sigue sin datos
   reales en este Codespace (`data/` no tiene capturas TIFF, solo el
   registro de procedencia) — pero la herramienta ya está lista para
   correr apenas existan.** Implementado
   `src/ptyco_full_simulator/chromatic_diagnostics.py`:
   `measure_lateral_shift_px` (corrimiento lateral sub-píxel entre dos
   canales, correlación de fase normalizada + ajuste parabólico sub-píxel)
   y `measure_focus_offset_um` (offset de foco relativo, buscando sobre
   distancias de desenfoque candidatas con
   `propagation.angular_spectrum_propagate` cuál hace que un canal
   coincida mejor con el otro), combinados en
   `chromatic_registration_report` (red-green y blue-green, con green
   como referencia).

   Validado contra corrimientos/desenfoques sintéticos conocidos
   (`tests/test_chromatic_diagnostics.py`, 5 tests): recupera un
   corrimiento lateral sub-píxel inyectado con error <0.15px sobre campos
   ideales, un desenfoque de 25µm inyectado con error <3µm, controles
   negativos en 0 para ambos, y un test de punta a punta que inyecta un
   corrimiento lateral conocido en el canal blue *antes* de simular su
   pila LR y reconstruye los 3 canales con el solver Wirtinger flow real
   (no campos ideales) — lo detecta correctamente (red≈0, blue≈corrimiento
   inyectado, dentro de ~1.5px de tolerancia, más ancha que con campos
   ideales por el ruido propio de la reconstrucción).

   **Límite honesto, documentado en el docstring del módulo**: ambas
   mediciones se validaron contra campos de verdad de referencia (ideales)
   con precisión de una fracción de píxel / pocos µm; a través de la
   reconstrucción real de este proyecto (imperfecta), el ruido de medición
   crece con el error de reconstrucción — este diagnóstico es tan bueno
   como la reconstrucción que mide, no mejor. Una corrida con su propio
   problema de fase débil o mínimo local (ver las limitaciones ya
   documentadas de `reconstruction.py`) va a reportar un corrimiento
   cromático más ruidoso/menos confiable, no uno silenciosamente
   incorrecto sin aviso — conviene chequear siempre
   `metrics.convergence_summary`/`compare_to_ground_truth` (cuando exista
   verdad de referencia) antes de confiar en este diagnóstico sobre una
   reconstrucción mal convergida.

   **[HECHO — 2026-09-18] Formalizado en el registro de procedencia y
   cableado como flag de CLI.** `scripts/compute_numbers.py` gana
   `chromatic_shift_recovery_error()`: mismo escenario que el test de
   punta a punta de arriba (corrimiento 2.0/−1.5px inyectado en blue,
   reconstruido con el solver real) — recupera el corrimiento con error
   euclídeo de ~1.55px (ver `report/report.md` milestone 10 para el
   número exacto vía `[srcnum:chromatic_shift_recovery_error_px]`), y
   reporta ~0.09px para el par sin corrimiento inyectado (control
   negativo). Nuevo claim `chromatic_diagnostic_recovers_injected_shift`
   en `structure/claims.yaml`, nueva sección "Milestone 10" en
   `report/report.md`. `scripts/reproduce.sh` pasa completo (21 tags
   `\src`, 20 `\srcnum`, 21 entradas, 11 claims).

   También cableado como `--chromatic-report` en
   `reconstruct_multispectral_independent.py`/`coupled.py`: corre
   `chromatic_registration_report` sobre los 3 canales ya reconstruidos y
   guarda `chromatic_report.json` en `--output-dir` — sigue sin datos
   reales para correrlo con sentido en este Codespace, pero ya no hace
   falta escribir código nuevo cuando existan.

3. **[RESUELTO — 2026-09-17]** La capa de agentes es **Opción A: Claude
   Code orquestando** (subagentes/forks/tareas en background invocados
   desde el pipeline, como en esta misma conversación) — no un framework
   standalone tipo LangGraph/AutoGen. Cada corrida de las fases 3 en
   adelante va a necesitar una sesión/API de Claude disponible.

4. **[RESUELTO PARCIALMENTE — 2026-09-17, ver
   `docs/literature_check_multispectral_dispersion.md`]** El unwrapping
   (2b.i) tiene precedente directo a adaptar: `shen2025` (agregado a
   `references/bibliography.yaml`). La recuperación de n(λ) (2b.ii) no
   apareció publicada en la búsqueda (no exhaustiva, sin acceso a bases
   pagas) — sigue siendo la apuesta de mayor originalidad del proyecto.
   También surgió CWMFP (multiplexado espectral acoplado, propósito
   distinto al nuestro) y una revisión general ("Ptychography at all
   wavelengths", Nat. Rev. Methods Primers 2025) no leída en profundidad,
   útil como contexto de estado del arte si hace falta antes de escribir
   un eventual paper/reporte de 2b.

### A1 modelo directo independiente (auditoría 2026-09-21)

Ataca el hallazgo A1: el "GD 0.995 contra WF 0.076" con k exacto genera los
datos con `jc.simulate_lr_stack_continuous`, el mismo operador que invierte
GD. `scripts/audit_independent_forward_model.py` (datos crudos en
`data/audit_independent_forward_model.jsonl`) genera los datos con un modelo
que no comparte discretización con ningún solver: objeto sobremuestreado x3
(interpolación bicúbica), tilt del LED en el espacio real a k continuo,
pupila con borde de coseno alzado (1 bin) y píxel de cámara que integra
intensidad (5x5 sub-muestras). `selfcheck` lo valida: con esas tres
diferencias apagadas coincide con el operador de GD (diferencia 0.0000); el
modelo completo difiere de él en 6.8% (phantom) y 7.3% (Lena/Map) de RMS
relativo en intensidad.

Condiciones: green, 9x9 LEDs, recorte de 16 px, canvas 48x48, 100 iteraciones
por solver, posiciones VERDADERAS para todos (sin calibración), 1 core. Sin
ruido: 1 corrida por objeto. Poisson a pico 1000: **3 semillas** (0, 1, 2) por
objeto. Nada se sintonizó acá: GD con `lr` 0.02 (el que se entrega) y 0.01;
WF con `step_max` 2, 5 y 20 (20 = hitos 11-14; 2 y 5 = candidatos de
`audit_wf_tuning_and_gd_ablation.py`).

Correlación de fase, media de 3 semillas a pico 1000 (entre corchetes, sin
ruido, n=1):

| Objeto | Datos | GD lr 0.02 | GD lr 0.01 | WF s2 | WF s5 | WF s20 |
|---|---|---|---|---|---|---|
| phantom | A mismo operador, k exacto | 0.951 [0.995] | 0.958 [0.982] | 0.09 | 0.04 | 0.05 |
| phantom | B independiente, k exacto | **0.748** [0.776] | 0.717 [0.737] | -0.12 | -0.12 | -0.03 |
| phantom | C independiente, k a bin | 0.084 | 0.051 | 0.10 | 0.13 | 0.25 |
| phantom | D modelo de WF, k a bin | 0.994 | 0.995 | 0.60 | 0.68 | 0.96 |
| Lena/Map | A mismo operador, k exacto | 0.447 [0.539] | 0.381 [0.423] | 0.08 | 0.09 | 0.03 |
| Lena/Map | B independiente, k exacto | **0.384** [0.396] | 0.321 [0.371] | 0.10 | 0.09 | 0.02 |
| Lena/Map | C independiente, k a bin | 0.195 | 0.173 | 0.11 | 0.15 | 0.18 |
| Lena/Map | D modelo de WF, k a bin | 0.286 | 0.234 | 0.21 | 0.26 | 0.23 |

Lectura:
- **El 0.995 era un techo del inverse crime.** En el phantom, GD baja de 0.995
  (sin ruido, mismo operador) a 0.776 con el modelo independiente, y a 0.748 a
  pico 1000 (0.951 con el mismo operador): la caída atribuible al desajuste de
  modelo es ~0.2. En Lena/Map casi no cae (0.447 a 0.384 a pico 1000), porque
  ahí el techo con el mismo operador ya es bajo (0.45-0.54) y lo limita el
  objeto, no el modelo.
- **GD sigue ganándole a WF con k exacto y modelo independiente**: 0.75 contra
  -0.12 a 0.0 (phantom) y 0.38 contra 0.02-0.10 (Lena/Map). La ventaja no se
  reduce a la coincidencia de operador. Pero WF es el solver cuyo modelo (k
  redondeado a bin) no coincide con datos de k exacto, así que ese contraste
  sigue midiendo en parte "modelo de posición correcto contra incorrecto".
- **La posición manda más que el operador**: con el mismo modelo independiente
  pero k redondeado a bin (C) GD cae a 0.08 (phantom) y 0.20 (Lena/Map). Esto
  refuerza el hito 16: la exactitud de la posición de los LEDs es la incógnita
  dominante con hardware real.
- **WF solo es competitivo en su propio modelo (D)**: 0.96 con `step_max` 20 en
  el phantom, donde iguala a GD (0.994). Ahí GD no pierde, pero WF con
  `step_max` 2-5 sí (0.60-0.68), por lo que el `step_max` sí importa (A2).

Salvedades:
- 3 semillas a pico 1000 y 1 sin ruido; solo phantom y Lena/Map, un canal
  (green), un recorte (16 px), un solo pico. Las desviaciones entre semillas
  son chicas (<0.05), pero con n=3 no son intervalos de confianza.
- Independiente no es realista: comparte con GD la misma definición de k y de
  pupila hasta el borde, y sigue siendo una simulación numérica, no un
  microscopio. Es un modelo más distinto, no el más distinto posible. No
  incluye aberraciones, ruido de lectura ni error de posición.
- Los WF están con 100 épocas y sin `adaptive_step`; el WF nunca alcanza su
  techo en B (correlaciones ≈0 con k exacto), lo que dice poco de cuánto rinde
  bien afinado en datos reales.
- Las diferencias entre `lr` 0.02 y 0.01 (~0.03-0.06) son del orden del ruido
  entre semillas; no se elige uno.
- `phase_correlation` de la inicialización es NaN (fase cero); se omite.

## 5. Traspaso de la sesión nocturna autónoma (2026-09-22, 00:34–~02:50)

El usuario pidió seguir explorando sin supervisión durante ~5 horas; se
cerró antes (~2h20m) por indicación del advisor, con margen de sobra.
**Chequeo final antes de cerrar**: `pytest` no estaba instalado en este
entorno (solo numpy/pillow/pyyaml/scipy) — instalado (`pip install pytest`)
y corrida la suite completa después de los edits de la noche
(`scripts/plan_p4_led_position_error.py`, `scripts/plan_p3_object_phase_geometry.py`,
`scripts/coupled_opl_ceiling_sweep.py` nuevo; ningún cambio en `src/`):
**178 tests, todos pasan, sin regresiones** (21m23s,
`PTYCO_DATA_SOURCE` configurado). No se corrió `scripts/reproduce.sh` (la
puerta de procedencia completa) por tiempo — nada de lo tocado esta noche
afecta esa cadena, pero queda sin verificar formalmente.

Commits locales de esa ventana, **ninguno pusheado** (`origin/main` sigue en
`63eae1f`; hay que revisar y correr `git push` a mano):

1. `63eae1f` — P1/P3 (error de posición de LEDs) ampliados a 4 semillas.
2. `9866908` — fix de `NameError` con `multiprocessing.Pool` en Windows
   (`spawn` vs `fork`) en `plan_p4_led_position_error.py`.
3. `c8f906d` — P2/P4 corridos (resultado inconcluso por diseño, documentado).
4. `64d297c` — mismo fix de `multiprocessing` en `plan_p3_object_phase_geometry.py`.
5. `12dc5ce` — hito 19: techo de fase (GD-amplitude) y piso de contraste de
   amplitud.
6. `ad1ba17` — hito 20: techo de la cadena acoplada completa
   (`couple_rgb_channels`) con el solver real; corrige también la lectura
   del hito 19 por encima de π (artefacto de envolvimiento en `metrics.py`).
7. `2e9e176` — hito 21: el colapso a contraste 0% es un problema de cuenca
   de atracción (init), no del paisaje de optimización — arrancar en la
   verdad converge perfecto, una perturbación de fase chica no rescata nada.
8. `a4f1b86` — primer borrador de esta nota de traspaso.
9. `d2b9a2e` — **corrige el hito 20**: ni el refinamiento TV (probado
   `refine=True` contra `False`, resultado idéntico bit a bit — el
   refinamiento resulta estar completamente sin usar en
   `couple_rgb_channels`, ver docstring) ni el pistón (chequeado,
   coincide con la media circular) explican la pérdida al acoplar. El
   mecanismo real: un puñado de píxeles con número de envolvimiento
   espurio (0.3-2.5% a escala baja) inyectan errores enormes de OPL que
   dominan la correlación de Pearson sobre toda la imagen — excluirlos
   muestra que acoplar en realidad **gana** contra lo ingenuo para WF.
   Para GD el hallazgo original se sostiene (90% de píxeles con `k≠0`
   incluso sin necesitarlo — ruido extendido, no outliers raros).
10. `3a69987` — agrega `corr_coupled_masked` como métrica permanente del
    script (formaliza el diagnóstico del punto 9).
11. `47239be` — confirma el punto 9 con el barrido completo de 4 semillas:
    enmascarar gana limpio para WF en escala 1/2/4 (0.80/0.88/0.93,
    fracción enmascarada ≤20%); en escala 8+ la fracción salta a 68-93%
    y enmascarar pasa a ser la peor métrica (ya está tirando señal real,
    no solo ruido). Para GD, enmascarar ayuda pero nunca llega a bueno
    (fracción enmascarada 88-97% siempre, sin transición limpia).
12. `117ddea` — corrige una afirmación imprecisa sobre `crop=32` que se
    había colado en el commit anterior (el chequeo real era mixto:
    ayudaba a lo acoplado, empeoraba lo ingenuo).

**Para retomar en otra máquina**: `data_source/` (con `Lena_512.png` y
`Map_512.tiff`) vive **fuera del repo**, en una carpeta hermana
(`Documents/data_source/` en esta máquina) — no está en git. Sin ella,
cualquier script que use `lena_map` falla con `FileNotFoundError`. Hay que
copiarla a mano o apuntar `PTYCO_DATA_SOURCE` a donde esté. También hace
falta configurar la identidad de git local (`git config user.name/email`)
en cada máquina nueva — no hay `.gitconfig` global en esta.

**El hilo que estaba "en curso" al escribir el primer borrador de esta nota
ya se resolvió** (era exactamente los puntos 9-12 de arriba) — ver hito 20
en la sección 3 para el resultado completo, no repetido acá.

**Hilos abiertos, no atacados esta noche** (quedan en el roadmap, priorizar
si se retoma, ningún orden implícito salvo el primero):
- **La reconstrucción ingenua (sin acoplar) de GD-amplitude en el objeto del
  hito 20 (crop 16, bump oscilante, grid 9×9) es mucho peor que la de WF
  ahí** (0.04-0.20 contra 0.66-0.89 a escala baja) — lo opuesto de los
  hitos 11-19, donde GD solía ganar. Un chequeo de una sola celda con
  crop 32 dio mixto (ayudó a lo acoplado, empeoró lo ingenuo), así que no
  está resuelto si es el crop, el objeto, o algo específico de esta
  geometría. Es la salvedad más grande que quedó sin cerrar.
- Usar `pair_disagreement` (que `couple_rgb_channels` ya calcula y
  devuelve, documentado como "diagnóstico de confianza por píxel") para
  enmascarar o ponderar de forma automática en vez del filtro binario
  ad hoc de esta noche (`K1≠0 or K2≠0`) — la mejora concreta más barata
  identificada, no implementada.
- P2/P4 rediseñados correctamente (ver salvedades del hito 18).
- Confirmar la degeneración A/B/t con datos que pasen por el solver real
  (hoy solo probada con OPL inyectado).
- Por qué el ruido de conteo del init "default" empuja de forma consistente
  a un atractor malo en vez de solo agregar varianza (hito 21).
- Si el problema de cuenca del hito 21 aparece también a contraste bajo
  pero no cero (2-5%), o es específico de contraste exactamente cero.

**Patrón que se repitió tres veces esta noche, vale tenerlo presente**: un
resultado inicial sorprendente (P1/P3→P2/P4, el techo de fase, el colapso
de inicialización, "acoplar empeora") resultó tener un problema de
metodología (convención de forward model mezclada, métrica que envuelve mal
por encima de π, o una métrica sin robustez a outliers) que cambiaba la
conclusión real. Ninguno de los hallazgos que sobrevivió esta noche se tomó
al pie de la letra en su primera corrida — todos se verificaron con al
menos una corrida de control antes de escribirse. Vale seguir con esa
disciplina si se retoma cualquiera de los hilos de arriba.

## 6. Primera validación con datos reales de laboratorio (2026-09-22)

Hasta esta sesión, absolutamente todo el trabajo del proyecto (milestones
1-21, la auditoría adversarial, la sesión nocturna autónoma) corrió sobre
datos **sintéticos** — ninguna captura TIFF real había pasado nunca por
`pipelines/reconstruct_real_images.py`,
`pipelines/reconstruct_multispectral_independent.py` ni
`pipelines/reconstruct_multispectral_coupled.py` (ver sección 1 y el cierre
de la sección 5). Esta sesión usó la primera captura real disponible:
`/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2025-12-12/organizado`
(grid 9x9, `crop=400`, los 3 canales red/green/blue con 81/81 LEDs cada
uno).

### 6.1 Bug encontrado y corregido antes de poder cargar los datos

La convención asumida por `io_utils.py`
(`fila<R>_columna<C>.tiff`, un único `index_base` compartido entre fila y
columna) no coincidía con la captura real en dos puntos independientes:

- Los archivos se llaman `fila<R>_col<C>.tiff`, no `fila<R>_columna<C>.tiff`.
- Las filas numeran 13-21 y las columnas 11-19 para el mismo escaneo 9x9 —
  bases distintas por eje, algo que `LEDArrayConfig` no podía representar
  (asumía `index_base` único, usado tanto para el rango de filas como el de
  columnas al calcular la posición física de cada LED).

Antes de tocar código, se confirmó de forma independiente cuál es el LED
sobre el eje óptico usando los propios metadatos del laboratorio
(`green/leds_por_tiempo_17.100.json`, que agrupa LEDs por tiempo de
exposición — los de exposición más corta son los más brillantes, es decir
los más cercanos al eje): el bucket de exposición más corta es
`[[16,15],[17,15],[18,15]]`, centrado exactamente en fila=17, columna=15 —
el centro geométrico de la ventana 9x9 (13+4=17, 11+4=15). Esto confirmó
que la ventana capturada SÍ está centrada en el eje óptico, solo que fila y
columna se numeran desde esquinas distintas, antes de generalizar el
código (evitando adivinar la calibración física a ciegas).

Corregido en el commit `56d9ae6` ("Support asymmetric LED row/col index
bases and add a real-HR-reference correlation tool"): `LEDArrayConfig`
gana `row_index_base`/`col_index_base` (caen de vuelta al `index_base`
compartido si no se pasan) y las propiedades `row_base`/`col_base`/
`center_row`/`center_col`; `led_array.py` usa `center_row`/`center_col`
por separado en vez de un único `center_index`; `io_utils.load_real_lr_stack`
prueba ambas grafías de nombre de archivo; los 3 scripts de datos reales
ganan `--row-index-base`/`--col-index-base`. 196 tests recolectados en el
árbol de trabajo actual (`python3 -m pytest --collect-only -q tests/`),
incluyendo 12 tests nuevos de geometría (`tests/test_real_capture_index_base.py`)
y 6 de la herramienta de correlación de la sección 6.3
(`tests/test_metrics.py`).

### 6.2 Primeras reconstrucciones reales (Wirtinger flow, milestone 2a)

`pipelines/reconstruct_multispectral_independent.py`, solver `wirtinger`,
`--row-index-base 13 --col-index-base 11`:

- **20 iteraciones** (`results/real_run1_2025-12-12/`): mejora relativa
  minúscula en los 3 canales (~0.25-0.3%); la fase queda completamente
  plana (`std=0.0` en los PNG de fase guardados) — el solver prácticamente
  no movió la fase todavía.
- **200 iteraciones** (`results/real_run2_iter200_2025-12-12/`): mejora
  relativa ~3.7-4.1%, pero el error **sigue bajando en el 100% de las
  épocas** (`fraction_of_epochs_that_improved: 1.0`), sin señal de
  plateau — no convergió. La fase recién empieza a moverse pero queda muy
  chica (`std` ~0.3-0.4 sobre un rango 0-255 que mapea a 2π, es decir unos
  pocos centésimos de radián). 13m30s de tiempo de pared para los 3
  canales en esta máquina.

Esto coincide con la salvedad ya documentada en los milestones 2a/2b sobre
convergencia lenta de fase débil, pero es la primera vez que se observa
sobre datos reales ruidosos en vez de sintéticos — el efecto es
notablemente más marcado de lo visto en sintéticos.

### 6.3 Nuevo método de validación: referencia HR real, y un hallazgo contraintuitivo

El usuario compartió una imagen de referencia real de alta resolución
(`/home/chanoscopio/Documents/AleYLu/elefante_referencia_recortada_400/img_mov_alineada_recortada_1120.tif`,
400x400, float32, una captura bien enfocada de amplitud de la muestra real)
— la primera verdad de referencia real con la que contó el proyecto (hasta
ahora todo `compare_to_ground_truth` corría contra fantasmas sintéticos).
Nueva herramienta `metrics.correlate_against_hr_reference()` (commit
`56d9ae6`): redimensiona (Lanczos) la referencia a la grilla de la
reconstrucción, normaliza ambas (z-score) y correlaciona probando las 4
combinaciones de volteo vertical/horizontal, devolviendo la mejor —
pensado específicamente para poder chequear por primera vez si la
convención de ejes fila/columna del forward model coincide con la cámara
real, algo que antes no había forma de verificar.

**Resultado**: ningún volteo fue necesario para la mejor correlación en
ningún canal — confirma que la convención de ejes del forward model
coincide con la cámara real. Correlaciones: 20 iteraciones
red/green/blue = 0.691/0.725/0.743; 200 iteraciones
red/green/blue = 0.666/0.697/0.713.

**Actualizado (mismo día, sweep de seguimiento): el hallazgo dejó de ser
abierto, se confirmó con 4 puntos y se generalizó.** Sweep en el canal
green (único canal con múltiples puntos de iteración; el resto son de
las corridas de 3 canales ya citadas), usando
`scripts/sweep_real_reconstruction_quality.py` (nueva herramienta
reusable) más dos variantes de solver corridas aparte:

| corrida | mejora interna (`relative_improvement`) | correlación vs. referencia real |
|---|---|---|
| WF 20 iter | ~0.25-0.3% (los 3 canales) | red 0.691 / green 0.725 / blue 0.743 |
| WF 50 iter (green) | 0.83% | green 0.721 |
| WF 200 iter | ~3.7-4.1% (los 3 canales) | red 0.666 / green 0.697 / blue 0.713 |
| WF 600 iter (green) | 11.8% | green 0.602 |
| `--recover-pupil` 200 iter | 0.19% / 0.06% / **-0.33%** (blue empeoró cada época) | red 0.691 / green 0.726 / blue 0.744 |
| `--adaptive-step` 400 iter | ~0.05% (los 3 canales) | red 0.692 / green 0.726 / blue 0.745 |

Con 4 puntos de WF puro (20/50/200/600 iteraciones) la correlación baja
**monótonamente** (0.725 → 0.721 → 0.697 → 0.602) mientras la mejora
interna sigue subiendo (0.3% → 0.83% → 3.9% → 11.8%) — ya no es ruido de
la métrica, es una tendencia clara en un rango de 30x en iteraciones.
Además, `--recover-pupil` y `--adaptive-step` en estas configuraciones
apenas movieron el residuo interno (igual de poco que WF a ~20
iteraciones) y sus correlaciones caen justo donde caería WF a esas pocas
iteraciones -- **no hay evidencia de que sean "mejores algoritmos" acá**;
lo que se observa es consistente con que TODAS las corridas, sin importar
el mecanismo, caen sobre la misma curva "cuanto menos se movió el residuo
interno desde el arranque, mejor correlaciona con la verdad real" (ver
6.7 para la lectura unificada).

### 6.4 Diagnóstico cromático sobre datos reales

Primera corrida real de
`chromatic_diagnostics.chromatic_registration_report` (`--chromatic-report`;
la herramienta se construyó el 2026-09-18, ver sección 4 pregunta 2, y
hasta ahora nunca había tenido datos reales para correr con sentido).
Señal consistente entre las corridas de 20 y 200 iteraciones (dos
reconstrucciones independientes):

- **red vs green**: ~0 corrimiento lateral, pero desenfoque repetible de
  -25 a -27.5 µm (`corr_at_offset` 0.76-0.81 vs. `corr_at_zero` 0.75-0.80
  — señal real pero débil, consistente en signo y magnitud entre las dos
  corridas).
- **blue vs green**: ~0 corrimiento lateral Y ~0 desenfoque, correlación
  alta (0.89-0.92).

Lectura tentativa, no confirmada: posible aberración cromática axial real
entre red y green específicamente (no entre blue y green). Dado que la
reconstrucción todavía no convergió bien (sección 6.2), y el propio
docstring del módulo advierte que la precisión de este diagnóstico depende
de la calidad de la reconstrucción que mide, esto necesita reconstrucciones
mejor convergidas antes de confirmarse.

### 6.5 gd-amplitude: ~10-20x más lento que WF -- es el costo real de su ventaja, no un bug

`--solver gd-amplitude` (100 iteraciones, mismos datos) se mató a los 77
minutos sin haber terminado ni el primer canal de 3 (`reconstruct_all_channels`
no guarda nada a disco hasta que terminan los 3 canales, así que esta
corrida no dejó ningún resultado de calidad de reconstrucción utilizable
-- solo el dato de tiempo de pared, usado abajo). Contra 13.5 minutos que
tardó `wirtinger` en los 3 canales completos a 200 iteraciones, es una
desaceleración por iteración de ~10-20x que el texto de ayuda del CLI
("Use ~100 --iterations") no anticipa.

**Primer diagnóstico (solo lectura) e intento de corrección -- corregido
más abajo, no tomar la primera lectura como conclusión final**:
`joint_calibration.py` hace su forward/backward pass **en espacio real a
resolución HR completa por cada LED y cada iteración** (líneas ~128-131 y
~150-158: arma un `tilt` complejo sobre la grilla HR entera de 1200x1200,
una `fft2` HR completa por LED), mientras que `reconstruction.py` (WF)
mantiene un único espectro HR persistente y por cada LED solo recorta la
ventana LR (`reconstruction.py:175`, `:187-190`). Medido de forma aislada:
~22x de sobrecosto por LED, que coincide con la brecha observada. La
primera lectura concluyó que era "una ineficiencia de implementación, no
un costo inherente" y propuso adoptar el truco de recorte de WF.

**Se intentó ese cambio en un segundo pase y se DETUVO antes de tocar
código, tras verificar por qué el diseño actual es así**: el propio
docstring de `joint_calibration.py` (líneas ~13-19 y ~277-285) explica que
existe específicamente para EVITAR el redondeo que sí hace el recorte de
WF -- `spectral_ops.led_crop_window` (`spectral_ops.py:34-35`) redondea el
k de cada LED al bin de FFT HR más cercano (`int(round(...))`);
`joint_calibration.py` aplica el tilt en espacio real con k **continuo**
(sin cuantizar) precisamente para poder evitar esa pérdida de precisión
sub-bin. El propio docstring cita el número que sustenta el diseño: con k
exacto/continuo este solver da 0.995 de correlación de fase contra 0.076
de WF; forzado al mismo grid redondeado a bins que usa el truco de
recorte, la correlación cae a **0.09** -- una regresión de ~10x, justo en
el régimen (posiciones físicas de LED reales, no cuantizadas) que es la
razón de ser de este solver sobre hardware real. Verificado leyendo
`spectral_ops.py:24-47` directamente, no solo el docstring.

**Conclusión corregida: la lentitud es el costo real y documentado de la
ventaja de precisión de gd-amplitude, no un bug de implementación libre de
arreglar.** No se tocó el código. Camino legítimo para acelerar sin perder
precisión de k continuo, anotado para el futuro pero fuera de alcance de
esta sesión: una NUFFT / chirp-Z transform (lectura de frecuencia
fraccionaria exacta desde un único espectro HR persistente, en vez de
recorte por índice entero) -- técnica genuinamente distinta con su propio
error de interpolación a caracterizar, no un ajuste trivial. Este es
exactamente el patrón de la sección 5: el primer diagnóstico sorprendente
("es solo un bug") no sobrevivió una verificación más profunda antes de
tocar la ruta de reconstrucción científica.

### 6.6 Primera corrida acoplada real (milestone 2b, `--qc`)

`reconstruct_multispectral_coupled.py`, mismos datos, `--qc` (dry-run, sin
llamada real a la API), `--chromatic-report`. 10m22s de pared.

- Diagnóstico cromático: red vs green desenfoque -25.00µm
  (`corr_at_offset=0.792` vs `corr_at_zero=0.779`), blue vs green ~0 —
  **tercera medición independiente** (20-iter, 200-iter, y esta corrida
  acoplada) que da el mismo número para red-green, reforzando que es una
  señal real y no ruido de una sola corrida.
- `pair_disagreement` (red_green/green_blue, el diagnóstico de confianza
  por píxel que `couple_rgb_channels` ya calculaba pero el roadmap tenía
  como "no explotado" en la sección 5): mean 0.0003µm, max ~0.0045µm en
  ambos pares — **sospechosamente bajo, no necesariamente bueno**. Dado
  que la fase todavía casi no se movió (sección 6.2: excursión de unos
  centésimos de radián), es esperable que los canales "no disientan" entre
  sí trivialmente, no porque el acople esté funcionando bien. El QC agent
  (dry-run, heurística canned) dio `confidence=high, recommendation=report`
  — **este veredicto probablemente es engañoso** por la misma razón: una
  heurística de bajo disagreement no distingue "acople genuinamente bueno"
  de "no hay señal de fase todavía para disentir". No tomar el veredicto
  del QC agent al pie de la letra sin reconstrucciones mejor convergidas
  primero, siguiendo la misma disciplina de esta sección para cualquier
  resultado que parezca demasiado bueno de entrada.
- No se registró ningún ajuste de dispersión C/D (`baseline_index` no se
  pasó) — solo quedaron el reporte cromático y las métricas de
  disagreement en `results/real_run4_coupled_2025-12-12/`.

### 6.7 Lectura unificada, y una salvedad importante encontrada al refinar el sweep

La tabla de la sección 6.3 sugiere algo más general que "más iteraciones
empeoran la amplitud": en las 6 corridas (WF a 20/50/200/600 iteraciones,
`--recover-pupil` a 200, `--adaptive-step` a 400), **la correlación contra
la referencia real cae de forma consistente con cuánto se movió el
residuo interno**, sin importar qué mecanismo produjo ese movimiento. La
primera lectura de esto fue **semi-convergencia** (fenómeno bien
documentado en problemas inversos mal condicionados resueltos con métodos
iterativos -- Landweber, ART, y similares, ver p. ej. Hansen, *Discrete
Inverse Problems*: las primeras iteraciones recuperan la señal verdadera,
las siguientes empiezan a ajustar ruido de los datos).

**Salvedad encontrada después, con `scripts/sweep_real_reconstruction_quality.py`
recién construido: un sweep fino (0/1/3/5/10/15/20/30/40 iteraciones,
green) muestra que la correlación YA es máxima en la iteración 0 -- el
objeto inicial, antes de cualquier paso del solver -- y decae de forma
monótona y suave desde ahí (0.7268 en iter 0-1, 0.7225 en iter 40).**
Investigando por qué el objeto inicial ya correlaciona tan bien:
`reconstruction.initial_hr_guess` (`reconstruction.py:33-43`) es
literalmente la imagen capturada por el LED central (on-axis), sobre-
muestreada por vecino-más-cercano -- una foto real de baja resolución del
objeto, del mismo tipo que la referencia. Y la propia referencia
(`img_mov_alineada_recortada_1120.tif`) es **400x400 nativo, la MISMA
resolución que el crop de cámara LR** (`--crop 400`), sobremuestreada a
1200x1200 solo para poder compararla contra la grilla HR -- no tiene
ningún detalle real más allá de esa resolución nativa.

Esto abre una segunda explicación, al menos igual de plausible que la
semi-convergencia y **no descartada todavía**: la reconstrucción por
apertura sintética existe específicamente para ganar resolución más allá
del píxel de cámara LR -- si WF está agregando detalle fino genuino (el
objetivo real del algoritmo), la correlación contra una referencia que
**no tiene ese detalle para empezar** va a bajar sin importar si el
detalle nuevo es señal real o ruido, porque la métrica no puede
distinguir entre ambos casos a esa escala. En otras palabras: esta
referencia en particular sirve para validar que la reconstrucción no se
fue por las ramas en estructura gruesa (y para eso ya sirvió -- confirmó
la convención de ejes en 6.3), pero **no puede confirmar ni descartar por
sí sola si las iteraciones adicionales están mejorando o empeorando la
reconstrucción a la escala fina que WF está diseñado para recuperar**.

**Conclusión, con las dos lecturas sobre la mesa sin resolver entre
ellas**: sobre datos reales, `metrics.convergence_summary` sigue sin ser
un proxy confiable de precisión real contra esta referencia externa
(apunta en la dirección contraria a la correlación, sea cual sea la causa
de fondo) -- eso se sostiene igual bajo cualquiera de las dos lecturas, y
sigue siendo la salvedad relevante para el veredicto del QC agent en 6.6.
Pero "correr menos iteraciones" NO se sigue automáticamente de este
hallazgo sin antes resolver la ambigüedad -- podría estar recomendando
exactamente lo contrario de lo correcto si la lectura de resolución es la
que manda. **Siguiente paso necesario, no opcional, antes de actuar sobre
este hallazgo**: conseguir o construir una referencia a la resolución HR
real (más allá de 400x400 nativo -- p. ej. una captura de mayor aumento/NA
del mismo target, o comparar contra la resolución que predice la apertura
sintética del propio montaje) para poder separar estas dos hipótesis.

**Otras salvedades sin cerrar**: n pequeño, mayormente un solo canal
(green) y un solo punto para `--recover-pupil`/`--adaptive-step`; no se
sabe si muestran la misma curva en su propio eje de iteraciones. No
tratar ninguna de las dos lecturas como establecida todavía -- exactamente
el patrón que ya se repitió tres veces en la sección 5 y una vez en 6.5
esta misma sesión: la primera explicación de un hallazgo sorprendente no
sobrevivió el siguiente control.

**Actualización 2026-09-23 (ver 6.8)**: la ambigüedad queda mayormente
resuelta a favor del límite de la referencia -- resultó ser una toma Zeiss
2.5x/0.075 con *menos* alta frecuencia que una sola captura LR. Matiz: en la
grilla LR 400x400 (sin nada por encima del Nyquist LR) persiste una caída
chica (0.740 -> 0.733 con `2x_na010` a 200 it), así que algo cambia también
dentro de la banda que la referencia sí ve.

### 6.8 Procedencia de la referencia, objetivo equivocado y calibración del sistema (2026-09-23)

Tres hallazgos, en orden de solidez: la procedencia de la referencia
(verificada), el objetivo equivocado en todas las corridas reales
(confirmado por el usuario, pero su corrección casi no cambia nada), y
una calibración del sistema que no cierra con los valores nominales
(indicios, no confirmado).

**1. Procedencia de la referencia (verificada).** En
`~/Documents/AleYLu/` conviven dos archivos de nombre parecido:

- `img_ref_recortada_1120.tif` **es la captura FPM on-axis de verde**
  (`fila17_col15`) -- correlación cruzada 1.000. Es la imagen *fija* del
  registro, no una referencia.
- `img_mov_alineada_recortada_1120.tif` (la referencia usada en 6.3-6.7)
  es el tile Zeiss `elefante/2025-12-02/3x3` registrado sobre la grilla de
  la cámara FPM: se lo encuentra dentro del tile con NCC 0.896 a escala
  0.745, columnas invertidas y ~2° de rotación. Metadatos del tile:
  objetivo activo posición 6 = **Plan-Neofluar 2.5x/0.075**, tubo 1.0x,
  **2.344 µm/px** en muestra. La torreta también tiene montados un
  N-Achroplan 10x/0.25 y un EC Plan-Neofluar 63x/1.25 Oil, no usados.
- Espectro de potencia radial (en fracción del Nyquist LR): la captura FPM
  mantiene señal hasta el Nyquist (-27 dB en el borde); la referencia cae
  mucho más rápido y toca un **piso de ruido de ~-43 dB desde ~0.7 del
  Nyquist LR** -- firma de una imagen de píxel más grueso sobremuestreada.
  Tiene *menos* alta frecuencia que una sola captura LR.

Consecuencia: **esta referencia no puede validar superresolución**, ni
siquiera la resolución LR completa. Cierra con los números de 6.7: la
iteración 0 (captura on-axis sobremuestreada) da 0.727 contra la
referencia, y la captura cruda contra la referencia da 0.706 -- la "mejor
reconstrucción" era la foto LR. Una referencia genuina tendría que ser un
mosaico Zeiss con el 10x/0.25 (~0.59 µm/px) sobre el mismo FOV; el límite
de RAM aplica a la pila LR, no a la referencia.

**2. Objetivo equivocado en todas las corridas reales (confirmado).** El
usuario confirmó que la captura 2025-12-12 se tomó con el objetivo
**2x/NA 0.10**, píxel de cámara 3.2 µm, sin nada entre objetivo y cámara.
Todas las corridas reales previas (`results/real_run1..4`, `sweep_*`)
usaron el default `current` = 2.5x/0.07 -- aumento y NA equivocados.
Corregido en código: presets renombrados a `2x_na010` (nuevo default de
`default_setup` y de los CLIs de datos reales) y `2_5x_na007`; `current`
y `future` quedan como alias deprecated (mismos objetos); todo lo
sintético con números registrados (incluida la cadena de
`scripts/reproduce.sh`) fija `2_5x_na007` explícito, así que no cambia.
Test nuevo: `tests/test_objective_presets.py`.

**3. Chequeo independiente de aumento/NA, sin el Zeiss
(`results/mag_check_2025-12-12/summary.json`).** El registro con el Zeiss
implicaba ~1.75 µm/px en muestra, 9% más que los 1.60 esperados con 2x.

- *Corte del espectro de intensidad* (espectro promedio sobre todos los
  LEDs; el soporte en intensidad está acotado por 2NA/λ sin importar la
  iluminación): en rojo (630 nm) el corte está en r_c = 690 px
  (680-700) -> **NA·px_muestra = 0.194 ± 0.003 µm**. Verde y azul no
  muestran corte antes de la esquina de 792 px, consistente con el
  escalado 1/λ (predicho ~820 y ~925 px). Control: un artefacto de sensor
  caería al mismo radio en los tres colores; solo rojo muestra la rodilla
  -> es óptico.

  | hipótesis | NA·px predicho (µm) | veredicto |
  |---|---|---|
  | `current` 2.5x/0.07 (px 1.28) | 0.090 | descartado (factor 2.2) |
  | 2x/0.10 nominal (px 1.60) | 0.160 | no cierra (medido 21% más alto) |
  | px del registro Zeiss (1.746) + NA 0.10 | 0.175 | 11% bajo |
  | NA implícita con px 1.746 | 0.111 | -- |
  | NA implícita con px 1.60 | 0.121 | -- |
  | px implícito con NA 0.10 | 1.94 (aumento 1.65x) | choca con el registro |

  Lo más consistente: **aumento ~1.83x con NA ~0.11**. Un aumento
  distinto del nominal es plausible sin lente de tubo (depende de la
  distancia real objetivo-sensor).
- *Mapa campo claro/campo oscuro* (mediana/exposición, 13x13 verde): la
  transición es gradual (~3 dB por paso de LED, sustrato muy difusor), sin
  escalón. La meseta a -3 dB tiene radio ~2.0 pasos; con NA 0.10-0.11 eso
  pide sinθ/paso ~0.055, pero la geometría del config (pitch 6 mm, altura
  70 mm) da 0.0857 -> radio de campo claro de solo 1.2-1.3 pasos. **La
  geometría de LEDs del config queda sospechosa** (criterio blando). La
  meseta parece centrada en fila 17.5 / col 14.7 en vez de (17, 15), y el
  LED más brillante (en brillo/exposición) es el (18, 15): posible
  descentrado de ~medio LED, sin confirmar.
- *Desplazamiento del disco de pupila por LED* (para separar NA de
  aumento): no concluyente -- bordes de ~150 px de ancho, ajustes
  inestables con esta muestra dispersiva.

**4. Rerun de verde con `2x_na010` (`results/sweep_green_future/`,
`results/real_run5_future_2025-12-12/`).** *(Ver 6.9: estas corridas, como
todas las reales previas, tenían el solver congelado -- miden la estimación
inicial, no el solver.)* Corre sin cambios de código:
factor de upsampling 5, grilla HR 2000x2000, píxel HR 0.32 µm (vs 3,
1200x1200, 0.427 µm con `current`), ~3 s/iteración.

| objetivo | it | corr. grilla HR | corr. grilla LR 400 | std fase (rad) | energía amp. > 0.377 ciclos/µm |
|---|---|---|---|---|---|
| `2x_na010` | 0 | 0.7267 | 0.7397 | 0 | 3.5% |
| `2x_na010` | 20 | 0.7256 | 0.7391 | 0.0003 | 3.6% |
| `2x_na010` | 50 | 0.7236 | 0.7382 | 0.0008 | 3.9% |
| `2x_na010` | 200 | 0.7112 | 0.7329 | 0.0042 | 5.8% |
| `2_5x_na007` | 0 | 0.7268 | 0.7389 | 0 | 3.7% |
| `2_5x_na007` | 20 | 0.7250 | 0.7379 | 0.0006 | 3.9% |
| `2_5x_na007` | 200 | 0.6966 | 0.7251 | 0.0089 | 8.6% |

(0.377 ciclos/µm = 2·0.10/0.53 µm. El barrido oficial a 1/3/5/10/20/50/200
it coincide punto por punto: 0.7267/0.7266/0.7266/0.7263/0.7256/0.7236/0.7112;
mejora interna del residuo 11.4% a 200 it, no comparable entre objetivos
porque cambia la pupila.)

**Corregir el objetivo casi no cambia nada**: la curva tiene la misma
forma (máximo en la iteración 0, caída monótona, algo más lenta con
`2x_na010`), y la fase sigue prácticamente quieta (~0.004 rad a 200 it).
El error de objetivo, siendo real, **no explica** el comportamiento de los
datos reales. La caída en la grilla LR 400 (0.740 -> 0.733) es chica pero
indica que algo cambia también dentro de la banda que la referencia ve.

**5. Estado y próximos pasos.** Confirmado: la procedencia de la
referencia y el objetivo equivocado. Todo lo demás son indicios.

- (a) Confirmar con el usuario el pitch real de los LEDs, la altura de la
  matriz sobre la muestra y el centrado.
- (b) Probar aumento 1.83 / NA 0.11 y/o calibración de posiciones de LED
  (con la geometría corregida si (a) la cambia).
- (c) Referencia genuina: mosaico Zeiss 10x/0.25 del mismo FOV
  (~0.59 µm/px), registrado contra la captura on-axis.
- (d) Captura FPM de un target USAF: separa NA de aumento de forma directa
  y da una medida de resolución sin necesidad de referencia.

Mismo hábito que en 5 y 6.5-6.7: el primer candidato ("todo era el
objetivo equivocado") no sobrevivió el control -- se corrigió y la curva
casi no se movió.

### 6.9 El solver estaba congelado en datos reales: paso, exposición y escala inicial (2026-09-23)

Buscando si la geometría corregida (z=76 mm, centro de la matriz estimado,
1.83x/0.11) por fin movía la fase, apareció algo previo a la geometría: con
la configuración por defecto, **WF prácticamente no itera sobre datos
reales**. Tres causas independientes, las tres medidas con control
(`results/led_geometry_2025-12-12/`, scripts copiados ahí).

**1. Paso de WF ∝ 1/N a `step_max` fijo.** `reconstruct` divide el
gradiente espectral por `lr_n_px` (`reconstruction.py:217-222`) y usa
`step_max=20`. El comentario del adjunto es correcto en lo que dice (el
adjunto de `ifft2` es `fft2/N`), pero su consecuencia no estaba registrada:
el paso unitario clásico de ePIE/GS equivale a `step = lr_n_px`, así que a
`step_max` fijo el paso efectivo escala como 1/N. A crop 400
(`lr_n_px`=160000) es **~1/8000 del paso ePIE unitario**. Control sintético
sin ruido, 20 iteraciones, factor 5 (`synthetic_step_size_control.json`):

| crop | paso | mejora relativa | corr. de fase |
|---|---|---|---|
| 16 | default (20) | 0.617 | 0.527 |
| 16 | 0.3·lr_n_px | 0.907 | 0.933 |
| 64 | default (20) | 0.204 | 0.169 |
| 64 | 0.3·lr_n_px | 0.898 | 0.943 |
| 128 | default (20) | 0.051 | 0.227 |
| 128 | 0.3·lr_n_px | 0.904 | 0.945 |

Con paso relativo a ePIE la calidad es independiente del crop; con el
default se degrada monótonamente. Los tests y los hitos sintéticos usan
crops chicos (16-32), donde `step_max=20` todavía es una fracción
razonable del paso ePIE -- por eso nunca se vio.

**2. Datos crudos sin normalizar y estimación inicial mal escalada.**
- La captura usa exposición por LED de 3 a 1000 ms
  (`leds_por_tiempo_*.json`) y el cargador real no la corrige: un LED de
  campo oscuro a 175 ms da media cruda 924 contra 389 del on-axis a 3 ms.
  Además hay un nivel de oscuro de ~188 cuentas (medido con la captura sin
  LEDs), saturación despreciable (<0.04%), y el laboratorio descartó el LED
  (13,17).
- `initial_hr_guess` queda ×factor² respecto del forward model: residuo
  relativo inicial de campo claro 24.3 con la escala por defecto, 0.24
  dividiéndola por factor² (controles `ctl_norm_default_20` vs
  `ctl_norm_scaled_20`). Estaba enmascarado porque el solver no se movía.

**3. Consecuencia.** Todas las corridas reales previas (run1-run5, los
barridos de 6.3/6.7 y el rerun de 6.8.4) **no evalúan el solver**: la
reconstrucción es esencialmente la estimación inicial (fase ~0.004-0.009
rad de excursión). La curva correlación-vs-iteraciones de 6.3/6.7 es la
deriva mínima de un solver congelado sobre datos sin normalizar. Lo que
sigue en pie: la procedencia de la referencia (6.8.1) y el objetivo
equivocado (6.8.2). El diagnóstico cromático (red-green ~-25 µm, 6.4/6.6)
**queda a re-verificar**: se midió sobre reconstrucciones congeladas.

**4. Centro de la matriz.** Ajuste del mapa de radiancia BF/DF (mediana /
exposición, polinomio radial): **fila 17.45 ± 0.1, col 14.65 ± 0.1**
(nominal 17/15), idéntico con z=70 y z=76, con polinomio de orden 2/4/6,
ajuste cuadrático central y jackknife (`center_from_radiance.json`).
`led_calibration.brightfield_calibration` no sirve con esta muestra
dispersiva: según la hipótesis de aumento/NA da escala 0.58-0.97, rotación
5-9° y desplazamiento que cambia de signo (`center_from_bf_calibration.json`).
Confirmación débil independiente: el residuo BF inicial (solo datos) ordena
estimado 0.244 < nominal 0.255 < espejado 0.297.

**5. Variantes con el solver descongelado** (verde; datos normalizados,
estimación inicial /factor², paso 0.3·lr_n_px = 48000, 200 iteraciones;
`variants_summary.json`). Referencia: fase uniforme aleatoria tiene std
1.81 rad.

| variante | std fase (rad) | corr HR / LR400 | residuo todos (ini→fin) | BF | DF |
|---|---|---|---|---|---|
| (d) congelado: crudo, paso 20, 1.83x/0.11 z76 + centro | 0.0075 | 0.719 / 0.741 | 1.97→1.79 | 23.3→21.1 | 0.87→0.79 |
| (a) 2x/0.10 z70 centrado | 1.60 | 0.305 / 0.538 | 0.927→0.280 | 0.255→0.278 | 0.972→0.281 |
| (b) 2x/0.10 z76 centrado | 1.61 | 0.305 / 0.522 | 0.922→0.289 | 0.255→0.294 | 0.966→0.288 |
| (c) 1.83x/0.11 z76 centrado | 1.61 | 0.290 / 0.545 | 0.917→0.278 | 0.255→0.282 | 0.961→0.277 |
| (d_b) 2x/0.10 z76 + centro | 1.60 | 0.309 / 0.524 | 0.930→0.288 | 0.243→0.287 | 0.967→0.288 |
| (d_c) 1.83x/0.11 z76 + centro | 1.63 | 0.293 / 0.551 | 0.926→0.278 | 0.244→0.287 | 0.961→0.278 |
| control espejado 1.83x/0.11 (16.55, 15.35) | 1.65 | 0.288 / 0.543 | 0.927→0.278 | 0.297→0.294 | 0.961→0.278 |
| control espejado 2x/0.10 (16.55, 15.35) | 1.62 | 0.305 / 0.519 | 0.932→0.288 | 0.297→0.293 | 0.966→0.288 |

Lectura: con paso ePIE el solver se mueve y los LEDs de campo oscuro pasan
a ajustar (0.97 → 0.28), pero **todas las geometrías, incluidos los
controles con centro espejado, terminan en el mismo residuo ~0.28**, con
fase de std ~1.6 rad (prácticamente ruido) y amplitud con moteado de alta
frecuencia. A este nivel de ajuste los datos no discriminan geometría y la
reconstrucción no es confiable. La caída de correlación contra la referencia
(0.72 → 0.30) no dice nada sobre superresolución (6.8.1), pero sí es
coherente con una reconstrucción dominada por artefactos. Comparar
residuos entre NA 0.10 y 0.11 no es justo (pupila más grande = más grados
de libertad). **El piso de ~0.28 independiente de la geometría es el
próximo problema** (candidatos: ruido, variación de intensidad por LED,
muestra gruesa/dispersiva fuera del modelo de objeto delgado).

**6. Cambios de código.**
- `2ec3018` (fork E): z=76 mm por defecto en los puntos de entrada de datos
  reales (`REAL_CAPTURE_Z_DISTANCE_MM`; `LEDArrayConfig`/`default_setup`
  siguen en 70 para lo sintético), `LEDArrayConfig.center_offset_mm` y
  flags `--z-distance-mm`, `--led-center-offset-mm DX DY`, `--na`,
  `--magnification` en los 4 CLIs reales; geometría efectiva en el JSON de
  salida.
- Fork G (`7c6fc3c`): normalización de exposición + resta de
  oscuro en el cargador real, corrección de la escala de la estimación
  inicial, y `--step-epie FRACTION` opt-in. **El default del paso NO se
  cambió**: con el solver descongelado la fase sale tipo ruido en datos
  reales, así que es decisión del usuario.

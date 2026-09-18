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

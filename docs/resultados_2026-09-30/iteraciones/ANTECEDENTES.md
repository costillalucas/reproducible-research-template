# Antecedentes: cantidad de iteraciones / épocas (2026-09-30)

Solo lectura del repo. `R` = roadmap `docs/roadmap_agentic_multispectral_pipeline.md`. Hecho con poco
tiempo: lo marcado [INCOMPLETO] no se verificó a fondo.

## 1. Antes del arreglo del paso congelado (NO sirve para concluir)

- **Dic. 2025, WF 20/50/200/600 it, verde** (R:2446-2509, 6.2-6.3): correlación contra la referencia
  0.725 → 0.721 → 0.697 → 0.602 mientras la mejora interna sube 0.3 % → 11.8 %. `--recover-pupil` 200 it y
  `--adaptive-step` 400 it caen sobre la misma curva. A 200 it el error bajaba en el 100 % de las épocas,
  sin meseta (R:2452-2455).
- **Barrido fino 0..40 it** (R:2631-2634, 6.7): el máximo ya está en la iteración 0 (0.7268 → 0.7225 a 40 it).
  Se leyó como semi-convergencia, con una alternativa: la referencia no tiene resolución extra.
- **Por qué no concluye:**
  1. La referencia es un Zeiss 2.5x/0.075 con *menos* alta frecuencia que una captura LR (R:6.8.1,
     ~R:2690-2720).
  2. El paso de WF ∝ 1/N (`reconstruction.py:217-222`; `step_max`=20 a crop 400 ≈ 1/8000 del paso
     ePIE; R:2819-2840, 6.9.1). Todas las corridas run1-run5 y los barridos de 6.3/6.7/6.8.4 "no evalúan
     el solver" (R:2861-2867). Solo miden la deriva de la estimación inicial, que además estaba sin normalizar.
  3. El objetivo estaba mal (2.5x/0.07 en vez de 2x/0.10); corregirlo no cambió la forma de la curva
     (R:6.8.4, tabla 0/20/50/200 it).
- Sintético, sep. 2026 (antes de sep-23, con otro solver/paso): después de TIE, 40 it mejoran un objeto
  y empeoran otro, así que "no hay un punto de corte universal seguro" (R:236-240). El diagnóstico por
  par desenfocado tampoco elige la cantidad de iteraciones (R:1181-1210, ítem 12 negativo).

## 2. Después del arreglo (paso ePIE relativo, opt-in `--step-epie`/`step_relative`, commit `7c6fc3c`; EPRY `bcb7cc6`)

- **Sintético, geometría real (fork I, R:2930-2958):** ePIE 0.3 llega al piso de ruido en ~50 it. ePIE 0.1
  necesita más de 100. Con g=1, 20/50/100 it dan residuo 0.087 / 0.036 / 0.035. **Es la única justificación
  medida del paso 0.3** (sintético, crop 128, 9x9).
- **Piso real, dic. 2025 (`results/residual_floor_2025-12-12/`, R:2970-3000):** con ePIE 0.3 el residuo
  baja 0.93 → 0.330 (it 10) → 0.306 (40) → 0.295 (100), y la std de fase ya es 1.56 rad en la it 10
  (`SUMMARY.json: runs_iteration_meanres_phasestd_rms`). Con 0.1 y 0.03 pasa lo mismo, pero más lento.
  "No es sobreajuste tardío: la fase tipo ruido ya está en la iteración 10 con cualquier paso" (R:2991-2993).
  El control sintético a crop 400 llega al piso en 10-30 it.
- **Fork K (R:3001-3030):** con 35 it por punto, el residuo es 0.29 en entrenamiento y 0.50 en los LEDs
  excluidos. Hay sobreajuste fuerte, pero se midió a un solo número de iteraciones.
- **J3, 24/09 (`results/captura_2026-09-24/j3/`):** 100 it, `step_relative` 0.3. Es el default de
  `cv_run(..., iterations=100)` y `setdefault("step_relative", 0.3)` en `j3/common/cv_common.py:88,97`,
  que viene del brief (`docs/jobs_esferas/j3_intent_base.txt:15`: `--step-epie 0.3 --iterations 100`;
  `j3_intent_2026-09-24.txt:69`). Costo: ~2.7-3.8 s/it a crop 400, factor 5 (`t4_final/timing.json`).
  No se barrieron iteraciones.
- **Rojo 25/09, set 3 y 28/09 (b):** 40 épocas y paso 0.3, fijados de antemano en el pre-registro
  (`captura_2026-09-25_red/criterios.md:16`; `run.py:24 ITERS = 40`; `fpm_red.py:115`). El 28/09 (b) los
  hereda ("los mismos del set 3", `captura_2026-09-28b/INFORME.md:13`; `red/run.py:24`), igual que la
  simulación multiespectral (`sim_multiespectral_2026-09-29/sim.py:101`). **Nadie justificó el 40 en lo que
  se leyó.** Hipótesis probable: costo (5 folds × variantes × 169 LEDs) [INCOMPLETO: no se revisaron los
  transcripts de la sesión]. El paso 0.3 viene de J3 y del fork I. Detalle oculto: `fpm_red.reconstruct`
  tiene una rampa `mu = step·(1−exp(−0.3·it))` (`fpm_red.py:135`), sin rampa con EPRY.
  - El mismo informe admite que 40 puede ser poco: "El techo lo pone el solver con 40 épocas"
    (sintético R held-out 0.46-0.62 contra un piso de 0.03-0.08; `INFORME.md:46-48`, `criterios.md:70`).
    Propone "más épocas (80-150) con init Fourier" (`INFORME.md:125`) y "más épocas o paso adaptativo en
    anillos externos" (`INFORME.md:120`).
  - `fpm_red.reconstruct` guarda `hist` (costo por época, `fpm_red.py:175`), pero no una métrica
    held-out por época.
- **Conjunta 3 colores (`results/conjunta_2026-09-30/INFORME.md`, R:3140-3151):** otro modelo (espesor
  compartido). A 240 épocas el costo queda por debajo del piso de ruido y S1 empeora de forma monótona:
  A1_D1 −0.037 (ép. 80) → −0.079 (180) → −0.092 (240) (`INFORME.md:112-123`). Costo y calidad apuntan en
  direcciones opuestas (`:131-133`). La regla del plan ("<1 % de caída en 10 épocas") invierte el orden
  entre algoritmos según dónde se pare (`:381-386`). Recomienda "un conjunto de LEDs reservado evaluado
  época a época" (`:429-432`).

## 3. Criterios de parada en `src/`

- `metrics.convergence_summary` (`metrics.py:101-116`) solo resume el primer y el último `recovery_error`
  (RMS de amplitud de entrenamiento). No corta nada. Lo usan los pipelines y los agentes
  (`pipelines/reconstruct_*`, `agents/reconstruction_orchestrator.py:71`, `agents/qc_agent.py`). Está
  documentado como ciego: "`recovery_error` is proven blind"
  (`pipelines/reconstruct_multispectral_independent.py:86,149`; `reconstruction.py:156`; R:6.7).
- `reconstruction._next_adaptive_step` (`reconstruction.py:72-100`, zuo2016 Eq. 16, η=0.01) solo divide
  el paso por 2 cuando el costo se estanca. Es opt-in (`--adaptive-step`) y no detiene la corrida.
- **No hay parada temprana ni criterio held-out dentro del solver.** Todas las corridas usan un número
  fijo de iteraciones.

## 4. Métricas sin verdad de referencia que ya existen

- **C1, residuo held-out por LED** (5 folds por anillo, ajuste afín, R = rms/std;
  `captura_2026-09-25_red/criterios.md:20-30`, `run.py`; `j3/common/cv_common.py: heldout_keys,
  per_led_amplitude_residual, cv_all_folds`).
- **C2, FRC entre mitades de LEDs** (en la banda 2NA/λ..., contra el nulo con geometría mezclada `_scr`).
- **C3, puntaje de red** (`cv_common.lattice_score`).
- **C4, partículas confirmadas en las dos mitades.**
- Residuo BF/DF por separado y std de fase (residual_floor). También la coherencia entre colores
  (`captura_2026-09-28b/comparar_colores.py`: en banda y en todo el espectro).

## 5. Preguntas abiertas para un barrido de iteraciones real (28/09 b RGB, rojo 25/09 set 3)

1. ¿C1 held-out tiene un mínimo interior en épocas (semi-convergencia), o sigue bajando después de 40?
   ¿Dónde queda el mínimo en cada color?
2. ¿C2 (FRC entre mitades) y C3 (red) mejoran o empeoran con las épocas? ¿La mejora de C1 viene con
   detalle que no se reproduce entre mitades (C2 contra el nulo)?
3. ¿El mínimo de C1 coincide con el de C2? Si no coincide, ¿cuál se usa como regla de parada?
4. ¿La coherencia entre colores (28/09 b, en banda y en todo el espectro) sube o baja con las épocas?
5. ¿Con 80-150 épocas (lo que propone el informe del 25/09) mejora C2 en el sintético calibrado? ¿Y en el real?
6. ¿Cuánto pesa la rampa de `fpm_red` y el paso 0.3 contra 0.1 en la curva?
7. ¿La brecha entre entrenamiento y held-out (0.29 contra 0.50 en fork K) crece con las épocas?
8. ¿Los umbrales de C1-C4 se recalibran con el sintético al mismo número de épocas?

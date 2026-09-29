# Plan: reconstrucción conjunta de los tres colores (2026-09-29, revisado; ~4 h sin supervisión)

## Por qué
La cadena actual (reconstruir cada color por separado, después combinar) falla en simulación: el desenvolvimiento con
longitudes de onda sintéticas necesita error de fase < ~0.1 rad y las reconstrucciones por color tienen 0.17-0.54 rad
(`results/sim_multiespectral_2026-09-29/DIAGNOSTICO.md`). Reconstruir los tres colores juntos, con UN espesor compartido,
evita desenvolver: el ajuste va directo contra las fotos.

## Regla general
Ninguna decisión (inicio, número de vueltas, variante, paso) se toma mirando la verdad de la simulación: solo con el ajuste
a las fotos o con fotos no vistas, igual que se haría con datos reales. La verdad se usa solo para los criterios S1-S3.

## Modelo
- **Grilla común** (la misma cuadrícula para la imagen de los tres colores): 1600 px, 0.32 µm (factor 4 sobre la cámara de
  1.28 µm). Verificado el 2026-09-29: con factor 4 las ventanas de `spectral_ops.led_crop_window` de los 225 LEDs caben en los
  tres colores (con factor 3 quedan afuera 49 del azul y 5 del verde). `fpm_red.geometry()` elige su propio factor (3 o 5):
  hay que forzar 4 (`optics.actual_hr_pixel_size_um(setup, 4)`).
- **Objeto por color**: O_c(x) = g_c · a_c(x) · exp(i · 2π · dn(λ_c) · t(x) / λ_c).
  - t(x): espesor compartido (µm), la incógnita principal.
  - g_c: una ganancia escalar real por color (ajustada). Hace falta porque el nivel de intensidad difiere entre colores
    (brillo de los LEDs, planos, y en simulación la escala del modelo directo depende del factor: `sim.py` divide por factor²).
  - Amplitud: **A1** a_c(x) libre por color, o **A2** un solo a(x) compartido.
- **Dispersión** dn(λ) = A + B/λ² (diferencia de índice partícula − medio).
  - Tablas: DMSO n = 1.492 / 1.485 / 1.477 a 470 / 530 / 630 nm (refractiveindex.info, Li 2022 y Kozma 2005; B_DMSO
    0.006-0.0075); nylon 12 n_d ≈ 1.52-1.53, sin dato de dispersión (supuesto Abbe 40-55 → B_nylon 0.005-0.007).
    Resultado: A = 0.04-0.05, B entre −0.002 y 0 (las dos dispersiones casi se cancelan).
  - Simulación: la verdad tiene A = 0.045, B = +0.0015 (signo opuesto al real; no invalida la prueba del método).
    **D1** = A y B verdaderos fijos. **D2** = A fijo, B ajustado desde 0 dentro de [−0.005, +0.005]; tiene que recuperar
    0.0015 (±0.0005) o D2 no se usa en datos reales.
  - Datos reales: A = 0.045 fijo (solo escala t). **D1** = B = 0. **D2** = B ajustado dentro de [−0.003, +0.001]. Si D2 termina
    en un borde del rango, anotarlo como señal de que compensa otra cosa.
- **Fotos**: el modelo directo de `fpm_red.predict` (ventana del espectro por LED, pupila circular NA/λ_c) con la geometría
  de LEDs de cada color a 98 mm; intensidad = |ψ|². Usar las máscaras de saturación de `load_real()` en datos reales.
- **Corrimiento entre colores (datos reales)**: `results/captura_2026-09-28b/comparar_colores.json` →
  "crudas": rojo-verde [2, 0] y azul-verde [−2, 0] px de cámara (1.28 µm/px) = ±2.56 µm en filas = ±8 px en la grilla común.
  Entra como corrimiento conocido de t y a para ese color. El signo está definido por `pc()` de `comparar_colores.py`
  (np.roll(a, −s) alinea a con b); verificarlo antes de usarlo (la correlación rojo-verde de las reconstrucciones
  independientes tiene que subir con el corrimiento elegido). En simulación no hay corrimiento.

## Algoritmo
- Costo: Σ_c Σ_k ‖ |ψ_ck| − √I_ck ‖² sobre píxeles no saturados, todos los LEDs con peso 1 (pesar por ruido empeoró en el
  set 3 del 25/09).
- Dos variantes permitidas; elegir UNA en la fase 1 por el costo final sobre un recorte chico de la simulación (no por la
  verdad):
  (i) gradiente de lote completo respecto de t, a (y g_c, B), con Adam o Nesterov;
  (ii) por vuelta: un paso ePIE en cada color (como `fpm_red.reconstruct`) y después proyectar los tres O_c sobre el modelo
  conjunto, minimizando Σ_c ‖O_c − g_c a_c exp(iκ_c t)‖² por gradiente en t desde el t anterior (no hace falta desenvolver).
- Inicio: t0 desde la reconstrucción independiente, con la cadena `couple_rgb_channels(..., dispersion_B=B)` →
  `thickness_known_dispersion_um` (0.55 en simulación) y como alternativa la fase del verde solo. Elegir por costo, no por verdad.
- Vueltas: 80 por defecto (~15 min; ver Tiempos); más solo si el costo sigue bajando > 1 % en las últimas 10 y hay tiempo.
- **Chequeo de gradiente obligatorio antes de todo**: `gradcheck(seed=0)` en un problema chico (64 px, 9 LEDs, 3 colores),
  contra diferencias centrales, error relativo < 1e-5, para t, a_c, g_c y B.

## Criterios fijados ANTES de correr
Simulación: 98 mm, fotos con ruido medido `results/sim_multiespectral_2026-09-29/datos_z98_<color>.npz`, verdad `verdad.npz`
(2000 px, 0.256 µm). Métricas en la grilla común (1600 px), con un margen de 100 px descartado. Las referencias se
recalculan con el MISMO código que la conjunta.
- **S1** (espesor): correlación de Pearson entre t y la verdad filtrada a la banda que dejan pasar los LEDs (como
  `analisis.py`: fmax = min sobre colores de NA/λ + frecuencia máxima de iluminación). Pasa si ≥ 0.90.
  Referencias: cadena libre sobre las reconstrucciones independientes (0.11 en `analisis.py`), dispersión conocida 3 colores,
  dispersión conocida verde + azul (0.55 y 0.80 contra la verdad sin filtrar; recalcular con esta métrica).
- **S2** (fase por color): desvío estándar de la diferencia de fase contra la verdad sobre los píxeles de partícula, tras quitar
  la constante con el fondo. valor = máx sobre colores de (error conjunto − error independiente), en rad; pasa si < 0.
  Referencia independiente medida el 2026-09-29 en la grilla de 1200 px: 0.54 / 0.17 / 0.17 rad (rojo / verde / azul);
  recalcularla en la grilla de 1600 px con el mismo código que la conjunta.
- **S3** (mitades): reconstrucción conjunta con cada mitad del damero ((fila+col) % 2) → O_c de cada mitad →
  FRC en [2NA/λ_c, 0.45] 1/µm por color (la métrica C2). valor = mín sobre colores de (conjunta − independiente); pasa si ≥ 0.
  Referencia independiente: 0.66 / 0.86 / 0.93 (`analisis.json`, z98, frc_mitades).
- **B_ajustado**: el B final de D2.
- Orden en simulación: A1_D1 y A2_D1; la de menor costo final ("la mejor") se usa para D2 y para las dos mitades de S3.
  S1 y S2 se informan para todas las variantes corridas; "pasa" de S1 y S2 se toma de la mejor.
- Muestra con amplitud distinta por color (0.95 / 0.90 / 0.85 dentro de las partículas; fotos nuevas con el mismo generador y
  ruido que `sim.py`): A1 y A2, S1 de cada una. Mide cuánto pierde A2 cuando su suposición es falsa.
- Si S1 falla para todas las variantes, NO se pasa a datos reales: real = {"omitido": "<por qué>"}.

Datos reales (captura 28/09 b, `load_real()` de `results/captura_2026-09-28b/<color>/fpm_red.py`):
- Elección de variante (A1/A2 × D1/D2): error de predicción de fotos no vistas en el grupo 0 de `fpm_red.folds` (el mismo
  grupo apartado en los tres colores; campo claro nunca se aparta), `affine_residual`, anillos < 7, promedio de los tres
  colores. Gana el menor.
- **R1**: con la variante elegida, los 5 grupos; por color, pasa si el error ≤ el independiente + 0.05. Independiente
  (`criterios_b.json`): 0.461 / 0.615 / 0.596.
- **R2**: t de las dos mitades del damero; FRC de t en [2NA/λ_rojo, 0.45] = [0.22, 0.45] 1/µm. Nulo: lo mismo con la
  geometría desordenada (`run.scrambled`, semilla 0, la misma permutación en los tres colores). Pasa si ≥ 0.143 y ≥ nulo + 0.068.
  Informativo: lo mejor por color hoy es 0.099 (azul).

## Tiempos (medidos el 2026-09-29)
Ida y vuelta de 225 LEDs de un color en la grilla de 1600 px: 3.6 s → ~11 s por vuelta de los tres colores → 80 vueltas
≈ 15 min (≈ 18 min con 3 procesos a la vez). Máximo 3 procesos pesados en paralelo (4 núcleos).
Corridas previstas: simulación ~7 (A1, A2, D2, dos de amplitud distinta, dos mitades de la mejor) ≈ 45 min;
datos reales ~12 (4 variantes en el grupo 0, 4 grupos más, 2 mitades, 2 nulos) ≈ 75 min.

| h | qué | salida |
|---|---|---|
| 0:00-0:50 | `joint.py`, chequeo de gradiente, elección de variante de algoritmo en un recorte | joint.py |
| 0:50-1:50 | simulación: S1-S3, D2, amplitud distinta | resultados.json (sim) |
| 1:50-3:15 | datos reales (si S1 pasó): variante, R1, R2 | resultados.json (real) |
| 3:15-4:00 | informe y figuras | INFORME.md, figs/ |
Prioridad si falta tiempo: chequeo de gradiente → S1-S3 y D2 → amplitud distinta → datos reales.

## Reglas
- Escribir solo en `results/conjunta_2026-09-30/` y en la carpeta del job. No tocar `src/`, `tests/`, `report/`, `docs/`,
  otras carpetas de `results/` ni `~/Documents/LucasC/code/ptyco-full-simulator`. Sin commits ni push.
- `results/conjunta_2026-09-30` es un enlace a `jobs/<id>/work/conjunta_2026-09-30`: el vigilante del job solo cuenta
  escrituras dentro de su carpeta (en el J3 cortó dos turnos de trabajadores a los 30 min, "idle-timeout, no output salvaged").
  Con el enlace, todo lo que se escribe en resultados cuenta como actividad; el corte se subió a 60 min.
- Corridas largas en segundo plano, con OMP_NUM_THREADS=1, reanudables, con un latido en `logs/<corrida>.log` al menos una
  vez por minuto. Máximo 3 procesos pesados en total para todo el equipo.
- El verificador recalcula desde lo guardado (chequeo de gradiente, métricas con su propio código); no repite
  reconstrucciones completas (a lo sumo una prueba corta de <= 10 vueltas).
- Si algo se traba más de 30 min, anotarlo y pasar a lo siguiente.
- Aceptación (fija, el job no puede editarla): `pytest tests/test_acceptance_conjunta.py` — exige los entregables, no que el
  método funcione; un resultado negativo bien explicado es válido.

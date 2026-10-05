# Offset de fuente LED por color — 28/09b (2026-10-02)

**Estado: ETAPA 1 (solo rojo, dataset completo) terminada. Verde/azul, folds CV y mitades NO lanzados (esperan confirmación).**

## Qué se cambió (y nada más)
Misma reconstrucción que `results/iteraciones_2026-09-30` (A+init: init `fourier_avg`, sin pesos, sin s/b, sin EPRY,
paso 0.3 con rampa, máscara de saturados, mismos LEDs/tareas de `run.py`). Única diferencia: la geometría usa
`offset_mm = (0, 3 + Δ_color)` en vez de `(0, 3)`, con Δ = R +1.06, G +0.63, B +0.15 mm (eje de filas LED = y),
del ajuste de frontera en flats (`docs/resultados_2026-10-01/geometria/frontera/`).

- Convención de signo: en `frontera/ajustar.py` la posición nominal es `y = (fila − 17.5)·6 mm` y el ajuste da
  `y_real = nominal + dy` con dy = +1.06 (rojo). En `led_array.led_position_mm` la posición es
  `(fila − 18)·6 + off_y`, que con off_y = 3 es el mismo nominal. Por lo tanto el rojo va con `offset_mm = (0, 4.06)`.
- Arnés: `runner.py` (importa `iter_runner.py` sin tocarlo; solo cambia `offset_mm`). Salidas en `out/<variante>/b_red/`.

## Verificaciones previas
1. **Reproducción bit a bit de la base.** `runner.py` con variante `nominal`, rojo fold 0, 40 épocas: `per_led`,
   `heldout_R_ring_lt7` y `lattice` idénticos (diferencia máxima 0.0) a `iteraciones_2026-09-30/out/b_red/..._f0`
   en todas las épocas 0–40. C1 fold 0 @40 = 0.472964924257311, igual a la base. → el arnés solo difiere en el offset.
2. **Prueba de signo** (rojo, full, 40 épocas), Δ = +1.06 vs −1.06:

   | época | Δy LED equivalente de la rampa (mm): nominal | +1.06 | −1.06 |
   |---|---|---|---|
   | 8 | 0.00 | 0.00 | −1.51 |
   | 20 | 0.00 | 0.00 | −1.91 |
   | 40 | −0.28 | 0.00 | −1.99 |

   Con −1.06 la rampa aparece antes y tiende a −2.1 mm (= el doble del error); con +1.06 no aparece. El residuo de
   entrenamiento en las primeras épocas (2–20, antes de que el solver "absorba" el error con la rampa) también ordena
   +1.06 < nominal < −1.06 (ép. 5: 0.398 / 0.406 / 0.421). **Signo confirmado: +.** Además el nominal deriva hacia
   −1.06 mm, justo el valor que predice el ajuste de frontera.

## Resultados etapa 1 (rojo, full, misma época, pareado)

| métrica | ép. | nominal (0, 3) | die (0, 4.06) |
|---|---|---|---|
| rampa global p-p (rad) | 5 | 0.08 | 0.06 |
| | 40 | 17.8 | 0.11 |
| | 160 | 26.9 | 0.30 |
| Δy LED equivalente (mm) | 40 | −0.28 | 0.000 |
| | 160 | −0.52 | +0.001 |
| R afín medio, LEDs de entrenamiento | 5 | 0.406 | 0.398 |
| | 40 | 0.349 | 0.330 |
| | 160 | 0.320 | 0.317 |
| d_vol/d (mediana, d ≥ 5 µm; N) | 5 | 0.86 (63) | 1.04 (34) |
| | 40 | 0.93 (36) | 1.05 (36) |
| | 160 | 1.10 (21) | 1.09 (32) |
| V_die / V_nominal, misma partícula (mediana; N) | 5 / 40 / 160 | — | 0.98 (30) / 1.01 (20) / 1.00 (21) |
| rayas horizontales: rms del perfil en y (rad) | 5 / 40 / 160 | 0.01 / 0.12 / 0.72* | 0.13 / 0.52 / 0.60 |

\* en el nominal a 160 el valor está contaminado por los saltos de desenrollado de la rampa; a 5 y 40 es limpio.

Figuras: `figs/rampa_vs_epoca_rojo.png` (Δy equivalente y residuo vs época, con la variante de signo opuesto),
`figs/mapas_fase_rojo.png` (fase desenrollada, nominal arriba / die abajo, épocas 5, 40, 160).
Números: `etapa1.json`, `vol_pareado.json`, `rayas.json`; scripts `etapa1.py`, `vol_pareado.py`, `rayas.py`, `volumen.py`
(`volumen.py` reproduce la regla del 01/10 sobre los objetos base: 0.935 / 0.691 / 0.653).

## Lectura (preliminar)
- **La rampa roja desaparece.** Con el offset del die la rampa queda en 0.1–0.3 rad p-p hasta la época 160
  (nominal: 18 → 27 rad, desplazamiento equivalente −0.28 → −0.52 mm y creciendo hacia −1.06). La rampa del nominal
  era el solver compensando un error de posición de fuente de ~1 mm, no deriva espontánea.
- **Por qué crece con las épocas y no está desde el principio:** un desplazamiento rígido de todos los LEDs es casi una
  simetría exacta del modelo (corrido de todo el espectro = rampa de fase en el objeto); en sinθ el corrimiento
  δ/z es independiente de λ. El init `fourier_avg` no tiene rampa y el costo es casi plano en esa dirección, así que el
  solver la recorre lentamente. Con el offset correcto el init ya es consistente y no hay nada que recorrer.
  Consecuencia: una rampa global sola no rompe la simetría entre colores; lo que es medible y no es ambiguo es la
  **diferencia** entre colores (R−B ≈ 0.9 mm, G−B ≈ 0.5 mm), que solo una reconstrucción conjunta (o un registro de
  fase entre colores) puede ver. Queda abierto por qué el verde (Δ = 0.63 mm) no mostró rampa clara en la base; se
  verá en la etapa 2.
- **El residuo mejora un poco:** −5 % en la época 40, −1 % en la 160 (el nominal "alcanza" al die absorbiendo la rampa).
  Esto es residuo de entrenamiento en el full; el C1 retenido (folds) no se midió todavía.
- **El volumen de fase del rojo NO cambia.** La subida aparente de d_vol/d (0.93 → 1.05 a 40) es un artefacto de la
  segmentación: el umbral es max(0.3, 5·ruido de fondo) y el die tiene más ruido de fondo (ver abajo), lo que achica las
  máscaras (d ≈ 10 % menor). Partícula a partícula, V_die/V_nominal = 0.98–1.01. Esperable: si el offset solo quita
  una rampa, el volumen local con fondo restado no se mueve. Por lo tanto no hay que esperar que el offset por color
  recupere por sí solo el volumen faltante de verde/azul (aunque sí cambia los cocientes entre colores solo si cambian
  sus volúmenes, lo que este resultado hace improbable).
- **Artefacto nuevo: rayas horizontales.** Con el offset del die aparece desde la época 5 una modulación de fase a lo
  largo de y (eje de filas LED), período ≈ 68 µm (fy ≈ 0.015 ciclos/µm ≈ 7.5 píxeles espectrales), rms del perfil
  0.13 rad a ép. 5 y ~0.5–0.6 rad a 40–160; en el nominal a ép. 5 es 0.01 rad. No sabemos aún el origen: candidatos
  (i) el Δ rígido no es exacto (frontera: ±0.1 mm, y z≈101 mm / NA≈0.072 no corregidos) y el residuo no rígido se
  manifiesta como rayas; (ii) redondeo de las ventanas de recorte a píxeles enteros que cambia con el offset;
  (iii) una LED de campo claro (filas 17/18, ahora asimétricas: y = −1.94 / +4.06 mm) mal modelada. Hay que
  entenderlo antes de declarar ganadora la geometría corregida.

## Veredicto etapa 1
La rampa roja se explica por completo con el offset del die (signo confirmado de forma independiente); el residuo de
entrenamiento mejora levemente; el volumen de fase del rojo no cambia. El offset corrige la geometría pero introduce
(o desenmascara) rayas de ~68 µm a lo largo de las filas que hay que diagnosticar.

## Pendiente (no lanzado, espera confirmación)
- Etapa 2: verde/azul full con Δ = +0.63 / +0.15 (volumen, V_G/V_R, V_B/V_R vs esperado ~1.23 / 1.42).
- C1 retenido (5 folds) y C2 de mitades, pareados con la base (el arnés ya los soporta: `runner.py run die 3 160 b_red,b_green,b_blue`).
- Diagnóstico de las rayas (barrido fino de Δ rojo, p. ej. 0.9 / 1.06 / 1.2; z 98 vs 101).

---

# Diagnóstico de las rayas (rojo, full, 40 épocas)

Métrica: `rayas2.py` (fase demodulada con el campo suavizado σ = 60 µm; rms del perfil en y = mediana en x; MAD del fondo).
Chequeo de código: `bordes.py` y `redondeo.py`. `led_crop_window` redondea el centro de cada LED al bin entero
(dk = 1/512 µm⁻¹), así que el patrón de errores de redondeo (±0.5 bin) sí cambia con el offset.

| variante (rojo) | rms rayas ép. 5 | rms rayas ép. 40 | MAD fondo ép. 40 | R_train ép. 40 | rampa p-p ép. 40 |
|---|---|---|---|---|---|
| nominal (0, 3), 225 LEDs | 0.012 | 0.116 | 0.31 | 0.349 | 17.8 |
| die Δ=1.06, z=98 | 0.128 | 0.516 | 0.78 | 0.330 | 0.11 |
| Δ=0.90 | 0.129 | 0.494 | 0.77 | 0.330 | 0.11 |
| Δ=1.20 | 0.133 | 0.289 | 0.52 | 0.332 | 0.13 |
| Δ=1.06, z=101 | 0.121 | 0.469 | 0.82 | 0.329 | 0.17 |
| Δ=1.06, NA=0.072 | 0.135 | 0.476 | 0.79 | 0.333 | 0.22 |
| **die sin (18,14),(18,16)** | 0.005 | **0.008** | **0.077** | 0.318* | 0.10 |
| die sin (18,14),(18,16),(16,15) | 0.005 | 0.014 | 0.081 | 0.317* | 0.05 |
| nominal sin (18,14),(18,16) | 0.005 | 0.018 | 0.081 | 0.326* | 0.07 |

\* R_train sobre otro conjunto de LEDs (223): comparar solo entre filas con *. Comparación pareada con el mismo conjunto:
die 0.318 contra nominal 0.326 en la época 40 (−2.2 %), y 0.314 contra 0.317 en la 60.

**Hipótesis que explica las rayas: las LEDs (18,14) y (18,16) quedan a horcajadas del borde de la pupila.**
- `bordes.py`: con el nominal esas LEDs quedan 1.4 bins *dentro* de la pupila (campo claro). Con el die rojo quedan
  3.0 bins *fuera* (campo oscuro en el centro del campo). Pero `load_real` las trata como campo claro, con división
  por flat, y los datos son de campo claro en parte del campo.
- El ajuste de frontera ya lo decía: para (18,14) y (18,16) la frontera |sinθ| = NA cruza el campo de visión a
  ~170 µm del centro. Hacia un lado son campo claro y hacia el otro campo oscuro, porque el ángulo varía unos 4 bins a
  lo largo de los 512 µm del campo con la LED a 98 mm.
- Un modelo de onda plana con un solo k no puede representar eso. Con el die, el solver mete energía de baja
  frecuencia en fy (rayas a lo largo de las filas) para explicar la parte clara.
- Sacarlas elimina las rayas por completo: rms 0.52 → 0.008 rad, fondo 0.78 → 0.08 rad. Queda incluso más limpio
  que el nominal con todas las LEDs (0.12 / 0.31).
- Ni Δ (0.90 / 1.20), ni z = 101, ni NA = 0.072 las sacan. Tampoco el redondeo: cambia con cada Δ y las rayas siguen.
  El "período" no es una línea fija: es una banda ancha de 5 a 12 bins, así que no es aliasing del redondeo.
  Sacar además la (16,15) (borde a 8.7 bins de k = 0) no agrega nada.
- Verde: con Δ = 0.63 las mismas dos LEDs quedan 1.3 bins fuera. Hay rayas fuertes (0.60 rad a ép. 40, 0.70 a
  ép. 160) y sin ellas desaparecen (0.014). En azul (Δ = 0.15) siguen dentro (−1.1 bins) y no hay rayas.

**Esas dos LEDs probablemente también producen la rampa del nominal.** El nominal sin (18,14) y (18,16) no muestra
rampa (0.07 rad a ép. 40 y 0.08 a ép. 60, contra 17.8 con todas). La corrida de control a 160 épocas
(`out/nom_sin18_160`, `out/die_sin18_160`) seguía corriendo al escribir esto: mirar `logs/diag_*_160.log` y la figura
de `etapa2.py`. La rampa del nominal aparece de golpe entre las épocas 30 y 40. Lectura actual: el error de offset es
real (la frontera, el signo confirmado y el residuo pareado −2.2 % lo apoyan), pero el disparador de la deriva son las
LEDs de borde.

# Etapa 2: verde (+0.63) y azul (+0.15), full, z = 98

| métrica | color | ép. 5 nom / die | ép. 40 nom / die | ép. 160 nom / die |
|---|---|---|---|---|
| R_train | verde | 0.494 / 0.496 | 0.436 / 0.441 | (120) 0.424 / 0.427 |
| | azul | 0.465 / 0.465 | 0.409 / 0.407 | (120) 0.399 / 0.394 |
| rampa p-p (rad) | verde / azul | ~0 / ~0 | 0.18 (die verde, ép. 60–80) | sin rampa en ninguno |
| rayas rms (rad) | verde | 0.010 / 0.202 | 0.024 / 0.605 | 0.032 / 0.700 |
| | azul | 0.007 / 0.008 | 0.014 / 0.018 | 0.016 / 0.021 |

Volumen de fase con máscara fija (`vol_fijo.py`). Se segmenta en el nominal de la misma época y se mide el die con las
mismas máscaras, así que el umbral no sesga. Es la mediana con d ≥ 5 µm.

| ép. | color | N | d_vol/d nom | d_vol/d die | V_die/V_nom (p25–p75) |
|---|---|---|---|---|---|
| 5 | rojo | 63 | 0.86 | 0.86 | 0.96 (0.79–1.04) |
| 5 | verde | 26 | 0.87 | 0.84 | 1.00 (0.87–1.13) |
| 5 | azul | 36 | 0.79 | 0.77 | 1.00 (0.92–1.01) |
| 40 | rojo | 36 | 0.93 | 0.88 | 0.93 (0.77–1.06) |
| 40 | verde | 35 | 0.69 | 0.48 | 0.35 (0.01–0.73) ← rayas |
| 40 | azul | 61 | 0.65 | 0.64 | 0.98 (0.96–1.03) |
| 160 | rojo | 21 | 1.10 | 1.08 | 0.93 (0.81–1.02) |
| 160 | verde | 43 | 0.68 | 0.48 | 0.49 (0.11–0.65) ← rayas |
| 160 | azul | 61 | 0.66 | 0.65 | 0.99 (0.91–1.02) |

Cocientes entre colores (misma partícula, d ≥ 5 µm; esperado 1.23 para V_G/V_R y 1.42 para V_B/V_R):
- V_G/V_R: ép. 5 nom 0.95 / die 0.90; ép. 40 nom 0.81 / die 0.38; ép. 160 nom 1.18 (N = 8) / die 0.41.
- V_B/V_R: ép. 5 nom 1.06 / die 1.08; ép. 40 nom 1.04 / die 1.11; ép. 160 nom 1.11 / die 1.15.

Controles sin (18,14) y (18,16), ép. 40, pareados con el mismo conjunto de LEDs:
- Rojo die/nom: V 1.01 (0.98–1.04).
- Contra el nominal con todas las LEDs, sacar esas dos LEDs baja d_vol/d del rojo de 0.93 a 0.86, con o sin offset.
- Verde die sin las dos LEDs, contra nominal con todas: V 0.63.
- `g_nom_sin18` (control pareado del verde) seguía corriendo al escribir esto.

# Veredicto (etapas 1 + 2 + diagnóstico)
1. **La rampa roja** desaparece con el offset del die, y también sin el offset si se sacan (18,14) y (18,16), al menos
   hasta la época 60. El control a 160 épocas está pendiente.
2. **El volumen de fase no lo arregla el offset.** Partícula a partícula, con el mismo conjunto de LEDs, V_die/V_nom
   ≈ 1.0 en los tres colores (el verde con todas las LEDs está arruinado por las rayas). Verde y azul no recuperan
   volumen: d_vol/d azul 0.65 → 0.64. V_B/V_R sube apenas, de 1.04 a 1.11, lejos de 1.42.
3. **Las rayas** salen de LEDs a horcajadas del borde de pupila, que el modelo de onda plana con un solo k no puede
   representar. No vienen del redondeo ni de z/NA. El offset correcto las vuelve a la vez peores (el modelo las mete en
   campo oscuro) y más visibles.
4. **Simetría:** un corrimiento rígido δ/z en sinθ es casi exactamente una rampa de fase del objeto. Por eso el offset
   casi no cambia el residuo (−1 a −2 %) ni el volumen local. Lo que sí cambia con el offset es la clasificación campo
   claro/oscuro de las LEDs que están cerca del borde, y eso domina todo.
5. **Recomendación:** usar el offset por color *y* sacar (o modelar con k que varíe en el campo, por ejemplo
   reconstrucción por teselas) las LEDs a horcajadas del borde en cada color. Medir C1/C2 así antes de concluir.

## Actualización (controles terminados o casi)
- Verde, mismo conjunto de LEDs (sin (18,14),(18,16)), ép. 40:
  - die contra nominal: V_die/V_nom = 0.97 (0.88–1.05); d_vol/d 0.72 → 0.65 (N = 26);
  - rayas 0.014 / 0.018 rad;
  - R_train 0.424 (die) contra 0.428 (nominal).
  - El offset tampoco cambia el volumen verde.
- Rojo sin las dos LEDs, ép. 120: no hay rampa ni con nominal (0.09 rad) ni con die (0.05 rad); la base con todas las
  LEDs tenía 26 rad. R_train 0.310 (nominal) contra 0.309 (die).
  - **La rampa del nominal la disparan las LEDs a horcajadas del borde, no el offset por sí solo.**
  - La época 160 de estos controles no estaba guardada al escribir esto.
- Época 160, rojo sin (18,14) y (18,16): rampa 0.01 rad (nominal) y 0.05 rad (die), contra 26.9 rad de la base con
  todas las LEDs; R_train 0.3085 contra 0.3081.
  - Confirmado: sin esas dos LEDs no hay rampa en ningún momento.
  - Con ellas excluidas, el offset casi no cambia el residuo a 160 épocas, aunque ayuda en las primeras (−2 % a la 40).

## Configuración final `final_z101` (02/10, 40 épocas, 28/09b full)
z = 101 mm (NA 0.07), offset del die por color (filas 4.06 / 3.63 / 3.15 mm), sin (18,14),(18,16) en rojo y verde
(frontera r = 7.07 mm de `teselas_2026-10-02/mapa_bfdf`); en azul la frontera solo corta una esquina y se dejan todas.
Script `final_cmp.py` → `final_cmp.json`. Volumen con máscaras fijas segmentadas en el nominal base (como `vol_fijo.py`).
**Ojo verde:** a z = 101 el factor de sobremuestreo baja de 5 a 3 (N 2000 → 1200, hrpx 0.256 → 0.427 µm); para las
máscaras fijas el objeto se rellenó en Fourier a 2000. Es un confusor: no es un pareado limpio.

| color | corrida | rayas rms (rad) | rampa p-p (rad) | R_train (común sin 18,x) | d_vol/d |
|---|---|---|---|---|---|
| rojo | base (nominal, todas) | 0.116 | — | 0.343 | 0.93 |
| rojo | die (todas) | 0.516 | 0.11 | 0.325 | 0.88 |
| rojo | die_sin18 (z98) | 0.008 | 0.10 | 0.318 | — |
| rojo | **final_z101** | 0.011 | 0.05 | 0.318 | 0.89 |
| verde | base | 0.024 | — | 0.432 | 0.69 |
| verde | die | 0.605 | 0.10 | 0.436 | 0.48 |
| verde | g_die_sin18 (z98) | 0.014 | 0.17 | 0.424 | 0.65 (ref. con mismo set) |
| verde | **final_z101** | 0.012 | 0.13 | 0.434 | 0.57 |
| azul | base | 0.014 | — | 0.406 | 0.65 |
| azul | die | 0.019 | 0.12 | 0.404 | 0.64 |
| azul | **final_z101** | 0.015 | 0.01 | 0.404 | 0.64 |

V_final/V_nom por partícula: rojo 0.88 (0.80–1.02), verde 0.67 (0.33–0.83), azul 0.98 (0.93–1.01).
Cocientes entre colores (esperado 1.23 / 1.42): V_G/V_R nominal 0.81 → final 0.50 (N = 18); V_B/V_R 1.04 → 1.16 (N = 23).

**Veredicto:** z = 101 + exclusión de LEDs de borde limpia rayas y rampa en los tres colores, pero **no corrige el
déficit de volumen de verde y azul**: azul queda igual (d_vol/d 0.64), el verde empeora (en parte por el factor 3).
El déficit G/B no viene de la geometría de iluminación.
Variante `final_z101_dfnorm` (todas las LEDs, las dos de borde con preprocesado DF, solo rojo y verde), época 40:
- rojo: rayas 0.012 rad, rampa 0.04 rad, R_train 0.338 (225 LEDs). Tan limpio como la exclusión.
- verde: **roto**, con rayas 0.613 rad y rampa 27.6 rad (dy −0.42 mm), R_train 0.449.
- En verde, el preprocesado DF no alcanza; la exclusión sí.
- Volumen de esta variante: no medido.

## Geometría de trabajo `final_z102` (02/10, 40 épocas, 28/09b full)
Objetivo Zeiss 2.5x/0.07 (diseñado para tubo de 164.5 mm) con tubo Thorlabs de 150 mm → aumento ≈ 2.35×, así que
lrpx = 3.2/2.35 = **1.362 µm** (antes 1.28), NA 0.069, z = 102 mm, offset del die por color (filas 4.06 / 3.63 / 3.15 mm).
- **Hook** (`runner.py`, claves `_mag`, `_naobj`, `_factor`): envuelve `F.setup` para reemplazar aumento y NA del objetivo.
  El `LRPX` de `fpm_red.py:42` es un literal que no se usa: lrpx sale de `objective.magnification`. NA y lrpx llegan a
  pupila, ventanas y hrpx vía `geo`. Config efectiva impresa al arrancar: lrpx 1.3617, na 0.069, z 102, factor R3/G5/B5,
  hrpx 0.454/0.272/0.272 µm.
- **Horcajadas** (`mapa_z102.py` → `mapa_z102.json`; R_BF = 7.055 mm, campo ±272 µm):
  - rojo: (18,14) y (18,16) con 13 % del campo en campo claro;
  - verde: las mismas dos, con 59 %;
  - azul: las mismas dos, con 96.6 % (solo una esquina).
  - Se excluyen en R y G y se dejan en B, igual que en z101.
- **Factor de sobremuestreo:** con lrpx 1.362 el natural ya coincide con el nominal en los tres colores (R3/G5/B5): N
  1200/2000/2000, pareado píxel a píxel con base. Igual se forzó vía `_factor` (sin efecto).
- **Control `final_z101_f5`** (verde, z101 con factor 5): da *exactamente* el mismo R_train (0.4338) y el mismo
  d_vol/d (0.566) que final_z101 con factor 3. **El factor 3 de z101 no era un confusor.**
- Script `final_cmp_z102.py` → `final_cmp_z102.json`.
- **Escala:** vol_fijo usa hr = 512/N, que corresponde a lrpx 1.28. Con lrpx 1.362 el área real por píxel es s² mayor
  (s = 1.0638), así que d_vol/d corregido = crudo × s^(-1/3) = crudo × 0.980. Los cocientes entre colores y V/V con la
  misma máscara no cambian. Con el dx nuevo, también el base bajaría de 0.93/0.69/0.65 a 0.92/0.68/0.64.

| color | corrida | rayas rms (rad) | rampa p-p (rad) | R_train (común, 223 LEDs) | d_vol/d crudo | d_vol/d con dx nuevo |
|---|---|---|---|---|---|---|
| rojo | base | 0.116 | — | 0.343 | 0.93 | 0.92 |
| rojo | final_z101 | 0.011 | 0.05 | **0.318** | 0.89 | — |
| rojo | final_z102 | 0.010 | 0.06 | 0.331 | 0.85 | 0.84 |
| verde | base | 0.024 | — | 0.432 | 0.69 | 0.68 |
| verde | final_z101 (f3) / _f5 | 0.012 | 0.13 / 0.18 | 0.434 | 0.57 | — |
| verde | final_z102 | 0.012 | 0.12 | **0.426** | 0.56 | 0.55 |
| azul | base | 0.014 | — | 0.406 | 0.65 | 0.64 |
| azul | final_z101 | 0.015 | 0.01 | **0.404** | 0.64 | — |
| azul | final_z102 | 0.016 | 0.07 | 0.412 | 0.63 | 0.62 |

**Volumen, misma máscara, z102 contra z101** (V_z102/V_z101 en píxeles, mediana y p25–p75):
- rojo 0.99 (0.97–1.01);
- verde 0.97 (0.90–1.06), contra z101_f5;
- azul 0.96 (0.92–1.02).

Contra base: rojo 0.90, verde 0.71, azul 0.98 en píxeles; × s² = 1.02 / 0.81 / 1.10.

**Cocientes entre colores** con z102 (esperado 1.23 / 1.42):
- V_G/V_R = 0.55 (N = 18); nominal 0.81, z101 0.50.
- V_B/V_R = 1.09 (N = 23); nominal 1.04, z101 1.16.

**Veredicto z102:**
1. Rayas y rampa quedan tan limpias como en z101.
2. El volumen no cambia (±4 %) y el déficit de G y B sigue igual. La escala nueva baja todos los d_vol/d un 2 % más.
3. Con el conjunto común de 223 LEDs, R_train **no favorece** la geometría z102/1.362:
   - rojo +4.1 % (0.331 contra 0.318);
   - azul +1.9 %;
   - solo verde mejora, −1.7 %; pareado, porque z101_f5 ≡ z101.
4. Señal mixta, dominada por el rojo, que es el canal con más contraste. Los datos no confirman lrpx 1.362 con z 102.
   Recordar que en el modelo lo que cuenta es el paso de LED en bins, ∝ lrpx/z: 0.0134 µm/mm en z102 contra 0.0127 en
   z101, +5.4 %; z/dx = 74.9 contra 78.9 mm/µm. El residuo prefiere el paso de z101 en R y B.
5. Si se quiere zanjar, conviene un barrido 1D de lrpx/z con z fijo, por ejemplo lrpx ∈ {1.28, 1.32, 1.362} a z = 102,
   mirando R_train por color.

## Barrido de lrpx extendido a z = 102 (05/10, 40 épocas, 28/09b)
Mismo protocolo que `sweep_lrpx.sh`: tarea `full`, 40 épocas, die por color, NA 0.069, factor R3/G5/B5, sin (18,14),(18,16)
en R y G. Variantes nuevas en `runner.py`: `z102_m258` (lrpx 1.24), `z102_m267` (1.20), `z102_m276` (1.16).
Scripts `sweep_lrpx2.sh` (rojo), `sweep_lrpx3.sh` (descomposición, G/B, folds), `sweep_lrpx4.sh` (NA).
Análisis en `barrido_lrpx.py` → `barrido_lrpx.json`. Métrica: R_train a la época 40 (223 LEDs en R y G, 225 en B), la
misma de la sección anterior.

| lrpx (µm) | aumento | R_train rojo | R_train verde | R_train azul | R held-out rojo (folds) |
|---|---|---|---|---|---|
| 1.16 | 2.76 | 0.3265 | — | — | 0.404 |
| 1.20 | 2.67 | 0.3189 | 0.4346 | **0.4038** | — |
| 1.24 | 2.58 | **0.3136** | 0.4340 | 0.4087 | 0.406 |
| 1.28 | 2.50 | 0.3153 | 0.4265 | 0.4079 | — |
| 1.32 | 2.42 | 0.3204 | **0.4262** | 0.4081 | — |
| 1.362 | 2.35 | 0.3310 | 0.4263 | 0.4144 | 0.461 |

- **Rojo: mínimo encerrado.**
  - Parábola con los 6 puntos: lrpx = 1.254 µm. Con los 3 puntos alrededor del mínimo: 1.250 µm.
  - Bootstrap sobre LEDs: 1.248–1.259 (p16–p84). Es solo el error estadístico; el sistemático es mayor (forma
    asimétrica, 40 épocas sin converger, redondeo de ventanas).
  - Estimación honesta: **lrpx ≈ 1.25 ± 0.02 µm**, o sea aumento ≈ **2.56 ± 0.04×**.
  - Diferencias pareadas entre puntos vecinos: 4–10 veces su error estándar (±0.001), salvo 1.24 → 1.28
    (+0.0017 ± 0.0010).
- **Verde:** meseta entre 1.28 y 1.362 (diferencias < 0.0003) y salto de +0.007 al bajar a 1.24. Prefiere lrpx ≥ 1.28 y
  no discrimina dentro de ese rango.
- **Azul:** curva irregular. Hay una meseta 1.24–1.32 (≈ 0.408); 1.362 da peor (+0.006) y 1.20 da mejor (−0.005).
  No hay un mínimo limpio.
- Las curvas de verde y azul tienen saltos del orden de 0.005, compatibles con el redondeo de las ventanas a bins
  enteros (`redondeo.py`). Sirven para descartar 1.362 en azul, pero no para ubicar un mínimo.

**¿Es trivial (más lrpx chico = más libertad)?** No.
1. R_train no es monótono: sube de nuevo en 1.20 y 1.16.
2. Held-out con 5 folds en rojo (cada LED de anillo < 7 queda fuera del entrenamiento en un fold, sin contar las dos de
   horcajadas; 148 LEDs pareadas): 1.16 → 0.404, 1.24 → 0.406 (+0.002 ± 0.004), 1.362 → 0.461 (+0.057 ± 0.007).
   - La penalidad de 1.362 en held-out (+14 %) es mayor que en entrenamiento (+5 %). El modelo con lrpx chico *predice*
     mejor las LEDs que no vio; no es sobreajuste.
   - El held-out no separa 1.16 de 1.24: su mínimo cae en ≤ 1.24, y la parábola de 3 puntos da 1.19, pero con poca
     resolución.

**Qué mide realmente el barrido (degeneración).** En unidades de píxel el modelo solo ve dos cosas:
- el radio de pupila ∝ NA·lrpx/λ;
- el paso de LED ∝ lrpx/z.

Bajar lrpx con z y NA fijos achica las dos a la vez y conserva z·NA, que es la frontera BF/DF medida, ≈ 7.03 mm.
Descomposición en rojo a lrpx 1.362 (`z102_desc_*`):

| variante | pupila (como lrpx) | paso (como lrpx) | R_train | ganancia vs 1.362 |
|---|---|---|---|---|
| final_z102 | 1.362 | 1.362 | 0.3310 | — |
| desc_paso (z = 108.5) | 1.362 | 1.28 | 0.3284 | −0.0026 |
| desc_pupila (NA 0.0649) | 1.28 | 1.362 | 0.3208 | −0.0102 |
| z102_m250 | 1.28 | 1.28 | 0.3153 | −0.0157 |

Barrido de NA con lrpx 1.362 y z 102 (paso fijo al del paso espectral, z/dx ≈ 75):
- NA 0.069 → 0.3310;
- NA 0.0649 → 0.3208;
- NA 0.062 → 0.3195;
- NA 0.059 → 0.3459 (rampa 2.6 rad: cambia la clasificación BF/DF).

Nunca llega al 0.3136 del mínimo en lrpx. Estos puntos además rompen z·NA = 7.03.

Lectura:
- Unos 2/3 de la preferencia vienen de la **pupila** (el residuo quiere un radio de pupila en píxeles ~8 % menor).
- El resto viene del **paso de LED**, que prefiere z/dx ≈ 102/1.25 = 81.6 mm/µm. El paso espectral medido daba
  ≈ 75, así que la tensión es de ~8 %.

**Conclusión.**
1. Con z = 102 y NA 0.069 (z·NA = 7.04, compatible con la frontera medida), el residuo rojo tiene su mínimo en
   lrpx ≈ 1.25 µm. Eso implica un **aumento ≈ 2.56×**: más cerca de 2.5× que de 2.35×, y lejos del nominal 2.28×
   (lrpx 1.40).
2. Por la degeneración, el mismo ajuste en píxeles se obtiene con el aumento nominal 2.28× si z = 102·1.40/1.25 ≈
   **114 mm** y NA = 7.03/114 ≈ **0.062**. El residuo no distingue «aumento 2.56×, z 102, NA 0.069» de «aumento 2.28×,
   z 114, NA 0.062».
3. **La tensión 2.28× contra 2.5× persiste.** Ahora es más precisa: el residuo fija NA·lrpx ≈ 0.086 µm y
   lrpx/z ≈ 0.0123 µm/mm. Para que el aumento sea 2.28× hace falta z ≈ 114 mm y NA efectiva ≈ 0.062.
   - z ≈ 114 contradice z ≈ 101–102 (geometría de julio y montaje).
   - NA 0.062 sería una pupila efectiva menor que la nominal 0.07 (viñeteo o aberración).
   - Alternativa: la pupila efectiva chica es en realidad borroneo no modelado (desenfoque o aberraciones). Encaja con
     que 2/3 de la ganancia venga de la pupila.
4. Verde y azul no confirman el mínimo rojo: verde prefiere ≥ 1.28 y azul es ruidoso. El que fija el número es el rojo,
   que es el canal con más contraste.
5. Ninguna corrida separa las dos lecturas: «2.28×, z 114, NA 0.062» es equivalente píxel a píxel a lrpx 1.25 con
   z 102 (solo cambia el ángulo del offset del die, que es casi una rampa). Hace falta una medida independiente:
   - el aumento (micrómetro);
   - o **z directo con regla**, más barato: z ≈ 102 favorece 2.56×, y z ≈ 114 favorece 2.28× con una NA efectiva
     reducida.

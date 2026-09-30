# Copia adaptada del TPWFP de Lucas (trabajo anterior, no original de este repo)

## Procedencia

| archivo | origen | sha256 |
|---|---|---|
| `original/real_images_reconstruction.py` | `~/Documents/LucasC/code/ptyco-full-simulator/real_images_reconstruction.py` | `bafb1445…bbeb1` |
| `original/common.py` | `~/Documents/LucasC/code/ptyco-full-simulator/common.py` | `36be284f…6b09a` |

- Los dos archivos de `original/` son copias textuales, sin tocar, del repo `ptyco-full-simulator` de Lucas Costilla (commit `fea5c80`, 2026-09-22, sin cambios locales), hechas el 2026-09-28.
- `real_images_reconstruction_rojo_2026-09-25.py` es la copia **adaptada**. Tiene la lógica de Lucas:
  - TPWFP de Bian 2016, con la variable de ruido `N`/`epsilon`;
  - paso `mu = min(1 - exp(-ndx/330), mu_max) / normest²`, con `mu_max` 0.4;
  - 76 iteraciones y métricas cada 5;
  - inicialización con la raíz de la imagen del medio de la lista, reescalada y agrandada con `skt.resize`;
  - diagnósticos de solapamiento y tasa de muestreo;
  - las mismas salidas: png, fase y magnitud `.npy`, imágenes intermedias, estadísticas de fase y los tres CSV.

  Las funciones que no necesitaban cambios se importan de `original/common.py`. Las que cambiaron están reescritas en la copia, con cada cambio marcado `# [CAMBIO Cn]`.
- `evaluar_tpwfp.py` la mide con los mismos criterios de `results/captura_2026-09-25_red/criterios.md`, para compararla con el método A+init.

Correr desde la raíz del repo:

```
python3 scripts/lucas_tpwfp/real_images_reconstruction_rojo_2026-09-25.py            # una reconstrucción, ~10 min
python3 scripts/lucas_tpwfp/evaluar_tpwfp.py --iteraciones 76 --procesos 2           # C1-C3 + sintético, ~2 h
```

Las salidas quedan en `results/captura_2026-09-25_red/tpwfp_lucas/` (fuera de git).

## Qué se cambió y por qué

Sin estos cambios, la copia no reconstruye estos datos. C3, C5 y C7 no son parámetros: son errores del modelo para esta captura, y C7 es un error del código en general.

| | cambio | original | ahora | cómo se verificó |
|---|---|---|---|---|
| C1 | datos | `fila*.tiff` crudos de una carpeta, sin oscuro ni exposición | los del 25/09 set 3 procesados igual que nuestras reconstrucciones: `prep.py` + `fpm_red.load_real`. Eso es (muestra − oscuro)/t, BF dividido por el flat, DF menos el flat suavizado y saturados enmascarados | mismo arreglo de datos que A+init |
| C2 | geometría | 680 nm, 2x, NA 0.10, z 76 mm, offset (4, 2) mm (julio 2025) | 630 nm, 2.5x, NA 0.07, píxel 3.2 µm, z 74 mm, eje en fila 17.5 (`y_offset` = −3 mm) | ventanas idénticas a `fpm_red` (assert en cada corrida) |
| C3 | orientación LED → frecuencia | `k[:2]` → (eje 0, eje 1): la columna del LED mueve el espectro a lo largo de las filas de la imagen | eje 0 ← −k_y (fila del LED), eje 1 ← +k_x | en los datos, los LEDs vecinos en fila corren los discos en vertical y los vecinos en columna, en horizontal (`results/captura_2026-09-25_red/figs/real_espectro_crudo_circulos.png`) |
| C4 | redondeo del índice k | `floor` | `round` | igual que `spectral_ops.led_crop_window` |
| C5 | radio de la pupila | `0.5·min(lr_shape)` = 200 px, que supone píxel = λ/(2NA) = 4.5 µm | NA/λ · N·dx = 56.9 px, porque el píxel es 1.28 µm, 3.5 veces más fino | idéntica a `optics.circular_pupil` |
| C6 | lienzo HR | `lr/ratio_LR` = 2821 px, con ventanas que se salen y `safe_slice` corriéndolas en silencio | factor 3 = 1200 px, como A+init; error si una ventana no entra | todas las ventanas entran |
| C7 | operador inverso (gradiente) | el bloque acumulado se pega en `mn0` y no en `mn0 − n0//2`; `safe_slice` lo corre y recorta en 0 las ventanas cercanas a `mn0`, así que **no es el adjunto del directo** | cada LED vuelve a su ventana, con la misma normalización (fft2 sin normalizar, /L) | test de adjunto: error relativo **1.42** en el original y **6e-16** en la copia |
| C8 | LEDs usados | cuadrado recortado + círculo, centrado en el LED (17,15) | los 169 capturados; el círculo queda como opción (`--radio-leds`), centrado en el eje real (17.5, 15) | |
| C9 | opcional, **no es la lógica original** | gradiente / L | gradiente / cobertura de cada píxel (`--cobertura`) | se evalúa aparte |

Además:
- Los píxeles saturados no aportan gradiente.
- La inicialización recorta a 0 los valores negativos, que aparecen en DF después de restar el flat.
- `sigma2` = 0, como se pasaba en el original.

## Resultados

Corrida del 2026-09-28: 76 iteraciones y los parámetros del original. Los resúmenes están en `results/captura_2026-09-25_red/tpwfp_lucas/eval/resumen_it76.json`. Se compara contra el método A+init del 25/09 (INFORME.md).

| | sin FPM | A+init (25/09) | TPWFP de Lucas (copia corregida, /L) |
|---|---|---|---|
| R held-out, real (menor es mejor) | 0.991 | **0.517 ± 0.022** | 0.985 ± 0.003 |
| R de los LEDs usados para reconstruir, anillos 4–8 (real) | — | — | 0.999–1.000 |
| FRC mitades en la banda, real | — | 0.026 | 0.085 (sin nulo, no interpretable) |
| FRC contra la verdad en la banda, sintético | — | 0.62 (A) / 0.72 (B) | 0.30 |
| FRC mitades en la banda, sintético | — | 0.157 (A) / 0.185 (B) | 0.081 |

Lectura:
- **Con su lógica, la copia corregida casi no pasa de la foto de campo claro.** Predice los LEDs apartados igual que no reconstruir (0.985 contra 0.991). Tampoco ajusta los LEDs de campo oscuro que sí usó: R ≈ 1 desde el anillo 4. En el sintético, donde se conoce la verdad, recupera la mitad que A o B.
- La causa es de diseño, no un error:
  - el gradiente se promedia sobre los L = 169 LEDs, pero cada frecuencia del espectro la cubren en promedio solo 2.3–3.0 LEDs (medido en todas las bandas). El paso efectivo queda en ~1/60 del nominal: como máximo 0.2 × 2.5/169 ≈ 0.003, o sea el solver queda prácticamente congelado fuera de lo que ya trae la imagen inicial;
  - la rampa `1 − exp(−ndx/330)` llega a 0.2 recién en la iteración 76.
  - Con la pupila grande del original (C5) cada frecuencia la cubrían muchos LEDs y ese efecto quedaba escondido.
- **La variante C9** (dividir por la cobertura en vez de por L) **diverge**: da NaN con `mu_max` = 0.4. Arreglarla exige cambiar el paso, y eso ya no es la lógica original.
- **Lo que sí sirve del original:**
  - el diagnóstico de solapamiento y tasa de muestreo: 31 % entre vecinos y η = 1.9, cuando el propio código pide η > 6;
  - encontrar C7, que afecta a toda reconstrucción hecha con `reconstruct_real_images_test` de `common.py`, incluidas las de julio de 2025.


## Parche para el repo original (puntos 1–6)

`parche_puntos_1-6.patch` es para `~/Documents/LucasC/code/ptyco-full-simulator` (commit `fea5c80`). No está aplicado: el repo original no se tocó. Para revisarlo y aplicarlo:

```
cd ~/Documents/LucasC/code/ptyco-full-simulator
git apply --check ~/Documents/LucasC/reproducible-research-template/scripts/lucas_tpwfp/parche_puntos_1-6.patch   # verificado: aplica limpio
git apply        ~/Documents/LucasC/reproducible-research-template/scripts/lucas_tpwfp/parche_puntos_1-6.patch
```

Todo lo que cambia está marcado `# [PARCHE punto N]`.

| punto | archivo | cambio |
|---|---|---|
| 1 | `common.py` | `inverse_linear_operator_real_images_vectorized`: cada LED vuelve a la misma ventana que usa el operador directo. Si una ventana se sale del lienzo, la corre igual que `safe_slice_lo`, así sigue siendo el adjunto y las simulaciones con ventanas en el borde no se rompen. **Afecta a los cuatro solvers que lo usan, incluidos los de simulación**: sus resultados van a cambiar, porque antes el gradiente caía en frecuencias corridas. |
| 4 | `common.py` | nueva función `k_a_ejes` y parámetro `orientacion` en `calculate_k_vectors_k_indices*`. El valor por defecto `"original"` deja igual a todos los demás scripts; `"actual"` es el montaje de hoy. El signo falta confirmarlo con una toma desenfocada. |
| 5 | `common.py` | `reconstruct_real_images_test` acepta `mask`, para que los saturados no aporten gradiente. La inicialización recorta a 0 los negativos. |
| 5 | `real_images_reconstruction.py` | nuevo cargador `cargar_captura`: exposición por LED (`<t>ms_recortada_<N>/`), resta del oscuro, división por t, saturados desde los cuadros crudos; los LEDs de campo claro se dividen por el flat y a los de campo oscuro se les resta el flat suavizado. |
| 2 | `real_images_reconstruction.py` | pupila con radio físico NA/λ · N · píxel / aumento (56.9 px, antes 200). |
| 3 | `real_images_reconstruction.py` | lienzo HR cuadrado, dimensionado con los corrimientos reales para que entren todas las ventanas (1064 px, antes 3599), con un `assert` que lo comprueba. |
| 6 | `real_images_reconstruction.py` | captura 25/09 set 3, rojo: 630 nm, NA 0.07, 2.5x, z 74 mm, offset (0, −3) mm, recorte 400; carpetas de muestra, oscuro y flat. Con el filtro de LEDs de siempre usa el círculo de radio 5 alrededor de (17,15): 81 LEDs. |

Verificado sobre una copia con el parche aplicado, con una corrida corta de 3 iteraciones con los datos del 25/09:
- test de adjunto: error 6e-16, y 8e-15 con ventanas que se salen del lienzo (antes 1.42);
- pupila idéntica a `optics.circular_pupil`;
- corrimientos k a ≤ 1 px de los de nuestras reconstrucciones (`floor` en vez de `round`, que no está en los puntos 1–6);
- datos preprocesados iguales a `fpm_red.load_real` (diferencia relativa 5e-8) y máscara idéntica;
- salida finita.

El parche **no** toca la normalización del paso (punto 7), así que con 76 iteraciones el solver sigue casi congelado; ver Resultados arriba.

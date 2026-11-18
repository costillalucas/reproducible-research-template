# Resultados 18/11/2026 — z = 143,5 mm, NA, exposición, grilla y red de 500 l/mm

Rojo, ROI 4160,1626 (1120 px), eje (17,15), grilla de 21×21 LEDs. Datos crudos en
`~/Documents/AleYLu/imagenes_tomadas/2026-11-18.*`; reconstrucciones en
`~/Documents/AleYLu/reconstrucciones/2026-11-18/` (no versionadas por tamaño).

## 1. La red de 500 líneas/mm se reconstruye: primera superresolución con período conocido

Captura `2026-11-18.2048ms-grilla.c` (red de transmisión de 500 l/mm, T nominal 2,0 µm), z = 145,6 mm por el
borde campo claro/oscuro, flat `2048ms-sinmuestra`, NA 0,0747, 160 iteraciones, validación por mitades.
Script: `correr_red500.sh`; análisis: `red500_espectro.py`; figura: `red500_reconstruccion.png`.

| Reconstrucción | Pico del espectro (amplitud) | Período | Pico/mediana de la banda |
| --- | --- | --- | --- |
| Completa | 0,499 µm⁻¹ | 2,01 µm | 165 |
| Mitad A (LEDs pares) | 0,508 µm⁻¹ | 1,97 µm | 119 |
| Mitad B (LEDs impares) | 0,512 µm⁻¹ | 1,95 µm | 105 |

- **El objetivo solo no puede ver esta frecuencia.** El corte coherente es NA/λ = 0,119 µm⁻¹ (período mínimo
  8,4 µm), y la cámara solo muestrea la imagen cruda hasta 0,388 µm⁻¹ (1,29 µm/px). En la imagen cruda de campo
  claro la red no aparece; en la reconstrucción aparecen líneas horizontales cada ~2 µm.
- **Las dos mitades, con LEDs disjuntos, dan el mismo período** (1,95–2,01 µm entre amplitud y fase).
  El vector de la red está a ~2,5° del eje de filas.
- **Antes de reconstruir, los datos crudos ya lo anticipaban.** En campo oscuro aparecen dos lóbulos opuestos,
  90 a 285 veces más brillantes que con esferas, a 7–10 pasos del eje: son los LEDs que mandan el orden ±1 a la
  pupila. El período que estimé a partir del centro de esos lóbulos (~1,85 µm) estaba sesgado; el espectro da 2,0 µm.
- **C1 = 0,794** (mitades 0,792 / 0,796; sin FPM 0,981): pasa, pero es más alto que con esferas (0,55). Un motivo
  posible es que el flat no incluye el sustrato de la red.
- **C3 = 0,061 "ALTO", pero es la red.** `lattice_score` mide la energía en picos aislados, y una red real tiene
  justamente eso. Sin sus órdenes ±1, ±2 y ±3, C3 vale **0,0077**, que pasa (≤ 0,01).

## 2. NA del objetivo: 0,0747, independiente de z

Radio del disco de campo claro en la FFT del LED del eje, calibrado con una curva radio→NA de simulaciones con
pupila circular (`na_pupila.py`, `na_pupila.json`, `na_pupila.log`):
13/11 (z ≈ 100) 0,0739 con flat y 0,0745 sin flat; 18/11 (z 143,5) 0,0747 ± 0,0009 y 0,0757 ± 0,0007, todos con
λ 0,630 (−2 % con λ 0,617). Desde a71f604 es el `NA_OBJ` por defecto de `scripts/reconstruir.py`.

## 3. Diseño 2×2 de exposición y NA (z 143,5; esferas): C1 no distingue los casos, el residuo por anillo sí

| C1 (anillos < 7) | NA 0,0669 | NA 0,0747 |
| --- | --- | --- |
| 1025 ms | 0,547 | 0,551 |
| 2048 ms | 0,559 | 0,552 |

Residuo held-out por anillo (`r_por_anillo.py`, `r_por_anillo.json`; hay que correrlo en la carpeta de
reconstrucciones): en los anillos ≤ 6 los cuatro casos son iguales. Desde el anillo 8, con 1025 ms el residuo sube
de 0,57 a 0,78; con 2048 ms queda entre 0,53 y 0,64. La diferencia en el anillo 12 es ~0,11, unas diez veces la
dispersión entre mitades. Esto confirma la predicción de Lucas, registrada antes del resultado, de que la exposición
importa en los anillos exteriores. La conclusión del 13/11 («la exposición no es el cuello de botella») dependía de
mirar solo C1. Limitaciones: un solo campo y sin piso de ruido, porque con un frame por LED la varianza vale 0.
Script: `correr_2x2.sh`.

## 4. El borde campo claro/oscuro mide z

| Toma | R (pasos) | z efectivo |
| --- | --- | --- |
| Esferas (tres chequeos) | 1,768–1,769 | 143,5 mm (referencia) |
| Grilla, soportes 2,4 + 0,8 mm | 1,807 | 146,7 mm |
| Grilla dada vuelta | 1,796 | 145,8 mm |
| Red de 500 l/mm | 1,794 | 145,6 mm |

## 5. Grilla de ~1 µm: fuera de banda

Vista en un microscopio de NA 0,65 (~10 líneas en 10 µm) e invisible con NA 0,25: T ≈ 1 µm. En rojo necesita
NA de iluminación ≥ 0,55, y la grilla de 21×21 llega a 0,39 en la cruz. Se capturó sin reenfocar
(`correr_grilla.sh`): C1 0,615 / 0,704, sin red en el campo oscuro ni en el espectro.

# Captura del 2026-09-28 (segunda tanda, ".b"): mapas de exposición usados

- Matriz a ~98 ± 2 mm (medida a mano), 15×15 LEDs (filas 11–25, columnas 8–22).
- Cada color en su propio foco, en las carpetas `2026-09-28.b_{green,red,blue}_enfocado`. Flats sin muestra de los tres colores con un solo mapa (`.b_rgb_sin_muestra`) y oscuros de 4, 8, 16, 32, 64, 128 y 250 ms.
- **Verde** (`leds_por_tiempo_verde.py`): predicción de `scripts/exposicion_z100.py 98`, a partir de la captura del 28/09 a 74 mm. En la toma, el campo claro quedó subexpuesto a 4 ms y se repitió a **16 ms**. Faltaron 58 LEDs por un error de tipeo, `(244, 18)`, y se completaron.
- **Rojo y azul** (`leds_por_tiempo_rojo.py`, `leds_por_tiempo_azul.py`): la misma predicción, **calibrada** con lo medido a 98 mm:
  - campo claro: el de 74 mm escalado por (74/98)², con el perfil entre LEDs medido en verde (y en rojo, para el azul);
  - campo oscuro: el factor medido/predicho por rango de ángulo, del verde para el rojo y del rojo para el azul;
  - pico objetivo: ≤ 3600 cuentas.
  - Resultado de la calibración: campo claro a 1.08 (rojo) y 1.02 (azul) veces lo predicho.
- **Flats** (`leds_por_tiempo_flats_rgb.py`): para cada LED, el mínimo de los tres mapas; campo claro a 8 ms para que el verde sin muestra no sature.
- Chequeos de cada toma: `results/exposicion_2026-09-28_z100/chequeo_b_{green,red,blue}.csv`, fuera de git.

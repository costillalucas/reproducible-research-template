# Evolución de la fase con las épocas (28/09 b, A+init, z = 98 mm, campo entero) — 2026-10-01

**Estado: completo para los tres colores.** Tablas: `python3 results/fase_2026-10-01/epocas/resumen.py`.

## Método (`analizar_fase.py`)
- Rejillas: rojo 1200 px → 0.4267 µm/px; verde/azul 2000 px → 0.256 µm/px (campo de 512 µm).
- Fase: `unwrap_phase(angle)` + polinomio de orden 2 sobre el 70 % de píxeles cercanos a la mediana (convención de
  `make_fig_fase_2809b.py`); referencia = mediana del fondo (fuera de las partículas dilatadas).
- Partículas: elegidas en la época 400 sobre la fase pasa-altos (resta de gaussiana de 12 µm), umbral max(0.35, 6·MAD),
  aisladas, excentricidad < 0.8, solidez > 0.85; 16 repartidas por tamaño. Por época: recorte propio, desenrollado
  local, fondo = mediana de un anillo. Pico = p95 − fondo; volumen = Σ(φ − fondo)·área de píxel.
- Época 0 y 1: la fase es idénticamente 0 (inicialización solo de amplitud; la fase arranca en la época 2).

## Rojo (resultados)
| época | std fondo robusta (rad) | std fondo pasa-altos | rango del polinomio (rad) | frac. píxeles desenrollados | cambio rel. fase |
|---|---|---|---|---|---|
| 5 | 0.058 | 0.076 | 0.007 | 0.020 | 0.55 |
| 30 | 0.230 | 0.177 | 0.042 | 0.022 | 0.45 |
| 40 | 3.16 | 0.253 | **12.8** | **0.74** | 0.99 |
| 120 | 1.51 | 0.182 | 25.6 | 0.68 | 0.98 |
| 160 | 1.19 | 0.175 | 28.3 | 0.70 | 1.05 |
| 400 | 1.03 | 0.184 | 27.8 | 0.71 | 0.40 |

- **Deriva de baja frecuencia:** entre las épocas 30 y 40 aparece una rampa de fase global que crece hasta ~28 rad de
  pico a pico a la época 160 y luego queda fija. Es el gradiente rojo de la figura RGB. Una rampa lineal equivale a un
  corrimiento del espectro (error de k / posición de LED). Hace que el 70 % de los píxeles necesite desenrollado.
- **Ruido local del fondo** (pasa-altos): crece de 0.08 (época 5) a 0.25 (época 40) y baja a 0.18 (160-400).
- **El mapa de fase no converge** en rojo: el cambio relativo entre épocas guardadas sigue en 0.4 entre 320 y 400.
- **Partículas** (`resumen.py`): las de 7.8 y 8.7 µm tienen pico estable desde la época 3 (6.6 → 6.4 y 7.0 → 7.1 rad
  entre 5 y 400) y volumen estable (±10 %). Las > 10 µm fluctúan mucho (pico 5.4-14.9 rad, volumen ×0.3 a ×4 entre
  épocas), con ruido de anillo de 0.3-1.2 rad: probable falla de desenrollado sobre la rampa. No hay un aumento monótono
  del volumen en las grandes; la razón vol 400/120 = 1.39 (d > 6 µm) viene de dos partículas que oscilan.
- Las "partículas" de 1-2 µm muestran picos de 2-4 rad que **bajan** con las épocas (p. ej. 4.1 → 2.7). Es demasiada fase
  para su tamaño, con Δn ≈ 0.05 en DMSO. Probablemente sean artefactos o bordes, no partículas pequeñas reales.

## Verde y azul (resultados)
| | std pasa-altos 5 / 40 / 400 | rango polinomio 40 / 160 / 400 | fondo lento (σ 30 px) 40 / 400 | cambio rel. fase 320→400 |
|---|---|---|---|---|
| verde | 0.072 / 0.114 / 0.125 | 0.015 / 0.042 / 0.134 | 0.073 / 0.232 | 0.40 |
| azul | 0.073 / 0.106 / 0.113 | 0.029 / 0.066 / 0.232 | 0.050 / 0.133 | 0.26 |

- **Sin salto como el del rojo.** La fracción de píxeles desenrollados queda en 1.6-1.8 % en todas las épocas.
- **Ruido local** (pasa-altos): se estabiliza en la época 40, en 0.11-0.12 rad.
- **Fondo lento:** crece de forma sostenida desde la época 160, poco antes en el azul. La std robusta del fondo pasa de
  0.12 a 0.23 rad (verde) y de 0.10 a 0.16 rad (azul) entre las épocas 40 y 400. Es una deriva lenta, mucho menor que
  los 28 rad del rojo, pero que no para.
- **Azul (el más limpio):**
  - Partículas de 6-15 µm: pico estable desde la época 5-30 (p. ej. 6.3 → 6.5 rad, 8.0 → 8.2 rad). Volumen 400/40 = 1.00.
  - Partículas de 1-2.4 µm: siguen ganando fase después de la época 40. Pico 400/40 = 1.16, volumen 400/40 = 1.21; entre
    120 y 400 ya es solo ×1.03.
- **Verde:**
  - Las partículas que se desenrollan bien son estables desde la época 5. Por ejemplo, 6.3 µm: 6.45 → 6.33 rad; 13 µm:
    12.8 → 12.3 rad; 18 µm: volumen 2179 → 2203.
  - Unas 6 de las 13 grandes tienen saltos de 2π en el desenrollado local (volúmenes negativos, picos que saltan de
    1.8 a 12 rad). Sus razones agregadas (×1.9, ×−5.6) son artefacto, no física.

## Respuesta
- **Fase de partículas medianas:** satura temprano (época ≤ 5) y no cambia hasta la 400.
- **Fondo:** se degrada. Aparece una rampa global en 30-40 que se estabiliza recién a 160. El mapa sigue cambiando
  a la 400.
- No hay evidencia limpia de que las partículas grandes ganen fase (señal de sub-recuperación): sus curvas son ruido
  de desenrollado, no una tendencia.

- **Verde y azul:**
  - La fase de las partículas satura temprano: hacia la época 5 en las grandes y medianas, hacia la 120 en las pequeñas
    (el azul gana 16-21 % entre 40 y 400).
  - No hay señal de sub-recuperación en las grandes: en el azul el volumen 400/40 = 1.00.
  - Lo que se degrada es el fondo lento, que crece desde la época 160.
- **Resumen:** las partículas se estabilizan a las ≈ 5 épocas (grandes) y a las ≈ 120 (pequeñas). El fondo empeora con
  más épocas: en el rojo hay una rampa de ≈ 28 rad desde la época 30-40; en verde y azul, una deriva suave desde la 160.
  El mapa no converge en ningún color: el cambio relativo entre 320 y 400 es 0.26-0.40.

Figuras: `fig_a_fase_pico.png`, `fig_b_volumen_fase.png`, `fig_c_tira_fase.png`. La tira está centrada en la partícula
más grande de cada color; la escala satura en el p99.8 de la época 400, 21.7 rad.

# Recuperación de pupila (EPRY) en 28/09b rojo con la geometría z102 (2026-10-05)

**Pregunta.** El residuo prefiere un aumento de ≈2.5x (lrpx 1.28 µm) aunque la óptica nominal da ≈2.28–2.35x.
¿Será que, con la pupila ideal fija, la geometría compensa aberraciones de pupila (desenfoque, etc.)? Si es así,
al dejar libre la pupila la preferencia por 2.5x debería desaparecer y la pupila recuperada debería tener un
desenfoque o una inclinación del tamaño necesario.

## Qué existe (no se escribió nada en `src/`)
- `src/ptyco_full_simulator/reconstruction.py::reconstruct(recover_pupil=True, epry_alpha, epry_beta, step_relative)`:
  EPRY (ou2014 Eq. 3/4), con soporte fijo en el círculo de NA ideal. Su docstring trae dos advertencias. Puede
  empeorar reconstrucciones chicas sin aberración (tests/test_epry_pupil_recovery.py). Además, sin `step_relative`
  el paso queda dividido por lr_n_px y la pupila prácticamente no se mueve con recortes grandes (el "paso congelado"
  de forks H/K, roadmap 6.10).
- `results/captura_2026-09-*/fpm_red.py::reconstruct(epry=True)`: el solver que usan los runners reales, con mu
  constante y sin división por N. Antecedente: en la CV del set 3 (25/09, `captura_2026-09-25_red/INFORME.md`) dio
  "B + EPRY" R 0.529 ± 0.020, peor que A+init (0.517), y por eso no se adoptó. Desde entonces ningún runner real
  la usa (`iter_runner`/`offset_color` corren "sin EPRY").

## Qué se corrió
`epry.py` copia el lazo de `iter_runner.reconstruct_snap` (A+init, rampa mu = 0.3(1−e^{−0.3 it}), máscara de
saturados) y la geometría de `offset_color_2026-10-02/runner.py`: z = 102, NA 0.069, die rojo +1.06 mm, sin
(18,14) ni (18,16), factor 3. Le agrega la actualización EPRY de la pupila desde la época 5, con paso β·mu. No se
importa ni se edita `runner.py`.
- **Control:** sin actualizar la pupila reproduce exactamente z102_m250 (R 0.9826 / 0.4603 / 0.4314 en las épocas 1–3).
- Corridas: tarea full, 40 épocas, 1 núcleo (~9 min cada una). Dos aumentos, 2.5 (z102_m250) y 2.35 (final_z102),
  cada uno con β = 1 y β = 5.
- Métrica: `train_R` (R afín por LED, medio sobre los LEDs de entrenamiento), calculada con la pupila recuperada. Es
  la misma métrica que `offset_color`, así que los números se comparan contra sus corridas de pupila fija.
- `zernike.py`: ajusta la fase desenvuelta sobre el soporte, ponderada por |P|, con Zernikes de Noll (rms 1).
  Convierte a unidades físicas así: Δz = 2√3·c4·λ/(π NA²) y Δx = c2/(π NA/λ). Se validó con una pupila sintética
  (30 µm y 1.5 µm se recuperan exactos).

## Resultados
train_R por época:

| | 5 | 12 | 20 | 30 | 40 |
|---|---|---|---|---|---|
| fija, 2.5x | 0.3994 | 0.3528 | 0.3328 | 0.3209 | **0.3153** |
| fija, 2.35x | 0.4126 | 0.3707 | 0.3491 | 0.3369 | **0.3310** |
| EPRY β=1, 2.5x | 0.3994 | 0.3548 | 0.3362 | 0.3247 | 0.3175 |
| EPRY β=1, 2.35x | 0.4126 | 0.3724 | 0.3527 | 0.3388 | 0.3311 |
| EPRY β=5, 2.5x | 0.3994 | 0.3590 | 0.3421 | 0.3311 | 0.3239 |
| EPRY β=5, 2.35x | 0.4126 | 0.3758 | 0.3584 | 0.3444 | 0.3355 |

- **EPRY no mejora el residuo en ningún caso.** La pérdida de amplitud del solver baja (0.0133 → 0.0102), pero R
  empeora o queda igual, y empeora más cuanto más rápido se mueve la pupila. Es el mismo patrón de sobreajuste que
  describe el docstring de `src`.
- **La ventaja de 2.5x sobre 2.35x se mantiene.** En la época 40, ΔR(2.35 − 2.5) vale 0.0157 con pupila fija, 0.0136
  con β=1 y 0.0116 con β=5. Se achica un 13–26 %, pero porque 2.5x empeora más, no porque 2.35x mejore. Con pupila
  libre, 2.35x sigue peor que 2.5x con pupila fija.

Pupila recuperada en la época 40 (rad, Noll):

| corrida | rms fase | Z4 desenf. | Δz equiv. | Z2/Z3 incl. | Δx equiv. | Z5/Z6 astig. | Z7 coma y | \|P\| último anillo | r_eff / soporte (bins) |
|---|---|---|---|---|---|---|---|---|---|
| β=1, 2.5x | 0.070 | −0.052 | −7.5 µm | +0.001/+0.011 | ≤0.03 µm | ≤0.001 | +0.028 | 0.89 | 53.9 / 56.1 |
| β=1, 2.35x | 0.078 | −0.054 | −7.8 µm | +0.018/+0.004 | ≤0.05 µm | ≤0.002 | +0.032 | 0.81 | 55.0 / 59.7 |
| β=5, 2.5x | 0.134 | −0.101 | −14.8 µm | +0.000/+0.019 | ≤0.05 µm | ≤0.003 | +0.045 | 0.83 | 53.9 / 56.1 |
| β=5, 2.35x | 0.140 | −0.099 | −14.5 µm | +0.032/+0.005 | ≤0.09 µm | ≤0.003 | +0.051 | 0.72 | 54.5 / 59.7 |

- **Las aberraciones de fase son chicas y no convergen.** El desenfoque crece casi lineal con el paso acumulado: con
  β=1 se duplica entre las épocas 20 y 40 (−3.8 → −7.5 µm). Escala con β y es **el mismo en los dos aumentos**. Aun
  en el peor caso, 15 µm es un 11 % de la profundidad de campo λ/NA² = 132 µm: 0.35 rad de fase en el borde, menos
  que λ/4. La inclinación es menor que 0.1 µm, y además una inclinación de pupila solo traslada la imagen (se
  confunde con un corrimiento del objeto, no con una escala). El astigmatismo es nulo. Hay algo de coma en y (el
  eje de filas LED, el mismo del offset del die), de 0.03–0.05 rad.

## ¿Puede esto imitar un cambio de aumento o de z?
En este modelo, lrpx entra en dos cantidades medidas en bins de frecuencia: el radio de la pupila (∝ NA·lrpx) y el
paso de LED (∝ lrpx/z). Pasar de 2.35x a 2.5x con NA y z fijos equivale a dejar lrpx fijo y cambiar a NA·0.94 y z/0.94,
porque una escala común se absorbe en el objeto. Concretamente, el radio de la pupila pasa de **59.7 a 56.1 bins**.
- Una fase de pupila (desenfoque, inclinación) **no cambia el radio del soporte**. Además, la que aparece no depende
  del aumento: es igual en 2.5x y en 2.35x, así que no está compensando la geometría.
- Donde sí aparece una diferencia es en la **amplitud del borde**. Con 2.35x, EPRY baja |P| en el anillo exterior
  hasta 0.72–0.81, contra 0.83–0.89 con 2.5x. El radio efectivo de amplitud queda en 54.5–55 bins, cerca del radio
  del soporte de 2.5x (56.1). Es un indicio, débil, de que lo que el residuo quiere es una **pupila efectiva más
  chica en bins** (NA efectiva ≈ 0.064 con 2.35x) y no un aumento distinto. Pero EPRY no logra convertir eso en un
  R mejor.

## Conclusión
La hipótesis "la geometría compensa un desenfoque o una inclinación de pupila" **no se sostiene**. La pupila
recuperada tiene desenfoque de ~8–15 µm (≪ DOF 132 µm), sin astigmatismo y con inclinación despreciable. Es
idéntica en los dos aumentos. Dejarla libre no mejora el residuo y no borra la preferencia por 2.5x (la reduce
≤26 %, y lo hace degradando 2.5x). La única señal que depende del aumento es una caída de amplitud en el borde de la
pupila con 2.35x. Eso apunta a la NA efectiva o a la apodización del borde (soporte en bins), no a la fase.
Siguiente prueba barata: con 2.35x, barrer NA (0.064–0.069) con pupila fija y ver si iguala a 2.5x/0.069.

## Advertencias
- La métrica es train_R de la tarea full. Faltan held-out y CV: el antecedente de CV del 25/09 con EPRY también fue
  negativo.
- Son 40 épocas, la pupila no convergió (sigue creciendo) y no hay regularización. Con más épocas la fase podría
  crecer, pero la tendencia de R va en contra de EPRY.
- Variante EPRY propia: arranque en la época 5, la misma rampa mu del objeto y β·mu para la pupila. No es
  exactamente `src` (`step_relative`) ni `fpm_red` (mu constante). Se hizo un solo color (rojo) y una sola
  geometría de LEDs.
- r_eff = sqrt(Σ|P|²/⟨|P|²⟩_{r<0.3}/π) es una medida tosca del radio efectivo.

## Archivos
`epry.py` (uso `python3 epry.py VARIANTE MAXEP PSTART TAG [BETA]`), `zernike.py` → `zernike.json`,
`out/<variante>_<tag>/` (metrics.jsonl con R por LED, obj/pupil en las épocas 5/20/40, done.json), `logs/`.
`out/z102_m250_ctrl/` es el control de reproducción (3 épocas).

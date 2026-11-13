# Por qué no converge la fase con 1 solo BF (simulación, 12/11)

Todo es simulación, hecha en ~15 min de reloj. `python sim_1bf_diag.py` (semillas fijas) regenera `runs.jsonl`, `fig1_mapas.png` y `fig2_variantes.png`. Importa sin modificar `sim_z.py`, `sim_z_clave.py` y `sim_z_1bf.py` (mismos datos: sin crimen inverso, Poisson + lectura, exposición extra de 5 ms).

**Cobertura:** z = 73 mm (1 BF real) y z = 103 mm (1 BF artificial), objetos 0 y 1, semilla 0, 14 variantes (n = 2 objetos por z, una sola semilla: sin desvíos útiles). Las tablas de abajo son de z = 73, objeto 0; el resto está en `runs.jsonl` / `run.log` y en `fig2_variantes.png`. Este informe se escribió con z = 73 completo (ambos objetos) y z = 103 objeto 0 hasta la variante `unit_1.0`; las filas posteriores de z = 103 se generaron después y **no fueron revisadas** al redactar.

**Los otros casos repiten el patrón:** z = 73 objeto 1: base 2.02 rad (DC aparte 0.40, θ 0.89), init verdad 0.06, init conj 2.69 (DC aparte 0.09, θ 1.38), lotes 2.68 (0.09, θ 1.39), prior fase pura 2.24-2.66. z = 103 objeto 0: base 2.34 (DC aparte 0.20, θ 1.04), init verdad 0.06, init conj 2.68 (0.06, θ 1.34), AP 2.55 (0.12), Poisson 2.58 (0.10), intensidad 1.79, prior fase pura 2.66. Con más solapamiento (49 %) el mínimo falso es el mismo.

## Diagnóstico: a qué solución converge

Se ajustó la reconstrucción a la verdad de varias formas (RMS de fase en esferas, rad; z = 73, objeto 0):

| variante | err | fase (cte. global) | fase invertida (conj) | gemela conj(o(-r)) | 2 ctes.: DC aparte | θ DC (rad) |
|---|---|---|---|---|---|---|
| ePIE base, 20 épocas | 0.183 | 2.12 | 0.67 | 1.73 | 0.49 | 0.93 |
| init = verdad | 0.020 | **0.05** | 2.48 | 1.70 | 0.04 | 0.00 |
| init = verdad + 0.5 rad ruido de fase | 0.366 | 0.37 | 2.45 | 1.74 | 1.52 | -0.01 |
| init = conj(verdad) | 0.242 | 2.69 | 0.30 | 1.75 | **0.08** | 1.35 |
| init fase al azar | 0.963 | 1.63 | 1.91 | 1.74 | 1.72 | -0.12 |

"2 ctes.: DC aparte" = se ajusta una constante compleja al pixel DC del espectro y otra a todo el resto; θ es la fase relativa entre ambas.

- **No es imagen gemela, ni espejo, ni rampa/desplazamiento** (la gemela da 1.7 rad en todos los casos).
- **Es un mínimo falso en el que la onda no difractada (DC) queda rotada ~0.9-1.5 rad respecto del campo difractado.** El campo difractado (todo menos DC) está bien: con sólo re-rotar el DC el error cae a 0.08 rad (init conj, lotes) o 0.18-0.49 (ePIE, AP, 20 épocas, aún sin terminar de llegar). Con una sola constante global ese estado se parece a la fase con signo invertido (conj: 0.3-0.7 rad), por eso "≈2 rad".
- **El mínimo correcto existe y es estable** (init = verdad se queda en 0.05 rad, err 0.020). Es un problema de mínimo local / inicialización, no de falta de información en los datos. El init con ruido también conserva θ = 0; su 0.37 rad es mayormente ruido blanco que quedó fuera del soporte medido (artefacto de la perturbación elegida, no deriva).
- Interpretación (no demostrada): el DC sólo aparece en la pupila del único BF, así que su fase relativa al resto la fija una sola imagen, |DC + s_bajo|². Con esferas de 5 µm poco resueltas en BF, s_bajo es casi "una mancha real por una constante compleja", y esa imagen admite dos fases de DC (reflexión). Con 5 BF el DC entra en 5 pupilas distintas y la ambigüedad se rompe. El init con amplitud BF y fase plana cae del lado equivocado.

## Otros solvers / costos / prior (z = 73, objeto 0, 1 BF)

| variante | err | fase esferas | 2 ctes. DC | θ DC |
|---|---|---|---|---|
| AP (paso 1, sin rampa) | 0.206 | 2.36 | 0.18 | 1.11 |
| costo intensidad (Gauss), 30 ép. | 0.156 | 1.49 | 0.28 | 0.76 |
| costo Poisson, 30 ép. | 0.209 | 2.37 | 0.21 | 1.13 |
| gradiente por lotes, paso adaptativo + inercia, 60 it. | 0.243 | 2.67 | 0.08 | 1.35 |
| prior fase pura, mezcla 0.5, 30 ép. | 0.259 | 2.67 | 0.27 | 1.49 |
| prior fase pura, proyección total, 30 ép. | 0.255 | 2.54 | 0.50 | 1.47 |
| ídem, 60 ép. | 0.262 | 2.65 | 0.35 | 1.51 |
| prior sólo en las 10 primeras épocas | 0.239 | 2.53 | 0.28 | 1.33 |
| prior + lotes, 60 it. | 0.201 | 1.73 | 1.72 | 0.48 |

**Resultado nulo: ningún solver, costo ni el prior |o| = cte rescata el 1 BF.** Todos caen en el mismo mínimo de DC rotado (θ 0.8-1.5 rad). El prior de amplitud unitaria, tal como se implementó (proyección o/|o| por época, recortada al soporte medido), no saca al solver del mínimo falso y con lotes empeora. El costo de intensidad es el menos malo (1.49 rad) pero no converge.

## Qué información mínima haría falta

No se encontró. Lo que el diagnóstico sugiere, **sin probar**: (i) el error es casi de un solo parámetro (la fase del DC), así que un barrido de θ sobre la solución convergida, eligiendo el menor residuo de datos, o un init con el signo de fase correcto (p. ej. fase inicial positiva en las esferas por saber que n_esfera > n_medio) podría bastar; (ii) un segundo BF, aunque sea uno solo, rompe la simetría. Que init = conj(verdad) termine con el campo difractado correcto y sólo el DC rotado indica que el DF está bien cosido a 30 % de solapamiento cuando el punto de partida es bueno.

## Límites

- Una sola semilla de ruido, 2 objetos, 2 alturas. Sin desvíos: diferencias de décimas de rad entre variantes no son significativas.
- Simulación idealizada (sin aberraciones, desenfoque ni error de posición), esferas de fase casi pura, 20-60 épocas, pupila conocida.
- No se probaron: TV de fase, inicialización espectral, barrido de θ, prior de signo. El prior de fase pura se probó en una sola forma (proyección dura/mezcla), sin pesos ni recocido.
- No se midió el costo de datos del mínimo falso contra el del verdadero: no se sabe si el falso es un mínimo local más alto (rescatable con búsqueda) o casi degenerado con ruido.
- La explicación de la ambigüedad de dos fases de DC es una hipótesis compatible con los números, no una demostración.

## Archivos

`sim_1bf_diag.py`, `runs.jsonl`, `run.log`, `fig1_mapas.png` (fases, error y espectro del error), `fig2_variantes.png` (fase por variante), `INFORME.md`.

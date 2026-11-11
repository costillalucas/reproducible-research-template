# Resultados 2026-11-11

Respaldo del experimento de recortes del 11/11: reconstruir recortes chicos (20×20 px crudos) centrados en partículas
aisladas y compararlos con las mismas partículas medidas dentro de una reconstrucción grande (200 o 400 px). Se
copiaron los archivos livianos (informes, figuras, tablas, `.json`/`.csv` y código), sin `.npy` ni las corridas. Los
originales están en `AleYLu/reconstrucciones/plan_2026-11-11/`.

Motivo: el tamaño físico del recorte L fija la grilla de Fourier, Δk = 1/L. El radio de la pupila en bins es
(NA/λ)·L. Con L ≈ 26 µm la pupila mide ~2–3 bins y el paso entre LEDs ~2.4 bins. Si el solver redondea el k de cada
LED, el error de geometría puede llegar a ~27 %. Para que quede por debajo de 3 % hace falta L ≳ 180 µm (~140 px).

## Redondeo en el solver

- El solver redondea el k de cada LED al bin entero más cercano (`ptyco_full_simulator/spectral_ops.py:34-35`,
  `int(round(...))`). No hay corrimiento subpíxel. La pupila es una máscara binaria (`optics.py:22-27`).
- El driver clasifica campo claro y campo oscuro con el k **exacto** (`reconstruir_plan.py:547`), pero el modelo usa
  el k **redondeado**. Con recortes chicos, esa diferencia hace que un LED del primer anillo cambie de clase.

## 1. PS 500 nm en aire, captura 30/10 red-c (`recortes/`)

Geometría z 99.5 mm, λ 0.617 µm, NA 0.072 (NA·z 7.16, el borde medido en esa captura), 160 épocas. 25 partículas
aisladas en tres recortes de referencia de 200 px.

- Error de redondeo: 15 % de mediana y 27 % de máximo a 20 px; 13 % a 40 px; 2.6 % a 200 px.
- En 20 de los 25 recortes de 20 px, un LED diagonal de campo oscuro, (16,14), (18,14) o (18,16), queda adentro de
  la pupila después del redondeo. El error del solver con ese salto es ≈ 0.50, contra ≈ 0.01 sin él.

| brazo | FWHM amplitud (µm), mediana | correlación con 200 px |
|---|---|---|
| imagen cruda (LED central) | 5.29 | — |
| 200 px | 3.09 | — |
| 20 px | 3.38 | 0.79 |
| 20 px sin el LED que cambia | 3.28 | 0.87 |
| 40 px | 3.19 | 0.93 |
| 80 px | 3.04 | 0.94 |

- Nulo con campo oscuro mezclado: la partícula desaparece y queda solo un grano fino. El ajuste da ~0.9 µm, igual que
  sobre el fondo.
- Pasar de 5.3 a 3.1 µm **no es un factor de resolución**. El ajuste toma un lóbulo brillante en la imagen cruda y un
  núcleo oscuro con anillo en la reconstrucción, y sobre el fondo vacío ya da ~2 µm. 3 µm sigue siendo mucho más que
  0.5 µm, así que esto no demuestra superresolución.

## 2. Esferas de 5 µm en DMSO, captura 03/11 red (`recortes_5um/`)

Geometría B (z 102 mm, NA 0.0669, λ 0.63 µm), 160 épocas. La referencia es `epocas_400b` a 160 épocas y el nulo es
`red_nulo_df`. 18 esferas medidas; 14 sin fase envuelta.

- Mismo mecanismo, al revés: el LED de campo claro (17,16), a 0.955 de NA/λ, el modelo lo trata como campo oscuro. Pasa
  en las 18 esferas a 20 px, en 6 de 12 a 80 px y en ninguna a 40 px. Que falle o no depende de dónde cae el
  redondeo, no solo del tamaño del recorte.

| brazo | borde 10–90 % (µm) | FWHM fase (µm) | volumen de fase (rad·µm²) |
|---|---|---|---|
| imagen cruda | 3.90 | 7.46 | — |
| referencia 400 px | 1.82 | 3.19 | 18.1 |
| 40 px | 1.82 | 3.28 | 18.3 |
| 20 px tal cual | 2.79 | 3.91 | 43.7 |
| 20 px sin el LED que cambia | 1.81 | 2.98 | 21.7 |
| nulo 400 px | ≈1.6 | — | 7.2 |

- El ancho del borde **no** separa la señal real del nulo. El volumen de fase sí: 18 contra 7, menor en el nulo en las
  14 esferas.
- El FWHM de fase reconstruido, 3.2 µm, queda por debajo de los ~4.3 µm que daría una esfera de 5 µm. Puede ser que
  las partículas sean polidispersas o que haya un sesgo de la reconstrucción. Está sin resolver.
- A 20 px sin el LED que cambia queda un sesgo sin explicar de +17 % de volumen y 0.7 µm de corrimiento.

## Conclusión

Con recortes de 200–400 px no hay problema con esta geometría: el margen del LED más cercano al borde es mayor que el
redondeo. La solución de fondo es que el modelo y la clasificación usen el mismo k. Queda abierto cuál arreglo
adoptar: (a) clasificar con el k redondeado o (b) que el modelo use el k exacto, con un corrimiento subpíxel. Hay
que ver cuál resuelve el desacuerdo entre el modelo y los datos.

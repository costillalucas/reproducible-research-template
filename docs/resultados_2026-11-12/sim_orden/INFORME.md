# Tarea B — ¿Importa el orden en que se recorren los LEDs? (simulación, 12/11)

**Respuesta corta:** el orden cambia la **velocidad** de convergencia (mucho, en las primeras ~40 épocas), pero **no el resultado final**: a 100 épocas todos los órdenes secuenciales dan el mismo error dentro de la variabilidad entre semillas. El orden actual del solver (anillo creciente, BF hacia afuera) es el más rápido de los probados. Lo único que sí cambia el resultado a igual número de épocas es pasar de secuencial a **lote completo**, que es 5-6 veces peor. Ninguna de las ideas adaptativas probadas le gana al anillo creciente.

## Método

- Scripts: `sim_orden.py` (simulación; `python sim_orden.py`) y `analiza_orden.py` (tablas y figuras; correr con `PYTHONIOENCODING=utf-8`). Semillas fijas (objeto+ruido: `1000+seed`; barajados: `7000+seed`). Resultados crudos: `runs.jsonl`, `rec/*.npz`; tabla completa: `tabla.md`.
- Geometría imitando la real: 15x15 LEDs, paso 6 mm, z = 102 mm, NA 0.07, 0.63 µm, píxel LR 1.28 µm, factor 3 (NA_syn ≈ 0.57, 5 LEDs de campo claro). Cobertura media 4.75 LEDs por píxel de frecuencia (máx 8).
- Objeto: 4 esferas de 5 µm (dn = 0.046, fase central 2.29 rad, 2 % de absorción), HR 96x96, LR 32x32. Ruido: Poisson (BF ≈ 5000 e-, DF con exposición 20x) + lectura 2 e-. Las mismas LR para todas las variantes de una semilla.
- Lazo: copia de `reconstruct` de `scripts/fpm_solver/fpm_red.py` (rama sin EPRY: `spec[win] += mu * P * D`, init `kron`), generalizado a orden arbitrario por época, lotes y paso por LED.
- Variantes corridas: `anillo_crec` (actual), `anillo_decr` (HF primero), `aleat_epoca` (re-barajado), `snake` (raster), `lote` (suma de las 225 correcciones dividida por la cobertura, una aplicación por época), `minilote15`, y las adaptativas `residuo_desc` (cada época procesa primero el LED con peor residuo relativo de la época anterior) y `anillo_paso_decr` (anillo creciente con paso 1 -> 0.4 del centro al borde).
- Pasos: `rampa` = mu = 0.3(1-exp(-0.3 it)) (solver real), 160 épocas; `fijo1` = mu = 1 (proyección completa), 40 épocas.
- Métricas: error complejo relativo vs verdad en la banda sintética (sin DC, fase global ajustada), costo de amplitud sobre las LR, FRC por bandas (BF 0-1, bajo 1-3, medio 3-5.5, alto 5.5-8.1 NA_obj), fase central de las esferas.

## Resultados (media ± desvío entre semillas; n = nº de semillas)

Error complejo, paso `rampa`:

| variante | n | época 40 | época 100 | época 160 | FRC alto ép. 40 |
|---|---|---|---|---|---|
| anillo_crec (actual) | 3 | 0.044 ± 0.009 | 0.0244 ± 0.0014 | 0.0245 ± 0.0014 | 0.90 ± 0.04 |
| anillo_decr | 3 | 0.123 ± 0.016 | 0.0246 ± 0.0016 | 0.0246 ± 0.0015 | 0.43 ± 0.14 |
| aleat_epoca | 3 | 0.102 ± 0.029 | 0.0245 ± 0.0014 | 0.0244 ± 0.0013 | 0.56 ± 0.22 |
| residuo_desc (adaptativo) | 3 | 0.101 ± 0.019 | 0.0246 ± 0.0013 | 0.0247 ± 0.0014 | 0.58 ± 0.18 |
| minilote15 | 3 | 0.122 ± 0.019 | 0.0258 ± 0.0028 | 0.0244 ± 0.0014 | 0.49 ± 0.15 |
| lote | 3 | 0.46 ± 0.04 | 0.24 ± 0.04 | 0.140 ± 0.031 | 0.13 ± 0.13 |
| snake | 2 | 0.120 ± 0.008 | 0.0242 ± 0.0017 | 0.0240 ± 0.0017 | 0.52 ± 0.13 |
| anillo_paso_decr (adaptativo) | 2 | 0.095 ± 0.011 | 0.0247 ± 0.0017 | 0.0237 ± 0.0016 | 0.59 ± 0.05 |

- **Época 40:** la diferencia entre órdenes (0.044 vs 0.10-0.12) supera claramente la variabilidad entre semillas (0.01-0.03); la diferencia pareada anillo_decr - anillo_crec es +0.078 ± 0.011. La diferencia está en la banda alta (FRC alto 0.90 vs 0.43-0.59, con desvíos de 0.05-0.22); BF y banda baja son iguales.
- **Épocas 100 y 160:** las diferencias pareadas entre órdenes secuenciales son |Δ| <= 0.0007, contra un desvío entre semillas de 0.0014-0.0017. **Resultado nulo:** el orden no cambia el error final. Costo LR idéntico (2.67e-4) y fase de las esferas idéntica (2.237-2.238 rad, verdad 2.29).
- **Paso fijo mu = 1:** converge en ~20 épocas y el orden importa todavía menos (época 40: 0.0266 anillo_crec, 0.0275 anillo_decr, 0.0260 aleatorio, 0.0272 residuo_desc; n = 2). El error final es algo peor que con la rampa (0.0266 vs 0.0245) y el costo queda por debajo del piso de ruido en ambos casos (2.67-2.74e-4 vs 2.79e-4 del objeto verdadero): el solver ajusta ruido.
- **Lote completo:** 0.14 a 160 épocas con rampa, 0.16 a 40 épocas con mu = 1; no llegó a converger en el presupuesto. Los mini-lotes de 15 se comportan como un secuencial lento.
- **Las reconstrucciones no son idénticas entre órdenes:** a época 160 la distancia entre la reconstrucción de un orden y la de anillo_crec es 0.43-0.56 de la distancia de anillo_crec a la verdad. Es decir, el orden mueve la parte de ruido de la solución, no su calidad.

Figuras: `curvas_rampa.png`, `curvas_fijo1.png` (error, costo, fase y FRC por banda vs época), `ultimo_escritor.png`.

## Explicación mecanística

Mapa de "quién escribió último" (`ultimo_escritor.png`, tabla en `tabla.md`): con anillo creciente el 78 % de los píxeles de frecuencia queda escrito por última vez por un LED más externo que el píxel (desplazamiento medio +0.40 NA); con anillo decreciente, el 0 % (-0.68 NA); snake y aleatorio quedan en el medio (41-43 %).

Pero "el último gana" es débil con el paso real: cada píxel lo escriben ~4.75 LEDs y el peso del j-ésimo escritor contando desde el último es mu(1-mu)^j = 0.30, 0.21, 0.15, 0.10 con mu = 0.3. El último pesa sólo 1.4 veces más que el anterior, y el sesgo se promedia entre épocas. Por eso no hay sesgo medible en el punto final.

Lo que sí explica la ventaja inicial del anillo creciente es la **propagación de fase**: cada LED nuevo se apoya en una zona solapada ya corregida por LEDs más internos, así que la información sale del BF hacia afuera en una sola época. En orden decreciente los LED de HF se actualizan contra un espectro todavía sin estructura, y esa actualización se pierde. El lote completo no tiene propagación dentro de la época (equivale a un Jacobi frente a un Gauss-Seidel), por eso es mucho más lento.

## Idea adaptativa (e)

`residuo_desc` y `anillo_paso_decr` **no ganan**: a época 40 son peores que anillo creciente (0.10 y 0.095 vs 0.044) y a época 100-160 son indistinguibles. `anillo_paso_decr` da 0.0237 vs 0.0245 a época 160 (Δ pareado -0.0004 ± 0.0002, n = 2): es menor que el desvío entre semillas y no lo considero una mejora demostrada. El orden por residuo relativo termina procesando primero los LED de DF más ruidosos, que es lo contrario de lo que ayuda.

## Límites

- Simulación idealizada: mismo modelo directo para generar y reconstruir (crimen inverso), posiciones de LED exactas, pupila conocida, sin aberraciones, sin fondo ni errores de intensidad por LED. Con descalibración el orden podría importar más; esto no se probó.
- Tamaño reducido (LR 32 px, 4 esferas) y sólo 2-3 semillas por variante; la máquina dio ~35-45 s por corrida, así que el plan se recortó.
- **No corridas:** espiral, azimut/cuadrante, aleatorio fijo, entrelazado BF/DF, `residuo_asc`, `paso_residuo`, `minilote45` (están implementadas en `sim_orden.py`; el último escritor de aleatorio fijo sí se calculó). El paso fijo se probó sólo con mu = 1, 40 épocas, 2 semillas y 5 variantes.
- El lote se probó sólo con normalización por cobertura y el mismo paso; con aceleración (momento, paso mayor) podría acercarse al secuencial.

## Recomendación para el solver real

Mantener el orden anillo creciente y la rampa actual. No vale la pena invertir en órdenes alternativos ni adaptativos. Si se usan menos de ~60 épocas, el orden creciente es necesario para que la banda alta llegue a converger; a 100+ épocas es indiferente. No pasar a lote completo sin aceleración.

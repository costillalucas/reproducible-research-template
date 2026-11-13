# ¿Se pueden modelar los LEDs de borde BF/DF en vez de excluirlos? (simulación, 12/11)

Todo es simulación, ~15 min de reloj. Se completaron 77 reconstrucciones (límite de 400 s). Tabla completa en `tablas.md`, figura `fig_borde.png` (`python sim_borde.py 400; python analiza_borde.py`).

## Método

- `sim_borde.py` importa sin modificar `../sim_z/sim_z.py` y `../sim_z_clave/sim_z_clave.py` (objetos, ruido HDR, métricas, margen). 15x15, pitch 6 mm, NA 0.07, LR 64 px, ePIE 20 épocas.
- Datos: pupila erf de ancho **w = 0.011** (el medido en datos reales), centro sub-píxel, grilla 2x fina, ruido Poisson + lectura.
- Variantes: a (pupila dura), b (excluir margen < 0.012), c (pupila erf en el solver con el w real), d (barrido del w del solver), e (paso ponderado por margen/0.012).

## Resultados (w datos 0.011; media de 2 objetos, semilla 0; err / error en banda NA < 0.23)

| z (n BF, margen) | a dura | b excl. 0.012 | c blanda | e ponderado |
|---|---|---|---|---|
| 103 (5, 0.012) ref | 0.071 / 0.25 | 0.24 / 0.97 | **0.036 / 0.049** | 0.071 / 0.25 |
| 146 (9, 0.012) ref | 0.068 / 0.25 | 0.053 / 0.16 | **0.037 / 0.029** | 0.068 / 0.25 |
| 120 (5, 0.0005) | 0.615 / 2.17 | 0.051 / 0.16 | **0.032 / 0.023** | 0.086 / 0.36 |
| 125 (9, 0.002) | 0.103 / 0.39 | 0.050 / 0.16 | **0.032 / 0.021** | 0.041 / 0.10 |
| 168 (9, borde) | 0.358 / 1.47 | 0.059 / 0.18 | **0.040 / 0.014** | 0.209 / 0.88 |
| 180 | 0.470 / 1.81 | 0.061 / 0.19 | **0.042 / 0.011** | 0.391 / 1.57 |
| 181 (13, 0.004) | 0.485 / 1.86 | 0.061 / 0.19 | **0.042 / 0.010** | 0.403 / 1.61 |
| 249 (25, 0.002) | 0.570 / 2.06 | 0.069 / 0.19 | **0.050 / 0.012** | 0.424 / 1.69 |

- **c (pupila blanda con el w correcto) vuelve viables 13 BF, 25 BF y las zonas "a medias"**: el error queda igual o mejor que en los centros de ventana, y mejora también las referencias (146: 0.068 -> 0.037). Con ese modelo, el error deja de depender del margen.
- **e (ponderar el paso) no sirve**: mejora poco donde más falla (181: 0.485 -> 0.403); sólo ayuda en 120 y 125 (0.615 -> 0.086, 0.103 -> 0.041), siempre peor que c.
- **b (excluir)** rescata (err ~0.06, banda ~0.19) pero queda ~10x peor que c en la banda común, y a z = 103 empeora (0.24): ahí el umbral 0.012 saca LEDs BF necesarios.
- Con borde ancho (0.011) la pupila dura falla más que en sim_z_clave (w 0.005): 181 da 0.485 contra ~0.2.

## Variante d: ¿se puede ajustar w? (z = 181, objeto 0, semilla 0)

| w solver | 0.003 | 0.005 | 0.008 | 0.011 | 0.015 | 0.020 |
|---|---|---|---|---|---|---|
| err, datos w 0.011 | 0.496 | 0.285 | 0.037 | 0.035 | 0.036 | 0.040 |
| residuo LEDs de borde | 0.047 | 0.076 | 0.016 | **0.000** | 0.010 | 0.029 |
| err, datos w 0.005 | 0.186 | 0.035 | 0.042 | 0.047 | 0.054 | 0.061 |
| residuo LEDs de borde | 0.010 | **0.000** | 0.042 | 0.106 | 0.173 | 0.229 |

- El residuo de amplitud en los LEDs de borde tiene el mínimo en el w verdadero en los dos casos: w se puede calibrar con un barrido simple.
- Tolerancia asimétrica: **sobreestimar w es benigno** (err ≤ 0.06 hasta 4x), **subestimarlo es fatal** (w solver ≤ 0.5 w real falla). Regla práctica: ante la duda, w grande.

## Límites y honestidad

- **n = 2 (2 objetos, 1 semilla)**; la segunda semilla y el bloque completo con datos w = 0.005 no entraron (sólo 3 corridas a z = 181: a 0.198, c 0.035, e 0.165). Barrido d: n = 1.
- **Casi crimen inverso en c**: datos y solver usan la misma forma funcional (erf) y el mismo radio; el residuo 0.000 lo delata. El barrido d muestra tolerancia al w, pero **no se probó** forma de borde distinta (apodización real, aberraciones), error de NA junto con w, ni error de posición de LEDs. En datos reales la ganancia será menor.
- No se simuló el LED de tamaño finito (suma incoherente): falta. Es la causa física probable del w = 0.011 real y no es equivalente a una pupila coherente blanda; es el siguiente control necesario.
- 20 épocas, intensidad optimista, simulación idealizada.

## Respuesta

Sí en simulación: modelar el borde con pupila blanda (c/d) elimina la restricción de ventanas de z (13 y 25 BF pasan de err 0.49-0.57 a 0.04-0.05). No se encontró margen mínimo con c (funciona hasta 0.002). El límite pasa a ser el conocimiento de la pupila: w del solver ≥ ~0.7 del real. Ponderar el paso (e) no alcanza. Falta validar con LED finito y datos reales antes de tomarlo como regla de diseño.

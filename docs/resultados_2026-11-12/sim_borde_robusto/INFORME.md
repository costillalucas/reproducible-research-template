# ¿El rescate por pupila blanda sobrevive a un desajuste de modelo? (simulación, 12/11)

Todo es simulación, ~15 min de reloj. 69 reconstrucciones válidas. Tabla completa en `tablas.md`, figura `fig_robusto.png`.
Reproducir: `python sim_robusto.py 400; python sim_robusto.py 150 na; python analiza_robusto.py` (semilla fija 0).

## Método

- `sim_robusto.py` importa sin modificar `../sim_borde_leds/sim_borde.py` (solver y métricas), `sim_z.py` y `sim_z_clave.py`. 15x15, pitch 6 mm, LR 64 px, ePIE 20 épocas, ruido HDR de sim_z.
- El solver siempre cree **erf, w 0.011, NA 0.070**. Los datos se generan con otro borde: `lin` (rampa lineal, mismo ancho 10-90 %), `cola` (0.7 erf w 0.006 + 0.3 erf w 0.030), `naXXX` (NA real 0.064 a 0.076), `elip` (NA 0.070 en x, 0.068 en y), `led` (erf + LED finito: suma incoherente de 3x3 puntos en ~0.2 mm).
- Variantes: a (dura), b (excluir margen < 0.012), c (erf w 0.011 fijo), d (w barrido en 0.006/0.011/0.016/0.022; se elige el de menor residuo en LEDs de borde; **un w global, no uno por LED**).

## Resultados (objeto 0, semilla 0; err total / error en banda NA < 0.23)

| datos | z=181 b | z=181 c | z=249 b | z=249 c | z=168 b | z=168 c |
|---|---|---|---|---|---|---|
| erf (control, crimen inverso) | 0.051 / 0.19 | 0.035 / 0.013 | - | - | - | - |
| lin | 0.051 / 0.19 | 0.035 / 0.037 | 0.059 / 0.21 | 0.041 / 0.031 | 0.050 / 0.18 | 0.033 / 0.019 |
| cola | 0.048 / 0.17 | 0.040 / 0.10 | 0.071 / 0.29 | 0.047 / 0.12 | 0.044 / 0.15 | 0.035 / 0.054 |
| NA 0.067 (-4 %) | 0.055 / 0.22 | 0.044 / 0.13 | 0.060 / 0.21 | 0.052 / 0.15 | 0.052 / 0.20 | 0.040 / 0.11 |
| NA 0.073 (+4 %) | 0.049 / 0.17 | 0.039 / 0.10 | 0.056 / 0.18 | 0.047 / 0.12 | 0.049 / 0.18 | 0.042 / 0.13 |
| NA 0.064 (-9 %) | 0.061 / 0.25 | 0.067 / 0.28 | - | - | - | - |
| NA 0.076 (+9 %) | 0.050 / 0.18 | 0.048 / 0.18 | - | - | - | - |
| elip | 0.052 / 0.20 | 0.036 / 0.046 | 0.058 / 0.20 | 0.043 / 0.055 | 0.049 / 0.18 | 0.035 / 0.046 |
| led 0.2 mm | 0.051 / 0.19 | 0.035 / 0.013 | 0.057 / 0.19 | 0.041 / 0.017 | 0.049 / 0.18 | 0.033 / 0.014 |

Pupila dura (a) a z = 181: err 0.40-0.62 con todos los desajustes (sigue fallando). Fase en esferas: c 0.08-0.18 rad, b 0.22-0.37 rad en todos los casos.

- **El rescate sobrevive**: con cualquier desajuste probado, c lleva 13 BF, 25 BF y 9 BF "a medias" de err 0.4-0.6 a 0.035-0.05. Ningún desajuste lo rompe del todo.
- **Pero la ventaja de 10x de sim_borde_leds era en gran parte crimen inverso**. El error en banda común de c sube de 0.013 a 0.03-0.05 (forma lineal, elipse), a 0.05-0.12 (cola larga) y a 0.10-0.15 (NA ±4 %). La ventaja sobre b pasa de ~15x a ~1.5-2x con cola larga o error de radio.
- **Lo que más daña es el radio, no la forma**: forma lineal o elipse de 3 % casi no cuestan; ±4 % de NA cuesta ~10x en la banda común; a -9 % (NA 0.064) c pierde contra b (0.28 contra 0.25) y a +9 % empatan (0.18).
- **b no le gana a c dentro de ±4 % de NA ni con ninguna forma**; b sólo gana (por poco) con NA -9 %. b es más *estable* (banda 0.15-0.29 siempre) pero nunca mejor que ~0.15.
- **LED finito de 0.2 mm: efecto nulo** (resultado nulo honesto: a z = 181 abre sólo ~0.0006 de NA, 20x menos que w). No explica por sí solo un w = 0.011, y no pone a prueba el modelo; haría falta una fuente de ~2-4 mm.
- **d (w ajustado) no arregla el desajuste**: elige w 0.011 o 0.016 y da el mismo err que c (0.036-0.044; ver `tablas.md`). Un w mayor absorbe en parte el NA +4 % (banda 0.099 -> 0.067) pero no el NA -4 %. Subestimar w (0.006) vuelve a ser lo peor (lin 0.079, NA 0.073 0.104).
- Referencia z = 146 con NA ±4 %: c 0.032 / 0.05-0.06, b 0.041-0.049 / 0.14-0.20.

## Tolerancias (z = 181, n = 1)

| variante | forma del borde | radio (NA) |
|---|---|---|
| a dura | no tolera borde ancho (falla siempre) | - |
| b excluir | insensible (banda ~0.15-0.29) | insensible hasta ±9 % (0.17-0.25) |
| c erf fijo | lineal y elipse 3 %: sin costo apreciable; cola larga: banda 0.05-0.12 | ±4 %: banda 0.10-0.15 (aún mejor que b); ±9 %: igual o peor que b |
| d w ajustado | igual que c | igual que c; ayuda algo sólo si el NA real es mayor |

## Límites y honestidad

- **n = 1 en casi todo** (objeto 0, semilla 0); del objeto 1 sólo entró NA 0.067 a z = 181 (c 0.059 / 0.12, b 0.078 / 0.22: mismo orden). Sin barras de error: diferencias < 20 % no son concluyentes.
- **No entró**: z = 103, z = 146 para forma/elipse/LED, d con elipse completo y LED, w ajustado por LED individual, NA intermedios (±6 %), segunda semilla.
- Una primera tanda de casos de NA tenía un error de escala en el radio de los datos (se detectó por err = 1.0); se descartó y se repitió. Los valores de NA de este informe son de la tanda corregida.
- El desajuste se probó de a uno; no se combinó (NA + cola + posición de LEDs), ni aberraciones. 20 épocas, intensidad optimista, simulación idealizada. No se revisó visualmente la figura.

## Respuesta

Sí, el rescate por pupila blanda funciona con desajuste de modelo, pero con ganancia mucho menor que la anunciada: de ~15x a ~1.5-4x sobre excluir. Se degrada con error de radio y con cola larga; deja de convenir frente a excluir cerca de ±9 % de NA. La excluida (b) no gana "siempre": sólo en el caso extremo de NA -9 %. Regla práctica: calibrar el NA a mejor que ~±4 % antes de confiar en c; si no se puede, excluir.

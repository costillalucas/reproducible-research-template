# Alturas clave de la matriz: conjuntos BF completos (simulación, 12/11)

Todo es simulación, hecha en ~15 min de reloj. Se corrieron los 5 experimentos previstos (72 reconstrucciones, 200 s). Las tablas completas están en `tablas.md` (se regeneran con `python analiza_clave.py`).

## Método

- `sim_z_clave.py` importa sin modificar `../sim_z/sim_z.py`: 15x15, pitch 6 mm, λ 0.63 µm, LR 1.28 µm/px, LR 64 px, factor 4, modelo directo sin crimen inverso (objeto en grilla 2x más fina, pupila con borde erf de 0.7 px = 0.005 NA, centro sub-píxel), ruido Poisson + lectura con HDR simplificado, solver ePIE de 20 épocas con pupila dura y NA 0.070.
- 2 objetos (8 esferas separadas; 16 densas) x 2 semillas de ruido (1000, 1001): **n = 4 por celda** (n = 2 en el Exp. 5). El desvío informado mezcla objeto y ruido y está dominado por el objeto.
- Exp. 3: los datos se generan con radio de pupila escalado a la NA real (0.067 o 0.073); el solver sigue usando 0.070.
- Métricas (tras ajustar un escalar complejo): `err` total; `e_c23` = error espectral en la banda absoluta NA < 0.23, cubierta en el eje por todos los z hasta 249 mm (el `e_comun` de sim_z usa NA < 0.30, que a z ≥ 216 ya no está cubierta en el eje, y se informa sólo en `tablas.md`); FRC por bandas absolutas (BF 0-0.07, bajo -0.2, medio -0.35, alto -0.5); RMS de fase en esferas.
- "Margen" = mínimo de |NA_ilum − NA_obj| sobre los 225 LEDs.

## Ventanas de z (geometría exacta del simulador, barrido de 0.5 mm)

| n BF | ventana z (NA 0.070) | z de margen máximo | margen máximo | z con margen ≥ 0.007 (NA 0.070) | ídem NA 0.067 |
|---|---|---|---|---|---|
| 5 | 86.0-120.5 | 103.0 | 0.0118 | 95.5-109.5 | 100.0-114.0 |
| 9 | 121.0-171.0 | 146.0 | 0.0119 | 134.5-155.0 | 141.5-161.5 |
| 13 | 171.5-191.0 | 181.0 | **0.0038** | ninguno | ninguno |
| 21 | 191.5-241.5 | 216.5 | 0.0081 | 213.0-219.5 | 223.5-228.5 |
| 25 | 242.0-256.5 | 249.0 | **0.0020** | ninguno | ninguno |

- Las ventanas que se propusieron (86-121, 121-171, 171-191, 191-242) y sus centros **se confirman** (diferencia ≤ 0.5 mm, el paso del barrido). 17 BF no existe.
- **Corrección importante**: estar en el centro de la ventana no garantiza margen. El criterio "ningún LED a menos de 0.01 del borde" sólo se cumple en 5 BF (z 100-105.5) y 9 BF (z 141.5-149.5). En 13 BF y 25 BF el margen máximo posible es 0.004 y 0.002: el anillo que acaba de entrar y el que está por entrar quedan los dos pegados al borde, en cualquier z de la ventana. 21 BF llega a 0.008.
- Con NA 0.067 todas las ventanas se corren ~+4.5 % en z (103 → 108, 146 → 152.5, 216.5 → 226).

Geometría de los centros (NA 0.070):

| z | BF / DF | solap. vecinos centro % | NA_syn eje | NA_syn esquina | irradiancia centro (rel. 102) | margen |
|---|---|---|---|---|---|---|
| 103 | 5 / 220 | 49 | 0.448 | 0.570 | 0.98 | 0.0118 |
| 146 | 9 / 216 | 63 | 0.346 | 0.447 | 0.49 | 0.0119 |
| 181 | 13 / 212 | 70 | 0.296 | 0.382 | 0.32 | 0.0038 |
| 216 | 21 / 204 | 75 | 0.261 | 0.335 | 0.22 | 0.0080 |
| 249 | 25 / 200 | 78 | 0.236 | 0.302 | 0.17 | 0.0020 |

## Exp. 1 y 4: calidad en el centro de cada ventana (`fig1_calidad_vs_nbf.png`)

| z | BF | margen | err | e_c23 | FRC BF | FRC medio | FRC alto | fase esferas (rad) |
|---|---|---|---|---|---|---|---|---|
| 103 | 5 | 0.0118 | 0.045±0.004 | 0.107±0.003 | 0.995 | 0.963±0.019 | 0.70±0.12 | 0.126±0.017 |
| 146 | 9 | 0.0119 | 0.044±0.008 | 0.099±0.003 | 0.996 | 0.995±0.000 | 0.458±0.002 | 0.150±0.003 |
| 181 | 13 | 0.0038 | **0.223±0.005** | **0.94±0.18** | 0.63±0.08 | 0.965±0.002 | 0.12±0.03 | 0.198±0.011 |
| 216 | 21 | 0.0080 | 0.052±0.009 | 0.100±0.006 | 0.995 | 0.916±0.005 | 0.02±0.02 | 0.191±0.003 |
| 249 | 25 | 0.0020 | **0.256±0.000** | **1.06±0.19** | 0.62±0.07 | 0.815±0.001 | 0.02±0.02 | 0.286±0.016 |

- **No hay un óptimo en nº de BF.** Con 5, 9 y 21 BF el error en la banda común es prácticamente el mismo (0.107, 0.099, 0.100; diferencias de 1-3 desvíos con n = 4) y `err` total no distingue (0.045, 0.044, 0.052, dentro del desvío). Pasar de 5 a 9 BF mejora poco (−8 % en e_c23); de 9 a 21 no mejora nada. Es un resultado nulo: más BF no compra calidad en la banda baja.
- Lo que sí cambia con z es lo esperado por NA_syn: FRC alto 0.70 → 0.46 → 0.02 y fase en esferas 0.126 → 0.150 → 0.191 rad al pasar de 103 a 146 a 216. La banda media (NA 0.2-0.35) es mejor a 146 (0.995) que a 103 (0.963±0.019, con más dispersión): a 103 hay menos solapamiento (49 % vs 63 %).
- **13 BF y 25 BF fallan en su mejor z** (e_c23 ≈ 1, FRC en la banda BF 0.63): no por el número de BF sino porque su margen máximo es 0.004 / 0.002. Al excluir del solver los LEDs a < 0.006 del borde (Exp. 5, n = 2: 12 LEDs a z = 181, 16 a z = 249) se recuperan: e_c23 0.133 en ambos, err 0.053 y 0.060. Siguen siendo peores que 146 (0.099) y con menos NA_syn.

## Exp. 2: centro vs borde de ventana con el mismo nº de BF (`fig2_centro_vs_borde.png`)

| z | BF | margen | LED crítico | err | e_c23 | FRC BF | fase esferas |
|---|---|---|---|---|---|---|---|
| 125 | 9 | 0.0023 | diagonales, apenas dentro | 0.071±0.012 | 0.251±0.001 | 0.992 | 0.153 |
| **146** | 9 | 0.0119 | — | 0.044±0.008 | 0.099±0.003 | 0.996 | 0.150 |
| 168 | 9 | 0.0012 | (0,±2), apenas fuera | 0.319±0.030 | 1.34±0.33 | 0.45±0.13 | 0.260 |
| 174 | 13 | 0.0012 | (0,±2), apenas dentro | 0.117±0.008 | 0.449±0.059 | 0.956 | 0.223 |
| 181 | 13 | 0.0038 | dentro y fuera | 0.223±0.005 | 0.94±0.18 | 0.63 | 0.198 |
| 188 | 13 | 0.0012 | (±1,±2), apenas fuera | 0.487±0.002 | 1.88±0.31 | 0.31±0.05 | 0.541 |

- Con los mismos 9 BF, moverse del centro (146) al borde de la ventana multiplica e_c23 por 2.5 (z = 125) o por 13 (z = 168). El nº de BF no predice la calidad; el margen al borde sí.
- Asimetría observada: un LED **apenas fuera** de la pupila (el solver lo trata como DF puro pero deja pasar parte del haz directo) es mucho más dañino (e_c23 1.3-1.9) que uno **apenas dentro** (0.25-0.45). Es consistente en los 4 casos de borde y en el Exp. 3, pero no se aisló con un experimento propio.
- La fase en esferas es poco sensible (0.15 a 125 pese al error); el daño está en las frecuencias bajas (FRC BF).

## Exp. 3: NA_obj real 0.067 / 0.070 / 0.073 con solver en 0.070 (`fig3_robustez_na.png`)

| z (BF nominal) | NA real | margen real | err | e_c23 | fase esferas |
|---|---|---|---|---|---|
| 103 (5) | 0.067 | 0.0088 | 0.051±0.008 | 0.151±0.001 | 0.150 |
| 103 (5) | 0.070 | 0.0118 | 0.045±0.004 | 0.107±0.003 | 0.126 |
| 103 (5) | 0.073 | 0.0091 | 0.051±0.005 | 0.115±0.003 | 0.152 |
| 146 (9) | 0.067 | 0.0090 | 0.050±0.009 | 0.143±0.004 | 0.185 |
| 146 (9) | 0.070 | 0.0119 | 0.044±0.008 | 0.099±0.003 | 0.150 |
| 146 (9) | 0.073 | 0.0089 | 0.044±0.008 | 0.096±0.006 | 0.148 |
| 181 (13) | 0.067 | 0.0008 | 0.107±0.008 | 0.404±0.052 | 0.204 |
| 181 (13) | 0.070 | 0.0038 | 0.223±0.005 | 0.94±0.18 | 0.198 |
| 181 (13) | 0.073 | 0.0009 | 0.504±0.003 | 1.93±0.33 | 0.516 |
| 216 (21) | 0.067 | 0.0050 | 0.054±0.010 | 0.112±0.010 | 0.173 |
| 216 (21) | 0.070 | 0.0080 | 0.052±0.009 | 0.100±0.006 | 0.191 |
| 216 (21) | 0.073 | 0.0053 | 0.053±0.008 | 0.114±0.004 | 0.177 |

- **103, 146 y 216 toleran ±0.003 de error en NA_obj**: ningún LED cambia de lado y `err` sube a lo sumo de 0.045 a 0.051. En e_c23 el caso desfavorable es NA real 0.067 (menor que la del solver): x1.41 a 103, x1.44 a 146, x1.12 a 216. Con NA real 0.073 casi no hay efecto (x1.07, x0.97, x1.14).
- Ese +40 % a 103 y 146 es error de modelo de pupila (el solver cree que pasa una corona 0.067-0.070 que no pasa), no efecto de borde: aparece con margen real 0.009. Se corregiría usando la NA correcta en el solver; no se probó.
- **13 BF es efectivamente la más frágil**: a z = 181 el error cambia un factor 4.8 entre NA 0.067 y 0.073 (e_c23 0.40 → 1.93) y en ningún caso baja de 0.40. Contra lo esperado, a 181 el error con NA real 0.067 es menor que con 0.070: con 0.067 el LED crítico queda apenas dentro (caso leve), con 0.073 apenas fuera (caso grave).
- 216 fue el menos sensible a la NA en e_c23 (x1.12-1.14) pese a tener margen real de sólo 0.005; no se probó hasta dónde aguanta.

## Conclusiones

1. Las ventanas propuestas son correctas, pero "conjunto BF completo y z en el centro" sólo da margen suficiente para **5 BF (≈103), 9 BF (≈146) y, más justo, 21 BF (≈216)**. Las ventanas de 13 y 25 BF son intrínsecamente malas con pitch 6 mm y NA 0.07 (margen máximo 0.004 y 0.002) salvo que se excluyan del solver los LEDs de borde.
2. Entre las tres alturas buenas, el nº de BF no cambia la calidad en la banda común (e_c23 0.10-0.11); la diferencia la hace NA_syn (resolución y fase en esferas mejores a z menor) y el solapamiento (banda media más limpia a 146 que a 103).
3. El control a medias confirma que con el mismo nº de BF el error sube x2.5 a x13 al acercarse al borde de la ventana, y sugiere que el LED apenas fuera de la pupila es peor que el apenas dentro.
4. Con NA real entre 0.067 y 0.070, los z con margen ≥ 0.007 para ambas NA son **141.5-155 mm (9 BF)** y **100-109.5 mm (5 BF)**; para 21 BF no hay intersección (213-219.5 vs 223.5-228.5).

**Recomendación**: subir la matriz a **z ≈ 148 mm (rango útil 142-155)**, 9 BF. Es la ventana más ancha, tolera la incertidumbre de NA y de z, y da la mejor banda media; cuesta NA_syn en esquina 0.45 contra 0.57 a z ≈ 103. Si se prioriza resolución, z ≈ 103-105 es la alternativa, con ventana más angosta (100-109.5). Sólo se simularon los centros 103 y 146: los rangos salen de la geometría y del umbral 0.007 (z = 135 con margen 0.007 funcionó en sim_z; 216 con 0.008 y 0.005 funcionó acá), no de un barrido fino.

## Límites

- Simulación idealizada: sin aberraciones, desenfoque, fondo ni error de posición de LEDs (jitter y δz se estudiaron en `../sim_z`, no acá).
- 20 épocas: la banda alta no converge en ningún z (FRC alto ≤ 0.70) y a z ≥ 216 esa banda directamente no está cubierta por la matriz.
- El tamaño del efecto de borde depende del ancho del borde erf (0.7 px = 0.005 NA, arbitrario). El umbral de margen "seguro" (0.007-0.01) está acotado por pocos puntos: funcionan 0.005 (216, NA 0.067) y 0.008; fallan 0.0038 y menores. No es un umbral medido.
- HDR simplificado a una exposición por LED y 175-202 de 225 LEDs en el tope de 1025 ms: el modelo de intensidad es optimista y el SNR real del DF lejano será peor, sobre todo a z alto (irradiancia central x0.22 a 216 respecto de 102).
- n = 4 (2 objetos x 2 semillas); n = 2 en el Exp. 5. LR de 64 px y un solo tipo de objeto (esferas de fase).
- No se probó el solver con la NA correcta ni con pupila suave/EPRY, que podrían absorber parte del efecto de borde y del error de NA.

## Archivos

`sim_z_clave.py`, `analiza_clave.py`, `runs.jsonl`, `geometria.json`, `tablas.md`, `fig1_calidad_vs_nbf.png`, `fig2_centro_vs_borde.png`, `fig3_robustez_na.png`, `run.log`.

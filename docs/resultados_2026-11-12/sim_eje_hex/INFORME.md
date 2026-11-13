# Eje de la matriz desplazado y grilla hexagonal: conjuntos BF, ventanas de z y margen (simulación, 12/11)

Todo es simulación, hecha en ~15 min de reloj: geometría de 6 disposiciones + 36 reconstrucciones (200 s). Tablas completas en `tablas.md`.

## Método

- `sim_eje_hex.py` importa sin modificar `../sim_z/sim_z.py` y `../sim_z_clave/sim_z_clave.py` (mismo modelo directo sin crimen inverso, ruido Poisson + lectura con HDR simplificado, ePIE 20 épocas con pupila dura NA 0.070, mismas métricas). Sólo cambia la posición (x, y) de los 225 LEDs.
- Disposiciones (pitch 6 mm, 15x15 = 225 LEDs): (a) eje sobre un LED; (b) eje en (½,½) pitch; (c) eje en (½,0); (d) hexagonal, eje sobre un LED; (e) hexagonal, eje en el centro de un triángulo; (f) hexagonal, eje entre 2 LEDs. Además, barrido del desplazamiento (ox, oy) de la grilla cuadrada en pasos de 0.05 pitch.
- (e) Matriz rotada: no se simuló porque **rotar la matriz alrededor del eje óptico no cambia nada** (la pupila es circular: los conjuntos BF y los márgenes dependen sólo de las distancias al eje).
- Geometría: z 40-262 mm, paso 0.5 mm. "Margen" = mínimo de |NA_ilum − 0.070| sobre los 225 LEDs. NA_syn "lado corto" = 0.070 + NA del LED del borde más cercano de la matriz (con el eje desplazado la matriz queda asimétrica: 6.5 pitch de un lado, 7.5 del otro).
- Simulación: 2 objetos x 2 semillas (n = 4 por celda), en el z de margen máximo de cada ventana. Las referencias 103 mm / 5 BF y 146 mm / 9 BF se volvieron a correr y reproducen sim_z_clave (e_c23 0.107 y 0.099).

## 1. Geometría (`fig1_margen_vs_z.png`)

| disposición | n BF | ventana z (mm) | z óptimo | margen máx. | z con margen ≥ 0.010 | DF | NA_syn lado corto / máx. |
|---|---|---|---|---|---|---|---|
| (a) sobre LED | 5 | 86-120.5 | 103 | 0.0118 | 100-105.5 | 220 | 0.448 / 0.570 |
| (a) sobre LED | 9 | 121-171 | 146 | 0.0119 | 141.5-149.5 | 216 | 0.346 / 0.447 |
| (a) sobre LED | 13 / 21 / 25 | — | 181 / 216.5 / 249 | 0.0038 / 0.0081 / 0.0020 | ninguno | 212 / 204 / 200 | — |
| **(b) (½,½)** | **4** | 60.5-135 | 97.5 | **0.0265** | **71-118** | 221 | 0.441 / 0.617 |
| (b) (½,½) | 12 | 135.5-181 | 158 | 0.0101 | 158-158.5 | 213 | 0.310 / 0.444 |
| (b) (½,½) | 16 | 181.5-217.5 | 199.5 | 0.0063 | ninguno | 209 | 0.262 / 0.374 |
| (b) (½,½) | 24 | 218-249 | 233.5 | 0.0046 | ninguno | 201 | 0.235 / 0.333 |
| (c) (½,0) | 2 | 43-95.5 | 69 | 0.0266 | 50-83.5 | 223 | 0.562 / 0.736 |
| (c) (½,0) | 6 | 96-128 | 112 | 0.0101 | 112 | 219 | 0.399 / 0.552 |
| (c) (½,0) | 8 / 12 / 16 | — | 141 / 165 / 195 | 0.0063 / 0.0046 / 0.0067 | ninguno | — | — |
| **(d) hex sobre LED** | **7** | 86-148 | 116.5 | **0.0186** | **100-129** | 218 | 0.368 / 0.515 |
| (d) hex sobre LED | 13 | 148.5-171 | 159.5 | 0.0050 | ninguno | 212 | 0.292 / 0.411 |
| (d) hex sobre LED | 19 | 171.5-226 | 198.5 | 0.0097 | ninguno | 206 | 0.250 / 0.350 |
| (e) hex centroide | 3 | 49.5-98.5 | 74 | 0.0232 | 58-86 | 222 | 0.494 / 0.678 |
| (e) hex centroide | 12 | 131-177.5 | 154 | 0.0106 | 152.5-155.5 | 213 | 0.289 / 0.416 |
| (f) hex arista | 4 | 74.5-113 | 93.5 | 0.0145 | 86.5-98.5 | 221 | 0.433 / 0.581 |

- Los conjuntos esperados se confirman, con una corrección: con el eje en (½,½) los conjuntos son **4, 12, 16, 24** (no existe 20); hexagonal: 7, 13, 19, 31.
- **Ventanas con margen > 0.012 existen sólo con pocos BF**: (b) 4 BF (0.0265, 47 mm de ancho con margen ≥ 0.010), (c) 2 BF, (e) 3 BF, (f) 4 BF (0.0145) y **hexagonal 7 BF (0.0186, 29 mm de ancho)**. Las referencias 5 y 9 BF tienen sólo 5.5 y 8 mm con margen ≥ 0.010.
- **Con más de 9 BF ninguna disposición supera el margen 0.012.** Lo mejor que hay: 12 BF con eje (½,½) a 158 mm (0.0101) o hex centroide a 154 mm (0.0106); 19 BF hexagonal a 198.5 mm (0.0097, mejor que los 21 BF de la referencia, 0.0081); 16 BF: 0.0063-0.0067. Es la regla general: el margen máximo de una ventana es ≈ 0.07·(r2−r1)/(r2+r1) entre anillos consecutivos, y los anillos se aprietan al crecer el radio.
- Barrido de desplazamientos (cuadrada, paso 0.05 pitch): ningún desplazamiento intermedio gana. Los óptimos por nº de BF caen siempre en posiciones simétricas ((0,0), (½,½), (½,0)); **17 BF existe sólo con desplazamientos raros y margen 0.002**.
- Los LEDs no se acaban: quedan 194-223 DF en todos los casos. El costo del desplazamiento es que la NA_syn del lado corto baja un poco (p. ej. 0.441 vs 0.448 a ~100 mm).

## 2. Simulación en el centro de las ventanas (`fig2_calidad.png`)

| disposición | BF | z | margen | NA_syn corto | err | e_c23 | FRC BF | FRC medio | FRC alto | fase esferas (rad) |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) ref. | 5 | 103 | 0.0118 | 0.448 | 0.045±0.004 | 0.107±0.003 | 0.995 | 0.963±0.019 | 0.70±0.12 | 0.126±0.017 |
| (a) ref. | 9 | 146 | 0.0119 | 0.346 | 0.044±0.008 | 0.099±0.003 | 0.996 | 0.995 | 0.458±0.002 | 0.150±0.003 |
| (b) (½,½) | 4 | 97.5 | 0.0265 | 0.441 | 0.045±0.007 | 0.130±0.001 | 0.991 | 0.976±0.003 | 0.852±0.013 | 0.143±0.003 |
| (b) (½,½) | 12 | 158 | 0.0101 | 0.310 | 0.046±0.008 | 0.096±0.002 | 0.995 | 0.984 | 0.329±0.006 | 0.163±0.000 |
| (b) (½,½) | 16 | 199.5 | 0.0063 | 0.262 | 0.062±0.004 | **0.186±0.091** | 0.965±0.028 | 0.942 | 0.040 | 0.133±0.005 |
| (c) (½,0) | 6 | 112 | 0.0101 | 0.399 | 0.040±0.007 | 0.095±0.001 | 0.995 | 0.991 | 0.794±0.008 | 0.116±0.001 |
| (d) hex | 7 | 116.5 | 0.0186 | 0.368 | 0.043±0.008 | 0.115±0.009 | 0.992 | 0.997 | 0.714±0.013 | 0.132±0.005 |
| (d) hex | 19 | 198.5 | 0.0097 | 0.250 | 0.053±0.009 | 0.111±0.001 | 0.995 | 0.923 | 0.02±0.02 | 0.203±0.000 |
| (e) hex centroide | 12 | 154 | 0.0106 | 0.289 | 0.047±0.008 | 0.107±0.002 | 0.994 | 0.980 | 0.297±0.005 | 0.171±0.000 |

- **Más margen no compra calidad en el centro de la ventana** (resultado nulo): 4 BF con margen 0.0265 tiene e_c23 0.130, peor que 5 BF (0.107) y 9 BF (0.099) con margen 0.012. `err` total no distingue ninguna de las configuraciones sanas (0.040-0.047, dentro del desvío, que está dominado por el objeto). Lo que el margen grande compra es **tolerancia en z** (ventana útil de 47 mm en vez de 5.5-8 mm), que aquí no se puso a prueba con reconstrucciones fuera del centro.
- **(c) eje en (½,0), 6 BF, 112 mm** dio los mejores números de la tabla (err 0.040, e_c23 0.095, FRC alto 0.79, fase 0.116 rad), pero las diferencias con 5 y 9 BF son chicas (n = 4) y su margen ≥ 0.010 existe en un único z: es una ventana frágil.
- **4 BF en (½,½) y 7 BF hexagonal** igualan a las referencias en err y fase, con FRC alto igual o mejor (0.85 y 0.71 vs 0.70±0.12 a 103 mm), y son las únicas con ventana ancha.
- 12 BF (cuadrada o hex) y 19 BF hex funcionan (e_c23 0.096-0.111) pero no mejoran a 9 BF y pierden NA_syn.

## 3. Respuestas concretas

- **¿4 BF con eje en (½,½) converge la fase? Sí.** Fase en esferas 0.143±0.003 rad (esferas de 2.3 rad), igual que 5 y 9 BF (0.126-0.150), contra 2.0-2.1 rad con 1 BF (sim_z_1bf, no se repitió aquí). También convergen 6 BF (0.116) y 7 BF hex (0.132). No se probaron los 2 BF de (½,0) ni los 3 BF del hex centroide: su z óptimo (69-74 mm) queda fuera del espectro HR del simulador.
- **¿16 BF tiene margen suficiente? No del todo.** El margen máximo es 0.0063 (0.0067 con eje en (½,0)), por debajo del ~0.01 que piden los estudios previos. En la simulación la reconstrucción queda a medias y depende del objeto: e_c23 0.277 en el objeto de 8 esferas y 0.094 en el de 16, FRC BF 0.965±0.028. La fase en esferas igual es buena (0.133). Es mejor que 13 BF (e_c23 0.94) pero no es fiable; 12 BF a 158 mm o 19 BF hex a 198.5 mm son las alternativas sanas si se quieren más de 9 BF.

## Límites

- 20 épocas de ePIE con pupila dura; el borde erf de 0.7 px (0.005 NA) del modelo directo es arbitrario y fija la escala del "margen necesario". Con la pupila real el umbral puede ser otro.
- Intensidad optimista y simulación idealizada: sin aberraciones, sin error de posición de LEDs ni de z, sin desalineación del eje. Con el eje en (½,½) el desplazamiento tiene que acertarse; no se midió cuánto error de centrado tolera cada disposición (con 4 BF el margen 0.0265 equivale a ~±0.35 pitch ≈ 2 mm, estimación geométrica no simulada).
- n = 4 por celda (2 objetos x 2 semillas); el desvío mezcla objeto y ruido. Objetos de fase casi pura (esferas), LR 64 px.
- Sólo se reconstruyó en el z de margen máximo: la ventaja esperada de las ventanas anchas (tolerancia a z) es geométrica, no está verificada con reconstrucciones.
- La grilla hexagonal es hipotética (la matriz real es cuadrada) y se modeló como 15 filas x 15 LEDs con filas alternas corridas ½ pitch.
- `fig1_margen_vs_z.png` se revisó; `fig2_calidad.png` se generó pero no se revisó visualmente (los números están en la tabla).

## Archivos

`sim_eje_hex.py` (`geo`, `sim`, `fig`), `geometria.json`, `runs.jsonl`, `tablas.md`, `fig1_margen_vs_z.png`, `fig2_calidad.png`, `run.log`.

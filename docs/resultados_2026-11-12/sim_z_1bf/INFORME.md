# Matriz baja con un solo LED en campo claro (simulación, 12/11)

Todo es simulación, hecha en ~10 min de reloj (24 reconstrucciones, 73 s). Tabla completa en `tablas.md` (se regenera con `python analiza_1bf.py`).

## Método

- `sim_z_1bf.py` importa sin modificar `../sim_z/sim_z.py` y `../sim_z_clave/sim_z_clave.py`: 15x15, pitch 6 mm, NA 0.07, LR 64 px, modelo directo sin crimen inverso (grilla 2x más fina, pupila erf de 0.7 px, centro sub-píxel), ruido Poisson + lectura, ePIE de 20 épocas con pupila dura. 2 objetos x 2 semillas (1000, 1001): n = 4 en el Exp. 1; n = 2 (2 objetos, 1 semilla) en los Exp. 2 y 3.
- Factor de upsampling: se dejó en 4 (HR 256). Se verificó con la geometría que alcanza hasta z = 55 (la ventana del LED de esquina llega a 99.5 px de 128); matriz completa, sin recorte.
- **Único cambio respecto del modelo base**: se agregó una exposición de 5 ms a la lista HDR, porque a z < 72 mm el BF central satura con 20 ms. Con eso, 0 % de píxeles saturados en el BF. Esa exposición no existe en el HDR real.
- Exp. 1: z = 55, 65, 73 (1 BF real con margen). Exp. 3: 1 BF artificial (se quitan del solver los demás BF) a z = 103, 146, 216, para separar "nº de BF" de "solapamiento". Exp. 2: rescates a z = 73.
- Métricas como en sim_z_clave: `err`, `e_c23` (banda absoluta NA < 0.23), FRC por bandas absolutas, RMS de fase en esferas.

## Resultados (`fig1_fase_vs_solapamiento.png`, `fig2_frc_bandas.png`)

| caso | z | BF/DF | solap. % | NA_syn eje/esq | margen | n | err | e_c23 | FRC bajo | FRC medio | FRC alto | fase esferas (rad) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 BF real | 55 | 1/224 | 12 | 0.68/0.80 | 0.038 | 4 | 0.231±0.030 | 0.92±0.04 | 0.69 | 0.18 | 0.11 | **2.12±0.12** |
| 1 BF real | 65 | 1/224 | 23 | 0.61/0.75 | 0.022 | 4 | 0.211±0.030 | 0.82±0.02 | 0.92 | 0.39 | 0.23 | **2.04±0.05** |
| 1 BF real | 73 | 1/224 | 30 | 0.57/0.70 | 0.012 | 4 | 0.212±0.028 | 0.82±0.03 | 0.95 | 0.44 | 0.33 | **2.06±0.09** |
| 1 BF real, borde (sim_z) | 80 | 1/224 | 35 | 0.54/0.67 | 0.005 | 6 | 0.308±0.032 | — | 0.85 | 0.80 | 0.71 | 2.63±0.03 |
| 1 BF artificial | 103 | 1/220 | 49 | 0.45/0.57 | 0.012 | 2 | 0.214±0.023 | 0.86±0.06 | 0.99 | 0.92 | 0.69 | 2.18±0.16 |
| 1 BF artificial (sim_z) | 135 | 1/216 | 60 | 0.37/0.47 | 0.007 | 6 | 0.199±0.028 | — | 1.00 | 1.00 | 0.61 | 1.89±0.11 |
| 1 BF artificial | 146 | 1/216 | 63 | 0.35/0.45 | 0.012 | 2 | 0.194±0.030 | 0.78±0.02 | 1.00 | 1.00 | 0.45 | 1.80±0.07 |
| 1 BF artificial | 216 | 1/204 | 75 | 0.26/0.34 | 0.008 | 2 | 0.189±0.032 | 0.76±0.01 | 1.00 | 0.92 | 0.02 | 1.76±0.02 |
| ref 5 BF (sim_z_clave) | 103 | 5/220 | 49 | 0.45/0.57 | 0.012 | 4 | 0.045±0.004 | 0.107±0.003 | 1.00 | 0.96 | 0.70 | 0.126±0.017 |
| ref 9 BF (sim_z_clave) | 146 | 9/216 | 63 | 0.35/0.45 | 0.012 | 4 | 0.044±0.008 | 0.099±0.003 | 1.00 | 1.00 | 0.46 | 0.150±0.003 |
| ref 21 BF (sim_z_clave) | 216 | 21/204 | 75 | 0.26/0.34 | 0.008 | 4 | 0.052±0.009 | 0.100±0.006 | 1.00 | 0.92 | 0.02 | 0.191±0.003 |

Rescates a z = 73 (n = 2; base: err 0.212, e_c23 0.82, fase 2.06):

| variante | err | e_c23 | FRC medio | FRC alto | fase esferas |
|---|---|---|---|---|---|
| 60 épocas | 0.269±0.036 | 1.08±0.04 | 0.87 | 0.62 | 2.52±0.03 |
| BF central actualizado 3 veces por época | 0.223±0.029 | 0.88±0.04 | 0.45 | 0.34 | 2.16±0.06 |
| paso 0.1 | 0.203±0.032 | 0.79±0.01 | 0.39 | 0.15 | 1.99±0.00 |

## Conclusiones

1. **Con 1 BF la fase no converge en ningún z probado**, ni siquiera con margen real al borde: 2.0-2.1 rad a z = 55, 65 y 73 (las esferas tienen 2.3 rad: el error es del orden de la señal), `err` 0.21-0.23 y e_c23 0.8-0.9, contra 0.13-0.15 rad, 0.045 y 0.10 en las referencias de 5 y 9 BF. El margen no era el problema de z = 80: a 73 mm con margen 0.012 el resultado es casi igual de malo.
2. **El solapamiento no es la variable que manda; el nº de BF sí.** Con 1 BF, llevar el solapamiento de 12 % a 75 % sólo baja la fase de 2.1 a 1.8 rad (y e_c23 de 0.92 a 0.76). Al mismo z y mismo solapamiento, pasar de 1 a 5 BF (103 mm, 49 %) la baja de 2.18 a 0.13 rad; de 1 a 9 (146 mm, 63 %), de 1.80 a 0.15. **No se encontró un solapamiento mínimo que haga converger la fase con 1 BF: hasta 75 % no alcanza.** La hipótesis "falta solapamiento" queda refutada como causa principal; la de "falta ancla de fase" es compatible con los datos.
3. Lo que sí depende del solapamiento con 1 BF es la consistencia de las bandas media y alta: FRC medio 0.18 / 0.39 / 0.44 a 12 / 23 / 30 % y ≥ 0.92 desde 49 %. Por debajo de ~35-50 % ni siquiera el DF queda bien cosido, así que la NA_syn nominal de 0.70-0.80 a z bajo no se aprovecha.
4. **Los rescates baratos no rescatan** (resultado nulo): paso 0.1 y BF ponderado x3 quedan dentro del desvío de la base; 60 épocas mejora FRC medio/alto (0.44 → 0.87, 0.33 → 0.62) pero empeora la fase (2.52 rad) y e_c23 (1.08): el solver converge a una solución autoconsistente pero equivocada en las frecuencias bajas.
5. Práctico: z < 85.5 mm (1 BF) no es una zona usable con este solver; el mínimo que funcionó sigue siendo 5 BF (z ≈ 100-109).

## Límites

- Simulación idealizada: sin aberraciones, desenfoque, fondo ni error de posición de LEDs. Borde erf de 0.7 px arbitrario. HDR simplificado a una exposición por LED, con una de 5 ms inventada; modelo de intensidad optimista.
- No se diagnosticó **qué** solución encuentra el solver con 1 BF (imagen gemela/conjugada, fase casi plana, etc.); una fase de ~2 rad de error con esferas de 2.3 rad sugiere que la fase de baja frecuencia directamente no se recupera, pero no se verificó. Los objetos son de fase casi pura (absorción débil): es el caso más difícil para 1 BF; con objetos de amplitud o fase débil el resultado puede ser distinto.
- Sólo ePIE con pupila dura, init con el BF y orden por NA creciente. No se probó otra inicialización (p. ej. fase DPC), otro orden, ni multiplexado; "inicialización ponderada" se implementó sólo como repetir el BF 3 veces por época.
- "1 BF artificial" a z alto no es igual a 1 BF real: se descartan datos y queda un hueco en el espectro donde iban los BF quitados.
- n = 4 (Exp. 1) y n = 2 (Exp. 2 y 3, una sola semilla); el desvío está dominado por el objeto. LR 64 px. `e_c23` no está disponible para los puntos de sim_z (z = 80 y 135).
- Solapamiento = fracción de área común de las pupilas de dos LEDs vecinos del centro; en el borde de la matriz es menor.

## Archivos

`sim_z_1bf.py`, `analiza_1bf.py`, `runs.jsonl`, `geometria.json`, `tablas.md`, `fig1_fase_vs_solapamiento.png`, `fig2_frc_bandas.png`, `run.log`.

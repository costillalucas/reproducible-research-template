# Barrido de z de la matriz 15x15 (simulación, 12/11)

Todo es simulación, con ~18 min de reloj. Los tres estudios están completos (el Estudio 1 se completó en una segunda pasada: z = 135 con 2 objetos, z = 150 y 180). Las tablas completas están en `tablas.md` (se regeneran con `python analiza_z.py`).

## Método

- `sim_z.py` (semillas fijas): 15x15, pitch 6 mm, NA 0.07, λ 0.63 µm, LR 1.28 µm/px, **LR 64 px**, factor 4 (HR 256; con factor 3 el espectro HR no contiene las esquinas a z = 80).
- **Sin crimen inverso**: datos generados con objeto en grilla 2x más fina (0.16 µm), pupila con borde suave erf (ancho 0.7 px = 0.005 NA) y centro de pupila sub-píxel; el solver (núcleo ePIE de `fpm_red.py`, 20 épocas, step 0.3 con rampa, orden por NA creciente) usa pupila dura y ventana entera.
- 2 objetos (8 esferas de 5 µm separadas; 16 densas que se tocan; dn 0.046, 2.3 rad) x 3 semillas de ruido.
- SNR: irradiancia del LED ∝ cos³θ / z²; BF central a media escala (15000 e-) en 20 ms a z = 102; por LED se usa la exposición más larga de 20/111/403/1025 ms que no satura (HDR simplificado a una sola exposición); pozo 30000 e-, lectura 3 e-, Poisson.
- Métricas tras ajustar un escalar complejo: `err` total, `e_comun` (error espectral en NA < 0.30, cubierta por todos los z), FRC por bandas en NA absoluta (BF 0-0.07, bajo -0.2, medio -0.35, alto -0.5), RMS de fase en esferas.

## Resultados

### Geometría (exacta, sin simulación)

| z (mm) | BF | DF | solap. vecinos centro % | NA_syn eje | NA_syn esquina | irradiancia centro (rel. 102) | esquina |
|---|---|---|---|---|---|---|---|
| 80 | 1 | 224 | 35 | 0.535 | 0.666 | 1.63 | 0.84 |
| 102 | 5 | 220 | 48 | 0.451 | 0.573 | 1.00 | 0.65 |
| 120 | 5 | 220 | 56 | 0.400 | 0.514 | 0.72 | 0.52 |
| 135 | 9 | 216 | 60 | 0.367 | 0.473 | 0.57 | 0.44 |
| 150 | 9 | 216 | 64 | 0.340 | 0.438 | 0.46 | 0.37 |
| 180 | 13 | 212 | 70 | 0.297 | 0.383 | 0.32 | 0.28 |

### Estudio 1: calidad vs z (matriz completa)

| z | variante | n | err | e_comun | FRC medio | FRC alto | fase esferas (rad) |
|---|---|---|---|---|---|---|---|
| 80 | ruido | 6 | 0.308±0.032 | 1.25±0.09 | 0.80±0.03 | 0.71±0.05 | 2.63±0.03 |
| 102 | ruido | 6 | 0.047±0.003 | 0.123±0.010 | 0.948±0.029 | 0.64±0.15 | 0.134±0.020 |
| 120 | ruido | 6 | 0.581±0.013 | 2.08±0.37 | 0.969±0.006 | 0.73±0.01 | 0.747±0.030 |
| 135 | ruido | 6 | 0.041±0.007 | 0.093±0.002 | 0.998±0.000 | 0.62±0.01 | 0.122±0.001 |
| 150 | ruido | 6 | 0.044±0.008 | 0.098±0.003 | 0.993±0.001 | 0.41±0.00 | 0.149±0.003 |
| 180 | ruido | 6 | 0.187±0.002 | 0.77±0.14 | 0.967±0.001 | 0.13±0.02 | 0.189±0.010 |

Con la matriz completa, 135 y 150 quedan empatados en `err` global (0.041 vs 0.044), pero 135 es mejor en banda alta (e_alto 0.81 vs 0.94; FRC alto 0.62 vs 0.41), como se espera de una NA_syn mayor. 180 falla por los LEDs de borde de pupila (se recupera al excluirlos, ver Estudio 1 bis).

La variante sin ruido da los mismos números con diferencia < 0.003 en `err` en los cuatro z: **con este presupuesto de fotones el SNR no es el factor limitante; manda la geometría**. ~200 de 225 LEDs llegan al tope de 1025 ms en todos los z.

La curva **no es suave**: z = 80 y z = 120 fracasan aun sin ruido. Causa identificada: LEDs cuya NA de iluminación cae a menos de ~1 px (0.008 NA) del borde de la pupila (z = 80: los 4 del primer anillo, NA 0.075; z = 120: las 4 diagonales, NA 0.0705). En esos LEDs el haz directo pasa parcialmente por el borde suave real y el solver, con pupila dura, lo modela como DF puro (o BF puro).

### Estudio 1 bis: sin ruido, excluyendo LEDs con |NA_ilum − NA_obj| < 0.012 (n = 2 objetos)

| z | excluidos | err | e_comun | FRC medio | fase esferas |
|---|---|---|---|---|---|
| 80 | 4 | 0.271±0.040 | 1.10 | 0.70 | 2.30 |
| 102 | 4 | 0.218±0.026 | 0.88 | 0.89 | 2.22 |
| 120 | 4 | 0.043±0.008 | 0.119 | 0.994 | 0.125 |
| 135 | 4 | 0.042±0.007 | 0.103 | 0.998 | 0.131 |
| 150 | 4 | 0.046±0.008 | 0.108 | 0.993 | 0.157 |
| 180 | 12 | 0.052±0.009 | 0.132 | 0.969 | 0.202 |

- z = 120 se recupera por completo al excluir las 4 diagonales (0.58 → 0.043): confirma el mecanismo.
- A z = 102 el umbral 0.012 elimina justamente los 4 BF de la cruz (NA 0.059) y la fase deja de converger (2.2 rad): con 1 solo BF y 48 % de solapamiento no hay ancla suficiente. Lo mismo a z = 80 (1 BF, 35 %).
- Entre 120 y 180 la calidad en la banda común es casi plana, con óptimo suave en **135** (e_comun 0.103 vs 0.119 a 120 y 0.132 a 180; diferencias de 2-10 desvíos entre objetos, pero n = 2). `err` total no distingue 120/135/150 (diferencia < desvío).

### Estudio 2: robustez a δz y jitter 0.2 mm (completo, n = 6 por celda, con ruido)

| z nominal | δz | err | e_comun | fase esferas (rad) |
|---|---|---|---|---|
| 102 | −5 | 0.066±0.009 | 0.211±0.014 | 0.203±0.018 |
| 102 | −2 | 0.053±0.007 | 0.153±0.012 | 0.152±0.026 |
| 102 | 0 | 0.048±0.006 | 0.133±0.012 | 0.142±0.020 |
| 102 | +2 | 0.049±0.006 | 0.136±0.009 | 0.153±0.018 |
| 102 | +5 | 0.062±0.009 | 0.198±0.016 | 0.212±0.016 |
| 135 | −5 | 0.049±0.008 | 0.138±0.003 | 0.106±0.020 |
| 135 | −2 | 0.043±0.007 | 0.106±0.003 | 0.112±0.012 |
| 135 | 0 | 0.042±0.007 | 0.098±0.003 | 0.122±0.007 |
| 135 | +2 | 0.043±0.008 | 0.105±0.004 | 0.140±0.003 |
| 135 | +5 | 0.048±0.009 | 0.136±0.005 | 0.177±0.001 |
| 180 | −5 | 0.104±0.022 | 0.389±0.117 | 0.168±0.042 |
| 180 | −2 | 0.138±0.028 | 0.555±0.172 | 0.159±0.034 |
| 180 | 0 | 0.181±0.031 | 0.744±0.199 | 0.182±0.033 |
| 180 | +2 | 0.240±0.031 | 0.991±0.223 | 0.218±0.029 |
| 180 | +5 | 0.344±0.032 | 1.389±0.271 | 0.330±0.037 |

- El jitter de 0.2 mm solo (δz = 0) casi no degrada a 102 ni a 135 (comparar con Estudio 1).
- ±2 mm es tolerable en ambos: e_comun x1.02-1.15 a 102 y x1.07-1.08 a 135 (del orden del desvío).
- ±5 mm: e_comun x1.48-1.58 a 102 y x1.39-1.41 a 135. **z = 135 es algo más robusta en términos relativos y claramente mejor en absoluto**: 135 con ±5 mm de error (0.136-0.138) iguala a 102 bien calibrado (0.133). La diferencia 102 vs 135 supera el desvío en e_comun en todos los δz; en `err` total no (desvío dominado por el objeto).
- La fase en esferas a 135 es asimétrica: mejora levemente con δz < 0 (0.106) y empeora con δz > 0 (0.177); no tengo explicación verificada.
- z = 180 con matriz completa parte mal (err 0.18) y varía monótonamente con δz (0.10 a −5, 0.34 a +5): es el efecto de los 8 LEDs a 0.6 px del borde de pupila, que δz acerca o aleja del borde, no una medida limpia de robustez. Excluyéndolos da 0.052 (Estudio 1 bis, sin δz).

### Estudio 3: número de LEDs BF a z = 135 (todo el DF, con ruido, n = 6)

| n BF | err | e_comun | fase esferas (rad) |
|---|---|---|---|
| 0 | 0.986±0.003 | 1.09±0.11 | 0.63±0.13 |
| 1 | 0.199±0.028 | 0.806±0.028 | 1.89±0.11 |
| 5 | 0.043±0.007 | 0.104±0.002 | 0.132±0.001 |
| 9 | 0.041±0.007 | 0.093±0.002 | 0.122±0.001 |

La fase no converge con 0 ni con 1 BF; con 5 (cruz) ya converge, y pasar de 5 a 9 mejora poco (e_comun 0.104 → 0.093, mayor que el desvío; `err` dentro del desvío). No se probó 13 (a z = 135 sólo hay 9 BF) ni 2-4 BF. Con 0 BF la inicialización sale de un DF, así que ese caso mezcla falta de ancla y mala inicialización.

## Conclusiones

1. El óptimo no lo fija el SNR sino dos condiciones geométricas: (a) suficientes BF solapados (≥ 5; con 1 no converge) y (b) **ningún LED con NA de iluminación a menos de ~0.01 del borde de la pupila**, o excluirlo.
2. z ≈ 135 cumple ambas con la matriz completa (9 BF; el LED más cercano al borde está a 0.007 por dentro, NA 0.063, y aun así funcionó) y da el mejor error en banda común; cuesta NA_syn x0.83 respecto de 102 (0.473 vs 0.573 en esquina).
3. z = 102 funciona pero depende de los 4 BF de la cruz, que están a 0.011 del borde; z ≈ 120 y z ≈ 80 son malas elecciones con pitch 6 mm y NA 0.07 salvo que se excluyan los LEDs de borde.

## Límites

- **Estudio 1**: completado en una segunda pasada (se borraron las líneas `"est": "e1"` de `runs.jsonl` y se volvió a correr `python sim_z.py e1`). Las cifras de z = 80, 102 y 120 se regeneraron con la misma semilla y coinciden con las de la primera pasada.
- El tamaño del efecto de borde depende del ancho del borde erf (0.7 px, arbitrario) y de que NA_obj valga exactamente 0.07; en el sistema real (NA 0.067-0.07) los z "malos" se corren. Lo robusto es el criterio (distancia al borde), no los valores 80/120.
- No se probó umbral de exclusión menor que 0.012 ni un solver con pupila suave/EPRY, que podrían rescatar esos LEDs.
- HDR simplificado a una exposición por LED; sin aberraciones, sin desenfoque, sin fondo; 20 épocas (banda alta no convergida, FRC alto 0.6-0.7 en todos los z).
- n = 6 como máximo (2 objetos x 3 semillas); el desvío está dominado por el objeto, no por el ruido.

## Archivos

`sim_z.py`, `analiza_z.py`, `runs.jsonl`, `geometria.json`, `tablas.md`, `fig1_calidad_vs_z.png`, `fig2_robustez_dz.png`, `fig3_n_bf.png`, `run.log`.

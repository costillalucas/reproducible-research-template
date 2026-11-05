# Simulación: ¿un borde de pupila blando explica la diferencia espectral vs. borde? (05/11)

**Pregunta.** En la captura roja 03/11, el método espectral da NA·z 6.97 (filas) / 6.71 (cols) y el método de borde da
7.40–7.47 mm. ¿Puede un borde de pupila blando (erf, ancho w) producir esa diferencia, si cada método "lee" el radio en un
punto distinto del perfil del borde? ¿Cuál de los dos métodos recupera la verdad?

**Respuesta corta: no.** En la simulación, un borde blando baja la lectura de **los dos** métodos, en magnitudes parecidas
(≈ −0.04 mm de NA·z por cada 0.001 de w). No puede hacer que el borde lea *más* que el espectral. Con pupila dura, el método
de borde (a) recupera la verdad exactamente (6.98 / 7.42 contra 6.98 / 7.42, contando la corrección tan/sin). El
espectral, tal como está escrito, tiene un **sesgo de búsqueda** propio: lee 6.76 cuando la verdad es 6.965 y
**≈ 6.5 cuando la verdad es 7.40**, así que no distingue entre las dos verdades. Ese sesgo se va en la simulación
si la etapa 1 deja libre el radio. En los datos reales, el mismo arreglo sube solamente la columna (6.71 → 6.94); las
filas siguen en 7.01. **La diferencia real (≈ 6.97 contra 7.40–7.47) sigue sin explicación** y este borde blando no la
reproduce.

## Qué se simuló

- **Verdades.** A: z 99.5 mm, NA 0.070, λ 0.617 µm (NA·z 6.965 mm). B: NA 0.0744 (NA·z 7.403 mm). Eje corrido
  (+0.073, −0.028) pasos, como la estimación (a) del 03/11. Pitch 6 mm, s = 3538 px/paso (0.001696 mm/px).
- **Pupila.** Dura (w = 0) o `0.5·erfc((|f|λ − NA)/w)` con w = 0.002 / 0.004 / 0.008, que es la misma definición que
  `_pupila_blanda`. Para B se corrió w ≤ 0.004: **B con w = 0.008 se cortó para no pasarse del tiempo.**
- **Muestra.** Objeto de fase delgado: esferas polidispersas (d entre 3 y 7 µm, mediana 4.5), Δn 0.046, con 60 esferas por
  recorte de 400², más un fondo suave de 0.1 rad rms. Grilla fina ×3 (0.43 µm); la intensidad se binea 3×3 a píxeles de
  1.29 µm.
- **Modelo directo.** `E = IFFT[P(f + k)·FFT(o)]`: se corre la pupila, evaluada analíticamente, en vez de inclinar el
  objeto. Así la componente DC pasa con amplitud exacta P(k).
  - **Campo no telecéntrico:** el k es local, con u(p) = (d − eje)·6 mm − p·0.001696 mm y sinθ = u/√(u²+z²).
  - **Teselado:** el campo de 1120² se parte en bloques de 80 px (margen 40 px). Los bloques cerca del borde BF/DF de
    cada LED se subdividen en sub-bloques de 16 px, para que el borde en espacio imagen no quede escalonado.
  - **Recorte espectral:** filas 360:760, cols 80:480 del mismo campo, igual que el real. Se corrió también una variante
    con onda plana única.
- **Ruido.** var = 0.297·S + 7.1, con el BF central en p99.9 = 3000 cuentas, tope 4095 − 188 y redondeo. Hay 3 semillas;
  cada semilla cambia **la muestra y el ruido**.
- **Métodos, sin cambios.**
  - Espectral: `score`, `grid` y el preprocesado de `auditoria/paso_espectral_0311.py`, copiados textualmente. Lo único
    que cambia es la fuente de imágenes (flat = 1). Para validar la copia, sobre los datos reales `prep.npz` reproduce
    **6.972 / 6.714**.
  - Borde: `centrado.ajustar` (estimación (a)), importado del repo. La estimación (b) es una réplica línea a línea de
    `centrado.analizar`.

## Resultados (con ruido, media ± sd de 3 semillas; NA·z en mm)

| verdad NA·z | w verdad | espectral filas | espectral cols | radio espectral (NA) | borde (a) NA·z | borde (a) w px (→ NA) | borde (b) NA·z |
|---|---|---|---|---|---|---|---|
| 6.965 | 0 | 6.76 ± 0.08 | 6.75 ± 0.08 | 0.0696 | **6.98 ± 0.00** | 0 | 7.00 ± 0.05 |
| 6.965 | 0.002 | 6.74 ± 0.05 | 6.74 ± 0.06 | 0.0690 | 6.91 ± 0.00 | 41 (0.0007) | 6.92 ± 0.02 |
| 6.965 | 0.004 | 6.68 ± 0.04 | 6.69 ± 0.05 | 0.0689 | 6.82 ± 0.00 | 82 (0.0014) | 6.79 ± 0.01 |
| 6.965 | 0.008 | 6.61 ± 0.03 | 6.61 ± 0.03 | 0.0692 | 6.62 ± 0.00 | 157 (0.0027) | 6.54 ± 0.00 |
| 7.403 | 0 | **6.53 ± 0.12** | **6.54 ± 0.08** | 0.0718 | **7.42 ± 0.00** | 0 | 7.45 ± 0.08 |
| 7.403 | 0.002 | 6.47 ± 0.07 | 6.61 ± 0.02 | 0.0717 | 7.35 ± 0.00 | 41 (0.0007) | 7.34 ± 0.04 |
| 7.403 | 0.004 | 6.61 ± 0.17 | 6.53 ± 0.04 | 0.0718 | 7.26 ± 0.00 | 78 (0.0013) | 7.28 ± 0.00 |

Notas sobre la tabla:
- Con borde duro, el borde (a) debe dar R = z·tan(asin NA)/pitch, o sea NA·z 6.982 (A) y 7.421 (B). Lo da exactamente.
- La sd ≈ 0 del borde (a) entre semillas es real: el cociente bineado 16×16 casi no depende de la muestra.
- Las columnas "w px (→ NA)" son la escala **logística** del ajuste, pasada a NA con w_px·0.001696/z. No es el ancho erf
  (ver más abajo).
- La tabla completa, con la variante de onda plana y los resultados sin ruido, está en `resultados/tabla_resumen.md` y en
  `resultados/resumen.json`. La onda plana da lo mismo que el recorte no telecéntrico, dentro del error.

**Validación del pipeline (pupila dura, sin ruido).**
- Borde (a): recupera la verdad, 6.981 / 7.421, con w ajustado ≈ 0 px.
- Espectral: **no** la recupera. Sin ruido es todavía peor que con ruido: A da 6.61 y B da 6.28, y en un caso de
  diagnóstico llega a 4.8. El escalón de log|FFT| en el límite del soporte, sin piso de ruido, atrae la búsqueda.
- Esto es una propiedad del método, no de esta simulación.

## Por qué falla el espectral (diagnóstico, `diag_rb0.py`)

**Causa.**
- La etapa 1 busca el centro con el radio **fijo** en rb0 = 0.0669/0.63/df = 54.8 bins.
- Después de `keep` sobrevive casi solo el arco lejano. Si el radio verdadero es mayor que rb0, el centro se corre hacia
  afuera para dejar ese arco tangente por dentro.
- La etapa 2 solo deja mover el centro ±3 bins. El paso entre LEDs queda sobreestimado: 55 bins en lugar de 50.3 para B.

**Prueba.** Se repitió la búsqueda con la etapa 1 recorriendo también el radio (0.92–1.20·rb0). Este arreglo no usa la
verdad. Datos: semilla 0, con ruido.

| caso | verdad | original filas / cols | etapa 1 con radio libre filas / cols | radio libre rb (verdad) |
|---|---|---|---|---|
| A, w 0 | 6.965 | 6.68 / 6.81 | 6.99 / 7.07 | 59.6 (58.5) |
| A, w 0.002 | 6.965 | 6.80 / 6.81 | 6.81 / 6.85 | 58.1 (58.5) |
| A, w 0.004 | 6.965 | 6.72 / 6.75 | 6.72 / 6.75 | 57.9 (58.5) |
| A, w 0.008 | 6.965 | 6.63 / 6.65 | 6.63 / 6.64 | 58.1 (58.5) |
| B, w 0 | 7.403 | 6.54 / 6.60 | **7.38 / 7.35** | 62.1 (62.2) |
| B, w 0.002 | 7.403 | 6.53 / 6.59 | 7.18 / 7.17 | 61.3 (62.2) |
| B, w 0.004 | 7.403 | 6.48 / 6.54 | 7.12 / 7.08 | 61.1 (62.2) |
| **real 03/11** | ? | 6.97 / 6.71 | **7.01 / 6.94** | 58.8 |

- Con radio libre, el espectral recupera la verdad con pupila dura, con un error de ±0.1 en una sola semilla.
- Un borde blando lo baja: para w = 0.004, unos −0.25 a −0.3 mm. El radio sale un poco más chico y el paso un poco más
  grande.
- En los datos reales el arreglo **iguala filas y columnas** (6.94–7.01), pero **no** los sube a 7.4.

Además, `diag_espectral.py` muestra el mismo sesgo con un objeto de **amplitud** de espectro plano. Por lo tanto el sesgo
no se debe a que se anule la transferencia de fase en la lente donde se solapan los círculos ±k.

## Entregable 2: ¿una pupila dura "quiere crecer" para imitar una blanda? (`fit_duro.py`)

**Montaje.**
- Objeto verdadero conocido, recorte 400² con onda plana y verdad A.
- Se escanea el NA de una pupila dura (borde antialiasado de 1 bin ≈ 0.001 NA) con escala libre por imagen.
- Control: con verdad dura, el óptimo es 0.0701.

**Resultado.**
- Con w = 0.002 / 0.004 / 0.008, el NA duro óptimo es **0.0698–0.0700**: no crece, como mucho baja 0.0002. Eso vale para
  pérdida en intensidad y en amplitud, con y sin ruido, con los 5 BF solos o con 5 BF + 4 diagonales.
- Única excepción: pérdida en **amplitud con las 4 diagonales (DF) y w = 0.008**. Ahí el mínimo salta a 0.077
  (NA·z 7.68). Esa curva de desajuste es casi plana entre 0.067 y 0.082 (0.0006–0.0022 relativo) y sale un mínimo en
  otro lado; no es una tendencia robusta.
- Toda la curva es muy plana por arriba de 0.067. Con objeto conocido y pocos LEDs, los datos BF casi no fijan el radio
  duro una vez que pasa el DC.
- **No lo verifiqué:** qué hace un solver completo (objeto + pupila, 225 LEDs, held-out). Este ajuste no es una
  reconstrucción.

## Conclusiones

1. **¿Qué método se sesga con un borde blando?** Los dos, y hacia **abajo**.
   - Borde (a): ≈ −0.36·w·z en NA·z (−0.06 / −0.15 / −0.36 mm para w = 0.002 / 0.004 / 0.008). Es lo esperable: el
     escalón logístico se centra donde |P|² = ½, es decir en NA − 0.38·w.
   - Espectral, con la búsqueda corregida: algo más (≈ −0.25 a −0.3 mm para w = 0.004).
   - Por lo tanto, **un borde blando no puede producir que el borde lea 7.4 y el espectral 6.97** si la verdad es 6.965.
     Con verdad 7.4, un borde blando bajaría el borde (a) por debajo de 7.4, no por encima.
2. **¿Qué método recupera la verdad con pupila dura?** El de borde (a): es exacto y lineal (A 6.98, B 7.42). El espectral
   como está escrito no es lineal: con verdad 7.40 lee 6.5. Su valor 6.97/6.71 no sirve para discriminar 6.97 de 7.4
   **hasta que se corrija la etapa 1**. Con la corrección, en los datos reales da 6.94–7.01.
3. **¿Qué w devuelve el método de borde?** El w logístico ajustado escala ≈ 20 px por cada 0.001 de w erf (41 / 82 / 157 px
   para 0.002 / 0.004 / 0.008). El real, **222–253 px**, correspondería a w erf ≈ 0.011–0.012. Eso es casi el triple del
   0.0037 que se citaba, porque ese 0.0037 era la escala **logística** pasada a NA, no el ancho erf. Con un w así, el borde
   (a) leería ≈ 0.4 mm *menos* que la verdad, lo que agravaría la discrepancia.
4. **Lo que queda abierto.**
   - En los datos reales, el borde ancho (222 px) y el R grande (1.23–1.25 pasos) no salen de una pupila blanda de este
     tipo.
   - Hipótesis no probadas, que quedan como candidatas:
     - una fuente extendida (área emisora del LED de ~1–1.5 mm, que ensancha el borde sin correr el punto del 50 %);
     - luz DF en exceso, que levanta el cociente;
     - la escala s: el ajuste real con s libre daba 2950 en lugar de 3538 px/paso, y R en pasos depende de s.
5. **¿Qué radio usar para una pupila dura de solver que imite una blanda?** En este modelo simple, el **NA nominal (el
   punto del 50 % en amplitud)**, o 0.0002 menos. No hay evidencia robusta de que la pupila dura "quiera crecer". La
   preferencia del held-out por 7.3–7.55 no se explica con un borde blando de w ≤ 0.008 en esta simulación.

## Limitaciones explícitas

- **Objeto y fuente.** El objeto es delgado (sin espesor ni desenfoque). Los LEDs son puntuales y monocromáticos (sin
  ancho espectral ni área emisora). La iluminación es uniforme (sin cos⁴ ni 1/r²). No hay aberraciones ni viñeteo:
  la pupila es un círculo centrado y la no telecentricidad entra solo como corrimiento lineal de k con el campo.
- **El modelo de borde blando de la pupila es el de `_pupila_blanda` y nada más.** Un borde con otra forma (asimétrico,
  apodización tipo coseno, viñeteo del tubo) no se probó.
- **Semillas y casos cortados.**
  - Las semillas son 3 por caso en la tabla principal, pero **el diagnóstico de la búsqueda espectral es de una sola
    semilla**: los recortes guardados son solo los de la semilla 0. Su error no está medido; estimo ±0.1 por la
    dispersión del original.
  - No se corrió B con w = 0.008, por tiempo.
- **Sin flat y con exposición única.** No hay campo plano real (flat = 1). Todas las imágenes del anillo 1 tienen la misma
  exposición que el BF central, sin promedio de frames.
- **Entregable 2:** objeto conocido, 9 LEDs, un recorte. No es un solver.

## Archivos

- `codigo/sim_borde.py`: simulación y aplicación de ambos métodos; un trabajo por (verdad, w, semilla).
- `codigo/resumen.py`: tabla y figura.
- `codigo/fit_duro.py`: entregable 2.
- `codigo/diag_espectral.py`: sesgo espectral contra el tipo de objeto.
- `codigo/diag_rb0.py`: búsqueda con radio libre.
- `codigo/real_rb0.py`: la misma búsqueda sobre el `prep.npz` real; solo lectura.
- `resultados/`: `res_*_s*.json`, `resumen.json`, `tabla_resumen.md`, `fit_duro.json`, `diag_espectral.json`,
  `diag_rb0_*.json`, `real_rb0_0311.json`, `imgs_*_s0.npz` (imágenes con ruido de la semilla 0) y logs.
- `fig_sim_borde.png`: NA·z medido contra w verdadero, por método y por verdad.

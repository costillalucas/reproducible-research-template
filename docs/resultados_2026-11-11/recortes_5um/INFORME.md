# Recortes chicos alrededor de esferas de 5 µm aisladas (captura 2026-11-03-red) — 11/11

Mismo experimento que `plan_2026-11-11/recortes/` (perlas de 500 nm, agente hermano), pero con las esferas de 5 µm.
No se modificó el repo, el paquete ni la carpeta del hermano (solo se leyeron y copiaron sus scripts).

## 1. ¿El solver redondea los k del LED? Sí
`src/ptyco_full_simulator/spectral_ops.py:34-35`: `cx = int(round((fx_led - fx_axis[0]) / df_x))` (igual para `cy`). Cada ventana del LED
se centra en el bin HR **más cercano**. La pupila es binaria sobre la grilla LR (`optics.py:16-27`). Con la geometría B
(`codigo/redondeo.py` → `redondeo.json`; offset del centro de epocas_200):

| recorte | L (µm) | radio de la pupila (bins) | paso de LED (bins) | error de redondeo, mediana / máx. (% del paso) | máx. (% del radio de la pupila) | LEDs BF↔DF cambiados |
|---|---|---|---|---|---|---|
| 20 | 26 | 2.74 (21 px vs 23.6 continuo) | 2.40 | 17.7 / 28.5 | 25.1 | (17,16) BF→DF (|f| = 0.955 NA/λ) |
| 40 | 52 | 5.48 | 4.81 | 8.4 / 14.1 | 12.4 | ninguno |
| 80 | 103 | 10.95 | 9.62 | 4.1 / 7.1 | 6.2 | ninguno en el centro |
| 200 | 258 | 27.4 | 24.1 | 1.6 / 2.8 | 2.4 | ninguno |

Lo que importa: si un LED cambia de BF a DF depende del offset de cada recorte. Con el offset de cada esfera, en el **recorte de 20 px el
LED (17,16) cambia en las 18 esferas** (y además (16,15) en 6 y (18,15) en 1). En 80 px cambia (17,16) en 6 de 12. En 40 px no cambia ninguno.

## 2. Geometría, épocas y referencias
- La geometría B es la que trae el driver por defecto (sin Z_MM/NA_OBJ/LAM_NM): z 102 mm, NA 0.06686, λ 0.63 µm, factor 3 (píxel HR 0.43 µm).
  Solver A+init, paso 0.3 con rampa, **160 épocas** en todos los brazos, tanto en los recortes como en las referencias.
- **Se validó el envoltorio (`codigo/recortes.py`).** Al reconstruir con él el recorte de 200 px a 20 épocas, el objeto sale **idéntico bit a bit** a
  `epocas_200/snapshots/objeto_full_e020.npy` (diferencia máxima 0). Eso confirma la NA 0.06686 y el preprocesado.
- **Desvío de lo previsto: la referencia principal es el recorte de 400 px.** Se usa `plan_2026-11-04/epocas_400b`, snapshot e160 (filas 360:760, cols 80:480; mismo
  centro y misma geometría). El motivo es que dentro del recorte de 200 px solo hay **3** esferas que pasan el criterio de aislamiento.
  `epocas_200` e160 (r200) se mide para esas 3. Su `prep.npz` es idéntico píxel a píxel al de 400 px en el solape.
- **Nulo de referencia: `red_nulo_df`.** Es de 400 px, 160 épocas y geometría B, con los DF permutados (seed 0). Coincide exactamente con la referencia de 400 px.
- **Recortes chicos.** Son sub-arreglos del `prep.npz` de 400 px: mismos oscuros, flat, exposición y máscaras. `F.load_real` se aplica sobre el
  recorte y el offset del LED se recalcula para el centro de cada recorte. El nulo de 20 px usa la misma permutación.

## 3. Selección (`codigo/seleccionar.py`, `particulas.json`, `fig_seleccion.png`)
Se buscaron esferas sobre la imagen BF cruda del LED (17,15) / flat. Las 18 elegidas cumplen todos estos criterios:
- disco oscuro;
- ningún otro objeto a menos de 20 px (25.8 µm);
- a 20 px o más del borde del recorte de 400 px;
- sin dobletes ni grumos (área de 60 px o menos, razón de ejes menor que 1.4).

Las partículas son polidispersas. 4 esferas (S04, S10, S11, S13) tienen fase envuelta (|φ| > 2.8 rad) en r400 y quedan **fuera de las
métricas de fase** (n = 14).

## 4. Métricas (`codigo/medir.py` → `medidas.csv/json`; `codigo/resumen.py` → `resumen.txt/json`)
Todas se miden sobre la misma huella de 25.8 µm. Pasos:
1. Se quita la rampa lineal de fase de fuera de la esfera.
2. Se normaliza por la media compleja del anillo de 7.5 a 11 µm y se resta un plano.
3. FWHM: gaussiana 2D. BORDE: subida del 10 al 90 % del perfil radial. Volumen de fase: integral en r < 5 µm, en rad·µm².

**b400** es r400 pasado por la pupila coherente (NA/λ), es decir, la misma reconstrucción limitada a la banda de una sola imagen BF. Sirve de
línea de base "sin FPM" para la fase.

Medianas [p25, p75], en µm salvo que se indique otra unidad:

| brazo | FWHM fase | borde fase | pico fase (rad) | vol. fase | desplaz. vs r400 | std fase en el marco (rad) |
|---|---|---|---|---|---|---|
| r400 (ref.) | 3.19 [2.85, 3.53] | 1.82 [1.55, 1.91] | 1.39 | 18.1 [16.5, 22.2] | — | 0.06 |
| b400 (banda BF) | 6.96 [6.69, 7.07] | 4.32 [4.18, 4.42] | 0.59 | 24.3* | 0.26 | 0.03 |
| r200 (n = 2) | 3.70 | 2.16 | 1.53 | 28.3 | 0.06 | 0.07 |
| **r20** | 3.91 [3.52, 4.58] | 2.79 [2.46, 3.17] | 1.89 | **43.7** [40.9, 50.0] | **1.48** | **0.59** |
| r20 sin LEDs cambiados (r20sc) | 2.98 [2.76, 3.21] | 1.81 [1.65, 1.94] | 1.64 | 21.7 [20.4, 24.0] | 0.69 | 0.07 |
| r40 | 3.28 | 1.82 | 1.37 | 18.3 | 0.10 | 0.06 |
| r80 (n = 8) | 3.36 | 1.97 | 1.30 | 16.8 | 0.09 | 0.09 |
| nulo 400 | (3.54) | (1.63 [0.71, 1.83]) | 0.34 | 7.2 [6.3, 7.8] | 0.28 | 0.09 |
| nulo 20 | (6.84, n = 7) | (2.28) | 1.09 | 27.2 | 1.74 | 0.59 |

\* El volumen de b400 en r < 5 µm incluye el borde ensanchado; en r < 3.5 µm da 17.0, contra 18.3 de r400.

En la imagen LR (amplitud de la BF cruda) la FWHM es 7.46 [7.32, 7.85] y el borde 3.90 [3.79, 3.99].

Diferencias pareadas contra r400 (mediana [p25, p75]):
- **r20sc:** FWHM −0.21 [−0.32, −0.07] (menor en 12 de 14), borde +0.19 [−0.11, +0.40], volumen +3.1 [+1.3, +5.2] (mayor en 12 de 14).
- **r20:** borde +1.08 (mayor en 13 de 14), volumen +21.8 (mayor en 14 de 14).
- **r40:** FWHM +0.04, borde +0.13, volumen +0.4.
- **nulo 400:** volumen −11.2 (menor en 14 de 14).

### Residuo del modelo dentro de la huella (`codigo/residuos.py` → `residuos.json`)
R = ‖pred − I‖ / ‖I − ⟨I⟩‖ sobre los 225 LEDs. Es ajuste, no validación.
- r400: 0.64–1.05.
- r20: **1.7–5.2 (peor que predecir la media)**. Sigue en 1.7–5.2 aunque se evalúe sin el LED cambiado.
- r20sc: 0.51–0.97.
- r400 contra los datos del recorte de 20 px: 0.67–1.03.

Error final del solver:
- r20: 0.16–0.46.
- r20sc: 0.006–0.028.
- r40: 0.011–0.020.
- r80 con (17,16) cambiado: 0.06–0.11; r80 sin cambio: 0.012–0.016.

## 5. Artefactos (`fig_recortes_5um.png`: S06, S07, S10 [fase envuelta en r400], S14)
- **r20 y nulo 20 tienen la misma sierra de fase.** Es una rampa de ≈ 0.1 bin con un escalón de ≈ ±1 rad que cruza la huella, muchas veces
  a través de la esfera. La amplitud muestra una banda oscura a lo largo del escalón (std de la fase en el marco 0.59, contra 0.06 en r400).
  Como el nulo la reproduce, sale de la parte BF/geometría y no de la información DF.
- **La sierra desaparece al sacar los LEDs que cambian BF/DF (r20sc):** la rampa baja de ≈ 0.10 a ≈ 0.01 bin (`rampa.txt`).
- No se correlaciona de forma clara con el error de redondeo del LED central (`rampa.json`).
- No hubo salidas en blanco.
- En r80, los recortes con (17,16) cambiado muestran desvíos de volumen de −7 y −10 rad·µm² (S09, S14) y marco de 0.17–0.29 (S10, S12). Los
  que no tienen cambio quedan dentro de ±0.5 de r400.

## 6. Tiempos (1 núcleo, máquina compartida con carga ≈ 6)
- Recortes, por esfera a 160 épocas: 20 px ≈ 13 s (r20sc ≈ 8 s), 40 px ≈ 18 s, 80 px ≈ 27 s. Las 18 esferas a 20 px tardan 3.9 min.
- 200 px: 22 s cada 20 épocas, es decir ≈ 3 min a 160 épocas (extrapolado).
- Referencias existentes: el nulo de 400 px, 160 épocas, tardó 13.4 min (3 tareas en 3 núcleos).

## 7. Lectura y puntos que contradicen la expectativa
1. **El recorte de 20 px tal cual (r20) falla.** No reproduce la referencia: volumen de fase ×2.4, borde +1.1 µm, centro corrido 1.5 µm,
   sierra de fase y R > 1. El nulo de 20 px tiene el mismo artefacto.
   - En estos datos, la causa dominante medible es que **un LED BF cerca del borde de la pupila (0.955 NA/λ) pasa a DF por el redondeo**. Un
     error de redondeo "suave" del 18–28 % del paso no alcanza para explicarlo: sin esos LEDs, el mismo recorte de 20 px queda cerca de r400.
     El sesgo residual es FWHM −0.2 µm, volumen +3 rad·µm² (+17 %), pico +0.25 rad y centro corrido 0.7 µm.
2. **El dominio chico en sí, para una esfera de 5 µm, no se vio que domine.** r20sc tiene el marco limpio (0.07). La envoltura de borde que se temía no
   aparece cuando no hay LEDs cambiados. Lo que queda (+17 % de volumen y 0.7 µm de corrimiento) no está explicado.
3. **Expectativa "el borde se afila y la FWHM queda ≈ tamaño de la esfera": solo se cumple a medias.**
   - El borde sí se afila: 4.3 µm en b400 (banda BF) contra 1.8 µm en r400, en las 14 esferas.
   - Pero la FWHM de fase **también** baja, de 7.0 a 3.2 µm, y queda **por debajo** de lo que daría una esfera de 5 µm (≈ 4.3 µm para la
     proyección de la esfera). Puede ser polidispersidad, que el tamaño de 5 µm es solo nominal, o falla del modelo de objeto delgado. Eso no se resolvió acá.
4. **El borde 10–90 % no separa real de nulo por sí solo.** El nulo 400 da borde de fase 1.6 [0.7, 1.8] y de amplitud 0.8, iguales o
   menores que los reales, porque mide grano o ruido sobre un pico débil (0.34 rad). Lo que sí separa al nulo es el pico y el volumen de fase:
   7 contra 18 rad·µm², menor en 14 de 14.
5. Las métricas de amplitud de las reconstrucciones son texturadas e inestables (IQR grande); no se usan para conclusiones.

## Archivos
- `codigo/`: seleccionar, recortes (envoltorio), redondeo, medir, resumen, rampa, residuos(+_r20_sin), figura, correr.sh.
- Corridas: `runs/r20`, `runs/r20_nulo`, `runs/r20_sincambian`, `runs/r40`, `runs/r80`, `runs/validacion` (+ logs).
- Resultados: `particulas.json`, `redondeo.json`, `medidas.csv/json`, `resumen.txt/json`, `rampa.txt/json`, `residuos.json`, `fig_seleccion.png`, `fig_recortes_5um.png`.

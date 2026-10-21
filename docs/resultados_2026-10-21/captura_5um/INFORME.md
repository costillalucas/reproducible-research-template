# Captura roja 21/10: eje sobre el LED (17,15). QC, reconstrucción y comparación

Captura de Lucas del 21/10: `~/Documents/AleYLu/imagenes_tomadas/2026-10-21` (muestra), `-sinmuestra` (flat) y `-dark`.
Tiene 15x15 LEDs (filas 10–24, columnas 8–22) en Mono12, con un ROI de 1120 px re-centrado para que el eje óptico caiga
sobre el LED (17,15). Geometría: 2.5x, z = 102 mm, 1.290 µm/px, λ = 630 nm.

**Resumen.**
1. Los datos están completos, no hay píxeles saturados y el eje está centrado.
2. La reconstrucción (`rojo_final`, con offset total ≈ 0) pasa C1, C3 y C4 y falla C2, igual que todos los sets anteriores.
3. Centrar el eje sí arregla los LEDs de borde:
   - no queda ningún LED a horcajadas del borde de pupila, así que no hay que excluir ninguno;
   - la rampa global de fase baja a 0.004 rad p-p, contra 0.05–0.10 antes;
   - el held-out del anillo 1 baja de 0.86–0.90 a 0.75.
4. La calidad global no se puede comparar limpiamente con los otros sets. Este campo tiene entre 2 y 6 veces menos
   contraste de la muestra (en BF y en DF), así que el R held-out global (0.72) es peor que el de 28/09b (0.42) por
   SNR, no por la geometría.
5. La resolución en fase entre mitades queda entre la de 28/09b y la de m2 (16/10): 5.1 µm con FRC ≥ 1/7 y 3.0 µm
   sobre el nulo a la época 160.

## 1. QC (`inventario.py`, `qc.py` → `qc.json`, `figs/qc_mapas.png`, `figs/qc_flat_bf.png`)

- **Completitud:** 225/225 LEDs en la muestra y en el flat, 2 frames por LED, misma exposición en la muestra y en el flat.
- **Exposiciones (una por LED, no hay HDR):**
  - 5 ms: la cruz BF (16,15), (17,14), (17,15), (17,16), (18,15).
  - 128 ms: el anillo de 8 LEDs (15,15), (16,14), (16,16), (17,13), (17,17), (18,14), (18,16), (19,15).
  - 257 ms: los 212 restantes.
  - Las carpetas `10ms/` y `64ms/` de `organizado/red` están vacías.
- **`organizado/red/<t>ms/filaR_colC.tiff`:** es el promedio de los 2 frames redondeado a uint16. La diferencia máxima con
  (f1+f2)/2 es 0.5 cuentas. No es el frame 1. El pipeline usa los frames crudos.
- **Oscuro:** hay oscuros justo para las 3 exposiciones usadas (5, 128 y 257 ms), así que no hizo falta interpolar.
  - Niveles: 187.6 / 187.6 / 188.1 cuentas, prácticamente independientes de la exposición. σ de un frame ≈ 4.2 cuentas.
  - Se resta píxel a píxel el oscuro de la misma exposición, a la muestra y al flat.
- **Saturación:** ninguna. Máximo crudo 4044 en la muestra y 4079 en el flat.
- **BF a 5 ms:** la media sobre oscuro es 480–545 cuentas, el 16–18 % del rango. El máximo por LED llega a 30–60 %
  (1231–2469). Hay margen para unas 3 veces más de exposición en el BF.
- **Señal por anillo** (mediana, recorte central, cuentas sobre oscuro / SNR por píxel de un frame):

| anillo | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| cuentas | 545 | 409 | 35 | 22 | 13 | 8.2 | 5.5 | 3.9 | 2.8 |
| SNR/px | 43 | 39 | 8.4 | 5.2 | 3.1 | 2.0 | 1.3 | 0.9 | 0.7 |

  Los DF a 257 ms dan una mediana de 5.5 cuentas sobre oscuro. En m2 (16/10) eran 14.1.
- **Luz espuria en DF (flat):** es ~30 % de la señal de la muestra en los anillos 2–4 (0.045 frente a 0.149 cuentas/ms en
  el anillo 2). Es el mismo exceso de luz DF de siempre.
- **Flat BF (17,15):**
  - Viñeteo suave: las esquinas quedan al 1.01–1.09 del centro.
  - Dentro del recorte, el flat va de 0.83 a 1.08 de su media.
  - Centroide en (552, 557) px.
- **Polvo:** la "fibra" del borde derecho y el "grupo" de abajo al centro **están también en el flat**: es suciedad en otra
  superficie, no en la muestra. La fibra se mueve con el ángulo del LED, o sea que está fuera de foco. La división por el
  flat las saca casi del todo (en el BF queda un anillado residual de la fibra).
  - Hay además una **mancha negra nítida fija** en todos los LEDs en (600, 572) px, probablemente polvo en el sensor.
    Cae dentro del recorte central y se enmascaró: 1767 px, 1.1 %.
  - El grupo de esferas real de la muestra está en y ≈ 740, x ≈ 440–500 px. El recorte se subió 50 px para dejarlo fuera.
- **BF/DF:** solo la cruz de 5 LEDs es BF. Los 4 vecinos de (17,15) son BF en todo el frame de 1120. Las diagonales y
  todo lo demás son DF en el recorte. **No hay ningún LED a horcajadas.**
- **Centrado del eje con los arcos del flat:**
  - Con el eje sobre (17,15), los arcos BF/DF de los vecinos quedan apenas en el borde del frame de 1120 (a ~500 px del
    centro) y fuera del recorte de 400.
  - La caída en el borde opuesto a cada LED es simétrica: (18,15) arriba 0.70 frente a (16,15) abajo 0.73; (17,16)
    izquierda 0.68 frente a (17,14) derecha 0.62, en cociente con el flat de (17,15).
  - Con la pendiente medida del borde (~0.017 por 4 px), esa asimetría equivale a ≲ 6–12 px, es decir ≲ 0.003 pasos
    (≲ 0.02 mm). Coincide con la verificación del visionpoint (0.01–0.02 pasos).
  - Una medición más fina con este flat no es posible. El cruce del 50 % no existe dentro del frame y además el polvo
    contamina los perfiles. Por eso el cruce automático de `qc.json['eje']` (−0.047 pasos) **no es confiable**.
- **Ganancia:** el ajuste de transferencia fotónica del BF da 0.19 (28/09b y octubre: 0.25).

## 2. Reconstrucción (`prep_2110.py`, `r21_red/`, `runner_2110.py`, `run160.sh`)

- **Preprocesado:** es igual a `octubre_capturas_2026-10-21/prep_oct.py`, con estas diferencias:
  - S = (media de 2 frames − oscuro_t) / (t − 0.20 ms), y el flat igual.
  - Recorte filas 310:710, columnas 360:760.
  - Máscara = saturados ∪ polvo.
- **Solver y objetivo:** son los de 28/09b y octubre, copiados en `r21_red/fpm_red.py`:
  - en BF, S/F·⟨F⟩; en DF, S − gauss(F, 8);
  - método A+init, paso 0.3 con rampa.
- **Cambios en `fpm_red.py`:** `row_index_base=10`, BF = la cruz con (17,15) primero, `CENTER=(17,15)`.
- **Variante `rojo_centrado`:** es `rojo_final` (z 102, lrpx 1.29, NA 0.069·1.25/1.29 = 0.0669, factor 3) con estos cambios:
  - offset **total** en filas de +0.085 mm. El eje medido está sobre (17,15) e incluye el die rojo, porque los arcos se
    midieron con luz roja. Los 0.085 mm compensan los 50 px que se corrió el recorte, con el factor no telecéntrico
    3538 px/paso.
  - sin exclusiones.
- **Corridas:** 160 épocas para full, mitades (par/impar), mitades mezcladas (nulo) y 5 folds, con 3 procesos y ~50 min
  de reloj.
- **Mitades:** quedan asimétricas en BF, con 1 frente a 4 LEDs de la cruz (paridad r+c). En 28/09b eran 3 y 3.
- **Corridas de apoyo:**
  - Folds f3 y f4 de m2_red, 40 épocas (`run_m2folds.sh`). En `octubre_capturas` habían quedado cortados y faltaban para
    su C1. Se escribieron en `out/rojo_final/m2_red/`; no se tocó el directorio de octubre.
  - Control de offset en r21, folds a 40 épocas (`run_offset.sh`).

## 3. Comparación (C1–C4 con las mismas definiciones que `octubre_capturas_2026-10-21/eval/criterios_oct.py`)

Scripts en `eval/`: `cv_epocas.py`, `resolucion.py`, `criterios_2110.py`, `heldout_anillos.py` y `datos_cmp.py`.
m2_red (2026-10-16-muestra2) es el set de octubre que eligió y reconstruyó el agente de octubre.

| | 28/09b `rojo_final` | m2 16/10 `rojo_final` | **21/10 `rojo_centrado`** |
|---|---|---|---|
| eje / LEDs a horcajadas | fila 17.32 / 2 excluidos | 17.32 / 2 excluidos | **17.00 / ninguno** |
| C1 R held-out e40 (sin FPM) | 0.420 ± 0.007 (0.986) | 0.669 ± 0.005 (0.983) | 0.724 ± 0.004 (0.982) |
| C1 e160 | 0.374 | — (folds solo a 40) | 0.708 ± 0.005 |
| piso de ruido medio de esos LEDs | 0.050 | 0.095 | 0.219 |
| C2 FRC [2NA/λ, 0.45] e40 / e160 (umbral 0.143) | 0.085 / 0.120 falla | 0.023 / 0.041 falla | 0.029 / 0.044 falla |
| C3 lattice e160 (≤ 0.01) | 1.9e-3 pasa | 2.2e-4 (e40) pasa | 1.0e-4 pasa |
| C4 nuevas en ambas mitades (azar) e160 | 28 % (5.5 %) pasa | 40 % (7 %) e40 pasa | 39 % (8.5 %) pasa |
| FRC complejo ≥ 1/7, e160 | 3.55 µm | 12.8 µm | 5.06 µm |
| FRC complejo sobre el nulo, e160 | 1.6 µm | 8.8 µm | 3.0 µm |
| FRC de fase ≥ 1/7 / sobre el nulo | 3.7 / 3.3 µm | — / 8.8 µm | 5.4 / 4.3 µm |
| FRC entre los 2 BF crudos, k para FRC 1/7 (1/µm) | 0.139 | 0.164 | 0.091 |
| **rampa global de fase p-p, full e40 / e160** | 0.100 / 0.027 rad | 0.051 / 0.063 rad | **0.004 / 0.004 rad** |
| R held-out mediano, anillo 1 | 0.90 | 0.86 | **0.75** |

**Calidad de los datos, que es lo que explica la mayor parte de la diferencia** (`eval/datos_cmp.py`). Es la mediana del
contraste std(I) del objetivo DF por anillo:

| anillo | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|
| 21/10 | 0.29 | 0.15 | 0.08 | 0.05 | 0.03 |
| m2 | 1.05 | 0.41 | 0.21 | 0.13 | 0.08 |
| 28/09b | 1.31 | 0.94 | 0.62 | 0.34 | 0.17 |

En BF pasa lo mismo:
- la desviación del cociente muestra/flat es 0.079, contra 0.161 en m2 y 0.174 en 28/09b;
- la fracción de píxeles con cociente < 0.8 es 2 %, contra 8 % y 6 %;
- la señal DF de la muestra (S − F) es ~3 veces menor que en m2.

Este campo tiene menos esferas o esferas más chicas dentro del recorte. Por eso el piso de ruido del R es 2 a 4 veces más
alto, y el C1 y el C2 absolutos no se pueden comparar entre capturas.

**Control de centrado** (C1 a 40 épocas, offset total en filas):

| offset | −0.6 mm | +0.085 mm (centrado) | +0.6 mm | +1.06 mm (die rojo sumado otra vez) |
|---|---|---|---|---|
| C1 | 0.7244 ± 0.006 | 0.7236 ± 0.004 | 0.7243 ± 0.007 | 0.757 ± 0.009 |

Con +1.06 mm el held-out de los anillos 1–2 se rompe (R 1.00 y 0.94). Entre ±0.6 mm el held-out es plano: con el eje sobre
un LED no hay LEDs cerca del borde y C1 no distingue offsets chicos. El dato es coherente con el eje medido y descarta
volver a sumar el offset del die.

## 4. Lectura: ¿centrar el eje en un LED mejora?

- **Sí, en lo que dependía de la geometría:**
  - No hay LEDs a horcajadas: se entrenan los 225 sin excluir ninguno.
  - Desaparece la rampa global de fase: 0.004 rad contra 0.03–0.10. La rampa de los LEDs de borde está resuelta por
    diseño.
  - Los LEDs más cercanos al borde de pupila, que antes eran los peores del held-out, quedan mejor predichos: anillo 1
    0.75 contra 0.86–0.90.
  - El modelo deja de necesitar el ajuste fino del die: el offset es ≈ 0 y es plano en ±0.6 mm.
- **No, en la calidad global ni en la superresolución, por lo menos con este campo:**
  - C2 sigue lejos (0.044 frente a 0.143).
  - El R held-out global y la resolución son peores que en 28/09b. El campo es mucho menos contrastado y el FRC entre los
    2 BF crudos ya es peor (k 0.091 frente a 0.139), así que no se puede atribuir al centrado.
  - Contra m2, que es el set más parecido en SNR, 21/10 tiene un C1 similar (0.72 frente a 0.67, con un piso de ruido
    2.3 veces mayor), C2 igual, y bastante mejor resolución entre mitades (5.1 frente a 12.8 µm con FRC ≥ 1/7).
- **Para una comparación limpia hace falta el mismo campo**, o uno con densidad parecida a 28/09b, con y sin el eje
  centrado. También conviene subir la exposición del BF, que usa solo ~17 % del rango, y la de los DF lejanos (SNR < 1 a
  partir del anillo 7).

## Figuras

- `figs/qc_mapas.png`: señal en cuentas/ms y SNR por LED, en la muestra y en el flat.
- `figs/qc_flat_bf.png`: flats de la cruz BF, con el recorte marcado.
- `figs/recon_r21_vs_m2.png`: BF crudo, fase y amplitud (full, e160) en 100 µm centrales, 21/10 frente a m2.
- `figs/heldout_anillos.png`: R held-out por anillo con el piso de ruido (21/10, m2 y 28/09b), y el control de offset.

# Simulación: ¿el desvío del eje (H2) o el desenfoque de la muestra (H1) mueven el NA·z medido? (06/11)

**Pregunta.** El borde (a) da en rojo real 7.35 ± 0.16 (06/11, eje +0.078), 7.40 (03/11, eje +0.073), 7.16 (30/10-red-c,
eje +0.117) y 7.08 (30/10-red/red-b, eje −0.31, w ≈ 99 px). ¿Puede (H2) el desvío del eje respecto del LED central o (H1)
un desenfoque de la muestra producir esa dispersión de ≈ 2.6–4 % entre días, con la verdad fija?

**Respuesta corta.**
- **H2: no.** Con pupila dura, el borde (a) devuelve 7.370 (= z·tanθ de la verdad 7.35) para eje en filas 0 / +0.04 /
  +0.08 / +0.117 / −0.31, con diferencias ≤ 0.007 mm (0.1 %). El eje ajustado coincide con el verdadero a ±0.001 paso.
  La tendencia "más |eje| → menos NA·z" de los datos reales **no** sale de este estimador con este modelo.
- **H1: no para el borde.** Desenfoque de ±50 y ±100 µm: el borde (a) da 7.370 en todos los casos (cambio < 0.001 mm).
  **El espectral sí se mueve: sube ≈ +2–3 %** (7.33 → 7.48–7.59) en 5 de 6 desenfoques (−25 µm no cambia).
- **Combinación** eje +0.117 y −100 µm: borde (a) 7.370. **El 7.16 de red-c no se alcanza desde la verdad 7.35** con
  nada de lo simulado.
- Con eje −0.31, el **espectral falla** (filas 9.8 / 11.2): el LED (18,15) queda a 1.31 pasos del eje, fuera del círculo
  BF (R = 1.235 pasos), así que deja de ser BF y la búsqueda del círculo no tiene sentido para ese LED.

## Qué se simuló

- **Código.** Copia de `plan_2026-11-05/sim_borde/codigo/sim_borde.py` → `codigo/sim_eje_foco.py`. Los originales y el
  repo no se tocaron (`centrado` y `precaptura` se importan solo lectura).
  Cambios respecto del original:
  - eje y desenfoque son parámetros por trabajo;
  - espectral solo en modo **etapa 1 con radio libre** (= `espectral_zonas.py` / `diag_rb0` modo `etapa1_radio`; `score`
    y `grid` sin cambios);
  - se sacaron la variante de onda plana y el modo espectral original;
  - la estimación (b) quedó dentro de un `try`: con pupila dura su w diverge (OverflowError en `precaptura`) en algún
    caso. No es el foco; (a) no tuvo problemas.
- **Verdad.** z 99.5 mm, λ 0.617 µm, NA = 7.35/99.5 = 0.07387 (V). Chequeo con NA = 6.97/99.5 (A). Pupila **dura**.
  El borde (a) mide R = z·tanθ/pitch, así que su "verdad" es **7.370** (V) y **6.987** (A).
- **Eje.** Filas 0, +0.04, +0.08, +0.117, −0.31 paso; columnas −0.023 (medido) en todos.
- **Desenfoque.** Se multiplica la pupila corrida por `exp(i2πd[kz(f+k) − kz(k)])`, con kz = √(1/λ² − |f+k|²). Es el
  espectro angular del campo **inclinado** (por LED y por bloque, con el k local no telecéntrico); la fase constante
  kz(k) no cambia la intensidad. **Validación** (`codigo/chequeo_kernel.py`, `resultados/chequeo_kernel.txt`): da la
  misma intensidad que inclinar el objeto y propagar con `angular_spectrum_propagate` del repo
  (`src/ptyco_full_simulator/propagation.py`), con diferencia relativa ≤ 1e-6. El contraste del recorte cambia con d
  (0.080 a d = 0; 0.060 a +50; 0.103 a −100 µm), así que el desenfoque sí está actuando.
- **Muestra, ruido, teselado y recorte espectral:** idénticos a `sim_borde` (esferas de fase Δn 0.046, ruido de la
  cámara, BF central p99.9 = 3000 cuentas). **Una sola semilla (0)** por caso, por tiempo.

## Resultados (NA·z en mm, semilla 0, con ruido)

### H2: eje (sin desenfoque)

| verdad | eje filas | borde (a) NA·z (verdad tan 7.370 / 6.987) | eje (a) ajustado (filas, cols) | w (a) px | espectral filas / cols | rb bins (sd 5 LEDs) |
|---|---|---|---|---|---|---|
| 7.35 | 0.000 | 7.363 (sin ruido 7.345) | 0.000, −0.024 | 0.3 | 7.39 / 7.31 | 61.8 (1.6) |
| 7.35 | +0.040 | 7.370 | +0.040, −0.023 | 0 | 7.39 / 7.27 | 61.7 (1.8) |
| 7.35 | +0.080 | 7.370 | +0.080, −0.023 | 0 | 7.35 / 7.33 | 61.7 (1.8) |
| 7.35 | +0.117 | 7.370 | +0.117, −0.023 | 0 | 7.32 / 7.30 | 61.6 (2.0) |
| 7.35 | −0.310 | 7.370 | −0.310, −0.023 | 0 | **9.80** / 7.58 | 63.4 (3.3) |
| 6.97 | 0.000 | 6.986 | 0.000, −0.023 | 0.1 | 7.11 / 6.95 | 59.0 (1.1) |
| 6.97 | −0.310 | 6.987 | −0.310, −0.023 | 0 | **11.19** / 7.39 | 61.1 (4.5) |

- Radio espectral verdadero: 61.8 bins (V), 58.6 (A). Paso esperado: 50.4 bins.
- Con eje 0, la diferencia de 0.007 mm (7.363 contra 7.370) es la única que aparece. Sin ruido da 7.345. Es menor que la
  dispersión entre zonas del 06/11 (± 0.16).
- Eje −0.31: el centro ajustado del LED (18,15) cae en (29–42, 9–24) bins en vez de ≈ (66, 5). El paso en filas sale
  33–39 bins en vez de 50, y por eso NA·z filas se dispara. El real 30/10-red dio 7.93 / 7.33 con sd 5.9 %: el mismo
  tipo de falla, aunque de otra magnitud.

### H1: desenfoque (eje +0.08, −0.023)

| dz (µm) | borde (a) NA·z | w (a) px | espectral filas / cols | rb bins (sd) |
|---|---|---|---|---|
| −100 | 7.370 | 0 | 7.55 / 7.59 | 63.0 (0.3) |
| −50 | 7.370 | 0 | 7.48 / 7.49 | 62.7 (0.3) |
| −25 | 7.370 | 0 | 7.35 / 7.33 | 61.8 (1.5) |
| 0 | 7.370 | 0 | 7.35 / 7.33 | 61.7 (1.8) |
| +25 | 7.370 | 0 | 7.51 / 7.49 | 62.9 (0.5) |
| +50 | 7.370 | 0 | 7.52 / 7.50 | 62.9 (0.4) |
| +100 | 7.370 | 0 | 7.49 / 7.52 | 62.6 (0.9) |

- ±25 µm no es simétrico: +25 ya da +2 % (7.51 / 7.49), pero −25 da lo mismo que foco (7.35 / 7.33). Con una sola
  semilla, el espectral parece **saltar** entre dos soluciones (radio ≈ 61.7 contra ≈ 62.6–63.0 bins) más que variar suave.
  Leerlo como "el desenfoque puede subir el espectral ≈ 2 %", no como una curva calibrada.
- En el espectral el aumento viene del radio (61.7 → 62.6–63.0 bins, +1.5–2 %). El paso casi no cambia (≈ 50 bins).
  Con desenfoque, la sd del radio entre los 5 LEDs baja de ≈ 1.8 a 0.3–0.9 bins. Con una semilla no puedo separar
  cuánto de los +2 % es efecto y cuánto ruido de búsqueda (en `sim_borde` estimé ±0.1 mm por semilla). Lo que sí se ve:
  5 de los 6 desenfoques dan +0.14 a +0.26 mm, todos hacia arriba; ninguno da para abajo.
- **Efecto geométrico, no simulado:** si al reenfocar se mueve la muestra, z cambia en d, o sea NA·z cambia en
  d/z ≈ 0.1 % por cada 100 µm. Es despreciable.

### Combinación

| eje filas | dz | borde (a) | espectral filas / cols |
|---|---|---|---|
| +0.117 | 0 | 7.370 | 7.32 / 7.30 |
| +0.117 | −100 | 7.370 | 7.55 / 7.55 |
| +0.117 | +100 | 7.370 | 7.51 / 7.51 |

## Conclusiones (lo que dice la simulación, nada más)

1. **Borde (a).** Con pupila dura y LEDs puntuales, es insensible al eje (0 a −0.31 paso) y al desenfoque (hasta
   ±100 µm) a nivel de 0.1 %. **Ni H1 ni H2, solas o combinadas, pueden producir la dispersión real 7.08–7.40 (≈ 4 %)
   ni el 7.16 de red-c desde una verdad 7.35.** El w ajustado es siempre ≈ 0. El w real (220 px; 99 px con eje −0.31)
   tampoco sale de eje ni de desenfoque.
2. **Espectral.** El desenfoque lo sube ≈ 2–3 % (5 de 6 casos; −25 µm no cambia), de forma escalonada. Esa magnitud es comparable a la dispersión
   entre días, pero va **siempre hacia arriba**: no explica valores por debajo de la verdad. Con eje −0.31 el método no
   es aplicable a la cruz BF5, porque el LED (18,15) pasa a DF.
3. **Lo que sigue abierto.** La causa de la variación día a día del borde (a) tiene que estar en algo que este modelo no
   incluye. Candidatas ya listadas en `sim_borde`: fuente extendida, luz DF en exceso, la escala s, viñeteo o pupila no
   circular/no centrada. Una más: un cambio físico real de z o NA entre días (por ejemplo, la distancia
   panel–muestra). No la probé.

## Limitaciones

- Una semilla por caso. El borde (a) casi no depende de la semilla (sd ≈ 0 en `sim_borde`). El espectral sí: ±0.1 mm
  estimado, no medido acá.
- Pupila dura, LEDs puntuales y monocromáticos, objeto delgado, sin aberraciones. El desenfoque es una propagación del
  objeto delgado, no una muestra gruesa.
- Las columnas del eje quedaron fijas en −0.023. Las filas cubren los valores reales.

## Archivos

- `codigo/sim_eje_foco.py`: simulación. Uso: `python3 sim_eje_foco.py 4`; saltea los casos ya hechos.
- `codigo/chequeo_kernel.py`: validación del desenfoque contra el repo.
- `codigo/resumen.py`: arma `resultados/tabla_resumen.md` y `resultados/resumen.json`.
- `resultados/res_*_s0.json`: un archivo por caso. `log.txt` es la corrida; `log_fallo1.txt` es la primera corrida,
  que se cortó por el OverflowError de (b).

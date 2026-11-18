# Resultados 2026-11-17: matriz a z = 143,5 mm, centrado a la nueva altura, forma de la pupila y lote del 13/11

## 1. Nueva altura de la matriz de LEDs

- Medido con regla (marcas cada 1 mm): muestra 31,2 cm; matriz 16,9 / 16,8 cm en los dos bordes (ancho ~193 mm).
  **z = 143,5 mm** (± ~1,5 mm de lectura; falta lo que la regla no ve: cara de los chips y portaobjetos).
  Inclinación ~0,3°, igual a la resolución de la regla. Primer intento: 17,0 / 17,3 cm → 0,9°, corregido.
- A esta z: 9 LEDs de campo claro (centro, cruz y diagonales), anillo de 12 mm en campo oscuro.
- La matriz no se puede mover lateralmente: el LED (17,15) queda ~0,1 paso fuera del eje y se compensa con el ROI.

## 2. Cambios de código (z por captura)

- Script de captura (`code/ptyco-full-simulator/iluminacion_con_toma_de_imagene.py`): perilla `Z_MM`, guardada en
  `captura.json` como `z_mm`. El modo prueba agrega los **LEDs de borde** para esa z (a menos de 0,5 paso del borde
  del círculo de campo claro, radio ≈ z·0,074/6 mm): 8 ms los de adentro, 8 + 128 ms los de afuera.
- `scripts/grilla.py`: `z_mm(carpeta)`; 102 si la captura no lo tiene (todas las anteriores al 17/11).
- `scripts/precaptura.py`:
  - paso px/LED de partida 3538·102/z; lejos de z 102 se ajusta libre (`--ajustar-paso` automático);
  - radio de campo claro en pasos = z·NA_BORDE/6 mm, con NA_BORDE = 0,074 (medido hoy con los arcos: 1,77–1,79 pasos);
  - el centrado usa los LEDs de borde de esa z, no un 3×3 fijo; el método fino (simetría de pares) usa la cruz a esa distancia;
  - si no hay arcos, criterio de reserva: ningún LED de borde con un borde campo claro/oscuro cruzando el ROI;
  - el plan de exposición clasifica campo claro con el radio de esa z (antes las diagonales salían a 128 ms y saturaban);
  - `--z-mm` para tomas sin `z_mm`.
- `scripts/reconstruir.py`: z de la captura (o `--z-mm`); el corrimiento del LED por posición del recorte escala con z.
- Regresión: con z 102 (tomas viejas) el chequeo y la reconstrucción dan lo mismo que antes
  (`2026-11-13.a-prueba-1304`: desvío +0,015 / −0,010, OK).

## 3. Secuencia de centrado del 17/11

| toma | ROI | resultado |
|---|---|---|
| prueba 16:28 | 3968, 1966 | chequeo viejo (calibración z 102) sugirió 4960, 1234: **incorrecto** |
| prueba 16:32 | 4960, 1234 | LED (18,14) con arco: peor; se volvió a 3968, 1966 |
| prueba 16:59 | 3968, 1966 | "OK" **falso**: el criterio miraba solo el 3×3 (error mío, corregido) |
| completa 17:02 (`2026-11-17.1025ms`) | 3968, 1966 | arcos en (17,13) y (19,15): eje corrido (+0,12, −0,08) pasos |
| prueba 17:24 | 3968, 1966 | con LEDs de borde: (+0,087, −0,070) pasos → sugerido 4128, 1756 |
| prueba 17:30 / **17:32** | **4160, 1626** | **OK**: (+0,012, −0,010) pasos; radio 1,769 pasos |

Con el eje centrado, los 4 LEDs a 2 pasos muestran solo un resplandor de borde (3–5 cuentas/ms, ~8 % del campo claro)
en la franja de 80 px de su propio lado del ROI, simétrico (`centro_prueba_1732_OK.png`). Es el límite a esta z:
margen 0,21 paso contra medio ROI 0,27 paso. Para un ROI de 1120 px completamente limpio haría falta z ≈ 138,5 mm.
El recorte de 400 px de la reconstrucción está limpio.

`bordes_toma_1702.png`: cocientes de los 9 LEDs de campo claro (uniformes) y los 4 LEDs a 12 mm en la toma de 17:02
(arcos de (17,13) y (19,15)).

**Pendiente antes de reconstruir las tomas de hoy:** `reconstruir.py` ubica el eje con la calibración del 21/10
(ROI 4000, 1942). Con el ROI movido para compensar la matriz, eso daría un corrimiento falso (~0,7 mm). Hay que usar el
eje medido por el chequeo. También: flat nuevo con este ROI y esta z; el solver sigue fijo en 15×15
(`cargar_solver`, `default_setup(color, 15, ...)`), así que todavía no usa los 441 LEDs.

## 4. Forma de la pupila por zonas (`pupila/`)

LED del eje, 18 ms, 14 tomas rojas del 13/11 (distintos campos de la misma muestra), flat del mismo día; 3×3 teselas de
373 px; borde del disco en 36 direcciones; control = misma cadena sobre imágenes simuladas con pupila circular NA 0,070.

- Forma: desviación rms del círculo 2,1–3,5 px (real) contra 2,1–2,9 px (control); ruido de la media 1,5–2,4 px.
  **No se detecta forma no circular ni dependencia con la zona**; el método no ve menos de ~2–3 px (~5 % del radio).
- Radio: real 54,9 px contra 52,4 en el control, en todas las teselas → NA ≈ 0,073 (indicio; textura simulada ≠ real).
- Limitación: con el LED del eje la FFT es centrosimétrica y no ve un corte de un solo lado (ojo de gato).
  Siguiente: LEDs del primer anillo (discos separados) y los 5 de campo claro.

## 5. Lote del 13/11 (`lote_13-11/correr.sh`, salida en `AleYLu/reconstrucciones/lote_2026-11-13/`)

14 tomas rojas, flat del mismo día (`2026-11-13.fondo`), 160 épocas, `--validar`, vistas 15×15 (el solver no acepta
21×21). Terminado 17/11 19:28 (log: `lote.log` en la carpeta de salida):

| campo | C1 (mitades) | campo | C1 (mitades) |
|---|---|---|---|
| 13.a (1025 ms) | 0,645 | med6 | 0,657 |
| 13 (2048 ms, mismo campo) | 0,647 | med7 | 0,637 |
| med1 | 0,667 | med8 | 0,710 |
| med2 | 0,700 | med9 | 0,729 |
| med3 | 0,730 | med10 | 0,685 |
| med4 | 0,644 | med11 | 0,676 |
| med5 | 0,633 | zonarojo | 0,671 |

El 13/11, el mismo campo 13.a con el flat del 12/11 había dado 0,728–0,734: el flat del mismo día baja C1 ~0,08.
Repetibilidad en un mismo campo (13 contra 13.a): 0,002. Entre campos: 0,63–0,73 (media ~0,675): la dispersión
es de la muestra, no del sistema. Ningún campo baja de ~0,63.

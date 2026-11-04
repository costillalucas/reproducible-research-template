# Plan 2026-11-04 (1 h sin supervisión): A = C2 + nulo; B = test de centrado

> **CORRECCIONES DE LA AUDITORÍA** (`auditoria/AUDITORIA.md`); prevalecen sobre el texto de abajo.
> - "Fase ±0,15 rad / esferas fragmentadas": **incorrecto**. Era la barra de color del zoom. Medido con el método
>   de volumen de octubre: 62 partículas, pico mediano 1,97 rad, volumen 22,8 rad·µm² (teórico 31,9), d_vol 4,3 µm.
>   Las partículas solo se ven fragmentadas en amplitud.
> - El C2 0,120 de referencia es de la captura **28/09b** (consolidada el 20/10), no de una captura del 20/10.
> - El cruce de la FRC con el estimador de octubre es 2,35 µm (NA_ef 0,27), no 2,11. El cruce del nulo está en 0,110 µm⁻¹.
> - z 97,4 y la frontera de 7,04 mm venían de la 28/09b. En el 03/11 dan z 97,4 por filas y 93,8 por columnas,
>   y una frontera de 7,40–7,47 mm.
> - Las mitades son 1:4 en BF, con V_B/V_A = 0,61. C2 solo evalúa hasta NA ≈ 0,28.

Captura: `imagenes_tomadas/2026-11-03-red` (esferas 5 µm en DMSO, 15x15 LEDs, 2 frames/LED, ROI 3968,1966),
flat `2026-11-03-red-sinmuestra`, oscuros propios de muestra y de flat. No se tocó el repo.

## A. ¿Pasa C2 esta captura? Sí: 0,185 contra 0,008 del nulo

| corrida | carpeta | R ajuste | C1 mitades | C3 | **C2** [0,212; 0,45] µm⁻¹ | cruce FRC 1/7 |
| --- | --- | --- | --- | --- | --- | --- |
| real (NA 0,0669, z 102) | `reconstrucciones/2026-11-03-red_1311` | 0,369 | 0,592 (A 0,604 / B 0,581) | 3,0e-3 | **0,185** | k 0,473 µm⁻¹ → 2,11 µm, NA_ef 0,30 |
| nulo (DF permutado, seed 0) | `plan_2026-11-04/red_nulo_df` | — | 0,882 | 7,3e-2 | 0,008 | k 0,222 (= borde BF) |

- Recorte filas 360:760, columnas 80:480 (elección de Lucas: borde izquierdo, lejos del gancho y la mancha del flat).
- Figura: `fig_frc_real_vs_nulo.png`. La FRC real queda por encima de 1/7 en toda la banda C2 y cruza en k ≈ 0,47.
  El nulo cae a ~0,01 apenas sale del campo claro.
- Fase relativa entre mitades (espectro cruzado con Hann): ≈ 61–72° **constante** en todas las bandas
  (0,05–0,6 µm⁻¹), y lo mismo a baja k en el nulo (62°). Una constante es la ambigüedad de fase global de FPM
  y no es un problema. Es distinto del 03/11 (red-c), donde la fase relativa cambiaba con k (~20° a ~180°).
  Ojo: `frc` toma el |suma| por anillo, así que C2 es ciego a una rotación de fase uniforme por anillo.
- Como el nulo comparte todo el preprocesado (flat, oscuros, máscara) y da 0,008, el 0,185 **no** viene de
  artefactos comunes del preprocesado: depende de la geometría correcta de los LEDs de campo oscuro.

**Tu predicción (escrita antes de reconstruir):** "si el límite del 20/10 era el ruido → C2 > 1/7; si era el
modelo → C2 ≈ 0,12". El resultado cumple la rama "ruido". Antes de concluirlo, faltan controles, porque cambiaron
más cosas que la exposición:

- campo y recorte distintos del 20/10 (C2 0,120, nulo 0,007);
- eje recentrado desde el 21/10 (antes los LEDs del borde estaban mal);
- otra muestra o preparado (polidispersa; el 20/10 tenía tamaños de 1,2 a 21,5 µm).

**Consistente no es fiel.** En `2026-11-03-red_1311/reconstruccion.png` las esferas quedan como manchas
fragmentadas, no como discos. La fase reconstruida es de ±0,15 rad, contra ~2,5 rad esperados en el pico de una
esfera de 5 µm en DMSO (Δn 0,05). Además, el fondo tiene una textura diagonal cruzada. NA_ef 0,30 sigue por
debajo de la NA_sint (0,45 en el eje, 0,57 en la esquina).

**Preguntas abiertas (para Lucas, sin responder):**
1. ¿Qué control separa "más SNR" de "mejor centrado" como causa de la subida de C2 (0,120 → 0,185)? ¿Sirve
   reconstruir esta misma captura usando solo 1 de los 2 frames? ¿O agregarle ruido hasta igualar la SNR del 20/10?
2. Si las mitades coinciden (C2 0,185) pero las esferas no se ven como esferas, ¿qué parte del modelo falla?
   Pistas: objeto grueso o fuerte para la aproximación de objeto delgado (5 µm, fase ~2,5 rad); pupila; geometría.
3. ¿Cómo se ve la fase integrada (volumen de fase) de una esfera aislada contra la esperada para 5 µm en DMSO?

## B. Test de centrado: ninguno de los dos métodos del chequeo ajusta bien

Detalle completo: `centrado/tabla.md`, `centrado/fig_centrado.png` y scripts en `centrado/`. Fila del eje en pasos de LED:

| captura | (a) borde | (b) simetría | (a) solo cruz | simetría diagonales | monotonía (rango) |
| --- | --- | --- | --- | --- | --- |
| 21/10, 22/10 (rojo) | +0,07…+0,09 | +0,013 | +0,05 | +0,06 | 0,00…0,09 |
| 23/10 (rojo) | +0,091 | +0,006 | +0,034 | +0,052 | 0,015…0,11 |
| 30/10-c (rojo) | +0,117 | +0,027 | +0,054 | +0,044 | 0,015…0,11 |
| 03/11 (rojo) | +0,073 | +0,024 | −0,015 | +0,053 | 0,03…0,125 |
| 27/10, 29/10 (azul) | −0,116 | +0,03 | −0,08 | −0,045 | −0,14…−0,05 |

- En rojo, los métodos que dependen menos del modelo dan una fila del eje de ≈ +0,05. (a) queda por arriba y
  (b) por abajo. En azul, (b) tiene el **signo opuesto** a todos los demás.
- El sentido y la escala del corrimiento por falta de telecentricidad (0,158 pasos al borde, 0,224 a la esquina)
  se confirman: las esquinas de abajo quedan más cerca de la fila 18 en todas las capturas.
- **Corrección a lo que dije hoy:** con la columna propia de (a) (−0,028), los márgenes son 0,110 y 0,214. Ambos
  son < 0,224, así que (a) **también** predice que (16,14) cruza. No es cierto que "(a) explica la asimetría":
  el margen es tan justo que no discrimina.
- El modelo de borde está en duda. Las esquinas de las diagonales miden 0,20–0,28, pero con brillo igual (A = 1)
  ambos métodos predicen 0,4–0,8. El ajuste lo absorbe con amplitudes A por LED de 0,02 a 1,6. "Mixto" es solo la
  cola del borde blando: ninguna esquina supera 0,5.
- Circularidad (tu pregunta): si se deja un vecino afuera, (a) es estable. Pero si se ajusta solo con la cruz,
  (a) baja a −0,015…+0,06: su desvío grande lo ponen las diagonales. La prueba cruz → diagonales casi no tiene poder.
- En la práctica: +0,05 pasos ≈ 0,3 mm, y C1 es plano en ±0,6 mm. Para la reconstrucción no importa; para el
  protocolo, la tolerancia de 0,05 pasos está al límite.

## Archivos
`codigo/` (copia de `reconstruir_plan.py` y `comun_plan.py` del 03/11, más `c2_rojo.py`), `c2.json`,
`fig_frc_real_vs_nulo.png`, `red_nulo_df/` (~113 MB), `centrado/`.

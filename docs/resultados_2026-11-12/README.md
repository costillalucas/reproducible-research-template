# Resultados 12/11/2026 — cuatro campos en rojo a z ≈ 99.5 mm (línea de base antes de subir la matriz)

## Capturas
- Muestra: esferas de 5 µm en DMSO. Cuatro campos distintos (.a, .b, .c, .d): solo se movió la platina; misma muestra, mismo foco, misma altura.
- 15×15 LEDs, rojo, eje (17,15), ROI 3968,1966 1120×1120, exposiciones HDR 20/111/403/1025 ms, 2 frames.
- Flat: `2026-11-12-sinmuestra` (12:58, misma altura). Darks por captura.
- Datos crudos en `~/Documents/AleYLu/imagenes_tomadas/2026-11-12.{a,b,c,d}` (no versionados).

## Chequeo (`chequeo.sh`, carpeta `<set>/chequeo.txt`, `qc.png`, `centro.png`)
- Centrado OK en los cuatro (desvío 0.018–0.027 paso).
- Saturación despreciable en la muestra (≤ 5 LEDs, ≤ 0.008 % de píxeles); el **flat satura en el LED (18,14)** → bajar su exposición en el próximo flat.
- SNR de pico ≥ 3 en todos los anillos.

## Reconstrucción (`reconstruir.sh --validar`, 160 épocas, recorte de 400 px; `<set>/reconstruccion.png`, `resumen.txt`)
| set | C1 (mitades) | C3 lattice |
|---|---|---|
| a | 0.628 | 8.4e-3 OK |
| b | 0.630 | 4.2e-3 OK |
| c | 0.668 | 1.3e-2 FALLA |
| d | 0.680 | 5.4e-3 OK |

C2 no calculado.

## Artefacto central (`patron_centro.png`)
Mancha en la fase en el mismo píxel en los cuatro campos. Corresponde a una mota de polvo fija en el sistema: aparece con anillos de difracción en el flat del LED (17,15) y como sombra en el flat de un LED de campo oscuro (17,19), **sin desplazarse con el ángulo de iluminación**. El preprocesado la enmascara (1782 px, filas 217–282, columnas 201–251 del recorte), y el solver rellena esa zona sin restricción.
Pregunta abierta: dónde está la mota (no se mueve con el ángulo → cerca del plano imagen/sensor?). Limpiar antes de la captura a z ≈ 135 mm o usar `--recorte auto`.

## Contexto
Línea de base para el diseño de z ≈ 131–135 mm (LEDs diagonales del anillo 1 dentro de la pupila → 9 LEDs en campo claro; NA sintética × 0.84).

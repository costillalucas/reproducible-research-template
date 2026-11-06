# Resultados 2026-11-06

Respaldo de lo hecho el 06/11 sobre la diferencia de NA·z entre los dos métodos (espectral ≈ 7.0, borde (a) ≈ 7.4 en la
captura del 03/11). Se copiaron los archivos livianos (sin `.npy`/`.npz` ni los enlaces a imágenes). Los originales
están en `AleYLu/reconstrucciones/plan_2026-11-06/`. Imágenes nuevas: `AleYLu/imagenes_tomadas/2026-11-06-*`.

Métodos usados sin cambios:
- **Espectral:** `paso_espectral_0311.py`, con la etapa 1 de radio libre (arreglo del 05/11).
- **Borde (a):** `centrado.py`, con la escala s fija en 3538 y también libre.

NA·z está en mm, con NA·z = 6·R_pasos.

## 1. Experimento A: dos capturas, misma ROI, distinta muestra (`zonas/`)

Capturas: 30/10 red-c (PS 500 nm en aire) y 03/11 red (esferas de 5 µm en DMSO). ROI 3968,1966, recorte 360:760, 80:480.

| captura | espectral filas / cols | borde (a), s fijo |
|---|---|---|
| 03/11 | 7.01 / 6.94 | 7.40 |
| 30/10 red-c | 7.27 / 7.23 | 7.16 |

- Los dos métodos cambian más que la vara de ±2 %, y en sentidos opuestos.
- La brecha pasa de +0.43 a −0.09.
- No se puede separar el efecto de la muestra del de la captura: entre las dos cambian la muestra, el día y el foco.
- El par 30/10 red y red-b da la repetibilidad del borde: 0.06 %.

## 2. Captura 06/11: 6 zonas, 3×3 LEDs centrales (`zonas_3x3/`)

Condiciones de la captura:
- ROI 3968,1966, sin reenfocar entre zonas.
- Cruz a 18 ms y diagonales a 114 ms, 2 frames por LED.
- Zona a tomada dos veces seguidas (a.1 y a.2).
- Flat `2026-11-06-sinmuestra`.

Chequeos de calidad (`qc_captura/`):
- No hay saturación.
- La repetición a.1/a.2 correlaciona 0.97; las zonas entre sí, 0.02–0.06, así que son campos distintos.
- El contraste va de 0.055 a 0.091.

Comando: ver `zonas_3x3/README.md`. Resultado completo en `zonas_3x3/resultados/2026-11-06/zonas.md`.

| método | repetición a.1/a.2 | dispersión entre zonas |
|---|---|---|
| borde (a), s fijo | 0.00 % | **0.16 %** (7.34–7.37) |
| borde (a), s libre | 0.01 % | 0.33 % (s 3061 ± 0.8 %) |
| espectral | 0.01–0.4 % | **1–4 %** (≈ 6.75–8.04; la zona b es atípica) |

El borde no depende de la muestra; el espectral sí.

## 3. Simulación: eje y desenfoque (`sim_eje_foco/`)

Condiciones: pupila dura, z 99.5, λ 0.617, NA·z verdadero 7.35 (y un control con 6.97).

- **Borde (a):** queda fijo al 0.1 % con el eje entre 0 y −0.31 paso y con desenfoques de hasta ±100 µm. Ni el enfoque
  ni el eje explican la variación del borde entre días. El ancho w simulado da ≈ 0, contra 220 px en el real.
- **Espectral:** el desenfoque lo sube entre +2 y +3 %, en escalones. Con el eje en −0.31 no se puede aplicar, porque
  el LED (18,15) cae en campo oscuro; es la misma falla que en el real del 30/10.

## 4. Archivo: todas las capturas rojas (`archivo/`, figura `fig_archivo.png`)

| período | borde (a), s fijo | espectral (válido, sd entre LEDs < 4 %) |
|---|---|---|
| 21/10 – 30/10 (varios ROI) | 7.02 – 7.18 | 6.97 – 7.27 |
| 03/11 y 06/11 | **7.35 – 7.40** | 6.92 – 7.27 |

- **El borde salta** entre el 30/10 a las 13:36 y el 03/11; antes coincidía con el espectral dentro de ~2 %.
- Lo único que acompaña el salto es el eje en columnas, que pasa de ≈ 0 a ≈ −0.025 (r = −0.92, armado por ese grupo).
- La exposición no influye dentro de un mismo día.
- La s libre está poco constreñida: 2043–4043.
- El par enfocado/desenfocado del 28/09 no sirve, porque le faltan LEDs.

## Pendiente

Preguntas para Lucas:
- ¿Qué cambió en el laboratorio entre el 30/10 y el 03/11?
- ¿La muestra del 06/11 es el mismo preparado en DMSO del 03/11?

Hipótesis abierta, sin probar: el menisco de la gota actuando como una lente débil.

Script de captura: para tomar solo los 3×3 hay que poner `USAR_PLAN = False`, porque el plan pisa `FILAS`/`COLUMNAS`.
Ese cambio está en el repo `ptyco-full-simulator` y no se commiteó.

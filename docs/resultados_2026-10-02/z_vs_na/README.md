# z vs NA en la captura 28/09b (2026-10-02)

Pregunta: la frontera BF/DF fija R = z·tan(asin NA) ≈ 7.07 mm, degenerado entre (z≈101, NA 0.070) y (z=98, NA≈0.072). Se buscó una cantidad que dependa de z y no de NA: el paso angular entre LEDs vecinos, pitch/z.

Scripts (correr desde la raíz, CPU liviana): `paso_espectral.py` (~1.5 min, nice 19, usa `results/captura_2026-09-28b/<color>/prep.npz`, recorte de 400 px) -> `paso_espectral.json`; `resumen.py` -> `resumen.json`.
Método: FFT de las 6 imágenes BF más brillantes por color (corregidas por flat). Por LED se ajustan el centro **y el radio** del círculo de pupila con el score de borde de `docs/resultados_2026-10-01/geometria/independiente/medir.py`. El paso se mide entre (17,14), (17,15) y (17,16): los tres son BF completos y están en la misma fila, así que el offset del die (que va por filas) se cancela. Los LEDs a horcajadas (18,14/16) y el paso por filas dan centros inconsistentes (residuo 5-11 bins) y se descartaron.

## Lo que se mide y de qué depende

En bins del espectro (N = 400, dx = píxel en la muestra):
- paso s = (pitch/z)·N·dx/λ  -> mide **z/dx** (y depende de λ)
- radio rb = NA·N·dx/λ       -> mide **NA·dx**
- s/rb = pitch/(z·NA)         -> no depende de dx ni de λ, pero es **la misma combinación z·NA que la frontera**

Así que el paso entre LEDs **no rompe la degeneración por sí solo**. Cambia z/NA por z/dx: se necesita la escala absoluta en la muestra (el aumento). Lo mismo pasa con cualquier medida angular de esta captura. La frontera en los flats (círculos de radio R centrados en los LEDs, en mm) tampoco depende de z: sólo da R y el offset. La dependencia de k con la posición en el campo da z/dx², pero en 512 µm cambia unos 3-4 bins y no alcanza para medir al 3 %.

## Números (dx = 1.28 µm, es decir aumento 2.5x exacto)

| color | paso (bins) | z (mm) | NA (radio libre) | z·NA = pitch·rb/s (mm) |
|---|---|---|---|---|
| R 0.63 | 50.44 ± 0.44 | 96.5 ± 0.8 | 0.0727 | 7.03 ± 0.09 |
| G 0.53 | 61.96 ± 1.56 | 93.4 ± 2.4 | 0.0739 | 6.91 ± 0.18 |
| B 0.47 | 67.95 ± 0.88 | 96.0 ± 1.2 | 0.0726 | 6.98 ± 0.11 |

- **z = 96 ± 1 mm (estadístico) ± ~1.7 mm (dispersión entre colores)**, con dx = 1.28 µm. El ajuste Eckert previo (rojo, radio fijo, `docs/resultados_2026-10-01/geometria/eckert/eckert_crop400.json`) daba 94.1 ± 1.2 mm.
- El radio libre sale 3.7-5.6 % mayor que el nominal en los tres colores. Con dx = 1.28 µm eso implica NA ≈ 0.073.
- Hay chequeo de consistencia: z·NA desde el espectro (6.9-7.0 mm) coincide con el R de la frontera (7.07-7.12 mm) dentro de ~1-2 %, de forma independiente.
- Una λ efectiva distinta de la nominal (centroide del LED) mueve z en la misma proporción. Eso podría explicar parte de la dispersión del verde.

## ¿Se distinguen 98 y 101?

**No sin calibrar el aumento.** Con lo que hay:
- Con aumento 2.5x exacto, los datos dan z ≈ 96 mm y NA ≈ 0.073. Eso excluye z = 101 (unas 3σ incluyendo la dispersión de colores) y queda en tensión leve con el 98 ± 2 medido a mano.
- Con z = 98 (medido a mano), hace falta dx ≈ 1.30-1.34 µm, es decir aumento ≈ 2.40-2.46 (−2 a −4 %), y entonces NA ≈ 0.0715.
- Con z = 101, hace falta dx ≈ 1.34-1.38 µm, es decir aumento ≈ 2.32-2.39 (−4.5 a −7 %), y NA ≈ 0.070.

Un error de aumento del 3-5 % en un "2.5x" con lente de tubo es plausible, así que los datos no eligen entre 98 y 101. Lo que sí dicen es que las tres cantidades (z, NA, aumento) están atadas: z/dx ≈ 75 mm/µm (±2 %) y z·NA ≈ 7.0 mm.

**Medida que lo cierra:** una foto de un micrómetro de platina o de un USAF (aumento al 1 %) con el mismo objetivo. Con eso, z sale al ~1-2 % de este paso espectral y NA del radio. Alternativa: medir z con calibre en varios puntos.

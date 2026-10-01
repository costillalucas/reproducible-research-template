# Regla incorporada: diámetro lateral vs espesor desde la fase (captura 28/09b)

Script: `regla.py` (correr desde la raíz). Salidas: `dispersion_t_vs_d.png`, `histogramas.png`, `particulas.csv`, `resultados.json`.
Objetos: `results/captura_2026-09-28b/<color>/out/obj_real_A+init_z98.0_full.npy` (rojo 1200 px, 0.427 µm/px; verde/azul 2000 px, 0.256 µm/px), borde de 16 µm descartado.

## Método
1. Fase: se divide el campo por su versión suavizada (σ = 12 µm, campo complejo unitario) para quitar franjas/inclinación de fondo; `skimage.restoration.unwrap_phase`; polinomio de orden 2 ajustado en el fondo (como `make_fig_fase_2809b.quitar_fondo`), segunda pasada con las partículas enmascaradas. Sin la demodulación, el desenrollado global del rojo falla (ruido de fondo 1.3 rad; con ella 0.16 rad). Verde 0.05 rad, azul 0.03 rad.
2. Segmentación: fase suavizada (σ = 1 µm) > max(0.3 rad, 5·ruido) (rojo: 0.8 rad), componentes conexas; se descartan las que tocan el borde, d < 1 µm, y cúmulos (elongación > 2 o área/elipse-de-momentos < 0.6). Fase pico = percentil 95 adentro − mediana de un anillo de 2 µm.
3. Desenrollado dudoso: se re-desenrolla solo el recorte de la partícula; si difiere > 1 rad del global, o el anillo tiene σ > 1 rad, se descarta.
4. t = φλ/(2πΔn), Δn(λ) = 0.045 + 0.0015/λ² (`results/sim_multiespectral_2026-09-29/sim.py:29,39-40`; hipótesis del modelo, «del orden de poliamida en DMSO», no medida): Δn = 0.0488 / 0.0503 / 0.0518 (R/G/B).

## Resultados
| color | candidatas | cúmulos | desenr. dudoso | N | mediana t/d (p25–p75) | Pearson / Spearman | t/d por d: 1–3 / 3–6 / >6 µm |
|---|---|---|---|---|---|---|---|
| rojo | 101 | 9 | 13 (13 %) | 82 | 1.24 (0.74–1.64) | 0.80 / 0.68 | 1.33 / 1.23 / 1.13 |
| verde | 169 | 52 | 16 (9 %) | 104 | 0.65 (0.43–1.13) | 0.89 / 0.61 | 0.73 / 0.48 / 0.45 |
| azul | 168 | 22 | 7 (4 %) | 139 | 0.52 (0.34–0.88) | 0.87 / 0.59 | 0.70 / 0.37 / 0.41 |

Cociente de fases entre colores (mismas partículas por centroide, < 2 µm, tras los corrimientos de `comparar_colores.json`):
- φ_G/φ_R: mediana 0.70 (0.57–0.88), N = 23; esperado 1.23 (1.19 sin dispersión).
- φ_B/φ_R: mediana 0.70 (0.54–0.85), N = 50; esperado 1.42 (1.34 sin dispersión).
- 24 partículas presentes en los tres colores (d ≈ 7–8 µm): t/d = 0.77 (R), 0.37 (G), 0.33 (B).

## Lectura
- Espesor y diámetro están correlacionados (Pearson 0.8–0.9), así que la fase sí mide algo de la partícula, pero la regla no cierra: en verde y azul el espesor es ~0.4–0.5 del diámetro en partículas > 3 µm; en rojo el cociente está cerca de 1 pero con mucha dispersión.
- El cociente entre colores va al revés de lo esperado: el rojo da más fase que verde y azul (0.70 en vez de 1.2–1.4). Con un mismo objeto y Δn casi constante eso no es físico: la escala de fase de las reconstrucciones no es la misma entre colores (o el Δn de la simulación no vale). La regla falla de forma distinta en cada canal, por lo que hoy no sirve para fijar Δn ni z.

## Advertencias
- Formas irregulares y polidispersas: una partícula aplanada da t/d < 1 sin error de fase.
- Resolución lateral ~1 µm: el diámetro de las partículas chicas está inflado; el umbral alto del rojo (0.8 rad ≈ 1.6 µm) selecciona partículas chicas de fase alta y sesga su t/d hacia arriba.
- Objeto delgado: para d ≳ 5 µm y φ de varios rad la aproximación de proyección falla y la reconstrucción FPM tiende a subestimar la fase de partículas grandes (frecuencias bajas mal recuperadas); la demodulación con σ = 12 µm también achica la fase de partículas > ~10 µm.
- Δn es el valor supuesto de la simulación; un error en Δn escala t/d pero no explica el cociente entre colores.

## Volumen de fase (seguimiento)
La simulación con la misma geometría del verde (`../sim_esferas/INFORME.md`) muestra que el pico de fase se sobreestima (+20–35 % para 5–10 µm), mientras que el volumen de fase se recupera dentro de 0.98–1.10 para d ≥ 5 µm. Por eso se rehízo la regla con V_φ = Σ(φ − fondo del anillo)·área de píxel sobre la máscara de la partícula, y d_vol = (6 V_φ λ / (2π Δn π))^(1/3). El Δn es el mismo de antes (sim.py:29,39-40). Script: `regla_volumen.py`; figura: `regla_volumen.png`; números: `resultados_volumen.json`.

| color | N (d ≥ 5 µm) | mediana d_vol/d (p25–p75) | Pearson |
|---|---|---|---|
| rojo | 36 | 0.93 (0.86–1.01) | 0.96 |
| verde | 35 | 0.69 (0.61–0.87) | 0.99 |
| azul | 61 | 0.65 (0.61–0.83) | 0.98 |

Cociente de V_φ en las mismas partículas con d ≥ 5 µm:
- V_G/V_R = 0.81 (0.57–1.04), N = 18; esperado 1.23.
- V_B/V_R = 1.04 (0.77–1.27), N = 23; esperado 1.42.

El rojo se acerca a la esfera (d_vol/d ≈ 0.93). Verde y azul quedan en ≈ 0.67, es decir ≈ 0.3 de la fase esperada. La inversión entre colores sobrevive con el volumen, aunque más débil: G/R baja de 1.23 a 0.81 y B/R de 1.42 a 1.04. Un Δn erróneo escala los tres colores juntos y no explica esto: la escala de fase difiere entre las reconstrucciones.

Advertencias propias del volumen: la máscara es la región sobre el umbral (0.8 rad en rojo, 0.3 en verde y azul), así que se pierde la cola de fase por debajo, más en rojo. La demodulación con σ = 12 µm resta algo de volumen en partículas grandes. La calibración del volumen viene de una simulación con la geometría del verde, no del rojo ni del azul.

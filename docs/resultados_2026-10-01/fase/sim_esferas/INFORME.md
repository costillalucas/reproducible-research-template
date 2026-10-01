# Calibración de fase con esferas simuladas (2026-10-01)

**Montaje:** verde 530 nm, 2.5x NA 0.07, 15×15 LEDs, z = 98 mm (geometría 28/09 b, `results/captura_2026-09-28b/green/fpm_red.py`), campo 128 µm (100 px LR, factor 5, 0.256 µm/px HR).
**Modelo directo y solver:** los del repo, sin cambios: `fpm_red.predict` y `fpm_red.reconstruct` con A+init (`init="fourier_avg"`, paso 0.3, 40 y 400 épocas). El ruido es el de `results/sim_multiespectral_2026-09-29/sim.py`: brillo por LED igualado al de la captura real y ruido gaussiano con la varianza medida en cada LED.
**Muestra:** esferas de fase pura (amplitud 1) de 1, 2, 3, 5, 7 y 10 µm, separadas al menos 40 µm. Δn = 0.045 + 0.0015/λ² = 0.0503, tomado de `results/sim_multiespectral_2026-09-29/sim.py:30` (descrito ahí como "del orden de poliamida en DMSO"; no hay un valor medido en el repo). La fase pico verdadera es (2π/λ)·Δn·d: va de 0.60 rad (1 µm) a 5.97 rad (10 µm).
**Procesamiento de la fase:** igual que en `report/informe/make_fig_fase_2809b.py` (unwrap_phase, resta de un polinomio de orden 2 y de la mediana). Además, se resta un fondo local: la mediana de un anillo entre R+4 y R+8 µm.
**Métricas:** el pico es el máximo dentro del disco de radio R. El volumen es la integral de la fase en un disco de radio R+3 µm. El diámetro aparente se calcula a partir del área por encima de la mitad del pico.
Scripts: `sim.py` y `analisis.py`. Salidas: `resultados.json`, `curva_calibracion.png` y `mapas_fase.png`.

## Resultados: recuperado / verdadero (pico | volumen | diámetro aparente, µm)

| d (µm) | sin ruido, 40 ép. | sin ruido, 400 ép. | con ruido, 40 ép. | con ruido, 400 ép. |
|---|---|---|---|---|
| 1  | 2.32 / 1.09 / 0.9 | 2.18 / 0.90 / 0.9 | 1.89 / −0.01 / 0.9 | 1.99 / 0.53 / 0.9 |
| 2  | 1.81 / 1.42 / 1.7 | 1.68 / 1.13 / 1.7 | 1.88 / 1.53 / 1.7 | 1.69 / 1.20 / 1.7 |
| 3  | 1.39 / 1.45 / 2.6 | 1.33 / 1.26 / 2.6 | 1.38 / 1.49 / 2.6 | 1.32 / 1.24 / 2.5 |
| 5  | 1.21 / 1.12 / 4.4 | 1.21 / 1.11 / 4.4 | 1.21 / 1.09 / 4.4 | 1.21 / 1.10 / 4.4 |
| 7  | 1.18 / 1.07 / 6.0 | 1.16 / 1.03 / 5.9 | 1.18 / 1.08 / 6.0 | 1.17 / 1.05 / 5.9 |
| 10 | 1.28 / 1.01 / 7.7 | 1.23 / 0.98 / 7.9 | 1.75 / 1.02 / 5.3 | 1.35 / 0.98 / 7.3 |

Control: la verdad muestreada en la misma grilla da un pico de 0.94 a 1.00 y un volumen de 1.00 a 1.05.

## Lectura

- El solver no pierde fase: la **sobreestima**. El pico sale entre +20 y +30 % alto para 5 a 10 µm, ×1.3 a 1.4 para 3 µm y ×1.7 a 2.2 para 1 a 2 µm. Además aparece amplitud espuria (×1.5 a 3) sobre las esferas, aunque son de fase pura: hay cruce entre fase y amplitud. Pasar de 40 a 400 épocas apenas lo corrige.
- **El volumen de fase (fase integrada) es la medida confiable** para d ≥ 5 µm: da entre 0.98 y 1.11. Para 2 a 3 µm sale +13 a 50 % alto. Para 1 µm, el ruido lo vuelve inutilizable (entre −0.01 y 1.09).
- El diámetro a media altura subestima el real entre un 10 y un 25 % (un efecto del perfil esférico, no del solver).
- Con ruido y 40 épocas, la esfera de 10 µm muestra un punto caliente central (pico ×1.75): un artefacto de desenrollado o convergencia. Hay que desconfiar de los picos aislados en las partículas grandes.
- **Para los datos reales:** una partícula real de 10 µm mostraría alrededor del 125 % de su pico de fase verdadero y cerca del 100 % de su volumen de fase. Para estimar Δn·tamaño conviene usar la fase integrada, no el pico.

## Límites

El simulador es de objeto delgado (una sola transmitancia, sin propagación dentro de la esfera ni dispersión múltiple). Esto mide solo los límites de banda y del algoritmo, no los efectos de muestra gruesa, que para 10 µm a Δn = 0.05 no son despreciables. Hay un solo campo y una sola semilla de ruido, y no hay errores de geometría (z, posición de los LEDs) ni el desajuste del modelo de la captura real (flat, luz parásita en campo oscuro). Por eso es una cota optimista del error.
